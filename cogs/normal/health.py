"""Runtime health checks with deduplicated administrator alerts."""
from __future__ import annotations

import asyncio
import logging
import os
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands, tasks

logger = logging.getLogger(__name__)
DEFAULT_INTERVAL = 60
DEFAULT_FAILURE_THRESHOLD = 2


@dataclass(slots=True)
class CheckResult:
    name: str
    ok: bool | None
    detail: str
    latency_ms: int | None = None


def parse_ids(value: str | None) -> set[int]:
    ids: set[int] = set()
    for part in (value or "").split(","):
        try:
            parsed = int(part.strip())
        except (TypeError, ValueError):
            continue
        if parsed > 0:
            ids.add(parsed)
    return ids


def positive_int(name: str, default: int, minimum: int = 1) -> int:
    try:
        value = int(os.getenv(name, str(default)))
        return value if value >= minimum else default
    except (TypeError, ValueError):
        return default


def sqlite_check_sync(database_path: str) -> str:
    path = Path(database_path)
    if not path.is_file():
        raise FileNotFoundError(f"SQLite database file is missing: {path.name}")
    connection = sqlite3.connect(f"file:{path.resolve()}?mode=ro", uri=True, timeout=3)
    try:
        row = connection.execute("PRAGMA quick_check").fetchone()
        if not row or row[0] != "ok":
            raise sqlite3.DatabaseError("SQLite quick_check did not return ok")
        connection.execute("SELECT 1").fetchone()
        return "SQLite quick_check: ok"
    finally:
        connection.close()


def safe_supabase_url(raw_url: str) -> str:
    parsed = urlsplit(raw_url.strip())
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError("SUPABASE_URL must be a valid HTTPS project URL")
    if parsed.query or parsed.fragment:
        raise ValueError("SUPABASE_URL must not contain a query or fragment")
    return raw_url.strip().rstrip("/")


class HealthCog(commands.Cog):
    """Checks gateway, local database and optional Supabase connectivity."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.interval = positive_int("HEALTH_CHECK_INTERVAL_SECONDS", DEFAULT_INTERVAL, 30)
        self.failure_threshold = positive_int(
            "HEALTH_FAILURE_THRESHOLD", DEFAULT_FAILURE_THRESHOLD, 1
        )
        self.alert_channel_id = self._read_optional_id("HEALTH_ALERT_CHANNEL_ID")
        self.admin_ids = parse_ids(os.getenv("HEALTH_ADMIN_USER_IDS"))
        developer_id = self._read_optional_id("DEVELOPER_ID")
        if developer_id:
            self.admin_ids.add(developer_id)
        self.session: aiohttp.ClientSession | None = None
        self.failure_counts: dict[str, int] = {}
        self.alerted: set[str] = set()
        self.last_results: list[CheckResult] = []
        self.alert_lock = asyncio.Lock()

    @staticmethod
    def _read_optional_id(name: str) -> int | None:
        try:
            value = int(os.getenv(name, "").strip())
            return value if value > 0 else None
        except (TypeError, ValueError):
            return None

    async def cog_load(self) -> None:
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=5)
        )
        if not self.monitor_loop.is_running():
            self.monitor_loop.change_interval(seconds=self.interval)
            self.monitor_loop.start()

    async def cog_unload(self) -> None:
        self.monitor_loop.cancel()
        if self.session and not self.session.closed:
            await self.session.close()

    async def check_gateway(self) -> CheckResult:
        if not self.bot.is_ready():
            return CheckResult("Discord Gateway", False, "Bot is not ready")
        latency = self.bot.latency
        if latency is None or latency < 0:
            return CheckResult("Discord Gateway", False, "Gateway latency unavailable")
        return CheckResult("Discord Gateway", True, "Connected", round(latency * 1000))

    async def check_sqlite(self) -> CheckResult:
        path = os.getenv("USER_DATA_DB", "data/user_data.sqlite3")
        started = time.perf_counter()
        try:
            detail = await asyncio.to_thread(sqlite_check_sync, path)
        except (OSError, sqlite3.Error, ValueError) as error:
            return CheckResult("SQLite", False, type(error).__name__)
        return CheckResult("SQLite", True, detail, round((time.perf_counter() - started) * 1000))

    async def check_supabase(self) -> CheckResult:
        raw_url = os.getenv("SUPABASE_URL", "").strip()
        service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
        if not raw_url and not service_key:
            return CheckResult("Supabase", None, "Not configured")
        if not raw_url or not service_key:
            return CheckResult("Supabase", False, "Configuration is incomplete")
        try:
            base_url = safe_supabase_url(raw_url)
        except ValueError as error:
            return CheckResult("Supabase", False, str(error))

        assert self.session is not None
        started = time.perf_counter()
        endpoint = f"{base_url}/rest/v1/ops_heartbeat?select=key&limit=1"
        headers = {"apikey": service_key, "Authorization": f"Bearer {service_key}"}
        try:
            async with self.session.get(endpoint, headers=headers) as response:
                if response.status >= 400:
                    return CheckResult("Supabase", False, f"HTTP {response.status}")
                await response.read()
        except (aiohttp.ClientError, asyncio.TimeoutError) as error:
            return CheckResult("Supabase", False, type(error).__name__)
        return CheckResult(
            "Supabase", True, "Heartbeat table reachable",
            round((time.perf_counter() - started) * 1000),
        )

    async def run_checks(self) -> list[CheckResult]:
        checks = await asyncio.gather(
            self.check_gateway(), self.check_sqlite(), self.check_supabase(),
            return_exceptions=True,
        )
        results: list[CheckResult] = []
        for name, result in zip(("Discord Gateway", "SQLite", "Supabase"), checks):
            if isinstance(result, BaseException):
                logger.error("Health check %s raised %s", name, type(result).__name__)
                results.append(CheckResult(name, False, type(result).__name__))
            else:
                results.append(result)
        self.last_results = results
        return results

    async def notify_admins(self, title: str, description: str, recovered: bool = False) -> bool:
        color = discord.Color.green() if recovered else discord.Color.red()
        embed = discord.Embed(title=title, description=description[:4000], color=color)
        embed.timestamp = discord.utils.utcnow()
        embed.set_footer(text="gakuseiBOT health monitor")
        delivered = False
        if self.alert_channel_id:
            try:
                channel = self.bot.get_channel(self.alert_channel_id)
                if channel is None:
                    channel = await self.bot.fetch_channel(self.alert_channel_id)
                if hasattr(channel, "send"):
                    await channel.send(
                        embed=embed, allowed_mentions=discord.AllowedMentions.none()
                    )
                    delivered = True
            except Exception:
                logger.exception("Could not send health alert to configured channel")
        for user_id in sorted(self.admin_ids):
            try:
                user = self.bot.get_user(user_id) or await self.bot.fetch_user(user_id)
                await user.send(embed=embed, allowed_mentions=discord.AllowedMentions.none())
                delivered = True
            except Exception:
                logger.warning("Could not deliver health alert to administrator ID %s", user_id, exc_info=True)
        if not delivered:
            logger.error(
                "Health alert could not be delivered; configure HEALTH_ALERT_CHANNEL_ID "
                "or HEALTH_ADMIN_USER_IDS."
            )
        return delivered

    async def process_results(self, results: list[CheckResult]) -> None:
        async with self.alert_lock:
            for result in results:
                if result.ok is None:
                    continue
                if result.ok:
                    self.failure_counts[result.name] = 0
                    if result.name in self.alerted:
                        delivered = await self.notify_admins(
                            f"✅ {result.name} recovered",
                            f"**{result.name}** is healthy again.\n{result.detail}",
                            recovered=True,
                        )
                        if delivered:
                            self.alerted.remove(result.name)
                    continue
                failures = self.failure_counts.get(result.name, 0) + 1
                self.failure_counts[result.name] = failures
                if failures >= self.failure_threshold and result.name not in self.alerted:
                    delivered = await self.notify_admins(
                        f"🚨 {result.name} health check failed",
                        f"**Component:** {result.name}\n"
                        f"**Consecutive failures:** {failures}\n"
                        f"**Reason:** {result.detail}\n"
                        "同じ障害の通知は復旧するまで抑制されます。",
                    )
                    if delivered:
                        self.alerted.add(result.name)

    @tasks.loop(seconds=DEFAULT_INTERVAL)
    async def monitor_loop(self) -> None:
        try:
            await self.process_results(await self.run_checks())
        except Exception:
            # A notification or transient runtime error must not permanently stop monitoring.
            logger.exception("Health monitoring cycle failed; the next cycle will retry.")

    @monitor_loop.before_loop
    async def before_monitor_loop(self) -> None:
        await self.bot.wait_until_ready()

    @monitor_loop.error
    async def monitor_loop_error(self, error: Exception) -> None:
        logger.error("Health monitor loop stopped unexpectedly", exc_info=error)

    @app_commands.command(name="health", description="管理者向けにBotとDBの状態を確認します")
    async def health(self, interaction: discord.Interaction) -> None:
        if interaction.user.id not in self.admin_ids:
            await interaction.response.send_message(
                "このコマンドは管理者のみ使用できます。", ephemeral=True
            )
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        results = await self.run_checks()
        lines = []
        for result in results:
            marker = "🟢" if result.ok is True else "🔴" if result.ok is False else "⚪"
            latency = f" · {result.latency_ms} ms" if result.latency_ms is not None else ""
            lines.append(f"{marker} **{result.name}** — {result.detail}{latency}")
        embed = discord.Embed(
            title="システムヘルスチェック",
            description="\n".join(lines),
            color=discord.Color.green() if all(r.ok is not False for r in results) else discord.Color.orange(),
        )
        embed.set_footer(
            text=f"監視間隔: {self.interval} 秒 · 異常通知: {self.failure_threshold} 回連続"
        )
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(HealthCog(bot))

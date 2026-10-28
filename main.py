from __future__ import annotations

import asyncio
import io
import json
import os
import time
from pathlib import Path
from typing import Any

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

# Load .env before reading any configuration. Existing environment variables win.
load_dotenv(Path(os.getenv("ENV_FILE", ".env")), override=False)

PREFIX = os.getenv("PREFIX", "/").strip() or "/"
def _read_heavy_threshold() -> float:
    try:
        value = float(os.getenv("HEAVY_THRESHOLD", "1.5"))
        return value if value > 0 else 1.5
    except ValueError:
        print("Warning: HEAVY_THRESHOLD must be a positive number; using 1.5 seconds.")
        return 1.5


HEAVY_THRESHOLD = _read_heavy_threshold()
HEAVY_COGS_PATH = Path(os.getenv("HEAVY_COGS_PATH", "data/heavy_cogs.json"))


def _read_optional_id(name: str) -> int | None:
    value = os.getenv(name, "").strip()
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        print(f"Warning: {name} must be an integer; related feature is disabled.")
        return None


REPORT_CHANNEL_ID = _read_optional_id("REPORT_CHANNEL_ID")

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents)

# Used by the admin Cog to display/clear extension load failures.
bot.load_failures = {}
bot.skipped_cogs = set()

status_list = [
    discord.Game("動作中..."),
    discord.Game("コマンドを待機中"),
    discord.Game("ヘルプを確認中"),
    discord.Game("ダッシュボードを確認中"),
]

log_buffer = io.StringIO()
_status_index = 0
_cogs_loaded = False
_commands_synced = False
_startup_reported = False
_observer: Observer | None = None


def log_print(*args: Any, **kwargs: Any) -> None:
    """Print to the console and retain a copy for the optional startup report."""
    print(*args, **kwargs)
    buffer_kwargs = {key: value for key, value in kwargs.items() if key != "file"}
    print(*args, **buffer_kwargs, file=log_buffer, flush=True)


def load_heavy_cog_list() -> list[str]:
    """Return the configured list, recovering safely from a missing/broken file."""
    if not HEAVY_COGS_PATH.exists():
        return []
    try:
        with HEAVY_COGS_PATH.open("r", encoding="utf-8") as file:
            value = json.load(file)
    except (OSError, json.JSONDecodeError) as error:
        log_print(f"[Warning] Could not read {HEAVY_COGS_PATH}: {error}")
        return []

    if not isinstance(value, list) or not all(
        isinstance(item, str) for item in value
    ):
        log_print(f"[Warning] {HEAVY_COGS_PATH} must contain a JSON array of strings.")
        return []
    return value


def save_heavy_cog_list(cog_list: list[str]) -> None:
    """Persist the heavy Cog list, creating the data directory when needed."""
    HEAVY_COGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with HEAVY_COGS_PATH.open("w", encoding="utf-8") as file:
        json.dump(cog_list, file, indent=2, ensure_ascii=False)


async def load_all_cogs() -> None:
    heavy_cogs = set(load_heavy_cog_list())
    cog_root = Path("cogs")
    if not cog_root.is_dir():
        log_print("[Warning] cogs/ directory was not found; no Cogs were loaded.")
        return

    for file_path in sorted(cog_root.rglob("*.py")):
        if (
            file_path.name == "__init__.py"
            or file_path.stem.startswith("test_")
            or file_path.stem.endswith("_test")
            or "tests" in file_path.parts
        ):
            continue

        cog_module = ".".join(file_path.with_suffix("").parts)
        cog_name = file_path.stem
        if cog_name in heavy_cogs or cog_module in heavy_cogs:
            bot.skipped_cogs.add(cog_module)
            log_print(f"[Skip] Marked heavy cog: {cog_module}")
            continue

        await load_cog_with_timing(cog_module)


async def load_cog_with_timing(cog_module: str) -> None:
    start = time.perf_counter()
    try:
        try:
            await bot.load_extension(cog_module)
            action = "Load"
        except commands.ExtensionAlreadyLoaded:
            await bot.reload_extension(cog_module)
            action = "Reload"

        elapsed = time.perf_counter() - start
        bot.load_failures.pop(cog_module, None)
        bot.skipped_cogs.discard(cog_module)
        log_print(f"[{action}] {cog_module} completed in {elapsed:.2f}s")
        if elapsed > HEAVY_THRESHOLD:
            log_print(
                f"[Warning] {cog_module} took {elapsed:.2f}s "
                f"(threshold: {HEAVY_THRESHOLD:.2f}s)"
            )
    except Exception as error:
        bot.load_failures[cog_module] = str(error)
        log_print(f"[Error] Failed to load/reload {cog_module}: {error}")


class CogChangeHandler(FileSystemEventHandler):
    def __init__(self, loop: asyncio.AbstractEventLoop):
        self.loop = loop

    def _schedule_reload(self, event: Any) -> None:
        if event.is_directory:
            return

        path = Path(event.src_path)
        if path.suffix != ".py" or path.name == "__init__.py":
            return

        try:
            relative_path = path.resolve().relative_to(Path.cwd().resolve())
        except (OSError, ValueError):
            return

        if (
            not relative_path.parts
            or relative_path.parts[0] != "cogs"
            or "tests" in relative_path.parts
            or relative_path.stem.startswith("test_")
            or relative_path.stem.endswith("_test")
        ):
            return

        cog_module = ".".join(relative_path.with_suffix("").parts)
        log_print(f"[Watchdog] Change detected in {cog_module}")
        asyncio.run_coroutine_threadsafe(
            load_cog_with_timing(cog_module),
            self.loop,
        )

    def on_modified(self, event: Any) -> None:
        self._schedule_reload(event)

    def on_created(self, event: Any) -> None:
        self._schedule_reload(event)


def start_watching(loop: asyncio.AbstractEventLoop) -> None:
    """Start one watcher at most, even when Discord reconnects."""
    global _observer

    if _observer is not None and _observer.is_alive():
        return
    if not Path("cogs").is_dir():
        log_print("[Warning] Watchdog was not started because cogs/ is missing.")
        return

    try:
        observer = Observer()
        observer.schedule(CogChangeHandler(loop), path="cogs", recursive=True)
        observer.start()
        _observer = observer
        log_print("[Watchdog] Cog folder monitoring started.")
    except Exception as error:
        log_print(f"[Warning] Could not start Cog watcher: {error}")


@tasks.loop(seconds=300)
async def change_status() -> None:
    global _status_index

    if not status_list:
        return
    await bot.change_presence(activity=status_list[_status_index])
    _status_index = (_status_index + 1) % len(status_list)


@change_status.before_loop
async def before_change_status() -> None:
    await bot.wait_until_ready()


async def send_startup_report() -> None:
    if REPORT_CHANNEL_ID is None:
        return

    try:
        channel = bot.get_channel(REPORT_CHANNEL_ID)
        if channel is None:
            channel = await bot.fetch_channel(REPORT_CHANNEL_ID)
    except (discord.NotFound, discord.Forbidden, discord.HTTPException) as error:
        log_print(f"[Warning] Could not access startup report channel: {error}")
        return

    if not isinstance(channel, (discord.TextChannel, discord.Thread)):
        log_print("[Warning] REPORT_CHANNEL_ID is not a text channel or thread.")
        return

    content = log_buffer.getvalue().strip() or "起動ログはありません。"
    chunk_size = 3900
    for offset in range(0, len(content), chunk_size):
        embed = discord.Embed(
            title="BOT 起動ログ",
            description=f"```\n{content[offset:offset + chunk_size]}\n```",
            color=discord.Color.green(),
        )
        try:
            await channel.send(embed=embed)
        except (discord.Forbidden, discord.HTTPException) as error:
            log_print(f"[Warning] Could not send startup report: {error}")
            return


@bot.event
async def on_ready() -> None:
    global _cogs_loaded, _commands_synced, _startup_reported

    log_print(f"Logged in as {bot.user} (ID: {bot.user.id})")

    # on_ready can run more than once after a gateway reconnect.
    if not _cogs_loaded:
        await load_all_cogs()
        _cogs_loaded = True

    if not _commands_synced:
        try:
            synced = await bot.tree.sync()
            log_print(f"[OK] Synced {len(synced)} slash commands")
            _commands_synced = True
        except Exception as error:
            log_print(f"[Error] Slash command sync failed: {error}")

    start_watching(asyncio.get_running_loop())
    if not change_status.is_running():
        change_status.start()

    if not _startup_reported:
        await send_startup_report()
        _startup_reported = True


if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN", "").strip()
    if not token or token == "your_discord_bot_token_here":
        raise SystemExit(
            "DISCORD_TOKEN is missing. Set it in the environment or in a .env file."
        )
    bot.run(token)

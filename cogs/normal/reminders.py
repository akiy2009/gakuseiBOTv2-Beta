"""Persistent, owner-scoped Discord reminders.

Delivery is at-least-once: reminders are leased before delivery and retried after
transient failures. A process crash after Discord accepts a DM but before the
database records success can result in a duplicate DM.
"""
from __future__ import annotations

import asyncio
import logging
import os
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import discord
from discord import app_commands
from discord.ext import commands, tasks

logger = logging.getLogger(__name__)
_JST = ZoneInfo("Asia/Tokyo")
_MAX_REMINDERS = 100
_MAX_MESSAGE_LENGTH = 1000
_LEASE_SECONDS = 120


class ReminderError(ValueError):
    """A reminder operation that can be corrected by the user."""


def parse_due_at(value: str) -> datetime:
    """Parse YYYY-MM-DD HH:MM as JST and return an aware UTC datetime."""
    try:
        local = datetime.strptime(value.strip(), "%Y-%m-%d %H:%M").replace(tzinfo=_JST)
    except ValueError as error:
        raise ReminderError("日時は YYYY-MM-DD HH:MM 形式で入力してください（日本時間）。") from error
    due_at = local.astimezone(timezone.utc)
    now = datetime.now(timezone.utc)
    if due_at <= now:
        raise ReminderError("過去の日時は指定できません。")
    if due_at > now + timedelta(days=365):
        raise ReminderError("登録できるのは現在から1年以内です。")
    return due_at


class ReminderStore:
    """SQLite-backed reminder store with per-user ownership and delivery leases."""

    def __init__(self, database_path: str | Path = "data/user_data.sqlite3"):
        self.database_path = Path(database_path)

    def _connect(self) -> sqlite3.Connection:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.database_path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA busy_timeout = 10000")
        return db

    def initialize(self) -> None:
        with closing(self._connect()) as db:
            db.execute("PRAGMA journal_mode = WAL")
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    message TEXT NOT NULL,
                    due_at TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending'
                        CHECK(status IN ('pending', 'sending', 'sent', 'cancelled', 'failed', 'completed')),
                    attempts INTEGER NOT NULL DEFAULT 0,
                    lease_until TEXT,
                    created_at TEXT NOT NULL,
                    sent_at TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_reminders_due
                    ON reminders(status, due_at);
                CREATE INDEX IF NOT EXISTS idx_reminders_owner
                    ON reminders(user_id, status, due_at);
                """
            )
            db.commit()

    @staticmethod
    def _iso(value: datetime) -> str:
        return value.astimezone(timezone.utc).isoformat(timespec="seconds")

    def add(self, user_id: int, message: str, due_at: datetime) -> int:
        message = message.strip()
        if not message or len(message) > _MAX_MESSAGE_LENGTH:
            raise ReminderError(f"内容は1〜{_MAX_MESSAGE_LENGTH}文字で入力してください。")
        if due_at.tzinfo is None:
            raise ReminderError("日時にはタイムゾーン情報が必要です。")
        due_utc = due_at.astimezone(timezone.utc)
        if due_utc <= datetime.now(timezone.utc):
            raise ReminderError("過去の日時は指定できません。")
        with closing(self._connect()) as db:
            db.execute("BEGIN IMMEDIATE")
            count = db.execute(
                "SELECT COUNT(*) FROM reminders WHERE user_id = ? AND status IN ('pending', 'sending')",
                (user_id,),
            ).fetchone()[0]
            if count >= _MAX_REMINDERS:
                db.rollback()
                raise ReminderError(f"未完了のリマインダーは最大{_MAX_REMINDERS}件です。")
            cursor = db.execute(
                """INSERT INTO reminders(user_id, message, due_at, created_at)
                   VALUES (?, ?, ?, ?)""",
                (user_id, message, self._iso(due_utc), self._iso(datetime.now(timezone.utc))),
            )
            db.commit()
            return int(cursor.lastrowid)

    def list_for_user(self, user_id: int) -> list[sqlite3.Row]:
        with closing(self._connect()) as db:
            return list(db.execute(
                """SELECT id, message, due_at, status FROM reminders
                   WHERE user_id = ? AND status IN ('pending', 'sending', 'failed')
                   ORDER BY due_at LIMIT 100""",
                (user_id,),
            ))

    def cancel(self, user_id: int, reminder_id: int) -> bool:
        with closing(self._connect()) as db:
            cursor = db.execute(
                """UPDATE reminders SET status = 'cancelled', lease_until = NULL
                   WHERE id = ? AND user_id = ? AND status IN ('pending', 'sending', 'failed')""",
                (reminder_id, user_id),
            )
            db.commit()
            return cursor.rowcount == 1

    def complete(self, user_id: int, reminder_id: int) -> bool:
        with closing(self._connect()) as db:
            cursor = db.execute(
                """UPDATE reminders SET status = 'completed', lease_until = NULL
                   WHERE id = ? AND user_id = ? AND status IN ('pending', 'sending', 'failed')""",
                (reminder_id, user_id),
            )
            db.commit()
            return cursor.rowcount == 1

    def snooze(self, user_id: int, reminder_id: int, minutes: int) -> bool:
        if not 1 <= minutes <= 10080:
            raise ReminderError("延長時間は1〜10080分で指定してください。")
        due_at = self._iso(datetime.now(timezone.utc) + timedelta(minutes=minutes))
        with closing(self._connect()) as db:
            cursor = db.execute(
                """UPDATE reminders SET due_at = ?, status = 'pending',
                   lease_until = NULL, attempts = 0
                   WHERE id = ? AND user_id = ? AND status IN ('pending', 'sending', 'failed')""",
                (due_at, reminder_id, user_id),
            )
            db.commit()
            return cursor.rowcount == 1

    def claim_due(self, now: datetime | None = None, limit: int = 20) -> list[sqlite3.Row]:
        now = now or datetime.now(timezone.utc)
        now_iso = self._iso(now)
        lease_iso = self._iso(now + timedelta(seconds=_LEASE_SECONDS))
        with closing(self._connect()) as db:
            db.execute("BEGIN IMMEDIATE")
            # Recover work abandoned by a process that stopped while holding a lease.
            db.execute(
                """UPDATE reminders SET status = 'pending', lease_until = NULL
                   WHERE status = 'sending' AND lease_until <= ?""",
                (now_iso,),
            )
            rows = list(db.execute(
                """SELECT id, user_id, message, due_at, attempts FROM reminders
                   WHERE status = 'pending' AND due_at <= ?
                   ORDER BY due_at, id LIMIT ?""",
                (now_iso, limit),
            ))
            if rows:
                ids = [row["id"] for row in rows]
                placeholders = ",".join("?" for _ in ids)
                db.execute(
                    f"""UPDATE reminders SET status = 'sending', lease_until = ?,
                        attempts = attempts + 1 WHERE id IN ({placeholders})
                        AND status = 'pending'""",
                    (lease_iso, *ids),
                )
            db.commit()
            return rows

    def mark_sent(self, reminder_id: int) -> None:
        with closing(self._connect()) as db:
            db.execute(
                """UPDATE reminders SET status = 'sent', sent_at = ?, lease_until = NULL
                   WHERE id = ? AND status = 'sending'""",
                (self._iso(datetime.now(timezone.utc)), reminder_id),
            )
            db.commit()

    def mark_failed(self, reminder_id: int) -> None:
        with closing(self._connect()) as db:
            db.execute(
                """UPDATE reminders SET status = 'failed', lease_until = NULL
                   WHERE id = ? AND status = 'sending'""",
                (reminder_id,),
            )
            db.commit()

    def retry_later(self, reminder_id: int, attempts: int) -> None:
        delay = min(3600, 30 * (2 ** min(max(attempts - 1, 0), 7)))
        due_at = self._iso(datetime.now(timezone.utc) + timedelta(seconds=delay))
        with closing(self._connect()) as db:
            db.execute(
                """UPDATE reminders SET status = 'pending', due_at = ?, lease_until = NULL
                   WHERE id = ? AND status = 'sending'""",
                (due_at, reminder_id),
            )
            db.commit()


class ReminderCog(commands.Cog):
    """Persistent personal reminder commands and background delivery."""

    remind = app_commands.Group(name="remind", description="自分用のリマインダーを管理します")

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.store = ReminderStore(os.getenv("USER_DATA_DB", "data/user_data.sqlite3"))

    async def cog_load(self) -> None:
        await asyncio.to_thread(self.store.initialize)
        if not self.delivery_loop.is_running():
            self.delivery_loop.start()

    def cog_unload(self) -> None:
        self.delivery_loop.cancel()

    @tasks.loop(seconds=30)
    async def delivery_loop(self) -> None:
        rows = await asyncio.to_thread(self.store.claim_due)
        for row in rows:
            reminder_id = int(row["id"])
            try:
                user = self.bot.get_user(int(row["user_id"]))
                if user is None:
                    user = await self.bot.fetch_user(int(row["user_id"]))
                embed = discord.Embed(
                    title="⏰ リマインダー",
                    description=discord.utils.escape_mentions(str(row["message"])),
                    color=discord.Color.blurple(),
                )
                embed.add_field(name="予定日時", value=row["due_at"], inline=False)
                embed.set_footer(text=f"リマインダー ID: {reminder_id}")
                await user.send(embed=embed, allowed_mentions=discord.AllowedMentions.none())
            except discord.Forbidden:
                logger.info("Reminder %s could not be delivered: user DMs are unavailable.", reminder_id)
                await asyncio.to_thread(self.store.mark_failed, reminder_id)
            except (discord.HTTPException, OSError):
                logger.exception("Transient delivery failure for reminder %s", reminder_id)
                await asyncio.to_thread(
                    self.store.retry_later, reminder_id, int(row["attempts"]) + 1
                )
            else:
                await asyncio.to_thread(self.store.mark_sent, reminder_id)

    @delivery_loop.before_loop
    async def before_delivery_loop(self) -> None:
        await self.bot.wait_until_ready()

    @remind.command(name="add", description="指定した日時に自分へDMで通知します")
    @app_commands.describe(
        when="日本時間 YYYY-MM-DD HH:MM（例: 2026-11-12 18:30）",
        message="通知する内容",
    )
    async def add(self, interaction: discord.Interaction, when: str, message: str) -> None:
        try:
            due_at = parse_due_at(when)
            reminder_id = await asyncio.to_thread(
                self.store.add, interaction.user.id, message, due_at
            )
        except ReminderError as error:
            await interaction.response.send_message(str(error), ephemeral=True)
            return
        await interaction.response.send_message(
            f"リマインダーを登録しました（ID: {reminder_id}）。\n"
            f"日時: {due_at.astimezone(_JST):%Y-%m-%d %H:%M} JST",
            ephemeral=True,
        )

    @remind.command(name="list", description="自分の未完了リマインダーを表示します")
    async def list_reminders(self, interaction: discord.Interaction) -> None:
        rows = await asyncio.to_thread(self.store.list_for_user, interaction.user.id)
        if not rows:
            await interaction.response.send_message("未完了のリマインダーはありません。", ephemeral=True)
            return
        lines = []
        for row in rows[:25]:
            due = datetime.fromisoformat(row["due_at"]).astimezone(_JST)
            message = discord.utils.escape_markdown(discord.utils.escape_mentions(row["message"]))
            lines.append(f"**ID {row['id']}** · {due:%m/%d %H:%M} · {row['status']}\n{message[:180]}")
        embed = discord.Embed(title="リマインダー一覧", description="\n\n".join(lines))
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @remind.command(name="cancel", description="リマインダーを取り消します")
    async def cancel(self, interaction: discord.Interaction, reminder_id: app_commands.Range[int, 1]) -> None:
        changed = await asyncio.to_thread(self.store.cancel, interaction.user.id, reminder_id)
        await interaction.response.send_message(
            "リマインダーを取り消しました。" if changed else "対象のリマインダーが見つかりません。",
            ephemeral=True,
        )

    @remind.command(name="done", description="リマインダーを完了扱いにします")
    async def done(self, interaction: discord.Interaction, reminder_id: app_commands.Range[int, 1]) -> None:
        changed = await asyncio.to_thread(self.store.complete, interaction.user.id, reminder_id)
        await interaction.response.send_message(
            "完了にしました。" if changed else "対象のリマインダーが見つかりません。",
            ephemeral=True,
        )

    @remind.command(name="snooze", description="リマインダーを指定分だけ延期します")
    async def snooze(
        self,
        interaction: discord.Interaction,
        reminder_id: app_commands.Range[int, 1],
        minutes: app_commands.Range[int, 1, 10080],
    ) -> None:
        try:
            changed = await asyncio.to_thread(
                self.store.snooze, interaction.user.id, reminder_id, minutes
            )
        except ReminderError as error:
            await interaction.response.send_message(str(error), ephemeral=True)
            return
        await interaction.response.send_message(
            f"{minutes}分後に延期しました。" if changed else "対象のリマインダーが見つかりません。",
            ephemeral=True,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ReminderCog(bot))

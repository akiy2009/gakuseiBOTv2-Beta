"""Optional HSS-backed timetable command for gakuseiBOT."""

from __future__ import annotations

import logging
import os
import sys
from typing import Any, Iterable

import discord
from discord import app_commands
from discord.ext import commands

logger = logging.getLogger(__name__)

_REQUIRED_ENV = (
    "HSS_API_TOKEN",
    "HSS_SCHOOL_ID",
    "HSS_GRADE",
    "HSS_CLASS",
)
_DAY_LABELS = {
    "sun": "日曜日",
    "mon": "月曜日",
    "tue": "火曜日",
    "wed": "水曜日",
    "thu": "木曜日",
    "fri": "金曜日",
    "sat": "土曜日",
}
_DAY_VALUES = {
    "日曜日": "sun",
    "月曜日": "mon",
    "火曜日": "tue",
    "水曜日": "wed",
    "木曜日": "thu",
    "金曜日": "fri",
    "土曜日": "sat",
}
_DAY_CHOICES = [
    app_commands.Choice(name=label, value=value)
    for label, value in _DAY_VALUES.items()
]


def _positive_int_env(name: str) -> int:
    raw_value = os.getenv(name, "").strip()
    value = int(raw_value)
    if value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _safe_label(value: Any, limit: int = 100) -> str:
    text = " ".join(str(value or "").split())
    if not text:
        return ""
    return discord.utils.escape_markdown(text)[:limit]


def format_lessons(lessons: Iterable[Any]) -> str:
    """Format HSS lesson objects into a bounded Discord embed description."""
    rows: list[str] = []
    for index, lesson in enumerate(lessons, start=1):
        if index > 20:
            rows.append("…残りのコマは省略しました。")
            break
        if lesson is None:
            rows.append(f"**{index}限** 登録なし")
            continue

        name = _safe_label(getattr(lesson, "name", None)) or "名称未設定"
        place = _safe_label(getattr(lesson, "place", None))
        is_event = bool(getattr(lesson, "is_event", False))
        suffix = f" — {place}" if place else ""
        if is_event:
            name = f"{name}（行事）"
        rows.append(f"**{index}限** {name}{suffix}")

    return "\n".join(rows) if rows else "この曜日には登録された授業がありません。"


class HssTimetableCog(commands.Cog):
    """Display one configured HSS school's timetable without requiring HSS at startup."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.client: Any | None = None
        self.school: Any | None = None
        self.classroom: Any | None = None
        self.grade: int | None = None
        self.class_number: int | None = None
        self.state = "not_configured"

    async def cog_load(self) -> None:
        settings = {name: os.getenv(name, "").strip() for name in _REQUIRED_ENV}
        if not all(settings.values()):
            self.state = "not_configured"
            return

        if sys.version_info < (3, 11):
            self.state = "unsupported_python"
            logger.warning("HSS timetable integration requires Python 3.11 or later.")
            return

        try:
            school_id = _positive_int_env("HSS_SCHOOL_ID")
            self.grade = _positive_int_env("HSS_GRADE")
            self.class_number = _positive_int_env("HSS_CLASS")
        except ValueError:
            self.state = "invalid_configuration"
            logger.warning("HSS timetable configuration contains an invalid positive integer.")
            return

        try:
            import hss

            client = hss.Client()
            self.client = client
            await client.setup(token=settings["HSS_API_TOKEN"])
            school = client.get_school(school_id)
            if school is None:
                self.state = "school_not_found"
                logger.warning("HSS integration could not access the configured school.")
                return

            grade_classes = school.classes.get(self.grade, {})
            classroom = grade_classes.get(self.class_number)
            if classroom is None:
                self.state = "class_not_found"
                logger.warning("HSS integration could not find the configured grade/class.")
                return

            self.school = school
            self.classroom = classroom
            self.state = "ready"
            logger.info("HSS timetable integration is ready for the configured class.")
        except ImportError:
            self.state = "missing_dependency"
            logger.warning(
                "HSS timetable integration is configured but HSS.py is not installed. "
                "Install requirements-hss.txt with Python 3.11+."
            )
            await self._close_client()
        except Exception as error:
            self.state = "connection_failed"
            # Never include the token or full request details in this log line.
            logger.warning(
                "HSS timetable initialization failed (%s). Check configuration and API access.",
                type(error).__name__,
            )
            await self._close_client()

    async def _close_client(self) -> None:
        client, self.client = self.client, None
        if client is None:
            return
        try:
            await client.close()
        except Exception:
            logger.debug("HSS client cleanup failed.", exc_info=True)

    async def cog_unload(self) -> None:
        await self._close_client()

    def _unavailable_message(self) -> str:
        messages = {
            "not_configured": (
                "HSS 時間割は未設定です。運営に HSS_API_TOKEN、HSS_SCHOOL_ID、"
                "HSS_GRADE、HSS_CLASS の設定を依頼してください。"
            ),
            "unsupported_python": "HSS 時間割機能には Python 3.11 以上が必要です。",
            "invalid_configuration": "HSS の設定値が不正です。運営に確認してください。",
            "missing_dependency": (
                "HSS の追加ライブラリがインストールされていません。運営に確認してください。"
            ),
            "school_not_found": (
                "設定された学校データを取得できません。学校 ID と API 権限を確認してください。"
            ),
            "class_not_found": (
                "設定された学年・クラスが見つかりません。HSS の設定を確認してください。"
            ),
            "connection_failed": (
                "HSS API に接続できませんでした。トークンと接続状態を運営に確認してください。"
            ),
        }
        return messages.get(self.state, "HSS 時間割機能は現在利用できません。運営に確認してください。")

    @app_commands.command(
        name="timetable",
        description="HSS に登録された曜日別の時間割を表示します",
    )
    @app_commands.choices(day=_DAY_CHOICES)
    async def timetable(
        self,
        interaction: discord.Interaction,
        day: app_commands.Choice[str],
    ) -> None:
        if self.state != "ready" or self.classroom is None or self.school is None:
            await interaction.response.send_message(
                self._unavailable_message(),
                ephemeral=True,
                allowed_mentions=discord.AllowedMentions.none(),
            )
            return

        day_timeline = getattr(self.classroom.timeline, day.value, None)
        lessons = getattr(day_timeline, "lessons", [])
        embed = discord.Embed(
            title=f"{_safe_label(self.school.name, 180)} — {_DAY_LABELS[day.value]}",
            description=format_lessons(lessons),
            color=discord.Color.blurple(),
        )
        embed.set_footer(text=f"{self.grade}年 {self.class_number}組 | HSS API")
        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )


async def setup(bot: commands.Bot) -> None:
    """Load the optional timetable cog."""
    await bot.add_cog(HssTimetableCog(bot))

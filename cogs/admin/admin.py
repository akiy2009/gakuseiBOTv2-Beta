"""Developer-only administration commands with constrained Cog loading."""

import logging
import os
import re
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands

logger = logging.getLogger(__name__)
_COG_MODULE_PATTERN = re.compile(r"^cogs(?:\.[A-Za-z_][A-Za-z0-9_]*)+$")


def _read_developer_id() -> int | None:
    raw_value = os.getenv("DEVELOPER_ID", "").strip()
    if not raw_value:
        return None
    try:
        value = int(raw_value)
    except ValueError:
        logger.warning("DEVELOPER_ID must be an integer; developer commands are disabled.")
        return None
    return value if value > 0 else None


class AdminCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _is_developer(self, user_id: int) -> bool:
        developer_id = _read_developer_id()
        return developer_id is not None and user_id == developer_id

    @staticmethod
    def _is_allowed_cog(cog: str) -> bool:
        """Only allow import targets that map to Python files below cogs/."""
        if not _COG_MODULE_PATTERN.fullmatch(cog):
            return False
        relative_path = Path(*cog.split(".")).with_suffix(".py")
        root = Path("cogs").resolve()
        target = (Path.cwd() / relative_path).resolve()
        try:
            target.relative_to(root)
        except ValueError:
            return False
        return target.is_file() and target.name != "__init__.py"

    @app_commands.command(
        name="admin",
        description="開発者専用: Cogのロード状況を確認します",
    )
    async def admin(self, interaction: discord.Interaction) -> None:
        if not self._is_developer(interaction.user.id):
            await interaction.response.send_message(
                "このコマンドは開発者のみ使用できます。",
                ephemeral=True,
            )
            return

        results = []
        for path in sorted(Path("cogs").rglob("*.py")):
            if path.name == "__init__.py":
                continue
            module = ".".join(path.with_suffix("").parts)
            if module in self.bot.extensions:
                status, marker = "読み込み済み", "OK"
            elif module in getattr(self.bot, "skipped_cogs", set()):
                status, marker = "スキップ", "--"
            else:
                status, marker = "未読み込み", "!!"
            results.append(f"{marker} {module} — {status}")

        description = "\n".join(results) or "Cog が見つかりません。"
        if len(description) > 4000:
            description = description[:3997] + "..."
        embed = discord.Embed(
            title="開発者用 - Cog の状態一覧",
            description=description,
            color=discord.Color.dark_grey(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="reload",
        description="開発者専用: 指定したCogをリロードします",
    )
    @app_commands.describe(cog="リロードするCogのモジュール名（例: cogs.admin.admin）")
    async def reload(self, interaction: discord.Interaction, cog: str) -> None:
        if not self._is_developer(interaction.user.id):
            await interaction.response.send_message(
                "このコマンドは開発者のみ使用できます。",
                ephemeral=True,
            )
            return

        if not self._is_allowed_cog(cog):
            await interaction.response.send_message(
                "指定できるのは cogs/ 配下に存在するCogのみです。",
                ephemeral=True,
            )
            logger.warning(
                "Rejected invalid Cog reload target: user_id=%s target=%r",
                interaction.user.id,
                cog,
            )
            return

        try:
            if cog in self.bot.extensions:
                await self.bot.reload_extension(cog)
                action = "リロード"
            else:
                await self.bot.load_extension(cog)
                action = "ロード"

            getattr(self.bot, "load_failures", {}).pop(cog, None)
            getattr(self.bot, "skipped_cogs", set()).discard(cog)
            await interaction.response.send_message(
                f"{cog} の{action}に成功しました。",
                ephemeral=True,
            )
        except (commands.ExtensionError, OSError, ImportError):
            logger.exception("Failed to load or reload Cog %s", cog)
            if not hasattr(self.bot, "load_failures"):
                self.bot.load_failures = {}
            self.bot.load_failures[cog] = "ロードに失敗しました。詳細はログを確認してください。"
            await interaction.response.send_message(
                f"{cog} のロードに失敗しました。設定とログを確認してください。",
                ephemeral=True,
            )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AdminCog(bot))

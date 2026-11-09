"""Centralized user-facing and diagnostic error handling for Discord commands."""

from __future__ import annotations

import logging
import secrets

import discord
from discord.ext import commands

logger = logging.getLogger(__name__)


class ErrorHandler(commands.Cog):
    """Translate expected command errors and log unexpected failures."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @staticmethod
    def generate_tx_id() -> str:
        """Return a short, collision-resistant support reference."""
        return f"TX-{secrets.token_hex(4).upper()}"

    @staticmethod
    def get_app_error_info(
        error: discord.app_commands.AppCommandError,
    ) -> tuple[str, str, discord.Color]:
        if isinstance(error, discord.app_commands.CommandOnCooldown):
            return "E001", "このコマンドはクールダウン中です。", discord.Color.orange()
        if isinstance(error, discord.app_commands.MissingPermissions):
            return "E002", "必要な権限がありません。", discord.Color.red()
        if isinstance(error, discord.app_commands.BotMissingPermissions):
            return "E007", "Bot に必要な権限がありません。", discord.Color.red()
        if isinstance(error, discord.app_commands.NoPrivateMessage):
            return "E005", "このコマンドはDMでは使用できません。", discord.Color.gold()
        if isinstance(error, discord.app_commands.MissingRole):
            return "E006", "必要なロールが不足しています。", discord.Color.dark_gold()
        if isinstance(error, discord.app_commands.CheckFailure):
            return (
                "E003",
                "このコマンドを使用する条件を満たしていません。",
                discord.Color.dark_orange(),
            )
        if isinstance(error, discord.app_commands.CommandInvokeError):
            return (
                "E004",
                "コマンドの実行中に内部エラーが発生しました。",
                discord.Color.dark_red(),
            )
        return "E999", "不明なエラーが発生しました。", discord.Color.light_grey()

    @staticmethod
    def get_prefix_error_message(error: commands.CommandError) -> str | None:
        if isinstance(error, commands.CommandNotFound):
            return None
        if isinstance(error, commands.CommandOnCooldown):
            return "このコマンドはクールダウン中です。少し待ってから再試行してください。"
        if isinstance(error, commands.MissingPermissions):
            return "このコマンドを実行するための権限がありません。"
        if isinstance(error, commands.BotMissingPermissions):
            return "Bot に必要な権限がありません。管理者に確認してください。"
        if isinstance(error, commands.MissingRequiredArgument):
            return f"必須の引数「{error.param.name}」が指定されていません。"
        if isinstance(error, commands.BadArgument):
            return "引数の形式が正しくありません。入力内容を確認してください。"
        if isinstance(error, commands.NoPrivateMessage):
            return "このコマンドはサーバー内でのみ使用できます。"
        if isinstance(error, commands.CheckFailure):
            return "このコマンドを使用する条件を満たしていません。"
        if isinstance(error, commands.CommandInvokeError):
            return "コマンドの実行中にエラーが発生しました。時間をおいて再試行してください。"
        return "コマンドを実行できませんでした。入力内容と権限を確認してください。"

    @commands.Cog.listener()
    async def on_app_command_error(
        self,
        interaction: discord.Interaction,
        error: discord.app_commands.AppCommandError,
    ) -> None:
        tx_id = self.generate_tx_id()
        error_id, message, color = self.get_app_error_info(error)
        original = getattr(error, "original", error)
        command_name = (
            getattr(
                interaction.command,
                "qualified_name",
                getattr(interaction.command, "name", "unknown"),
            )
            if interaction.command
            else "unknown"
        )

        if isinstance(error, discord.app_commands.CommandInvokeError):
            logger.error(
                "Application command failed: command=%s tx_id=%s error_type=%s",
                command_name,
                tx_id,
                type(original).__name__,
                exc_info=(type(original), original, original.__traceback__),
            )
        else:
            logger.warning(
                "Application command rejected: command=%s tx_id=%s error_type=%s",
                command_name,
                tx_id,
                type(error).__name__,
            )

        embed = discord.Embed(
            title=f"エラーが発生しました（{error_id}）",
            description=message,
            color=color,
        )
        embed.add_field(name="処理ID", value=tx_id, inline=False)
        embed.set_footer(text="問題が解決しない場合は、この処理IDを添えて開発者へご連絡ください。")

        try:
            if interaction.response.is_done():
                await interaction.followup.send(
                    embed=embed,
                    ephemeral=True,
                    allowed_mentions=discord.AllowedMentions.none(),
                )
            else:
                await interaction.response.send_message(
                    embed=embed,
                    ephemeral=True,
                    allowed_mentions=discord.AllowedMentions.none(),
                )
        except (discord.NotFound, discord.HTTPException):
            logger.warning(
                "Could not send application command error response: command=%s tx_id=%s",
                command_name,
                tx_id,
                exc_info=True,
            )

    @commands.Cog.listener()
    async def on_command_error(
        self,
        ctx: commands.Context,
        error: commands.CommandError,
    ) -> None:
        if ctx.command is not None and (
            ctx.command.has_error_handler()
            or (ctx.cog is not None and ctx.cog.has_error_handler())
        ):
            return

        message = self.get_prefix_error_message(error)
        if message is None:
            logger.debug("Unknown prefix command received.")
            return

        tx_id = self.generate_tx_id()
        original = getattr(error, "original", error)
        command_name = ctx.command.qualified_name if ctx.command else "unknown"

        if isinstance(error, commands.CommandInvokeError):
            logger.error(
                "Prefix command failed: command=%s tx_id=%s error_type=%s",
                command_name,
                tx_id,
                type(original).__name__,
                exc_info=(type(original), original, original.__traceback__),
            )
        else:
            logger.warning(
                "Prefix command rejected: command=%s tx_id=%s error_type=%s",
                command_name,
                tx_id,
                type(error).__name__,
            )

        try:
            await ctx.send(
                f"{message}\n処理ID: `{tx_id}`",
                allowed_mentions=discord.AllowedMentions.none(),
            )
        except (discord.Forbidden, discord.HTTPException):
            logger.warning(
                "Could not send prefix command error response: command=%s tx_id=%s",
                command_name,
                tx_id,
                exc_info=True,
            )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ErrorHandler(bot))

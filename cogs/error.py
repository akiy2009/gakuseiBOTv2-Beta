"""Centralized user-facing errors, diagnostics, and report actions."""

from __future__ import annotations

import logging
import os
import secrets
from datetime import datetime

import discord
from discord.ext import commands

logger = logging.getLogger(__name__)


def _read_report_channel_id() -> int | None:
    raw_value = os.getenv("ERROR_REPORT_CHANNEL_ID", "").strip()
    if not raw_value:
        return None
    try:
        channel_id = int(raw_value)
    except ValueError:
        logger.warning("ERROR_REPORT_CHANNEL_ID must be an integer; error reports are disabled.")
        return None
    return channel_id if channel_id > 0 else None


class ErrorReportView(discord.ui.View):
    """A short-lived button that forwards safe diagnostic metadata to staff."""

    def __init__(
        self,
        bot: commands.Bot,
        *,
        tx_id: str,
        error_id: str,
        command_name: str,
        guild_id: int | None,
        source_channel_id: int | None,
        occurred_at: datetime,
    ) -> None:
        super().__init__(timeout=900)
        self.bot = bot
        self.tx_id = tx_id
        self.error_id = error_id
        self.command_name = command_name
        self.guild_id = guild_id
        self.source_channel_id = source_channel_id
        self.occurred_at = occurred_at
        self._reported = False

    @discord.ui.button(
        label="このエラーを報告",
        style=discord.ButtonStyle.primary,
        emoji="📩",
        custom_id=None,
    )
    async def report_error(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        if self._reported:
            await interaction.response.send_message(
                "このエラーはすでに報告されています。",
                ephemeral=True,
            )
            return

        report_channel_id = _read_report_channel_id()
        if report_channel_id is None:
            await interaction.response.send_message(
                "報告先が設定されていないため、現在は報告を受け付けられません。",
                ephemeral=True,
            )
            return

        channel = self.bot.get_channel(report_channel_id)
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(report_channel_id)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                logger.exception(
                    "Could not access configured error report channel: tx_id=%s",
                    self.tx_id,
                )
                await interaction.response.send_message(
                    "報告先に接続できませんでした。時間をおいて再度お試しください。",
                    ephemeral=True,
                )
                return

        if not isinstance(channel, (discord.TextChannel, discord.Thread)):
            await interaction.response.send_message(
                "報告先の設定が正しくありません。管理者へご連絡ください。",
                ephemeral=True,
            )
            return

        report = discord.Embed(
            title="エラー報告を受信しました",
            description="利用者からエラー通知の報告が送信されました。",
            color=discord.Color.blurple(),
            timestamp=self.occurred_at,
        )
        report.add_field(name="問い合わせID", value=f"`{self.tx_id}`", inline=True)
        report.add_field(name="エラーコード", value=self.error_id, inline=True)
        report.add_field(name="コマンド", value=self.command_name[:100], inline=True)
        report.add_field(name="報告者ID", value=str(interaction.user.id), inline=True)
        report.add_field(
            name="サーバーID",
            value=str(self.guild_id) if self.guild_id else "DM",
            inline=True,
        )
        report.add_field(
            name="発生チャンネルID",
            value=str(self.source_channel_id) if self.source_channel_id else "不明",
            inline=True,
        )
        report.set_footer(text="詳細な例外情報はBotのログで問い合わせIDを検索してください。")

        self._reported = True
        try:
            await channel.send(
                embed=report,
                allowed_mentions=discord.AllowedMentions.none(),
            )
        except (discord.Forbidden, discord.HTTPException):
            self._reported = False
            logger.exception("Could not deliver error report: tx_id=%s", self.tx_id)
            await interaction.response.send_message(
                "報告の送信に失敗しました。時間をおいて再度お試しください。",
                ephemeral=True,
            )
            return

        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(
            f"報告を受け付けました。問い合わせID: `{self.tx_id}`",
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )


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

    def _build_error_message(
        self,
        *,
        tx_id: str,
        error_id: str,
        message: str,
        color: discord.Color,
        command_name: str,
        guild_id: int | None,
        channel_id: int | None,
    ) -> tuple[discord.Embed, ErrorReportView]:
        embed = discord.Embed(
            title=f"エラーが発生しました（{error_id}）",
            description=message,
            color=color,
        )
        embed.add_field(name="問い合わせID", value=f"`{tx_id}`", inline=False)
        embed.set_footer(text="下のボタンから、このエラーを運営へ報告できます。")
        view = ErrorReportView(
            self.bot,
            tx_id=tx_id,
            error_id=error_id,
            command_name=command_name,
            guild_id=guild_id,
            source_channel_id=channel_id,
            occurred_at=discord.utils.utcnow(),
        )
        return embed, view

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

        embed, view = self._build_error_message(
            tx_id=tx_id,
            error_id=error_id,
            message=message,
            color=color,
            command_name=command_name,
            guild_id=interaction.guild_id,
            channel_id=interaction.channel_id,
        )
        try:
            if interaction.response.is_done():
                await interaction.followup.send(
                    embed=embed,
                    view=view,
                    ephemeral=True,
                    allowed_mentions=discord.AllowedMentions.none(),
                )
            else:
                await interaction.response.send_message(
                    embed=embed,
                    view=view,
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

        embed, view = self._build_error_message(
            tx_id=tx_id,
            error_id="E004" if isinstance(error, commands.CommandInvokeError) else "E999",
            message=message,
            color=discord.Color.dark_red(),
            command_name=command_name,
            guild_id=ctx.guild.id if ctx.guild else None,
            channel_id=ctx.channel.id if ctx.channel else None,
        )
        try:
            await ctx.send(
                embed=embed,
                view=view,
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

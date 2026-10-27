import os

import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Modal, TextInput


def _channel_id_from_env(name: str) -> int | None:
    raw_value = os.getenv(name, "").strip()
    if not raw_value:
        return None
    try:
        value = int(raw_value)
    except ValueError:
        return None
    return value if value > 0 else None


class ReportModal(Modal):
    def __init__(self, bot: commands.Bot):
        super().__init__(title="ユーザー報告フォーム")
        self.bot = bot
        self.user_id_input = TextInput(
            label="対象ユーザーのID",
            placeholder="報告したい相手のユーザーIDを入力",
            required=True,
            max_length=20,
        )
        self.reason_input = TextInput(
            label="報告理由・詳細",
            style=discord.TextStyle.paragraph,
            placeholder="迷惑行為や不正利用の詳細を入力してください",
            required=True,
            max_length=2000,
        )
        self.add_item(self.user_id_input)
        self.add_item(self.reason_input)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        channel_id = _channel_id_from_env("REPORT_CHANNEL_ID")
        if channel_id is None:
            await interaction.response.send_message(
                "報告先が未設定です。運営に設定を確認するようお知らせください。",
                ephemeral=True,
            )
            return

        target_id = self.user_id_input.value.strip()
        if not target_id.isdecimal() or not (15 <= len(target_id) <= 20):
            await interaction.response.send_message(
                "対象ユーザーIDは、Discord の数値IDで入力してください。",
                ephemeral=True,
            )
            return

        embed = discord.Embed(title="ユーザー報告", color=discord.Color.red())
        embed.add_field(name="対象ユーザーID", value=target_id, inline=False)
        embed.add_field(name="内容", value=self.reason_input.value, inline=False)
        embed.set_footer(text=f"報告者ID: {interaction.user.id}")

        try:
            channel = self.bot.get_channel(channel_id)
            if channel is None:
                channel = await self.bot.fetch_channel(channel_id)
            if not isinstance(channel, (discord.TextChannel, discord.Thread)):
                raise TypeError("報告先がテキストチャンネルではありません")
            await channel.send(embed=embed)
        except (discord.Forbidden, discord.NotFound, discord.HTTPException, TypeError):
            await interaction.response.send_message(
                "報告を送信できませんでした。運営に設定を確認するようお知らせください。",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            "報告を運営へ送信しました。ご協力ありがとうございます。",
            ephemeral=True,
        )


class ReportCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="report",
        description="不正行為や規約違反を運営へ報告します",
    )
    async def report(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(ReportModal(self.bot))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ReportCog(bot))

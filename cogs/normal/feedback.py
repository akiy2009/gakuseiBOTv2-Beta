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


class FeedbackModal(Modal):
    def __init__(self, bot: commands.Bot):
        super().__init__(title="フィードバックを送信")
        self.bot = bot
        self.title_input = TextInput(
            label="タイトル",
            placeholder="フィードバックのタイトルを入力",
            max_length=100,
        )
        self.content_input = TextInput(
            label="内容",
            style=discord.TextStyle.paragraph,
            placeholder="詳細なフィードバックを入力してください。この内容は運営に閲覧されます。",
            max_length=2000,
        )
        self.add_item(self.title_input)
        self.add_item(self.content_input)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        channel_id = _channel_id_from_env("FEEDBACK_CHANNEL_ID")
        if channel_id is None:
            await interaction.response.send_message(
                "フィードバック送信先が未設定です。運営に設定を確認するようお知らせください。",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title=self.title_input.value,
            description=self.content_input.value,
            color=discord.Color.orange(),
        )
        embed.set_author(
            name=interaction.user.display_name,
            icon_url=interaction.user.display_avatar.url,
        )
        if self.bot.user is not None:
            embed.set_footer(
                text="フィードバック",
                icon_url=self.bot.user.display_avatar.url,
            )

        try:
            channel = self.bot.get_channel(channel_id)
            if channel is None:
                channel = await self.bot.fetch_channel(channel_id)
            if not isinstance(channel, (discord.TextChannel, discord.Thread)):
                raise TypeError("フィードバック先がテキストチャンネルではありません")
            await channel.send(embed=embed)
        except (discord.Forbidden, discord.NotFound, discord.HTTPException, TypeError):
            await interaction.response.send_message(
                "フィードバックを送信できませんでした。運営に設定を確認するようお知らせください。",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            "フィードバックを送信しました。ご協力ありがとうございます。",
            ephemeral=True,
        )


class FeedbackCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="feedback",
        description="運営にフィードバックを送信します",
    )
    async def feedback(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(FeedbackModal(self.bot))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(FeedbackCog(bot))

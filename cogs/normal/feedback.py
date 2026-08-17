import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Modal, TextInput

FEEDBACK_CHANNEL_ID = 1301185017619415092  # 送信先チャンネルID

class FeedbackModal(Modal):
    def __init__(self, bot: commands.Bot):
        super().__init__(title="フィードバックを送信")
        self.bot = bot

        self.title_input = TextInput(
            label="タイトル",
            placeholder="フィードバックのタイトルを入力",
            max_length=100
        )
        self.add_item(self.title_input)

        self.content_input = TextInput(
            label="内容",
            style=discord.TextStyle.paragraph,
            placeholder="詳細なフィードバックを入力してください。この内容は運営に閲覧されます。",
            max_length=2000
        )
        self.add_item(self.content_input)

    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title=self.title_input.value,
            description=self.content_input.value,
            color=discord.Color.orange()
        )
        embed.set_author(name=interaction.user, icon_url=interaction.user.display_avatar.url)
        embed.set_footer(text="フィードバック", icon_url=self.bot.user.display_avatar.url)

        channel = self.bot.get_channel(FEEDBACK_CHANNEL_ID)
        if channel and isinstance(channel, discord.TextChannel):
            await channel.send(embed=embed)
            await interaction.response.send_message("✅ フィードバックを送信しました。このご意見は運営の参考とさせていただきます。ご協力ありがとうございます！", ephemeral=True)
        else:
            await interaction.response.send_message("❌ フィードバックチャンネルが見つかりません。お手数をおかけしますが、開発者までこのことをご報告ください。", ephemeral=True)


class FeedbackCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="feedback", description="運営にフィードバックを送信します")
    async def feedback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(FeedbackModal(self.bot))


async def setup(bot: commands.Bot):
    if not bot.get_cog("FeedbackCog"):
        await bot.add_cog(FeedbackCog(bot))
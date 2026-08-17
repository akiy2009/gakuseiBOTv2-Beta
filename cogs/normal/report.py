import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Modal, TextInput

REPORT_CHANNEL_ID = 1291296590950301753  # 運営用の報告受信チャンネルID

class ReportModal(Modal):
    def __init__(self, bot: commands.Bot):
        super().__init__(title="ユーザー報告フォーム")
        self.bot = bot

        self.user_id_input = TextInput(
            label="対象ユーザーのID",
            placeholder="報告したい相手のユーザーIDを入力",
            required=True,
            max_length=20
        )
        self.reason_input = TextInput(
            label="報告理由・詳細",
            style=discord.TextStyle.paragraph,
            placeholder="迷惑行為や不正利用の詳細を入力してください",
            required=True,
            max_length=2000
        )

        self.add_item(self.user_id_input)
        self.add_item(self.reason_input)

    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="ユーザー報告",
            color=discord.Color.red()
        )
        embed.add_field(name="対象ユーザーID", value=self.user_id_input.value, inline=False)
        embed.add_field(name="内容", value=self.reason_input.value, inline=False)
        embed.set_footer(text=f"通報者ID: {interaction.user.id}")

        channel = self.bot.get_channel(REPORT_CHANNEL_ID)
        if isinstance(channel, discord.TextChannel):
            await channel.send(embed=embed)
            await interaction.response.send_message("✅ 通報が送信されました。ご協力ありがとうございます。", ephemeral=True)
        else:
            await interaction.response.send_message("❌ 通報チャンネルが見つかりませんでした。", ephemeral=True)
            


class ReportCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="report", description="不正行為や規約違反を匿名で報告します")
    async def report(self, interaction: discord.Interaction):
        await interaction.response.send_modal(ReportModal(self.bot))


async def setup(bot: commands.Bot):
    if not bot.get_cog("ReportCog"):
        await bot.add_cog(ReportCog(bot))
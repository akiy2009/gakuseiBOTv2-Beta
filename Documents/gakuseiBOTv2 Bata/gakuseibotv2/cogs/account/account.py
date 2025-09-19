import discord
from discord.ext import commands
from discord import app_commands

# ボタンを含むView
class AccountLinkView(discord.ui.View):
    def __init__(self, label: str, url: str):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(label=label, url=url, style=discord.ButtonStyle.link))

# Cog定義
class AccountCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="dashboard", description="ダッシュボードにログインします")
    async def account(self, interaction: discord.Interaction):
        user_id = interaction.user.id

        # 開発者ユーザーはアカウントを持っているとみなす
        if user_id == 1241366063858450485:
            label = "ログインする"
            url = "https://dashboard.gakuseibot.com/login"
            embed = discord.Embed(
                title="ログイン",
                description="既にアカウントをお持ちのようです。以下のボタンからログインしてください。",
                color=discord.Color.orange()
            )
        else:
            label = "アカウントを作成する"
            url = "https://dashboard.gakuseibot.com/register"
            embed = discord.Embed(
                title="アカウント作成",
                description="以下のボタンから新しくアカウントを作成できます。",
                color=discord.Color.og_blurple()
            )

        await interaction.response.send_message(
            embed=embed,
            view=AccountLinkView(label=label, url=url),
            ephemeral=True  # 自分だけに表示
        )

# setup関数
async def setup(bot: commands.Bot):
    await bot.add_cog(AccountCog(bot))
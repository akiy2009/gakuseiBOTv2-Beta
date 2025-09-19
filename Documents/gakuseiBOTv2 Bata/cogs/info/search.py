import discord
from discord.ext import commands
from discord import app_commands
import wikipediaapi

class WikiSearch(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.wiki = wikipediaapi.Wikipedia(language='ja',user_agent='GakuseiBot/v2.0 (https://github.com/akiy2009/gakuseiBOTv2-Beta)')  # 日本語で検索

    @app_commands.command(name="search", description="Wikipediaで語句を検索します")
    @app_commands.describe(keyword="検索キーワード（日本語）")
    async def search(self, interaction: discord.Interaction, keyword: str):
        await interaction.response.defer()  # 長時間処理対応

        page = self.wiki.page(keyword)

        if page.exists():
            summary = page.summary[0:500] + ("..." if len(page.summary) > 500 else "")
            embed = discord.Embed(
                title=page.title,
                description=summary,
                url=page.fullurl,
                color=discord.Color.blue()
            )
            embed.set_footer(text="Wikipediaより取得")

            view = discord.ui.View()
            button = discord.ui.Button(label="ページを開く", url=page.fullurl, style=discord.ButtonStyle.link)
            view.add_item(button)
            await interaction.followup.send(embed=embed, view=view)
        else:
            await interaction.followup.send(f"🔍「{keyword}」に一致するWikipediaページは見つかりませんでした。", ephemeral=True)

# Cog 登録関数
async def setup(bot: commands.Bot):
    await bot.add_cog(WikiSearch(bot))
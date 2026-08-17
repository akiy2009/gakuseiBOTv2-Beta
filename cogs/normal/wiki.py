import re

import discord
import wikipedia
from discord import app_commands
from discord.ext import commands

# Wikipediaを日本語に設定
wikipedia.set_lang("ja")

def clean_text(text: str) -> str:
    """Wikipediaの要約からタグを除去"""
    return re.sub(r"<.*?>", "", text)

class WikipediaCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # スラッシュコマンド定義
    @app_commands.command(name="wiki", description="Wikipediaで調べ物をします")
    async def wiki(self, interaction: discord.Interaction, query: str):
        """
        /wiki 検索ワード でWikipediaを検索する
        """
        await interaction.response.defer()

        try:
            # Wikipedia検索
            summary = wikipedia.summary(query, sentences=3)
            summary = clean_text(summary)  # タグを除去
            page = wikipedia.page(query)

            embed = discord.Embed(
                title=f"Wikipedia: {page.title}",
                description=summary[:1024], 
                color=discord.Color.blue()
            )
            embed.add_field(name="URL", value=page.url, inline=False)
            embed.set_footer(text="出典: Wikipedia")

            await interaction.followup.send(embed=embed)

        except wikipedia.DisambiguationError as e:
            await interaction.followup.send(
                f"検索ワードが曖昧です。候補: {', '.join(e.options[:5])} ..."
            )
        except wikipedia.PageError:
            await interaction.followup.send("該当するページが見つかりませんでした。")
        except Exception as e:
            await interaction.followup.send(f"⚠ エラーが発生しました: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(WikipediaCog(bot))

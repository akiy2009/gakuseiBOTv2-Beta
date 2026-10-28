import asyncio
import logging
import re

import discord
import wikipedia
from discord import app_commands
from discord.ext import commands

logger = logging.getLogger(__name__)
wikipedia.set_lang("ja")


def clean_text(text: str) -> str:
    """Remove HTML-like tags from a Wikipedia summary."""
    return re.sub(r"<.*?>", "", text)


class WikipediaCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="wiki", description="Wikipediaで調べ物をします")
    @app_commands.describe(query="Wikipedia で調べたいキーワード")
    async def wiki(self, interaction: discord.Interaction, query: str) -> None:
        await interaction.response.defer(thinking=True)
        try:
            page = await asyncio.to_thread(wikipedia.page, query)
            summary = await asyncio.to_thread(
                wikipedia.summary,
                page.title,
                sentences=3,
                auto_suggest=False,
            )
            summary = clean_text(summary)
            embed = discord.Embed(
                title=f"Wikipedia: {page.title}"[:256],
                description=summary[:4000],
                color=discord.Color.blue(),
            )
            embed.add_field(name="URL", value=page.url, inline=False)
            embed.set_footer(text="出典: Wikipedia")
            await interaction.followup.send(embed=embed)
        except wikipedia.DisambiguationError as error:
            options = ", ".join(error.options[:5]) or "候補を取得できませんでした"
            await interaction.followup.send(
                f"検索ワードが曖昧です。候補: {options[:1500]}"
            )
        except wikipedia.PageError:
            await interaction.followup.send("該当するページが見つかりませんでした。")
        except Exception:
            logger.exception("Wikipedia search failed for query=%r", query)
            await interaction.followup.send(
                "Wikipedia の検索に失敗しました。時間をおいて再試行してください。"
            )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(WikipediaCog(bot))

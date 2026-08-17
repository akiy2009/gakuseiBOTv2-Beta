import re

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands


class URLShortener(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="shorten", description="URLを短縮します")
    @app_commands.describe(url="短縮したいURLを入力してください")
    async def shorten(self, interaction: discord.Interaction, url: str):
        await interaction.response.defer()

        # URLの先頭に http:// または https:// がなければ https:// を付与
        if not re.match(r'^https?://', url):
            url = 'https://' + url

        api_url = f"https://is.gd/create.php?format=simple&url={url}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url) as resp:
                    if resp.status != 200:
                        await interaction.followup.send("⚠ URL短縮サービスに接続できませんでした。", ephemeral=True)
                        return
                    short_url = await resp.text()

            await interaction.followup.send(f"🔗 短縮URL: {short_url}")
        except Exception as e:
            await interaction.followup.send(f"⚠ エラーが発生しました: {e}", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(URLShortener(bot))
from urllib.parse import urlsplit

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands


class URLShortener(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="shorten", description="URLを短縮します")
    @app_commands.describe(url="短縮したいURLを入力してください")
    async def shorten(self, interaction: discord.Interaction, url: str) -> None:
        candidate = url.strip()
        if "://" not in candidate:
            candidate = f"https://{candidate}"

        parsed = urlsplit(candidate)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
        ):
            await interaction.response.send_message(
                "有効な http または https のURLを入力してください。",
                ephemeral=True,
            )
            return

        await interaction.response.defer(thinking=True)
        timeout = aiohttp.ClientTimeout(total=10)
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(
                    "https://is.gd/create.php",
                    params={"format": "simple", "url": candidate},
                ) as response:
                    result = (await response.text()).strip()
                    if response.status != 200 or result.lower().startswith("error:"):
                        await interaction.followup.send(
                            "URL短縮サービスがリクエストを受け付けませんでした。",
                            ephemeral=True,
                        )
                        return

            if not result.startswith(("https://", "http://")):
                await interaction.followup.send(
                    "URL短縮サービスから有効な結果が返されませんでした。",
                    ephemeral=True,
                )
                return

            await interaction.followup.send(f"短縮URL: {result}")
        except (aiohttp.ClientError, TimeoutError):
            await interaction.followup.send(
                "URL短縮サービスに接続できませんでした。時間をおいて再試行してください。",
                ephemeral=True,
            )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(URLShortener(bot))

import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import time

class PingBOTandWEB(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="ping", description="サービスの応答速度を測定します。")
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)

        latency_ms = round(self.bot.latency * 1000)

        # WebサーバーへのPing
        site_url = "https://gakuseibot.com"
        async with aiohttp.ClientSession() as session:
            try:
                start_time = time.perf_counter()
                async with session.get(site_url, timeout=5) as response:
                    end_time = time.perf_counter()
                    site_latency = round((end_time - start_time) * 1000)
                    status = response.status
            except Exception:
                site_latency = None
                status = "接続失敗"

        embed = discord.Embed(
            title="Ping 結果",
            color=discord.Color.green()
        )
        embed.add_field(name="🔁 Discord API", value=f"{latency_ms}ms", inline=False)
        if site_latency is not None:
            embed.add_field(name="🌐 公式サイト", value=f"{site_latency}ms (HTTP {status})", inline=False)
        else:
            embed.add_field(name="🌐 公式サイト", value="接続失敗", inline=False)

        embed.set_footer(text="gakuseiBOTv2 Ping Utility")
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(PingBOTandWEB(bot))
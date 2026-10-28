import discord
from discord import app_commands
from discord.ext import commands


class BOTInfo(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="botinfo",
        description="Botの導入サーバー数とユーザー数を表示します",
    )
    async def botinfo(self, interaction: discord.Interaction) -> None:
        guild_count = len(self.bot.guilds)
        user_count = sum(guild.member_count or 0 for guild in self.bot.guilds)

        embed = discord.Embed(
            title="Botの導入状況",
            color=discord.Color.green(),
        )
        embed.add_field(name="導入サーバー数", value=f"{guild_count} サーバー", inline=False)
        embed.add_field(name="合計ユーザー数", value=f"{user_count} 人（概算）", inline=False)
        embed.set_footer(text="gakuseiBOT Information")

        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(BOTInfo(bot))

import discord
from discord.ext import commands
from discord import app_commands

class About(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="about", description="Botの説明を表示します")
    async def about(self, interaction: discord.Interaction):

        embed = discord.Embed(
            title="About gakuseiBOT",
            description="gakuseiBOTは、学生向けの便利な機能を提供するDiscord Botです。\n"
                        "このBotは、学習支援、コミュニケーションの促進、サーバー管理など、様々な機能を備えています。",
            color=discord.Color.blurple()
        )
        embed.add_field(name="License", value="MIT License", inline=False)
        embed.add_field(name="Version", value="2.0.0-beta", inline=False)
        embed.add_field(name="Contributor", value=f"[Akiy2009](https://github.com/akiy2009)", inline=False)
        embed.add_field(name="GitHub repository", value=f"https://github.com/akiy2009/gakuseiBOTv2-Beta", inline=False)
        embed.add_field(name="Support Server", value=f"[Join here](https://discord.gg/9x3FwmPxhP)", inline=False)
        embed.add_field(name="Website", value="https://gakuseibot.com", inline=False)
        embed.add_field(name="Update Info", value="https://gakuseibot.com/updates", inline=False)
        embed.add_field(name="Privacy Policy", value="[Read here](https://gakuseibot.com/privacy)", inline=False)
        embed.add_field(name="Terms of Service", value="[Read here](https://gakuseibot.com/terms)", inline=False)
        embed.add_field(name="Contribute", value="Botの開発に貢献したい方は、GitHubリポジトリをチェックしてください。", inline=False)
        embed.add_field(name="Support", value="Botの利用に関する質問や問題は、サポートサーバーでお知らせください。", inline=False)
        embed.add_field(name="Feedback", value="ご意見・ご要望はサポートサーバーでお待ちしています！", inline=False)
        embed.set_footer(text="gakuseiBOT About Information")

        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(About(bot))

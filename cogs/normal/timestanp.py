from datetime import datetime

import discord
import pytz
from discord import app_commands
from discord.ext import commands


class set_timestanp(commands.Cog):
    def __init__(self, bot:commands.Bot):
        self.bot = bot

    @app_commands.command(name="timestanp", description="YYYY/MM/DD/h:m形式の日時をタイムスタンプに変換します")
    @app_commands.describe(date_str="YYYY/MM/DD/h:m 形式で入力してください", type="表示形式を選択してください")
    @app_commands.choices(type=[
        app_commands.Choice(name="時間表示", value="t"),
        app_commands.Choice(name="日付表示", value="d"),
        app_commands.Choice(name="日本語日付表示[年、月、日]", value="D"),
        app_commands.Choice(name="日本語日付表示と時間", value="f"),
        app_commands.Choice(name="日本語日付表示と時間と曜日", value="F"),
        app_commands.Choice(name="現在時刻との差", value="R"),
    ])
    async def timestanp(self, interaction: discord.Interaction, date_str: str, type: app_commands.Choice[str]):
        try:
            # pytzで日本時間(JST)に変換
            JST = pytz.timezone('Asia/Tokyo')
            dt = datetime.strptime(date_str, "%Y/%m/%d/%H:%M")
            dt = JST.localize(dt)
            unix_time = int(dt.timestamp())
            # タイムスタンプフォーマット
            timestamp_str = f"<t:{unix_time}:{type.value}>"
            embed = discord.Embed(
                title="変換結果",description=f"{timestamp_str}\n```{timestamp_str}```",color=discord.Color.brand_green()
            )
            await interaction.response.send_message(embed=embed)
        except ValueError:
            await interaction.response.send_message("日付の形式が正しくありません。YY/MM/DD/h:m 形式で入力してください。", ephemeral=True)

async def setup(bot):
    await bot.add_cog(set_timestanp(bot))
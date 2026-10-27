import discord
import pytz
from datetime import datetime
from discord import app_commands
from discord.ext import commands


class SetTimestamp(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="timestanp",
        description="YYYY/MM/DD/HH:MM形式の日時をタイムスタンプに変換します",
    )
    @app_commands.describe(date_str="YYYY/MM/DD/HH:MM 形式で入力してください", type="表示形式を選択してください")
    @app_commands.choices(
        type=[
            app_commands.Choice(name="時間表示", value="t"),
            app_commands.Choice(name="日付表示", value="d"),
            app_commands.Choice(name="日本語日付表示（年、月、日）", value="D"),
            app_commands.Choice(name="日本語日付表示と時間", value="f"),
            app_commands.Choice(name="日本語日付表示と時間と曜日", value="F"),
            app_commands.Choice(name="現在時刻との差", value="R"),
        ]
    )
    async def timestanp(
        self,
        interaction: discord.Interaction,
        date_str: str,
        type: app_commands.Choice[str],
    ) -> None:
        try:
            japan_tz = pytz.timezone("Asia/Tokyo")
            parsed_date = datetime.strptime(date_str, "%Y/%m/%d/%H:%M")
            localized_date = japan_tz.localize(parsed_date)
            unix_time = int(localized_date.timestamp())
            timestamp_text = f"<t:{unix_time}:{type.value}>"
            embed = discord.Embed(
                title="変換結果",
                description=f"{timestamp_text}\n{timestamp_text}",
                color=discord.Color.brand_green(),
            )
            await interaction.response.send_message(embed=embed)
        except ValueError:
            await interaction.response.send_message(
                "日付の形式が正しくありません。YYYY/MM/DD/HH:MM 形式で入力してください。",
                ephemeral=True,
            )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(SetTimestamp(bot))

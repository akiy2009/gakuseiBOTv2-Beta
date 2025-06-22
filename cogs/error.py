import discord
from discord.ext import commands
from datetime import datetime
import time

class ErrorHandler(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def generate_tx_id(self):
        # 現在のエポック秒を16進数で変換（TX-5F5E100形式）
        return f"TX-{hex(int(time.time()))[2:].upper()}"

    def get_error_info(self, error):
        # エラータイプごとの情報（ID, 説明, 色）を定義
        if isinstance(error, discord.app_commands.CommandOnCooldown):
            return "E001", "このコマンドはクールダウン中です。", discord.Color.orange()

        elif isinstance(error, discord.app_commands.MissingPermissions):
            return "E002", "必要な権限がありません。", discord.Color.red()

        elif isinstance(error, discord.app_commands.CheckFailure):
            return "E003", "このコマンドを使用する条件を満たしていません。", discord.Color.dark_orange()

        elif isinstance(error, discord.app_commands.CommandInvokeError):
            return "E004", "コマンドの実行中に内部エラーが発生しました。", discord.Color.dark_red()

        elif isinstance(error, discord.app_commands.NoPrivateMessage):
            return "E005", "このコマンドはDMでは使用できません。", discord.Color.gold()

        elif isinstance(error, discord.app_commands.MissingRole):
            return "E006", "必要なロールが不足しています。", discord.Color.dark_gold()

        else:
            return "E999", "不明なエラーが発生しました。", discord.Color.light_grey()

    @commands.Cog.listener()
    async def on_app_command_error(self, interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
        tx_id = self.generate_tx_id()
        error_id, message, color = self.get_error_info(error)

        embed = discord.Embed(
            title=f"エラーが発生しました（{error_id}）",
            description=message,
            color=color
        )
        embed.add_field(name="処理ID", value=tx_id, inline=False)
        embed.set_footer(text="問題が解決しない場合は開発者へご連絡ください。")

        try:
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except discord.InteractionResponded:
            await interaction.followup.send(embed=embed, ephemeral=True)

        # コンソールにも出力（開発用ログ）
        original = getattr(error, "original", error)
        print(f"[{tx_id}] [{error_id}] {type(original).__name__}: {original}")

async def setup(bot: commands.Bot):
    await bot.add_cog(ErrorHandler(bot))

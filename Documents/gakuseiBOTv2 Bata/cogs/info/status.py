import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import matplotlib.pyplot as plt
import io

COUNTER_FILE = "command_counts.json"

def load_counts():
    if os.path.exists(COUNTER_FILE):
        with open(COUNTER_FILE, "r") as f:
            return json.load(f)
    else:
        return {}

def save_counts(counts):
    with open(COUNTER_FILE, "w") as f:
        json.dump(counts, f, indent=2)

class CommandCounterCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.counts = load_counts()

    @commands.Cog.listener()
    async def on_command_completion(self, ctx):
        name = ctx.command.name if ctx.command else "unknown"
        self.counts[name] = self.counts.get(name, 0) + 1
        save_counts(self.counts)
    
    @commands.Cog.listener()
    async def on_app_command_completion(self, interaction, command):
        name = command.name if command else "unknown"
        self.counts[name] = self.counts.get(name, 0) + 1
        save_counts(self.counts)

    @app_commands.command(name="commandusage", description="コマンド使用回数の統計を表示します")
    async def command_usage(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        if not self.counts:
            await interaction.followup.send("コマンドの使用履歴がありません。")
            return

        # 上位10コマンドを抽出
        top_commands = sorted(self.counts.items(), key=lambda x: x[1], reverse=True)[:10]
        names, values = zip(*top_commands)

        # グラフ描画
        plt.figure(figsize=(10,6))
        plt.barh(names, values, color='skyblue')
        plt.xlabel('使用回数')
        plt.title('コマンド使用回数ランキング（上位10）')
        plt.gca().invert_yaxis()  # 上位が上に来るように

        buf = io.BytesIO()
        plt.tight_layout()
        plt.savefig(buf, format='png')
        buf.seek(0)
        plt.close()

        file = discord.File(buf, filename="command_usage.png")
        await interaction.followup.send(file=file)

async def setup(bot):
    await bot.add_cog(CommandCounterCog(bot))
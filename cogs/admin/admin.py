import discord
from discord.ext import commands
from discord import app_commands
import os
import glob

DEVELOPER_ID = 1241366063858450485

class AdminCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # 開発者チェック用
    async def cog_check(self, ctx: commands.Context):
        return ctx.author.id == DEVELOPER_ID

    @app_commands.command(name="admin", description="開発者専用: Cogのロード状況を確認します")
    async def admin(self, interaction: discord.Interaction):
        if interaction.user.id != DEVELOPER_ID:
            await interaction.response.send_message("❌ このコマンドは開発者のみ使用できます。", ephemeral=True)
            return

        # Cogディレクトリ内の.pyファイルを検索
        cog_files = glob.glob("cogs/**/*.py", recursive=True)
        results = []

        for path in cog_files:
            if path.endswith("__init__.py"):
                continue
            module = path[:-3].replace("/", ".").replace("\\", ".")
            status = "✅ 読み込み済み"
            color = "🟢"

            if module not in self.bot.extensions:
                status = "❌ 未読み込み"
                color = "🔴"
            elif module in self.bot.extensions and not self.bot.extensions[module]:
                status = "⚠️ 失敗または無効"
                color = "🟡"

            results.append(f"{color} `{module}` → {status}")

        embed = discord.Embed(
            title="開発者用 - Cogの状態一覧",
            description="\n".join(results) or "No Cogs found.",
            color=discord.Color.purple()
        )
        embed.set_footer(text="gakuseiBOT Developer Tool")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="reload", description="開発者専用: 指定したCogをリロードします")
    @app_commands.describe(cog="リロードするCogのモジュール名（例: cogs.admin.admin）")
    async def reload(self, interaction: discord.Interaction, cog: str):
        if interaction.user.id != DEVELOPER_ID:
            await interaction.response.send_message("❌ このコマンドは開発者のみ使用できます。", ephemeral=True)
            return

        try:
            if cog in self.bot.extensions:
                await self.bot.reload_extension(cog)
                await interaction.response.send_message(f"🔄 `{cog}` をリロードしました。", ephemeral=True)
                # 成功したらエラーリストから削除
                if cog in self.bot.load_failures:
                    del self.bot.load_failures[cog]
                if cog in self.bot.skipped_cogs:
                    self.bot.skipped_cogs.remove(cog)
            else:
                # 未読み込みなら読み込み試行
                await self.bot.load_extension(cog)
                await interaction.response.send_message(f"✅ `{cog}` を読み込みました。", ephemeral=True)
                if cog in self.bot.load_failures:
                    del self.bot.load_failures[cog]
                if cog in self.bot.skipped_cogs:
                    self.bot.skipped_cogs.remove(cog)

        except Exception as e:
            self.bot.load_failures[cog] = str(e)
            await interaction.response.send_message(f"❌ `{cog}` のリロードに失敗しました。\n```{e}```", ephemeral=True)
# setup
async def setup(bot: commands.Bot):
    await bot.add_cog(AdminCog(bot))

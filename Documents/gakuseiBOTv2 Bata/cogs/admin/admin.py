import discord
from discord.ext import commands
from discord import app_commands
import os
import glob

# 環境変数から開発者IDを取得
DEVELOPER_ID = os.getenv('DEVELOPER_ID')
if DEVELOPER_ID:
    try:
        DEVELOPER_ID = int(DEVELOPER_ID)
    except ValueError:
        print("Error: DEVELOPER_ID is not a valid integer")
        DEVELOPER_ID = None
else:
    print("Warning: DEVELOPER_ID not set in environment variables")
    DEVELOPER_ID = None

class AdminCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _is_developer(self, user_id: int) -> bool:
        """開発者権限をチェックする統一メソッド"""
        return DEVELOPER_ID is not None and user_id == DEVELOPER_ID
    
    def _get_permission_error_message(self) -> str:
        """権限エラーメッセージを統一管理"""
        if DEVELOPER_ID is None:
            return "❌ 開発者IDが環境変数に設定されていません。"
        return "❌ このコマンドは開発者のみ使用できます。"

    # 開発者チェック用
    async def cog_check(self, ctx: commands.Context):
        return self._is_developer(ctx.author.id)

    @app_commands.command(name="admin", description="開発者専用: Cogのロード状況を確認します")
    async def admin(self, interaction: discord.Interaction):
        if not self._is_developer(interaction.user.id):
            await interaction.response.send_message(self._get_permission_error_message(), ephemeral=True)
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
        if not self._is_developer(interaction.user.id):
            await interaction.response.send_message(self._get_permission_error_message(), ephemeral=True)
            return

        try:
            if cog in self.bot.extensions:
                await self.bot.reload_extension(cog)
                await interaction.response.send_message(f"🔄 `{cog}` をリロードしました。", ephemeral=True)
                # 成功したらエラーリストから削除（安全なアクセス）
                load_failures = getattr(self.bot, 'load_failures', {})
                skipped_cogs = getattr(self.bot, 'skipped_cogs', [])
                
                if cog in load_failures:
                    del load_failures[cog]
                if cog in skipped_cogs:
                    skipped_cogs.remove(cog)
            else:
                # 未読み込みなら読み込み試行
                await self.bot.load_extension(cog)
                await interaction.response.send_message(f"✅ `{cog}` を読み込みました。", ephemeral=True)
                load_failures = getattr(self.bot, 'load_failures', {})
                skipped_cogs = getattr(self.bot, 'skipped_cogs', [])
                
                if cog in load_failures:
                    del load_failures[cog]
                if cog in skipped_cogs:
                    skipped_cogs.remove(cog)

        except Exception as e:
            # エラー情報を内部用に記録し、ユーザーには簡略な情報のみ表示
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Cog reload failed for {cog}: {e}")
            
            self.bot.load_failures = getattr(self.bot, 'load_failures', {})
            self.bot.load_failures[cog] = str(e)
            
            # ユーザーにはシンプルなメッセージのみ表示
            await interaction.response.send_message(f"❌ `{cog}` のリロードに失敗しました。ログで詳細を確認してください。", ephemeral=True)
# setup
async def setup(bot: commands.Bot):
    await bot.add_cog(AdminCog(bot))
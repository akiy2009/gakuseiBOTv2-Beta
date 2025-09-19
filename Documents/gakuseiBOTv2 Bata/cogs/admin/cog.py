import discord
from discord.ext import commands
from discord import app_commands
import glob
import time
from datetime import datetime

DEVELOPER_ID = 1241366063858450485

class AdminCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Cogのロード状況を管理
        self.cog_status = {}  # {cog_module: {status:str, last_loaded:datetime, load_time:float, error:str or None}}
        self.load_logs = []   # [(timestamp, message), ...]

    # 開発者チェック
    async def cog_check(self, ctx: commands.Context):
        return ctx.author.id == DEVELOPER_ID

    # Cogのロード処理をラップする例（ロード時に状態とログを保存）
    async def load_cog(self, cog_module: str):
        start = time.time()
        try:
            await self.bot.load_extension(cog_module)
            elapsed = time.time() - start
            self.cog_status[cog_module] = {
                "status": "読み込み成功",
                "last_loaded": datetime.now(),
                "load_time": elapsed,
                "error": None
            }
            self.load_logs.append((datetime.now(), f"✅ {cog_module} loaded in {elapsed:.2f}s"))
            return True
        except commands.ExtensionAlreadyLoaded:
            # すでに読み込まれていればリロード
            try:
                await self.bot.reload_extension(cog_module)
                elapsed = time.time() - start
                self.cog_status[cog_module] = {
                    "status": "リロード成功",
                    "last_loaded": datetime.now(),
                    "load_time": elapsed,
                    "error": None
                }
                self.load_logs.append((datetime.now(), f"🔄 {cog_module} reloaded in {elapsed:.2f}s"))
                return True
            except Exception as e:
                self.cog_status[cog_module] = {
                    "status": "リロード失敗",
                    "last_loaded": datetime.now(),
                    "load_time": None,
                    "error": str(e)
                }
                self.load_logs.append((datetime.now(), f"❌ Failed to reload {cog_module}: {e}"))
                return False
        except Exception as e:
            self.cog_status[cog_module] = {
                "status": "読み込み失敗",
                "last_loaded": datetime.now(),
                "load_time": None,
                "error": str(e)
            }
            self.load_logs.append((datetime.now(), f"❌ Failed to load {cog_module}: {e}"))
            return False

    # Cog状態一覧コマンド
    @app_commands.command(name="cogstatus", description="Cogの詳細な読み込み状態を表示します")
    async def cogstatus(self, interaction: discord.Interaction):
        if interaction.user.id != DEVELOPER_ID:
            await interaction.response.send_message("❌ このコマンドは開発者のみ使用できます。", ephemeral=True)
            return

        cog_files = glob.glob("cogs/**/*.py", recursive=True)
        lines = []
        for path in cog_files:
            if path.endswith("__init__.py"):
                continue
            module = path[:-3].replace("/", ".").replace("\\", ".")
            info = self.cog_status.get(module)
            if info is None:
                status = "未読み込み"
                last_loaded = "-"
                load_time = "-"
                error = "-"
            else:
                status = info["status"]
                last_loaded = info["last_loaded"].strftime("%Y-%m-%d %H:%M:%S")
                load_time = f"{info['load_time']:.2f}s" if info['load_time'] else "-"
                error = info["error"] if info["error"] else "-"

            lines.append(f"**{module}**\n状態: {status}\n最後の読み込み: {last_loaded}\nロード時間: {load_time}\nエラー: {error}\n")

        embed = discord.Embed(title="Cog詳細ステータス", description="\n".join(lines), color=discord.Color.blue())
        embed.set_footer(text="gakuseiBOT Developer Tool")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ログ表示コマンド
    @app_commands.command(name="loadlogs", description="Cogのロード・リロードのログを表示します")
    async def loadlogs(self, interaction: discord.Interaction):
        if interaction.user.id != DEVELOPER_ID:
            await interaction.response.send_message("❌ このコマンドは開発者のみ使用できます。", ephemeral=True)
            return

        if not self.load_logs:
            await interaction.response.send_message("ログがありません。", ephemeral=True)
            return

        # 最新の20件を表示
        logs_text = "\n".join(f"{ts.strftime('%H:%M:%S')} - {msg}" for ts, msg in self.load_logs[-20:])
        if len(logs_text) > 1900:
            logs_text = logs_text[-1900:]  # 文字数制限対策

        embed = discord.Embed(title="Cogロードログ（最新20件）", description=logs_text, color=discord.Color.orange())
        embed.set_footer(text="gakuseiBOT Developer Tool")
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot):
    admin_cog = AdminCog(bot)
    await bot.add_cog(admin_cog)

    # 既存のCogをロードして状態管理に登録
    # ここは必要に応じて使ってください（例：初回起動時など）
    for ext in list(bot.extensions):
        admin_cog.cog_status[ext] = {
            "status": "読み込み済み",
            "last_loaded": datetime.now(),
            "load_time": None,
            "error": None
        }
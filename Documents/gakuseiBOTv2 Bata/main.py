import discord
from discord.ext import commands, tasks
import os
import asyncio
import time
import json
import glob
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import io

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
# 環境変数から設定を読み込み
PREFIX = os.getenv("PREFIX", "/")
bot = commands.Bot(command_prefix=PREFIX, intents=intents)

# 設定値（環境変数優先）
HEAVY_THRESHOLD = float(os.getenv("HEAVY_THRESHOLD", "1.5"))  # 秒
HEAVY_COGS_PATH = Path("./data/heavy_cogs.json")

# レポートチャンネル（環境変数から取得）
REPORT_CHANNEL_ID = os.getenv("REPORT_CHANNEL_ID")
if REPORT_CHANNEL_ID:
    try:
        REPORT_CHANNEL_ID = int(REPORT_CHANNEL_ID)
    except ValueError:
        print("Warning: REPORT_CHANNEL_ID is not a valid integer")
        REPORT_CHANNEL_ID = None
else:
    print("Warning: REPORT_CHANNEL_ID not set in environment variables")
    REPORT_CHANNEL_ID = None

status_list = [
    discord.Game("動作中..."),
    discord.Game("コマンドを待機中"),
    discord.Game("ヘルプを確認中"),
    discord.Game("ダッシュボードを確認中"),
]

# ログをためるバッファ
log_buffer = io.StringIO()

def log_print(*args, **kwargs):
    print(*args, **kwargs)
    print(*args, **kwargs, file=log_buffer, flush=True)


@bot.event
async def on_ready():
    log_print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    log_print("------")
    await load_all_cogs()
    try:
        synced = await bot.tree.sync()
        log_print(f"[O] Synced {len(synced)} slash commands")
    except Exception as e:
        log_print(f"[X] Slash command sync failed: {e}")
    log_print("Error handler loaded.")
    start_watching(asyncio.get_event_loop())
    change_status.start()

    # 起動時ログをEmbedで送信（チャンネルIDが設定されている場合のみ）
    if REPORT_CHANNEL_ID:
        channel = bot.get_channel(REPORT_CHANNEL_ID)
    else:
        channel = None
    
    if channel and isinstance(channel, discord.TextChannel):
        content = log_buffer.getvalue()
        # Discord Embedは最大4096文字なので分割送信
        chunk_size = 4000
        for i in range(0, len(content), chunk_size):
            embed = discord.Embed(
                title="BOT 起動ログ",
                description=f"```\n{content[i:i+chunk_size]}\n```",
                color=discord.Color.green()
            )
            await channel.send(embed=embed)
    else:
        print("報告用チャンネルが見つかりません。")

@tasks.loop(seconds=10)
async def change_status():
    for status in status_list:
        await bot.change_presence(activity=status)
        await asyncio.sleep(300)

def load_heavy_cog_list():
    if HEAVY_COGS_PATH.exists():
        with open(HEAVY_COGS_PATH, "r") as f:
            return json.load(f)
    return []

def save_heavy_cog_list(cog_list):
    with open(HEAVY_COGS_PATH, "w") as f:
        json.dump(cog_list, f, indent=2)

async def load_all_cogs():
    heavy_cogs = load_heavy_cog_list()

    cog_files = glob.glob("cogs/**/*.py", recursive=True)
    for file_path in cog_files:
        if file_path.endswith('__init__.py'):
            continue

        cog_module = file_path[:-3].replace('/', '.').replace('\\', '.')

        cog_name = cog_module.split('.')[-1]
        if cog_name in heavy_cogs:
            log_print(f"[Skip] Marked heavy cog: {cog_name}")
            continue

        await load_cog_with_timing(cog_module)

async def load_cog_with_timing(cog_module):
    start = time.time()
    try:
        await bot.load_extension(cog_module)
        elapsed = time.time() - start
        log_print(f"[Load] {cog_module} loaded in {elapsed:.2f}s")
        if elapsed > HEAVY_THRESHOLD:
            log_print(f"[Warning] {cog_module} is slow to load ({elapsed:.2f}s)")
    except commands.ExtensionAlreadyLoaded:
        try:
            await bot.reload_extension(cog_module)
            elapsed = time.time() - start
            log_print(f"[Reload] {cog_module} reloaded in {elapsed:.2f}s")
            if elapsed > HEAVY_THRESHOLD:
                log_print(f"[Warning] {cog_module} is slow to reload ({elapsed:.2f}s)")
        except Exception as e:
            log_print(f"[Error] Failed to reload {cog_module}: {e}")
    except Exception as e:
        log_print(f"[Error] Failed to load {cog_module}: {e}")

class CogChangeHandler(FileSystemEventHandler):
    def __init__(self, loop):
        self.loop = loop

    def on_modified(self, event):
        if event.src_path.endswith('.py') and '__init__' not in event.src_path:
            relative_path = os.path.relpath(event.src_path, '.')
            cog_module = relative_path[:-3].replace('/', '.').replace('\\', '.')
            log_print(f"[Watchdog] Change detected in {cog_module}")
            asyncio.run_coroutine_threadsafe(load_cog_with_timing(cog_module), self.loop)

    def on_created(self, event):
        self.on_modified(event)

def start_watching(loop):
    observer = Observer()
    handler = CogChangeHandler(loop)
    observer.schedule(handler, path='./cogs', recursive=True)
    observer.start()
    log_print("[Watchdog] Cog folder monitoring started.")

if __name__ == "__main__":
    if not HEAVY_COGS_PATH.parent.exists():
        os.makedirs(HEAVY_COGS_PATH.parent)
    TOKEN = os.getenv("DISCORD_TOKEN")
    bot.run(TOKEN) if TOKEN else print("DISCORD_TOKEN is not set in environment variables.")
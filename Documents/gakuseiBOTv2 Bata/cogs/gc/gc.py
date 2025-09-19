import discord
from discord.ext import commands
from discord import SyncWebhook
import asyncio
import requests
from datetime import datetime, timedelta
from pytz import timezone

from utils.global_helper import (
    load_settings,
    save_message_log,
    load_message_log,
    contains_prohibited_word,
    is_warning_active,
    bump_check,
    pinned_messages,
    repost_tasks
)

JST = timezone('Asia/Tokyo')
ALLOWED_BOT_IDS = [123456789012345678]  # 許可されたBOT IDリスト（例）

class GlobalChat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.message_log = load_message_log()

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot and message.author.id not in ALLOWED_BOT_IDS:
            return
        await bump_check(message)

        settings = load_settings()
        origin_guild_id = str(message.guild.id)

        if origin_guild_id not in settings:
            return

        if message.channel.id != settings[origin_guild_id]["channel_id"]:
            return

        if contains_prohibited_word(message.content):
            await message.delete()
            await message.channel.send(f"{message.author.mention}さん、このメッセージは不適切な内容を含んでいるため削除されました。")
            return

        if is_warning_active(message.author.id):
            await message.delete()
            await message.channel.send(f"{message.author.mention}さん、あなたは警告中です。")
            return

        embed = discord.Embed(
            description=message.content or "添付ファイル",
            color=discord.Color.blue(),
            timestamp=datetime.now(JST)
        )
        embed.set_author(name=message.author.name, icon_url=message.author.display_avatar.url)
        embed.set_footer(text=f"From {message.guild.name} | gakuseiBOT Global Chat System")

        if message.reference:
            try:
                replied = await message.channel.fetch_message(message.reference.message_id)
                replied_user = replied.author.display_name
                replied_content = replied.content or (replied.embeds[0].description if replied.embeds else "（内容なし）")
                if len(replied_content) > 100:
                    replied_content = replied_content[:100] + "..."
                embed.add_field(name="reply>>>", value=f"{replied_user}：{replied_content}", inline=False)
            except Exception:
                embed.add_field(name="reply>>>", value="メッセージが取得できませんでした", inline=False)

        attachments = [a.url for a in message.attachments]
        if attachments:
            embed.add_field(name="Attachment", value="\n".join(attachments), inline=False)
            for attachment in message.attachments:
                if attachment.filename.endswith(('jpg', 'jpeg', 'png', 'gif')):
                    embed.set_image(url=attachment.url)

        sent_log = []
        for guild_id, config in settings.items():
            if guild_id == origin_guild_id:
                continue
            try:
                data = {
                    "username": "gakuseiBOT Global",
                    "avatar_url": message.author.display_avatar.url,
                    "embeds": [embed.to_dict()]
                }
                webhook_url = config["webhook_url"]
                if "?wait=true" not in webhook_url:
                    webhook_url += "?wait=true"
                response = requests.post(webhook_url, json=data)
                response.raise_for_status()
                res_json = response.json()
                msg_id = res_json.get("id")
                if msg_id:
                    sent_log.append({"guild_id": guild_id, "message_id": msg_id})
            except Exception as e:
                print(f"Webhook送信失敗（{guild_id}）: {e}")

        try:
            await message.add_reaction("✅")
            await message.add_reaction("🗑️")
            await message.add_reaction("✏️")
        except Exception as e:
            print("リアクションエラー:", e)

        self.message_log[str(message.id)] = {
            "user_id": message.author.id,
            "channel_id": message.channel.id,
            "timestamp": datetime.now(JST).isoformat(),
            "sent_messages": sent_log
        }
        save_message_log(self.message_log)

        if str(message.channel.id) in pinned_messages:
            if str(message.channel.id) in repost_tasks:
                repost_tasks[str(message.channel.id)].cancel()
            repost_tasks[str(message.channel.id)] = asyncio.create_task(schedule_repost(message.channel))

        await self.bot.process_commands(message)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        # (省略：先ほどのコードのリアクション処理をそのまま記述)
        ...
        pass

async def setup(bot):
    await bot.add_cog(GlobalChat(bot))
    print("GlobalChat Cog loaded successfully.")
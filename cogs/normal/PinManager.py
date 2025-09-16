import discord
from discord import app_commands
from discord.ext import commands

class PinManager(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # {channel_id: message_id} を保持
        self.pinned_messages = {}

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"✅ {self.bot.user} でログインしました")
        # 各チャンネルの履歴をチェックして固定情報を復元
        for guild in self.bot.guilds:
            for channel in guild.text_channels:
                try:
                    async for msg in channel.history(limit=50):
                        if msg.author != self.bot.user or not msg.embeds:
                            continue
                        embed = msg.embeds[0]
                        # タイトルで固定メッセージか判定
                        if embed.title == "📌 固定メッセージ":
                            self.pinned_messages[channel.id] = msg.id
                            break
                except Exception:
                    continue
        await self.bot.tree.sync()
        print("✅ アプリコマンド同期完了")

    # ==============================
    # 固定メッセージ作成（コンテキストメニュー）
    # ==============================
    @app_commands.context_menu(name="📌 このメッセージを固定表示")
    async def pin_message(self, interaction: discord.Interaction, message: discord.Message):
        channel = message.channel

        # 本文Embed
        embed_main = discord.Embed(
            title="固定メッセージ",
            description=message.content or "（本文なし）",
            color=discord.Color.blue()
        )
        embed_main.set_author(name=message.author.display_name, icon_url=message.author.display_avatar.url)
        # 隠し情報: 元メッセージIDもEmbedに
        embed_main.set_footer(text=f"元ID:{message.id} | {message.created_at.strftime('%Y/%m/%d %H:%M:%S')}")

        embeds = [embed_main]

        # 添付ファイルがある場合は別Embed
        if message.attachments:
            file_urls = "\n".join([att.url for att in message.attachments])
            embed_files = discord.Embed(
                title="📎 添付ファイル",
                description=file_urls,
                color=discord.Color.green()
            )
            embeds.append(embed_files)

        # 既存の固定メッセージがあれば削除
        if channel.id in self.pinned_messages:
            try:
                old_msg = await channel.fetch_message(self.pinned_messages[channel.id])
                await old_msg.delete()
            except discord.NotFound:
                pass

        # 新規固定メッセージ送信
        new_msg = await channel.send(embeds=embeds)
        self.pinned_messages[channel.id] = new_msg.id
        await interaction.response.send_message("固定しました。", ephemeral=True)

    # ==============================
    # 固定解除（コンテキストメニュー）
    # ==============================
    @app_commands.context_menu(name="❌ 固定解除")
    async def unpin_message(self, interaction: discord.Interaction, message: discord.Message):
        channel = message.channel

        if channel.id in self.pinned_messages:
            try:
                pinned_msg = await channel.fetch_message(self.pinned_messages[channel.id])
                await pinned_msg.delete()
            except discord.NotFound:
                pass
            del self.pinned_messages[channel.id]
            await interaction.response.send_message("❌ 固定を解除しました。", ephemeral=True)
        else:
            await interaction.response.send_message("⚠️ 固定されていません。", ephemeral=True)

    # ==============================
    # 新規メッセージで固定再配置
    # ==============================
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        channel = message.channel
        if channel.id in self.pinned_messages:
            try:
                old_msg = await channel.fetch_message(self.pinned_messages[channel.id])
                embeds = old_msg.embeds
                await old_msg.delete()

                new_msg = await channel.send(embeds=embeds)
                self.pinned_messages[channel.id] = new_msg.id

            except discord.NotFound:
                pass


async def setup(bot: commands.Bot):
    await bot.add_cog(PinManager(bot))

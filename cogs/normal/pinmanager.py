import asyncio

import discord
from discord import app_commands
from discord.ext import commands


def _can_manage_fixed_messages(interaction: discord.Interaction) -> bool:
    if interaction.guild is None or not isinstance(interaction.user, discord.Member):
        return False
    permissions = interaction.user.guild_permissions
    return permissions.manage_messages or permissions.administrator


class PinManager(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.pinned_messages: dict[int, int] = {}
        self._cache_initialized = False
        self._channel_locks: dict[int, asyncio.Lock] = {}
        self.pin_context_menu = app_commands.ContextMenu(
            name="このメッセージを固定表示",
            callback=self.pin_message,
        )
        self.unpin_context_menu = app_commands.ContextMenu(
            name="固定解除",
            callback=self.unpin_message,
        )

    async def cog_load(self) -> None:
        self.bot.tree.add_command(self.pin_context_menu)
        self.bot.tree.add_command(self.unpin_context_menu)
        if self.bot.is_ready():
            await self._initialize_cache()

    async def cog_unload(self) -> None:
        self.bot.tree.remove_command(self.pin_context_menu.name, type=self.pin_context_menu.type)
        self.bot.tree.remove_command(self.unpin_context_menu.name, type=self.unpin_context_menu.type)

    def _lock_for(self, channel_id: int) -> asyncio.Lock:
        return self._channel_locks.setdefault(channel_id, asyncio.Lock())

    async def _initialize_cache(self) -> None:
        if self._cache_initialized:
            return
        for guild in self.bot.guilds:
            for channel in guild.text_channels:
                try:
                    async for message in channel.history(limit=50):
                        if message.author != self.bot.user or not message.embeds:
                            continue
                        if message.embeds[0].title == "固定メッセージ":
                            self.pinned_messages[channel.id] = message.id
                            break
                except (discord.Forbidden, discord.HTTPException):
                    continue
        self._cache_initialized = True
        print("[PinManager] Pinned-message cache initialized.")

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        await self._initialize_cache()

    @app_commands.default_permissions(manage_messages=True)
    async def pin_message(self, interaction: discord.Interaction, message: discord.Message) -> None:
        if not _can_manage_fixed_messages(interaction):
            await interaction.response.send_message("この操作には「メッセージの管理」権限が必要です。", ephemeral=True)
            return
        channel = message.channel
        if not hasattr(channel, "send") or not hasattr(channel, "fetch_message"):
            await interaction.response.send_message("このチャンネルではメッセージを固定表示できません。", ephemeral=True)
            return

        embed_main = discord.Embed(title="固定メッセージ", description=message.content or "（本文なし）", color=discord.Color.blue())
        embed_main.set_author(name=message.author.display_name, icon_url=message.author.display_avatar.url)
        embed_main.set_footer(text=f"元ID:{message.id} | {message.created_at.strftime('%Y/%m/%d %H:%M:%S')}")
        embeds = [embed_main]
        if message.attachments:
            file_urls = "\n".join(attachment.url for attachment in message.attachments)
            embeds.append(discord.Embed(title="添付ファイル", description=file_urls[:4000], color=discord.Color.green()))

        async with self._lock_for(channel.id):
            existing_id = self.pinned_messages.get(channel.id)
            if existing_id is not None:
                try:
                    old_message = await channel.fetch_message(existing_id)
                    await old_message.delete()
                except discord.NotFound:
                    pass
                except discord.HTTPException:
                    await interaction.response.send_message("既存の固定メッセージを更新できませんでした。Bot の権限を確認してください。", ephemeral=True)
                    return
            try:
                new_message = await channel.send(embeds=embeds)
            except (discord.Forbidden, discord.HTTPException):
                await interaction.response.send_message("固定メッセージを送信できませんでした。Bot の権限を確認してください。", ephemeral=True)
                return
            self.pinned_messages[channel.id] = new_message.id
        await interaction.response.send_message("固定しました。", ephemeral=True)

    @app_commands.default_permissions(manage_messages=True)
    async def unpin_message(self, interaction: discord.Interaction, message: discord.Message) -> None:
        if not _can_manage_fixed_messages(interaction):
            await interaction.response.send_message("この操作には「メッセージの管理」権限が必要です。", ephemeral=True)
            return
        channel = message.channel
        async with self._lock_for(channel.id):
            pinned_id = self.pinned_messages.get(channel.id)
            if pinned_id is None:
                await interaction.response.send_message("このチャンネルには固定メッセージがありません。", ephemeral=True)
                return
            try:
                pinned_message = await channel.fetch_message(pinned_id)
                await pinned_message.delete()
            except discord.NotFound:
                pass
            except (discord.Forbidden, discord.HTTPException):
                await interaction.response.send_message("固定を解除できませんでした。Bot の権限を確認してください。", ephemeral=True)
                return
            if self.pinned_messages.get(channel.id) == pinned_id:
                self.pinned_messages.pop(channel.id, None)
        await interaction.response.send_message("固定を解除しました。", ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return
        channel = message.channel
        if not hasattr(channel, "fetch_message"):
            return
        async with self._lock_for(channel.id):
            pinned_id = self.pinned_messages.get(channel.id)
            if pinned_id is None:
                return
            try:
                old_message = await channel.fetch_message(pinned_id)
                embeds = old_message.embeds
                await old_message.delete()
                new_message = await channel.send(embeds=embeds)
                self.pinned_messages[channel.id] = new_message.id
            except discord.NotFound:
                if self.pinned_messages.get(channel.id) == pinned_id:
                    self.pinned_messages.pop(channel.id, None)
            except (discord.Forbidden, discord.HTTPException):
                return


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(PinManager(bot))

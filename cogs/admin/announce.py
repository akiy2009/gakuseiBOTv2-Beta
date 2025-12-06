import discord
from discord.ext import commands

DEVELOPER_ID = 1241366063858450485

class BroadcastModal(discord.ui.Modal, title="📢 お知らせ送信フォーム"):
    title_input = discord.ui.TextInput(
        label="タイトル",
        placeholder="例）緊急メンテナンスのお知らせ",
        max_length=100
    )
    content_input = discord.ui.TextInput(
        label="本文",
        style=discord.TextStyle.paragraph,
        placeholder="詳細内容をここに記入してください。",
        max_length=2000
    )

    def __init__(self, bot: commands.Bot, inter: discord.Interaction):
        super().__init__()
        self.bot = bot
        self.inter = inter

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id != DEVELOPER_ID:
            await interaction.response.send_message("❌ あなたはこの機能を使用できません。", ephemeral=True)
            return

        embed = discord.Embed(
            title=self.title_input.value,
            description=self.content_input.value,
            color=discord.Color.blurple()
        )
        embed.set_footer(text="Powered by gakuseiBOT")

        success, fallback_dm, skipped = 0, 0, 0

        for guild in self.bot.guilds:
            sent = False
            try:
                # 優先1: システム通知チャンネル
                if guild.system_channel and guild.system_channel.permissions_for(guild.me).send_messages:
                    await guild.system_channel.send(embed=embed)
                    success += 1
                    sent = True
                # 優先2: オーナーDM
                elif not sent and guild.owner:
                    try:
                        await guild.owner.send(embed=embed)
                        fallback_dm += 1
                        sent = True
                    except discord.Forbidden:
                        skipped += 1
                else:
                    skipped += 1
            except Exception as e:
                print(f"❌ 送信失敗 ({guild.name}): {e}")
                skipped += 1

        await interaction.response.send_message(
            f"✅ お知らせ送信完了！\n"
            f"・システム通知チャンネル送信: {success}\n"
            f"・オーナーDM送信: {fallback_dm}\n"
            f"・送信できなかった: {skipped}",
            ephemeral=True
        )

class BroadcastModalCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @discord.app_commands.command(name="announce", description="全サーバーにお知らせを送信（開発者限定）")
    async def broadcast(self, interaction: discord.Interaction):
        if interaction.user.id != DEVELOPER_ID:
            await interaction.response.send_message("❌ このコマンドは開発者のみ使用できます。", ephemeral=True)
            return

        await interaction.response.send_modal(BroadcastModal(self.bot, interaction))

    @commands.Cog.listener()
    async def on_ready(self):
        try:
            synced = await self.bot.tree.sync()
            print(f"[🔃 Slash Command Sync] {len(synced)} commands")
        except Exception as e:
            print(f"[❌ Slash Command Sync Error] {e}")

async def setup(bot: commands.Bot):

    await bot.add_cog(BroadcastModalCog(bot))

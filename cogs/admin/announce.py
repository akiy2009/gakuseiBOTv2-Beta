import os

import discord
from discord.ext import commands


def _developer_id() -> int | None:
    raw_value = os.getenv("DEVELOPER_ID", "").strip()
    if not raw_value:
        return None
    try:
        return int(raw_value)
    except ValueError:
        return None


class BroadcastModal(discord.ui.Modal, title="お知らせ送信フォーム"):
    title_input = discord.ui.TextInput(
        label="タイトル",
        placeholder="例）緊急メンテナンスのお知らせ",
        max_length=100,
    )
    content_input = discord.ui.TextInput(
        label="本文",
        style=discord.TextStyle.paragraph,
        placeholder="詳細内容をここに記入してください。",
        max_length=2000,
    )

    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction) -> None:
        developer_id = _developer_id()
        if developer_id is None or interaction.user.id != developer_id:
            await interaction.response.send_message(
                "この機能は設定済みの開発者のみ使用できます。",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title=self.title_input.value,
            description=self.content_input.value,
            color=discord.Color.blurple(),
        )
        embed.set_footer(text="Powered by gakuseiBOT")

        sent_to_channel = 0
        sent_by_dm = 0
        skipped = 0

        for guild in self.bot.guilds:
            channel = guild.system_channel
            bot_member = guild.me
            if (
                channel is not None
                and bot_member is not None
                and channel.permissions_for(bot_member).send_messages
            ):
                try:
                    await channel.send(embed=embed)
                    sent_to_channel += 1
                    continue
                except (discord.Forbidden, discord.HTTPException):
                    pass

            try:
                owner = guild.owner or await guild.fetch_member(guild.owner_id)
                await owner.send(embed=embed)
                sent_by_dm += 1
            except (discord.Forbidden, discord.NotFound, discord.HTTPException):
                skipped += 1

        await interaction.response.send_message(
            "お知らせ送信が完了しました。\n"
            f"・チャンネル送信: {sent_to_channel}\n"
            f"・オーナーDM送信: {sent_by_dm}\n"
            f"・送信できなかったサーバー: {skipped}",
            ephemeral=True,
        )


class BroadcastModalCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @discord.app_commands.command(
        name="announce",
        description="全サーバーにお知らせを送信（開発者限定）",
    )
    async def broadcast(self, interaction: discord.Interaction) -> None:
        developer_id = _developer_id()
        if developer_id is None or interaction.user.id != developer_id:
            await interaction.response.send_message(
                "この機能は設定済みの開発者のみ使用できます。",
                ephemeral=True,
            )
            return

        await interaction.response.send_modal(BroadcastModal(self.bot))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(BroadcastModalCog(bot))

from urllib.parse import urlsplit

import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Modal, TextInput


def _valid_image_url(image_url: str) -> bool:
    try:
        parsed = urlsplit(image_url)
        return (
            parsed.scheme == "https"
            and bool(parsed.hostname)
            and parsed.username is None
            and parsed.password is None
            and parsed.path.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp"))
        )
    except ValueError:
        return False


class EmbedModal(Modal):
    def __init__(self):
        super().__init__(title="埋め込みを作成")
        self.title_input = TextInput(label="タイトル", placeholder="埋め込みメッセージのタイトルを入力してください", max_length=256, required=True)
        self.add_item(self.title_input)
        self.description_input = TextInput(label="メッセージ", style=discord.TextStyle.paragraph, placeholder="埋め込みメッセージの内容を入力してください", max_length=2048, required=True)
        self.add_item(self.description_input)
        self.image_url_input = TextInput(label="画像URL（任意）", placeholder="https://example.com/image.png", max_length=500, required=False)
        self.add_item(self.image_url_input)
        self.color_input = TextInput(label="色コード（任意）", placeholder="例: FF0000（デフォルトで青）", max_length=6, required=False)
        self.add_item(self.color_input)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        color_text = self.color_input.value.strip().removeprefix("#")
        if color_text and (
            len(color_text) != 6
            or any(character not in "0123456789abcdefABCDEF" for character in color_text)
        ):
            await interaction.response.send_message("色コードが無効です。6桁の16進数（例: FF0000）を入力してください。", ephemeral=True)
            return

        embed = discord.Embed(
            title=self.title_input.value,
            description=self.description_input.value,
            color=int(color_text, 16) if color_text else discord.Color.blue().value,
        )

        image_url = self.image_url_input.value.strip()
        if image_url:
            if not _valid_image_url(image_url):
                await interaction.response.send_message(
                    "HTTPS の画像URL（PNG、JPG、GIF、WebP）を入力してください。",
                    ephemeral=True,
                )
                return
            embed.set_image(url=image_url)

        await interaction.response.send_message(embed=embed)


class EmbedCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="embed", description="埋め込みメッセージを作成します")
    async def createembed(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(EmbedModal())


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(EmbedCog(bot))

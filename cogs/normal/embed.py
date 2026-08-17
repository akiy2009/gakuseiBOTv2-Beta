import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Modal, TextInput


class EmbedModal(Modal):
    def __init__(self):
        super().__init__(title="埋め込みを作成")

        self.title_input = TextInput(
            label="タイトル",
            placeholder="埋め込みメッセージのタイトルを入力してください",
            max_length=256,
            required=True
        )
        self.add_item(self.title_input)

        self.description_input = TextInput(
            label="メッセージ",
            style=discord.TextStyle.paragraph,
            placeholder="埋め込みメッセージの内容を入力してください",
            max_length=2048,
            required=True
        )
        self.add_item(self.description_input)

        self.image_url_input = TextInput(
            label="画像URL（任意）",
            placeholder="画像URLを入力",
            required=False
        )
        self.add_item(self.image_url_input)

        self.color_input = TextInput(
            label="色コード（任意）",
            placeholder="例: FF0000（デフォルトで青）",
            max_length=6,
            min_length=0,
            required=False
        )
        self.add_item(self.color_input)

    async def on_submit(self, interaction: discord.Interaction):
        # 色コードの取得と変換
        color_input = self.color_input.value.strip()
        try:
            color_value = int(color_input, 16) if color_input else discord.Color.blue().value
        except ValueError:
            await interaction.response.send_message(
                "❌ 色コードが無効です。\n6桁の16進数（例: `FF0000`）を入力してください。",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title=self.title_input.value,
            description=self.description_input.value,
            color=color_value
        )

        image_url = self.image_url_input.value.strip()
        if image_url:
            if image_url.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
                embed.set_image(url=image_url)
            else:
                await interaction.response.send_message("❌ 有効な画像URLを入力してください（.png, .jpg など）", ephemeral=True)
                return

        await interaction.response.send_message(embed=embed)

class EmbedCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="embed", description="埋め込みメッセージを作成します")
    async def createembed(self, interaction: discord.Interaction):
        await interaction.response.send_modal(EmbedModal())

async def setup(bot: commands.Bot):
    if not bot.get_cog("EmbedCog"):

        await bot.add_cog(EmbedCog(bot))

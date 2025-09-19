import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Modal, TextInput

class EmbedModal(Modal):
    def __init__(self):
        super().__init__(title="Embedを作成")

        self.title_input = TextInput(
            label="タイトル",
            placeholder="Embedのタイトルを入力してください",
            max_length=256,
            required=True
        )
        self.add_item(self.title_input)

        self.description_input = TextInput(
            label="メッセージ",
            style=discord.TextStyle.paragraph,
            placeholder="Embedの内容を入力してください",
            max_length=2048,
            required=True
        )
        self.add_item(self.description_input)

        self.image_url_input = TextInput(
            label="画像URL（任意）",
            placeholder="画像URLを入力（空欄可）",
            required=False
        )
        self.add_item(self.image_url_input)

        self.color_input = TextInput(
            label="色コード（任意）",
            placeholder="例: FF0000（未入力で青）",
            max_length=6,
            min_length=0,
            required=False
        )
        self.add_item(self.color_input)

    async def on_submit(self, interaction: discord.Interaction):
        color_input = self.color_input.value.strip()
        try:
            color_value = int(color_input, 16) if color_input else discord.Color.blue().value
        except ValueError:
            await interaction.response.send_message("色コードが無効です。6桁の16進数で入力してください。", ephemeral=True)
            return

        embed = discord.Embed(
            title=self.title_input.value,
            description=self.description_input.value,
            color=color_value
        )
        if self.image_url_input.value.strip():
            embed.set_image(url=self.image_url_input.value.strip())

        await interaction.response.send_message(embed=embed)

class EmbedCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="embed", description="Embedメッセージをモーダルから作成します")
    async def createembed(self, interaction: discord.Interaction):
        await interaction.response.send_modal(EmbedModal())

async def setup(bot):
    await bot.add_cog(EmbedCog(bot))
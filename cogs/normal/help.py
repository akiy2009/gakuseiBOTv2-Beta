import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Select

class HelpSelect(Select):
    def __init__(self, commands_list):
        options = [
            discord.SelectOption(label=cmd.name, description=(cmd.description[:100] if cmd.description else "説明なし"))
            for cmd in commands_list
        ]
        super().__init__(placeholder="コマンドを選択してください", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        selected_command = next(cmd for cmd in self.view.commands if cmd.name == self.values[0])
        embed = discord.Embed(
            title=f"/{selected_command.name} の説明",
            description=selected_command.description or "説明がありません。",
            color=discord.Color.blue()
        )
        await interaction.response.edit_message(embed=embed, view=self.view)

class HelpView(View):
    def __init__(self, commands_list):
        super().__init__(timeout=180)
        self.commands = commands_list
        self.add_item(HelpSelect(commands_list))

class HelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="コマンド一覧を表示し選択で詳細を確認できます")
    async def help(self, interaction: discord.Interaction):
        commands_list = list(self.bot.tree.get_commands())  # hidden判定を外す

        embed = discord.Embed(
            title="Help - コマンド一覧",
            description="下のメニューからコマンドを選択すると詳細が表示されます。",
            color=discord.Color.blue()
        )
        embed.add_field(name="コマンド一覧", value="\n".join(f"/{cmd.name}" for cmd in commands_list), inline=False)

        view = HelpView(commands_list)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(HelpCog(bot))
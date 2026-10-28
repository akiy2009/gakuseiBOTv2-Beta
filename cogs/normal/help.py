import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Select, View


class HelpSelect(Select):
    def __init__(self, commands_list: list[app_commands.Command]):
        options = [
            discord.SelectOption(
                label=command.name,
                description=(command.description or "説明なし")[:100],
            )
            for command in commands_list[:25]
        ]
        super().__init__(
            placeholder="コマンドを選択してください",
            options=options,
            min_values=1,
            max_values=1,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        commands_in_view = self.view.commands if self.view else []
        selected_command = next(
            (command for command in commands_in_view if command.name == self.values[0]),
            None,
        )
        if selected_command is None:
            await interaction.response.send_message(
                "選択したコマンドが見つかりません。/help をもう一度実行してください。",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title=f"/{selected_command.name} の説明",
            description=selected_command.description or "説明がありません。",
            color=discord.Color.blue(),
        )
        await interaction.response.edit_message(embed=embed, view=self.view)


class HelpView(View):
    def __init__(self, commands_list: list[app_commands.Command]):
        super().__init__(timeout=180)
        self.commands = commands_list
        self.add_item(HelpSelect(commands_list))


class HelpCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="help",
        description="コマンド一覧を表示し、選択して詳細を確認できます",
    )
    async def help(self, interaction: discord.Interaction) -> None:
        all_commands = sorted(
            (
                command
                for command in self.bot.tree.get_commands()
                if isinstance(command, app_commands.Command)
            ),
            key=lambda command: command.name,
        )
        selectable_commands = all_commands[:25]

        command_lines = [
            f"/{command.name} — {command.description or '説明なし'}"
            for command in all_commands
        ]
        description = "\n".join(command_lines) or "登録されているコマンドはありません。"
        if len(description) > 4000:
            description = description[:3997] + "..."

        embed = discord.Embed(
            title="Help - コマンド一覧",
            description=description,
            color=discord.Color.blue(),
        )
        if len(all_commands) > 25:
            embed.set_footer(text="選択メニューには先頭25件を表示しています。")

        await interaction.response.send_message(
            embed=embed,
            view=HelpView(selectable_commands) if selectable_commands else None,
            ephemeral=True,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(HelpCog(bot))

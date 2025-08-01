import discord
from discord import app_commands
from discord.ext import commands

class RoleSelect(discord.ui.Select):
    def __init__(self, role_dict: dict[str, discord.Role]):
        self.role_dict = role_dict
        options = [
            discord.SelectOption(label=role.name, value=str(role.id))
            for role in role_dict.values()
        ]

        super().__init__(
            placeholder="ロールを選択してください（複数可）",
            min_values=0,
            max_values=len(options),
            options=options,
            custom_id="role_select"
        )

    async def callback(self, interaction: discord.Interaction):
        member = interaction.user
        selected_ids = set(map(int, self.values))
        all_ids = set(role.id for role in self.role_dict.values())

        added = []
        removed = []

        for role_id in all_ids:
            role = interaction.guild.get_role(role_id)
            if not role:
                continue
            if role_id in selected_ids and role not in member.roles:
                await member.add_roles(role, reason="ロールパネルで選択")
                added.append(role.name)
            elif role_id not in selected_ids and role in member.roles:
                await member.remove_roles(role, reason="ロールパネルで非選択")
                removed.append(role.name)

        msg = ""
        if added:
            msg += f"✅ 付与: {', '.join(added)}\n"
        if removed:
            msg += f"❌ 剥奪: {', '.join(removed)}\n"
        if not msg:
            msg = "変更はありませんでした。"

        await interaction.response.send_message(msg, ephemeral=True)
    
class PanelRole(discord.ui.Select):
    def __init__(self, roles: list[discord.Role], description: str):
        self.roles = roles
        self.description = description
        options = [
            discord.SelectOption(label=role.name, value=str(role.id))
            for role in roles
        ]
        if not options:
            options = [discord.SelectOption(label="利用可能なロールがありません", value="none", default=True, description="サーバーに選択可能なロールがありません")]
        super().__init__(
            placeholder="ロールを選択してください", 
            options=options, 
            max_values=min(15, len(options)), 
            min_values=1 if len(options) > 1 else 0
        )
    
    async def callback(self, interaction: discord.Interaction):
        all_roles = self.roles
        
        view = discord.ui.View()
        view.add_item(RoleSelect(all_roles))
        
        await interaction.channel.send(content="ロールを選択してください。" if not self.description else self.description, view=view)
    
        await interaction.response.edit_message(content="✅ ロール選択パネルを作成しました。", view=None)


class RoleSelectView(discord.ui.View):
    def __init__(self, role_dict: dict[str, discord.Role]):
        super().__init__(timeout=None)
        self.add_item(RoleSelect(role_dict))


class RolePanelCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.views_to_register = []


    ### Protips: discord APIでは、コマンドで複数選択といったようなことはできません。
    
    @app_commands.command(name = "rolepanel", description = "ロール選択パネルを作成します。")
    async def createpanel(self, interaction: discord.Interaction, description: str = "以下のメニューからロールを選択してください。"):
        view = discord.ui.View()
        roles = [role for role in interaction.guild.roles if not role.is_bot_managed() and not role.is_default() and not role.is_integration() and not role.is_premium_subscriber()]
        view.add_item(PanelRole(roles, description))
        await interaction.response.send_message("追加するロールを選択してください。", view=view, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(RolePanelCog(bot))
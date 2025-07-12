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

class RoleSelectView(discord.ui.View):
    def __init__(self, role_dict: dict[str, discord.Role]):
        super().__init__(timeout=None)
        self.add_item(RoleSelect(role_dict))


class RolePanelCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.views_to_register = []

    @app_commands.command(name="createpanel", description="ロール選択パネルを作成します")
    @app_commands.describe(
        description="パネルの説明文（省略可）",
        roles="選択可能にするロール（最大15個）"
    )
    async def createpanel(
        self,
        interaction: discord.Interaction,
        description: str = "以下のメニューからロールを選択してください。",
        roles: list[discord.Role] = []
    ):
        if not roles:
            await interaction.response.send_message("⚠️ ロールを1つ以上指定してください。", ephemeral=True)
            return

        if len(roles) > 15:
            await interaction.response.send_message("⚠️ 最大15個までロールを指定できます。", ephemeral=True)
            return

        role_dict = {role.name: role for role in roles}
        embed = discord.Embed(
            title="🎭 ロール選択パネル",
            description=description,
            color=discord.Color.blurple()
        )

        view = RoleSelectView(role_dict)
        self.bot.add_view(view)  # 再起動後も動作するよう登録
        await interaction.response.send_message(embed=embed, view=view)

    @commands.Cog.listener()
    async def on_ready(self):
        print("[RolePanelCog] コグ読み込み完了・スラッシュコマンド同期を試みます")
        try:
            synced = await self.bot.tree.sync()
            print(f"✅ スラッシュコマンド {len(synced)} 件同期しました。")
        except Exception as e:
            print(f"❌ スラッシュコマンド同期失敗: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(RolePanelCog(bot))
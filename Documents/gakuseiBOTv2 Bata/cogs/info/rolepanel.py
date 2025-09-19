import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional

class RoleSelect(discord.ui.Select):
    def __init__(self, role_ids: list[int]):
        self.role_ids = role_ids
        options = [
            discord.SelectOption(label=f"ロールID: {rid}", value=str(rid))
            for rid in role_ids
        ]
        super().__init__(
            placeholder="ロールを選択（選択済みは再選択で剥奪）",
            min_values=0,
            max_values=len(options),
            options=options,
            custom_id=f"rp_{','.join(map(str, role_ids))}"
        )

    async def callback(self, interaction: discord.Interaction):
        member = interaction.user
        selected_ids = set(map(int, self.values))
        added, removed = [], []

        for rid in self.role_ids:
            role = interaction.guild.get_role(rid)
            if not role:
                continue
            if rid in selected_ids and role not in member.roles:
                await member.add_roles(role, reason="ロールパネル: 付与")
                added.append(role.name)
            elif rid in selected_ids and role in member.roles:
                await member.remove_roles(role, reason="ロールパネル: 剥奪")
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
    def __init__(self, role_ids: list[int]):
        super().__init__(timeout=None)
        self.add_item(RoleSelect(role_ids))


class RolePanelCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="createpanel", description="ロール選択パネルを作成")
    @app_commands.describe(
        description="パネルの説明文（省略可）",
        role1="ロール1", role2="ロール2", role3="ロール3", role4="ロール4", role5="ロール5",
        role6="ロール6", role7="ロール7", role8="ロール8", role9="ロール9", role10="ロール10",
        role11="ロール11", role12="ロール12", role13="ロール13", role14="ロール14", role15="ロール15"
    )
    async def createpanel(
        self,
        interaction: discord.Interaction,
        description: Optional[str] = "以下からロールを選択してください。",
        role1: Optional[discord.Role] = None,
        role2: Optional[discord.Role] = None,
        role3: Optional[discord.Role] = None,
        role4: Optional[discord.Role] = None,
        role5: Optional[discord.Role] = None,
        role6: Optional[discord.Role] = None,
        role7: Optional[discord.Role] = None,
        role8: Optional[discord.Role] = None,
        role9: Optional[discord.Role] = None,
        role10: Optional[discord.Role] = None,
        role11: Optional[discord.Role] = None,
        role12: Optional[discord.Role] = None,
        role13: Optional[discord.Role] = None,
        role14: Optional[discord.Role] = None,
        role15: Optional[discord.Role] = None,
    ):
        roles = [r for r in [role1, role2, role3, role4, role5, role6, role7, role8, role9,
                             role10, role11, role12, role13, role14, role15] if r]
        if not roles:
            await interaction.response.send_message("⚠️ ロールを1つ以上指定してください。", ephemeral=True)
            return

        role_ids = [r.id for r in roles]
        view = RoleSelectView(role_ids)

        embed = discord.Embed(
            title="🎭 ロール選択パネル",
            description=description,
            color=discord.Color.blurple()
        )
        await interaction.response.send_message(embed=embed, view=view)

    @commands.Cog.listener()
    async def on_ready(self):
        print("[RolePanel] View復元開始")
        for guild in self.bot.guilds:
            for channel in guild.text_channels:
                try:
                    async for msg in channel.history(limit=50):
                        if msg.author.id != self.bot.user.id:
                            continue
                        if not msg.components:
                            continue
                        for row in msg.components:
                            for comp in row.children:
                                if hasattr(comp, "custom_id") and comp.custom_id.startswith("rp_"):
                                    try:
                                        role_ids = list(map(int, comp.custom_id[3:].split(",")))
                                        self.bot.add_view(RoleSelectView(role_ids), message_id=msg.id)
                                        print(f"✅ View復元: {channel.name} / msg.id={msg.id}")
                                    except Exception as e:
                                        print(f"❌ View復元失敗: {e}")
                except Exception as e:
                    print(f"❌ チャンネル取得失敗: {channel.name} - {e}")

        try:
            synced = await self.bot.tree.sync()
            print(f"✅ スラッシュコマンド同期: {len(synced)} 件")
        except Exception as e:
            print(f"❌ コマンド同期失敗: {e}")


async def setup(bot: commands.Bot):
    await bot.add_cog(RolePanelCog(bot))


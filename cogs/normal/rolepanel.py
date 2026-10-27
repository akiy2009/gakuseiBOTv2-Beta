import discord
from discord import app_commands
from discord.ext import commands


_UNSAFE_ROLE_PERMISSIONS = (
    "administrator",
    "manage_guild",
    "manage_roles",
    "manage_channels",
    "manage_webhooks",
    "manage_messages",
    "manage_nicknames",
    "manage_events",
    "manage_threads",
    "manage_expressions",
    "create_guild_expressions",
    "view_audit_log",
    "moderate_members",
    "mention_everyone",
    "kick_members",
    "ban_members",
)


def _is_safe_self_assignable(role: discord.Role, bot_member: discord.Member) -> bool:
    if (
        role.is_default()
        or role.is_bot_managed()
        or role.is_integration()
        or role.is_premium_subscriber()
        or role >= bot_member.top_role
    ):
        return False
    return not any(
        getattr(role.permissions, permission, False)
        for permission in _UNSAFE_ROLE_PERMISSIONS
    )


class RoleSelect(discord.ui.Select):
    def __init__(self, roles: list[discord.Role]):
        self.roles_by_id = {role.id: role for role in roles[:25]}
        options = [
            discord.SelectOption(label=role.name[:100], value=str(role.id))
            for role in roles[:25]
        ]
        super().__init__(
            placeholder="ロールを選択してください（複数可）",
            min_values=0,
            max_values=max(1, len(options)),
            options=options,
            custom_id="role_select",
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild
        member = interaction.user
        if guild is None or not isinstance(member, discord.Member):
            await interaction.response.send_message(
                "このパネルはサーバー内でのみ使用できます。",
                ephemeral=True,
            )
            return

        bot_member = guild.me
        if bot_member is None:
            await interaction.response.send_message(
                "Bot のサーバーメンバー情報を取得できませんでした。",
                ephemeral=True,
            )
            return

        selected_ids = {int(value) for value in self.values}
        added: list[str] = []
        removed: list[str] = []
        failed: list[str] = []

        for role_id in self.roles_by_id:
            current_role = guild.get_role(role_id)
            if current_role is None or not _is_safe_self_assignable(current_role, bot_member):
                continue

            try:
                if role_id in selected_ids and current_role not in member.roles:
                    await member.add_roles(current_role, reason="セルフサービスのロールパネル")
                    added.append(current_role.name)
                elif role_id not in selected_ids and current_role in member.roles:
                    await member.remove_roles(current_role, reason="セルフサービスのロールパネル")
                    removed.append(current_role.name)
            except (discord.Forbidden, discord.HTTPException):
                failed.append(current_role.name)

        lines = []
        if added:
            lines.append("付与: " + ", ".join(added))
        if removed:
            lines.append("解除: " + ", ".join(removed))
        if failed:
            lines.append("変更できなかったロール: " + ", ".join(failed))
        if not lines:
            lines.append("変更はありませんでした。")

        await interaction.response.send_message("\n".join(lines), ephemeral=True)


class PanelRole(discord.ui.Select):
    def __init__(self, roles: list[discord.Role], description: str):
        self.roles_by_id = {role.id: role for role in roles[:25]}
        self.description_text = description
        options = [
            discord.SelectOption(
                label=role.name[:100],
                value=str(role.id),
                description=f"ロールID: {role.id}",
            )
            for role in roles[:25]
        ]
        super().__init__(
            placeholder="パネルに追加するロールを選択",
            options=options,
            max_values=max(1, len(options)),
            min_values=1,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        selected_roles = [
            self.roles_by_id[int(value)]
            for value in self.values
            if int(value) in self.roles_by_id
        ]
        if not selected_roles:
            await interaction.response.edit_message(
                content="選択できるロールがありませんでした。",
                view=None,
            )
            return

        channel = interaction.channel
        if channel is None or not hasattr(channel, "send"):
            await interaction.response.edit_message(
                content="このチャンネルにはパネルを送信できません。",
                view=None,
            )
            return

        view = discord.ui.View(timeout=900)
        view.add_item(RoleSelect(selected_roles))
        try:
            await channel.send(
                content=self.description_text or "以下のメニューからロールを選択してください。",
                view=view,
            )
        except (discord.Forbidden, discord.HTTPException):
            await interaction.response.edit_message(
                content="パネルを送信できませんでした。Bot の権限を確認してください。",
                view=None,
            )
            return

        await interaction.response.edit_message(
            content="ロール選択パネルを作成しました。",
            view=None,
        )


class RolePanelCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="rolepanel",
        description="安全なセルフサービス用ロール選択パネルを作成します。",
    )
    @app_commands.default_permissions(manage_roles=True)
    async def createpanel(
        self,
        interaction: discord.Interaction,
        description: str = "以下のメニューからロールを選択してください。",
    ) -> None:
        guild = interaction.guild
        if guild is None or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                "このコマンドはサーバー内で使用してください。",
                ephemeral=True,
            )
            return

        if not interaction.user.guild_permissions.manage_roles:
            await interaction.response.send_message(
                "ロール選択パネルの作成には「ロールの管理」権限が必要です。",
                ephemeral=True,
            )
            return

        bot_member = guild.me
        if bot_member is None:
            await interaction.response.send_message(
                "Bot のサーバーメンバー情報を取得できませんでした。",
                ephemeral=True,
            )
            return
        if not bot_member.guild_permissions.manage_roles:
            await interaction.response.send_message(
                "Bot に「ロールの管理」権限がありません。",
                ephemeral=True,
            )
            return

        roles = sorted(
            (
                role
                for role in guild.roles
                if _is_safe_self_assignable(role, bot_member)
            ),
            key=lambda role: role.position,
            reverse=True,
        )[:25]

        if not roles:
            await interaction.response.send_message(
                "セルフサービスに設定できるロールがありません。",
                ephemeral=True,
            )
            return

        view = discord.ui.View(timeout=180)
        view.add_item(PanelRole(roles, description[:2000]))
        await interaction.response.send_message(
            "パネルに追加するロールを選択してください。",
            view=view,
            ephemeral=True,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RolePanelCog(bot))

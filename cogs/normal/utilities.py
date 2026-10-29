from __future__ import annotations

import ast
import math
import operator
import random
from datetime import datetime, timezone
from typing import Callable

import discord
from discord import app_commands
from discord.ext import commands


_BINARY_OPERATORS: dict[type[ast.operator], Callable[[float, float], float]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY_OPERATORS: dict[type[ast.unaryop], Callable[[float], float]] = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def calculate_expression(expression: str) -> int | float:
    """Evaluate arithmetic without eval or arbitrary code execution."""
    if not expression or len(expression) > 100:
        raise ValueError("式は1〜100文字で入力してください。")
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as error:
        raise ValueError("計算式を読み取れませんでした。") from error

    def evaluate(node: ast.AST) -> int | float:
        if isinstance(node, ast.Expression):
            return evaluate(node.body)
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            value = node.value
            if not math.isfinite(value) or abs(value) > 1e100:
                raise ValueError("数値が大きすぎます。")
            return value
        if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPERATORS:
            return _UNARY_OPERATORS[type(node.op)](evaluate(node.operand))
        if isinstance(node, ast.BinOp) and type(node.op) in _BINARY_OPERATORS:
            left = evaluate(node.left)
            right = evaluate(node.right)
            if isinstance(node.op, ast.Pow) and abs(right) > 10:
                raise ValueError("累乗の指数は -10〜10 の範囲で指定してください。")
            result = _BINARY_OPERATORS[type(node.op)](left, right)
            if not math.isfinite(result) or abs(result) > 1e100:
                raise ValueError("計算結果が大きすぎます。")
            return result
        raise ValueError("数値、括弧、+ - * / // % ** のみ使用できます。")

    try:
        return evaluate(tree)
    except (ZeroDivisionError, OverflowError) as error:
        raise ValueError("ゼロ除算、または計算範囲外の値です。") from error


def parse_choices(value: str, *, minimum: int = 2, maximum: int = 20) -> list[str]:
    """Parse comma-separated choices and enforce user-friendly limits."""
    choices = [item.strip() for item in value.split(",") if item.strip()]
    if not minimum <= len(choices) <= maximum:
        raise ValueError(f"選択肢は{minimum}〜{maximum}個、カンマ区切りで入力してください。")
    if any(len(item) > 80 for item in choices):
        raise ValueError("各選択肢は80文字以内で入力してください。")
    if len({item.casefold() for item in choices}) != len(choices):
        raise ValueError("同じ選択肢を重複して指定できません。")
    return choices


class PollButton(discord.ui.Button["PollView"]):
    def __init__(self, index: int, label: str):
        super().__init__(
            label=label,
            style=discord.ButtonStyle.primary,
            custom_id=f"gakuseibot_poll_{index}",
        )
        self.index = index

    async def callback(self, interaction: discord.Interaction) -> None:
        if self.view is None:
            await interaction.response.send_message("この投票は利用できません。", ephemeral=True)
            return
        self.view.votes[interaction.user.id] = self.index
        await interaction.response.edit_message(embed=self.view.build_embed(), view=self.view)


class PollView(discord.ui.View):
    def __init__(self, question: str, options: list[str]):
        super().__init__(timeout=86400)
        self.question = question
        self.options = options
        self.votes: dict[int, int] = {}
        for index, option in enumerate(options):
            self.add_item(PollButton(index, option))

    def build_embed(self) -> discord.Embed:
        counts = [0] * len(self.options)
        for selected in self.votes.values():
            counts[selected] += 1
        total = len(self.votes)
        lines = []
        for option, count in zip(self.options, counts):
            percent = (count / total * 100) if total else 0
            lines.append(f"**{discord.utils.escape_markdown(option)}** — {count}票 ({percent:.0f}%)")
        embed = discord.Embed(
            title=f"📊 {discord.utils.escape_markdown(self.question)}",
            description="\n".join(lines),
            color=discord.Color.blurple(),
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_footer(text=f"投票数: {total} • ボタンを押すと投票先を変更できます")
        return embed

    async def on_timeout(self) -> None:
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True


class UtilityCommands(commands.Cog):
    """Everyday utility and server-information slash commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="coinflip", description="コインを投げて表か裏かを決めます")
    async def coinflip(self, interaction: discord.Interaction) -> None:
        result = random.choice(("表", "裏"))
        await interaction.response.send_message(
            embed=discord.Embed(
                title="コイントス",
                description=f"結果は **{result}** です。",
                color=discord.Color.gold(),
            )
        )

    @app_commands.command(name="choose", description="複数の候補からランダムに1つ選びます")
    @app_commands.describe(options="候補をカンマ区切りで入力（例：A, B, C）")
    async def choose(self, interaction: discord.Interaction, options: str) -> None:
        try:
            choices = parse_choices(options)
        except ValueError as error:
            await interaction.response.send_message(str(error), ephemeral=True)
            return
        selected = random.choice(choices)
        await interaction.response.send_message(
            embed=discord.Embed(
                title="ランダム選択",
                description=f"選ばれた候補：\n**{discord.utils.escape_markdown(selected)}**",
                color=discord.Color.green(),
            )
        )

    @app_commands.command(name="calculate", description="安全な四則演算式を計算します")
    @app_commands.describe(expression="例： (12 + 8) * 3 / 2")
    async def calculate(self, interaction: discord.Interaction, expression: str) -> None:
        try:
            result = calculate_expression(expression)
        except (ValueError, TypeError) as error:
            await interaction.response.send_message(f"計算できませんでした：{error}", ephemeral=True)
            return
        rendered = f"{result:,}" if isinstance(result, int) else f"{result:,.10g}"
        await interaction.response.send_message(
            embed=discord.Embed(
                title="計算結果",
                description=f"**{discord.utils.escape_markdown(expression)} = {rendered}**",
                color=discord.Color.blue(),
            )
        )

    @app_commands.command(name="poll", description="ボタンで投票できるアンケートを作成します")
    @app_commands.describe(question="投票の質問", options="選択肢をカンマ区切りで入力（2〜5個）")
    async def poll(self, interaction: discord.Interaction, question: str, options: str) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("このコマンドはサーバー内で使用してください。", ephemeral=True)
            return
        question = question.strip()
        if not question or len(question) > 180:
            await interaction.response.send_message("質問は1〜180文字で入力してください。", ephemeral=True)
            return
        try:
            choices = parse_choices(options, minimum=2, maximum=5)
        except ValueError as error:
            await interaction.response.send_message(str(error), ephemeral=True)
            return
        view = PollView(question, choices)
        await interaction.response.send_message(
            embed=view.build_embed(),
            view=view,
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @app_commands.command(name="serverinfo", description="サーバーの基本情報を表示します")
    async def serverinfo(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("このコマンドはサーバー内で使用してください。", ephemeral=True)
            return
        embed = discord.Embed(
            title=f"{guild.name} のサーバー情報",
            color=discord.Color.blurple(),
            timestamp=datetime.now(timezone.utc),
        )
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        embed.add_field(name="サーバーID", value=str(guild.id), inline=True)
        embed.add_field(name="メンバー数", value=str(guild.member_count or "不明"), inline=True)
        embed.add_field(name="チャンネル数", value=str(len(guild.channels)), inline=True)
        embed.add_field(name="ロール数", value=str(len(guild.roles)), inline=True)
        embed.add_field(name="作成日", value=discord.utils.format_dt(guild.created_at, style="F"), inline=False)
        if guild.owner_id:
            embed.add_field(name="オーナー", value=f"<@{guild.owner_id}>", inline=True)
        await interaction.response.send_message(embed=embed, allowed_mentions=discord.AllowedMentions.none())

    @app_commands.command(name="userinfo", description="メンバーの基本情報を表示します")
    @app_commands.describe(member="情報を表示するメンバー（省略時は自分）")
    async def userinfo(self, interaction: discord.Interaction, member: discord.Member | None = None) -> None:
        target = member or interaction.user
        embed = discord.Embed(
            title=f"{target.display_name} のユーザー情報",
            color=discord.Color.blurple(),
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="ユーザー名", value=str(target), inline=True)
        embed.add_field(name="ユーザーID", value=str(target.id), inline=True)
        embed.add_field(name="アカウント作成日", value=discord.utils.format_dt(target.created_at, style="F"), inline=False)
        if isinstance(target, discord.Member):
            embed.add_field(
                name="サーバー参加日",
                value=discord.utils.format_dt(target.joined_at, style="F") if target.joined_at else "不明",
                inline=False,
            )
            roles = [role.mention for role in target.roles if not role.is_default()]
            embed.add_field(name=f"ロール ({len(roles)})", value=", ".join(roles[:10]) if roles else "なし", inline=False)
        await interaction.response.send_message(embed=embed, allowed_mentions=discord.AllowedMentions.none())

    @app_commands.command(name="avatar", description="ユーザーのアバターを大きく表示します")
    @app_commands.describe(member="アバターを表示するメンバー（省略時は自分）")
    async def avatar(self, interaction: discord.Interaction, member: discord.Member | None = None) -> None:
        target = member or interaction.user
        avatar_url = target.display_avatar.replace(size=1024).url
        embed = discord.Embed(title=f"{target.display_name} のアバター", color=discord.Color.blurple())
        embed.set_image(url=avatar_url)
        embed.add_field(name="画像リンク", value=f"[アバターを開く]({avatar_url})", inline=False)
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(UtilityCommands(bot))

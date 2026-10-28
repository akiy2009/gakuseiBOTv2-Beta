import ast
import asyncio
import contextlib
import datetime
import io
import os
import platform
import sys
import time

import discord
import psutil
from discord import app_commands
from discord.ext import commands

# セキュリティのための環境変数取得
DEVELOPER_ID = os.getenv("DEVELOPER_ID")
if DEVELOPER_ID:
    try:
        DEVELOPER_ID = int(DEVELOPER_ID)
    except ValueError:
        DEVELOPER_ID = None


class JishakuCog(commands.Cog, name="🔧 Jishaku"):
    """開発者用デバッグ・管理コマンド群"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.last_result = None

    def _is_developer(self, user_id: int) -> bool:
        """開発者権限チェック"""
        return DEVELOPER_ID is not None and user_id == DEVELOPER_ID

    async def _get_permission_error(self) -> str:
        """権限エラーメッセージ"""
        return "❌ このコマンドは開発者のみ使用できます。"

    def _cleanup_code(self, content: str) -> str:
        """コードブロックから実際のコードを抽出"""
        if content.startswith("```") and content.endswith("```"):
            return "\n".join(content.split("\n")[1:-1])
        return content.strip("` \n")

    def _get_syntax_error(self, e: SyntaxError) -> str:
        """構文エラーの詳細を取得"""
        if e.text is None:
            return f"```py\n{e.__class__.__name__}: {e}\n```"
        return f"```py\n{e.text}{'^':>{e.offset}}\n{e.__class__.__name__}: {e}\n```"

    @app_commands.command(name="jsk", description="🔧 Jishaku メインコマンド")
    @app_commands.describe(action="実行するアクション")
    async def jishaku_main(self, interaction: discord.Interaction, action: str):
        if not self._is_developer(interaction.user.id):
            await interaction.response.send_message(
                await self._get_permission_error(), ephemeral=True
            )
            return

        embed = discord.Embed(
            title="🔧 Jishaku - 開発者デバッグツール",
            description="利用可能なコマンド一覧",
            color=0x2ECC71,
        )

        commands_info = [
            "`/jsk-py <code>` - Pythonコードを実行",
            "`/jsk-sh <command>` - シェルコマンドを実行",
            "`/jsk-load <extension>` - 拡張機能をロード",
            "`/jsk-unload <extension>` - 拡張機能をアンロード",
            "`/jsk-reload <extension>` - 拡張機能をリロード",
            "`/jsk-info` - システム情報を表示",
            "`/jsk-git` - Git情報を表示",
        ]

        embed.add_field(name="コマンド", value="\n".join(commands_info), inline=False)
        embed.set_footer(text="⚠️ 開発者専用 - 取り扱い注意")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="jsk-py", description="🐍 Pythonコードを実行")
    @app_commands.describe(code="実行するPythonコード")
    async def jishaku_python(self, interaction: discord.Interaction, code: str):
        if not self._is_developer(interaction.user.id):
            await interaction.response.send_message(
                await self._get_permission_error(), ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        # コードのクリーンアップ
        code = self._cleanup_code(code)

        # 実行環境のセットアップ
        env = {
            "bot": self.bot,
            "ctx": interaction,
            "interaction": interaction,
            "channel": interaction.channel,
            "author": interaction.user,
            "user": interaction.user,
            "guild": interaction.guild,
            "discord": discord,
            "commands": commands,
            "_": self.last_result,
            "__name__": "__main__",
        }

        # stdout/stderrのキャプチャ
        stdout = io.StringIO()

        try:
            with contextlib.redirect_stdout(stdout):
                # コードをASTで解析
                parsed = ast.parse(code, mode="eval")
                result = eval(compile(parsed, "<repl>", "eval"), env)

                if asyncio.iscoroutine(result):
                    result = await result

        except SyntaxError:
            # 式として解析できない場合、文として実行
            try:
                parsed = ast.parse(code, mode="exec")
                with contextlib.redirect_stdout(stdout):
                    exec(compile(parsed, "<repl>", "exec"), env)
                result = None
            except SyntaxError as e:
                await interaction.followup.send(
                    f"❌ 構文エラー:\n{self._get_syntax_error(e)}", ephemeral=True
                )
                return
            except Exception as e:
                await interaction.followup.send(
                    f"❌ 実行エラー:\n```py\n{type(e).__name__}: {e}\n```",
                    ephemeral=True,
                )
                return
        except Exception as e:
            await interaction.followup.send(
                f"❌ 実行エラー:\n```py\n{type(e).__name__}: {e}\n```", ephemeral=True
            )
            return

        # 結果の保存
        self.last_result = result

        # 出力の組み立て
        value = stdout.getvalue()
        if result is not None:
            if value:
                value += f"\n{result}"
            else:
                value = str(result)

        if not value:
            value = "✅ 実行完了 (出力なし)"

        # 長い出力は切り詰め
        if len(value) > 2000:
            value = value[:1997] + "..."

        embed = discord.Embed(
            title="🐍 Python実行結果",
            description=f"```py\n{value}\n```",
            color=0x3498DB,
        )
        embed.add_field(
            name="実行コード", value=f"```py\n{code[:1000]}\n```", inline=False
        )

        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="jsk-sh", description="💻 シェルコマンドを実行")
    @app_commands.describe(command="実行するシェルコマンド")
    async def jishaku_shell(self, interaction: discord.Interaction, command: str):
        if not self._is_developer(interaction.user.id):
            await interaction.response.send_message(
                await self._get_permission_error(), ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        # セキュリティチェック
        dangerous_commands = ["rm", "del", "format", "shutdown", "reboot"]
        if any(cmd in command.lower() for cmd in dangerous_commands):
            await interaction.followup.send(
                "❌ 危険なコマンドは実行できません。", ephemeral=True
            )
            return

        try:
            start_time = time.time()
            process = await asyncio.create_subprocess_shell(
                command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()
            end_time = time.time()

            embed = discord.Embed(title="💻 シェル実行結果", color=0x95A5A6)

            if stdout:
                output = stdout.decode("utf-8", errors="ignore")
                if len(output) > 1000:
                    output = output[:997] + "..."
                embed.add_field(
                    name="標準出力", value=f"```\n{output}\n```", inline=False
                )

            if stderr:
                error = stderr.decode("utf-8", errors="ignore")
                if len(error) > 1000:
                    error = error[:997] + "..."
                embed.add_field(
                    name="エラー出力", value=f"```\n{error}\n```", inline=False
                )

            embed.add_field(
                name="実行情報",
                value=f"終了コード: {process.returncode}\n実行時間: {end_time - start_time:.2f}秒",
                inline=False,
            )
            embed.add_field(name="実行コマンド", value=f"`{command}`", inline=False)

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.followup.send(
                f"❌ シェル実行エラー:\n```\n{type(e).__name__}: {e}\n```",
                ephemeral=True,
            )

    @app_commands.command(name="jsk-info", description="📊 システム情報を表示")
    async def jishaku_info(self, interaction: discord.Interaction):
        if not self._is_developer(interaction.user.id):
            await interaction.response.send_message(
                await self._get_permission_error(), ephemeral=True
            )
            return

        # システム情報の取得
        process = psutil.Process(os.getpid())

        embed = discord.Embed(title="📊 システム情報", color=0xE74C3C)

        # Botの情報
        embed.add_field(
            name="🤖 Bot情報",
            value=f"ユーザー: {self.bot.user}\n"
            f"ID: {self.bot.user.id}\n"
            f"サーバー数: {len(self.bot.guilds)}\n"
            f"ユーザー数: {len(self.bot.users)}",
            inline=True,
        )

        # システム情報
        embed.add_field(
            name="💻 システム",
            value=f"OS: {platform.system()} {platform.release()}\n"
            f"Python: {sys.version.split()[0]}\n"
            f"discord.py: {discord.__version__}\n"
            f"プロセスID: {os.getpid()}",
            inline=True,
        )

        # リソース使用量
        memory_usage = process.memory_info().rss / 1024 / 1024  # MB
        cpu_percent = process.cpu_percent()

        embed.add_field(
            name="📈 リソース使用量",
            value=f"メモリ: {memory_usage:.1f} MB\n"
            f"CPU: {cpu_percent:.1f}%\n"
            f"起動時間: {datetime.timedelta(seconds=int(time.time() - process.create_time()))}",
            inline=True,
        )

        # 拡張機能
        loaded_extensions = list(self.bot.extensions.keys())
        embed.add_field(
            name="🔧 読み込み済み拡張機能",
            value=f"```\n{chr(10).join(loaded_extensions[:10])}\n```"
            if loaded_extensions
            else "なし",
            inline=False,
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="jsk-git", description="🔄 Git情報を表示")
    async def jishaku_git(self, interaction: discord.Interaction):
        if not self._is_developer(interaction.user.id):
            await interaction.response.send_message(
                await self._get_permission_error(), ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        try:
            # Git情報を取得
            process = await asyncio.create_subprocess_shell(
                "git log --oneline -n 5",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                await interaction.followup.send(
                    "❌ Gitリポジトリが見つかりません。", ephemeral=True
                )
                return

            commits = stdout.decode("utf-8", errors="ignore").strip()

            # ブランチ情報
            process = await asyncio.create_subprocess_shell(
                "git branch --show-current", stdout=asyncio.subprocess.PIPE
            )
            stdout, _ = await process.communicate()
            current_branch = stdout.decode("utf-8", errors="ignore").strip()

            # リモート情報
            process = await asyncio.create_subprocess_shell(
                "git remote get-url origin", stdout=asyncio.subprocess.PIPE
            )
            stdout, _ = await process.communicate()
            remote_url = stdout.decode("utf-8", errors="ignore").strip()

            embed = discord.Embed(title="🔄 Git情報", color=0xF39C12)

            embed.add_field(
                name="現在のブランチ", value=f"`{current_branch}`", inline=True
            )
            embed.add_field(name="リモートURL", value=f"`{remote_url}`", inline=False)
            embed.add_field(
                name="最近のコミット", value=f"```\n{commits}\n```", inline=False
            )

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.followup.send(
                f"❌ Git情報の取得に失敗: {e}", ephemeral=True
            )

    @app_commands.command(name="jsk-load", description="📦 拡張機能をロード")
    @app_commands.describe(extension="ロードする拡張機能名")
    async def jishaku_load(self, interaction: discord.Interaction, extension: str):
        if not self._is_developer(interaction.user.id):
            await interaction.response.send_message(
                await self._get_permission_error(), ephemeral=True
            )
            return

        try:
            await self.bot.load_extension(extension)
            await interaction.response.send_message(
                f"✅ `{extension}` をロードしました。", ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ ロードに失敗: {e}", ephemeral=True
            )

    @app_commands.command(name="jsk-unload", description="📤 拡張機能をアンロード")
    @app_commands.describe(extension="アンロードする拡張機能名")
    async def jishaku_unload(self, interaction: discord.Interaction, extension: str):
        if not self._is_developer(interaction.user.id):
            await interaction.response.send_message(
                await self._get_permission_error(), ephemeral=True
            )
            return

        if extension == "cogs.admin.jishaku":
            await interaction.response.send_message(
                "❌ 自分自身はアンロードできません。", ephemeral=True
            )
            return

        try:
            await self.bot.unload_extension(extension)
            await interaction.response.send_message(
                f"✅ `{extension}` をアンロードしました。", ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ アンロードに失敗: {e}", ephemeral=True
            )

    @app_commands.command(name="jsk-reload", description="🔄 拡張機能をリロード")
    @app_commands.describe(extension="リロードする拡張機能名")
    async def jishaku_reload(self, interaction: discord.Interaction, extension: str):
        if not self._is_developer(interaction.user.id):
            await interaction.response.send_message(
                await self._get_permission_error(), ephemeral=True
            )
            return

        try:
            await self.bot.reload_extension(extension)
            await interaction.response.send_message(
                f"🔄 `{extension}` をリロードしました。", ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ リロードに失敗: {e}", ephemeral=True
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(JishakuCog(bot))

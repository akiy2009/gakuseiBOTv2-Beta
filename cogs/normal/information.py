"""Private, persistent notes and bookmarks for each Discord user."""

from __future__ import annotations

import asyncio
import os
import sqlite3
from collections.abc import Awaitable, Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

import discord
from discord import app_commands
from discord.ext import commands

_MAX_ITEMS_PER_USER = 100
_MAX_TITLE_LENGTH = 100
_MAX_NOTE_LENGTH = 2000
_MAX_URL_LENGTH = 2048


class ArchiveError(ValueError):
    """A user-correctable archive operation error."""


class PersonalArchiveStore:
    """SQLite-backed store with per-user ownership checks."""

    def __init__(self, database_path: str | Path = "data/user_data.sqlite3"):
        self.database_path = Path(database_path)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 10000")
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_notes_owner_created
                    ON notes(user_id, id DESC);
                CREATE TABLE IF NOT EXISTS bookmarks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    url TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_bookmarks_owner_created
                    ON bookmarks(user_id, id DESC);
                """
            )

    @staticmethod
    def _timestamp() -> str:
        return datetime.now(UTC).isoformat(timespec="seconds")

    def _check_limit(
        self, connection: sqlite3.Connection, table: str, user_id: int
    ) -> None:
        if table not in {"notes", "bookmarks"}:
            raise ValueError("Unsupported archive table")
        count = connection.execute(
            f"SELECT COUNT(*) FROM {table} WHERE user_id = ?", (user_id,)
        ).fetchone()[0]
        if count >= _MAX_ITEMS_PER_USER:
            raise ArchiveError(
                f"保存上限（{_MAX_ITEMS_PER_USER}件）に達しています。不要な項目を削除してください。"
            )

    def add_note(self, user_id: int, title: str, content: str) -> int:
        title, content = title.strip(), content.strip()
        if not title or len(title) > _MAX_TITLE_LENGTH:
            raise ArchiveError("タイトルは1〜100文字で入力してください。")
        if not content or len(content) > _MAX_NOTE_LENGTH:
            raise ArchiveError("本文は1〜2000文字で入力してください。")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._check_limit(connection, "notes", user_id)
            cursor = connection.execute(
                "INSERT INTO notes(user_id, title, content, created_at) VALUES (?, ?, ?, ?)",
                (user_id, title, content, self._timestamp()),
            )
            return int(cursor.lastrowid)

    def list_notes(
        self, user_id: int, limit: int = _MAX_ITEMS_PER_USER
    ) -> list[sqlite3.Row]:
        with self._connect() as connection:
            return list(
                connection.execute(
                    "SELECT id, title, created_at FROM notes WHERE user_id = ? ORDER BY id DESC LIMIT ?",
                    (user_id, limit),
                )
            )

    def get_note(self, user_id: int, note_id: int) -> sqlite3.Row | None:
        with self._connect() as connection:
            return connection.execute(
                "SELECT id, title, content, created_at FROM notes WHERE user_id = ? AND id = ?",
                (user_id, note_id),
            ).fetchone()

    def search_notes(
        self, user_id: int, keyword: str, limit: int = _MAX_ITEMS_PER_USER
    ) -> list[sqlite3.Row]:
        escaped = keyword.replace("!", "!!").replace("%", "!%").replace("_", "!_")
        pattern = f"%{escaped}%"
        with self._connect() as connection:
            return list(
                connection.execute(
                    """SELECT id, title, created_at FROM notes
                   WHERE user_id = ? AND (title LIKE ? ESCAPE '!' OR content LIKE ? ESCAPE '!')
                   ORDER BY id DESC LIMIT ?""",
                    (user_id, pattern, pattern, limit),
                )
            )

    def delete_note(self, user_id: int, note_id: int) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM notes WHERE user_id = ? AND id = ?", (user_id, note_id)
            )
            return cursor.rowcount > 0

    def add_bookmark(self, user_id: int, title: str, url: str) -> int:
        title, url = title.strip(), url.strip()
        try:
            parsed = urlparse(url)
            hostname = parsed.hostname
            _ = parsed.port
            valid_hostname = bool(hostname) and bool(hostname.encode("idna"))
        except (ValueError, UnicodeError):
            parsed = None
            valid_hostname = False
        if (
            len(url) > _MAX_URL_LENGTH
            or parsed is None
            or parsed.scheme not in {"http", "https"}
            or not valid_hostname
            or not parsed.netloc
            or parsed.username is not None
            or parsed.password is not None
            or "\\" in url
            or any(
                character.isspace() or ord(character) < 32 or character in "<>"
                for character in url
            )
        ):
            raise ArchiveError(
                "認証情報を含まない有効な http:// または https:// URLを入力してください。"
            )
        if not title:
            title = hostname or ""
        if not title or len(title) > _MAX_TITLE_LENGTH:
            raise ArchiveError("タイトルは1〜100文字で入力してください。")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._check_limit(connection, "bookmarks", user_id)
            cursor = connection.execute(
                "INSERT INTO bookmarks(user_id, title, url, created_at) VALUES (?, ?, ?, ?)",
                (user_id, title, url, self._timestamp()),
            )
            return int(cursor.lastrowid)

    def list_bookmarks(
        self, user_id: int, limit: int = _MAX_ITEMS_PER_USER
    ) -> list[sqlite3.Row]:
        with self._connect() as connection:
            return list(
                connection.execute(
                    "SELECT id, title, url, created_at FROM bookmarks WHERE user_id = ? ORDER BY id DESC LIMIT ?",
                    (user_id, limit),
                )
            )

    def search_bookmarks(
        self, user_id: int, keyword: str, limit: int = _MAX_ITEMS_PER_USER
    ) -> list[sqlite3.Row]:
        escaped = keyword.replace("!", "!!").replace("%", "!%").replace("_", "!_")
        pattern = f"%{escaped}%"
        with self._connect() as connection:
            return list(
                connection.execute(
                    """SELECT id, title, url, created_at FROM bookmarks
                   WHERE user_id = ? AND (title LIKE ? ESCAPE '!' OR url LIKE ? ESCAPE '!')
                   ORDER BY id DESC LIMIT ?""",
                    (user_id, pattern, pattern, limit),
                )
            )

    def delete_bookmark(self, user_id: int, bookmark_id: int) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM bookmarks WHERE user_id = ? AND id = ?",
                (user_id, bookmark_id),
            )
            return cursor.rowcount > 0


def _safe_text(value: str, limit: int = 100) -> str:
    return discord.utils.escape_mentions(discord.utils.escape_markdown(value))[:limit]


_PAGE_SIZE = 8


class ArchivePager(discord.ui.View):
    """Owner-only ephemeral pagination for archive results."""

    def __init__(self, owner_id: int, title: str, entries: list[str]):
        super().__init__(timeout=180)
        self.owner_id = owner_id
        self.title = title
        self.entries = entries
        self.pages: list[list[str]] = []
        current_page: list[str] = []
        current_length = 0
        for entry in entries:
            if current_page and (
                len(current_page) >= _PAGE_SIZE
                or current_length + len(entry) + 1 > 3500
            ):
                self.pages.append(current_page)
                current_page = []
                current_length = 0
            current_page.append(entry)
            current_length += len(entry) + 1
        if current_page or not self.pages:
            self.pages.append(current_page)
        self.page = 0
        self._sync_buttons()

    def _page_count(self) -> int:
        return len(self.pages)

    def make_embed(self) -> discord.Embed:
        visible = self.pages[self.page]
        embed = discord.Embed(
            title=self.title,
            description="\n".join(visible)
            if visible
            else "表示できる項目はありません。",
            color=discord.Color.blurple(),
        )
        embed.set_footer(
            text=f"{self.page + 1} / {self._page_count()} ページ ・ 全 {len(self.entries)} 件"
        )
        return embed

    def _sync_buttons(self) -> None:
        self.previous.disabled = self.page <= 0
        self.next.disabled = self.page >= self._page_count() - 1

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "この一覧を操作できるのは実行した本人だけです。", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="前へ", style=discord.ButtonStyle.secondary)
    async def previous(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        self.page = max(0, self.page - 1)
        self._sync_buttons()
        await interaction.response.edit_message(embed=self.make_embed(), view=self)

    @discord.ui.button(label="次へ", style=discord.ButtonStyle.secondary)
    async def next(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        self.page = min(self._page_count() - 1, self.page + 1)
        self._sync_buttons()
        await interaction.response.edit_message(embed=self.make_embed(), view=self)


class DeleteConfirmationView(discord.ui.View):
    """Owner-only confirmation before deleting a saved item."""

    def __init__(
        self, owner_id: int, delete_action: Callable[[], Awaitable[bool]], label: str
    ):
        super().__init__(timeout=60)
        self.owner_id = owner_id
        self.delete_action = delete_action
        self.label = label

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "この確認画面を操作できるのは実行した本人だけです。", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="削除する", style=discord.ButtonStyle.danger)
    async def confirm(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        deleted = await self.delete_action()
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True
        message = (
            f"{self.label}を削除しました。"
            if deleted
            else f"{self.label}が見つかりません。"
        )
        await interaction.response.edit_message(content=message, embed=None, view=self)

    @discord.ui.button(label="キャンセル", style=discord.ButtonStyle.secondary)
    async def cancel(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True
        await interaction.response.edit_message(
            content="削除をキャンセルしました。", embed=None, view=self
        )


class PersonalInformationCog(commands.Cog):
    """Personal notes and bookmarks with owner-only access."""

    note = app_commands.Group(name="note", description="個人メモを保存・検索します")
    bookmark = app_commands.Group(
        name="bookmark", description="URLをブックマークします"
    )

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.store = PersonalArchiveStore(
            os.getenv("USER_DATA_DB", "data/user_data.sqlite3")
        )

    async def cog_load(self) -> None:
        await asyncio.to_thread(self.store.initialize)

    @note.command(name="add", description="メモを新しく保存します")
    @app_commands.describe(title="メモのタイトル", content="メモの本文（最大2000文字）")
    async def note_add(
        self, interaction: discord.Interaction, title: str, content: str
    ) -> None:
        try:
            note_id = await asyncio.to_thread(
                self.store.add_note, interaction.user.id, title, content
            )
        except ArchiveError as error:
            await interaction.response.send_message(str(error), ephemeral=True)
            return
        await interaction.response.send_message(
            f"メモを保存しました。ID: **{note_id}**", ephemeral=True
        )

    @note.command(name="list", description="保存したメモの一覧を表示します")
    async def note_list(self, interaction: discord.Interaction) -> None:
        notes = await asyncio.to_thread(self.store.list_notes, interaction.user.id)
        if not notes:
            await interaction.response.send_message(
                "保存されたメモはありません。", ephemeral=True
            )
            return
        lines = [f"`{row['id']}` **{_safe_text(row['title'])}**" for row in notes]
        view = ArchivePager(interaction.user.id, "保存したメモ", lines)
        await interaction.response.send_message(
            embed=view.make_embed(), view=view, ephemeral=True
        )

    @note.command(name="view", description="指定したメモの内容を表示します")
    @app_commands.describe(note_id="メモID")
    async def note_view(
        self, interaction: discord.Interaction, note_id: app_commands.Range[int, 1]
    ) -> None:
        row = await asyncio.to_thread(self.store.get_note, interaction.user.id, note_id)
        if row is None:
            await interaction.response.send_message(
                "メモが見つかりません。", ephemeral=True
            )
            return
        embed = discord.Embed(
            title=_safe_text(row["title"], 256),
            description=discord.utils.escape_markdown(
                discord.utils.escape_mentions(row["content"])
            ),
            color=discord.Color.blurple(),
            timestamp=datetime.fromisoformat(row["created_at"]),
        )
        embed.set_footer(text=f"メモ ID: {row['id']}")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @note.command(name="search", description="タイトルや本文からメモを検索します")
    @app_commands.describe(keyword="検索キーワード")
    async def note_search(self, interaction: discord.Interaction, keyword: str) -> None:
        keyword = keyword.strip()
        if not keyword or len(keyword) > 100:
            await interaction.response.send_message(
                "検索語は1〜100文字で入力してください。", ephemeral=True
            )
            return
        rows = await asyncio.to_thread(
            self.store.search_notes, interaction.user.id, keyword
        )
        if not rows:
            await interaction.response.send_message(
                "一致するメモはありません。", ephemeral=True
            )
            return
        lines = [f"`{row['id']}` **{_safe_text(row['title'])}**" for row in rows]
        view = ArchivePager(interaction.user.id, "メモの検索結果", lines)
        await interaction.response.send_message(
            embed=view.make_embed(), view=view, ephemeral=True
        )

    @note.command(name="delete", description="保存したメモを削除します")
    @app_commands.describe(note_id="削除するメモID")
    async def note_delete(
        self, interaction: discord.Interaction, note_id: app_commands.Range[int, 1]
    ) -> None:
        row = await asyncio.to_thread(self.store.get_note, interaction.user.id, note_id)
        if row is None:
            await interaction.response.send_message(
                "メモが見つかりません。", ephemeral=True
            )
            return
        view = DeleteConfirmationView(
            interaction.user.id,
            lambda: asyncio.to_thread(
                self.store.delete_note, interaction.user.id, note_id
            ),
            "メモ",
        )
        await interaction.response.send_message(
            f"「{_safe_text(row['title'])}」を削除しますか？この操作は取り消せません。",
            view=view,
            ephemeral=True,
        )

    @bookmark.command(name="add", description="URLをブックマークに保存します")
    @app_commands.describe(url="保存するURL（http/https）", title="表示名")
    async def bookmark_add(
        self, interaction: discord.Interaction, url: str, title: str | None = None
    ) -> None:
        title = (title or "").strip()
        try:
            bookmark_id = await asyncio.to_thread(
                self.store.add_bookmark, interaction.user.id, title, url
            )
        except ArchiveError as error:
            await interaction.response.send_message(str(error), ephemeral=True)
            return
        await interaction.response.send_message(
            f"ブックマークを保存しました。ID: **{bookmark_id}**", ephemeral=True
        )

    @bookmark.command(name="list", description="保存したブックマークを表示します")
    async def bookmark_list(self, interaction: discord.Interaction) -> None:
        rows = await asyncio.to_thread(self.store.list_bookmarks, interaction.user.id)
        if not rows:
            await interaction.response.send_message(
                "ブックマークはありません。", ephemeral=True
            )
            return
        lines = [
            f"`{row['id']}` **{_safe_text(row['title'])}**\n<{row['url']}>"
            for row in rows
        ]
        view = ArchivePager(interaction.user.id, "ブックマーク", lines)
        await interaction.response.send_message(
            embed=view.make_embed(), view=view, ephemeral=True
        )

    @bookmark.command(name="search", description="タイトルやURLから検索します")
    @app_commands.describe(keyword="検索キーワード")
    async def bookmark_search(
        self, interaction: discord.Interaction, keyword: str
    ) -> None:
        keyword = keyword.strip()
        if not keyword or len(keyword) > 100:
            await interaction.response.send_message(
                "検索語は1〜100文字で入力してください。", ephemeral=True
            )
            return
        rows = await asyncio.to_thread(
            self.store.search_bookmarks, interaction.user.id, keyword
        )
        if not rows:
            await interaction.response.send_message(
                "一致するブックマークはありません。", ephemeral=True
            )
            return
        lines = [
            f"`{row['id']}` **{_safe_text(row['title'])}**\\n<{row['url']}>"
            for row in rows
        ]
        view = ArchivePager(interaction.user.id, "ブックマークの検索結果", lines)
        await interaction.response.send_message(
            embed=view.make_embed(), view=view, ephemeral=True
        )

    @bookmark.command(name="delete", description="ブックマークを削除します")
    @app_commands.describe(bookmark_id="削除するブックマークID")
    async def bookmark_delete(
        self, interaction: discord.Interaction, bookmark_id: app_commands.Range[int, 1]
    ) -> None:
        rows = await asyncio.to_thread(
            self.store.list_bookmarks, interaction.user.id, _MAX_ITEMS_PER_USER
        )
        if not any(row["id"] == bookmark_id for row in rows):
            await interaction.response.send_message(
                "ブックマークが見つかりません。", ephemeral=True
            )
            return
        view = DeleteConfirmationView(
            interaction.user.id,
            lambda: asyncio.to_thread(
                self.store.delete_bookmark, interaction.user.id, bookmark_id
            ),
            "ブックマーク",
        )
        await interaction.response.send_message(
            f"ブックマーク ID {bookmark_id} を削除しますか？この操作は取り消せません。",
            view=view,
            ephemeral=True,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(PersonalInformationCog(bot))

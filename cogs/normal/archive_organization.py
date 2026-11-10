"""Folder and tag organization for private notes.

This extension is intentionally additive: it stores organization metadata in
separate tables and never rewrites or deletes existing note content.
"""

from __future__ import annotations

import asyncio
import os
import re
import sqlite3
from contextlib import closing
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands

_NAME_RE = re.compile(r"^[^\x00-\x1f]{1,32}$")
_MAX_FOLDERS = 20
_MAX_TAGS_PER_NOTE = 10


class OrganizationError(ValueError):
    """An organization operation that can be corrected by the user."""


class NoteOrganizationStore:
    """Owner-scoped folder and tag metadata for existing personal notes."""

    def __init__(self, database_path: str | Path = "data/user_data.sqlite3"):
        self.database_path = Path(database_path)

    def _connect(self) -> sqlite3.Connection:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 10000")
        return connection

    def initialize(self) -> None:
        with closing(self._connect()) as db:
            db.execute("PRAGMA journal_mode = WAL")
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS note_folders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    name TEXT NOT NULL COLLATE NOCASE,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, name)
                );
                CREATE INDEX IF NOT EXISTS idx_note_folders_owner
                    ON note_folders(user_id, name);
                CREATE TABLE IF NOT EXISTS note_tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    name TEXT NOT NULL COLLATE NOCASE,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, name)
                );
                CREATE TABLE IF NOT EXISTS note_folder_map (
                    user_id INTEGER NOT NULL,
                    note_id INTEGER NOT NULL,
                    folder_id INTEGER NOT NULL,
                    PRIMARY KEY(user_id, note_id),
                    FOREIGN KEY(folder_id) REFERENCES note_folders(id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS note_tag_map (
                    user_id INTEGER NOT NULL,
                    note_id INTEGER NOT NULL,
                    tag_id INTEGER NOT NULL,
                    PRIMARY KEY(user_id, note_id, tag_id),
                    FOREIGN KEY(tag_id) REFERENCES note_tags(id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_note_tag_map_owner
                    ON note_tag_map(user_id, tag_id, note_id);
                """
            )
            db.commit()

    @staticmethod
    def _validate_name(name: str, kind: str) -> str:
        normalized = name.strip()
        if not _NAME_RE.fullmatch(normalized):
            raise OrganizationError(f"{kind}名は1〜32文字で入力してください。")
        return normalized

    def create_folder(self, user_id: int, name: str) -> int:
        name = self._validate_name(name, "フォルダ")
        with closing(self._connect()) as db:
            try:
                db.execute("BEGIN IMMEDIATE")
                count = db.execute(
                    "SELECT COUNT(*) FROM note_folders WHERE user_id = ?", (user_id,)
                ).fetchone()[0]
                if count >= _MAX_FOLDERS:
                    raise OrganizationError(f"フォルダは最大{_MAX_FOLDERS}個まで作成できます。")
                cursor = db.execute(
                    "INSERT INTO note_folders(user_id, name) VALUES (?, ?)",
                    (user_id, name),
                )
                db.commit()
                return int(cursor.lastrowid)
            except sqlite3.IntegrityError as error:
                db.rollback()
                raise OrganizationError("同じ名前のフォルダが既にあります。") from error
            except Exception:
                db.rollback()
                raise

    def list_folders(self, user_id: int) -> list[sqlite3.Row]:
        with closing(self._connect()) as db:
            return list(db.execute(
                """SELECT f.id, f.name, COUNT(m.note_id) AS note_count
                   FROM note_folders f
                   LEFT JOIN note_folder_map m
                     ON m.folder_id = f.id AND m.user_id = f.user_id
                   WHERE f.user_id = ?
                   GROUP BY f.id ORDER BY f.name COLLATE NOCASE""",
                (user_id,),
            ))

    def delete_folder(self, user_id: int, folder_id: int) -> bool:
        with closing(self._connect()) as db:
            db.execute("PRAGMA foreign_keys = ON")
            cursor = db.execute(
                "DELETE FROM note_folders WHERE user_id = ? AND id = ?",
                (user_id, folder_id),
            )
            db.commit()
            return cursor.rowcount > 0

    def organize_note(
        self, user_id: int, note_id: int, folder_name: str | None, tag_names: list[str]
    ) -> None:
        cleaned_tags = [self._validate_name(tag, "タグ") for tag in tag_names if tag.strip()]
        if len(cleaned_tags) > _MAX_TAGS_PER_NOTE:
            raise OrganizationError(f"1件のメモに付けられるタグは最大{_MAX_TAGS_PER_NOTE}個です。")
        if len({tag.casefold() for tag in cleaned_tags}) != len(cleaned_tags):
            raise OrganizationError("同じタグを重複して指定できません。")
        folder_name = self._validate_name(folder_name, "フォルダ") if folder_name else None

        with closing(self._connect()) as db:
            db.execute("BEGIN IMMEDIATE")
            exists = db.execute(
                "SELECT 1 FROM notes WHERE user_id = ? AND id = ?", (user_id, note_id)
            ).fetchone()
            if not exists:
                db.rollback()
                raise OrganizationError("メモが見つかりません。")
            folder_id = None
            if folder_name:
                folder = db.execute(
                    "SELECT id FROM note_folders WHERE user_id = ? AND name = ?",
                    (user_id, folder_name),
                ).fetchone()
                if folder is None:
                    db.rollback()
                    raise OrganizationError("フォルダが見つかりません。先に作成してください。")
                folder_id = int(folder["id"])

            db.execute(
                "DELETE FROM note_folder_map WHERE user_id = ? AND note_id = ?",
                (user_id, note_id),
            )
            if folder_id is not None:
                db.execute(
                    "INSERT INTO note_folder_map(user_id, note_id, folder_id) VALUES (?, ?, ?)",
                    (user_id, note_id, folder_id),
                )

            db.execute(
                "DELETE FROM note_tag_map WHERE user_id = ? AND note_id = ?",
                (user_id, note_id),
            )
            for tag in cleaned_tags:
                db.execute(
                    "INSERT INTO note_tags(user_id, name) VALUES (?, ?) ON CONFLICT(user_id, name) DO NOTHING",
                    (user_id, tag),
                )
                tag_id = db.execute(
                    "SELECT id FROM note_tags WHERE user_id = ? AND name = ?",
                    (user_id, tag),
                ).fetchone()["id"]
                db.execute(
                    "INSERT INTO note_tag_map(user_id, note_id, tag_id) VALUES (?, ?, ?)",
                    (user_id, note_id, tag_id),
                )
            db.commit()

    def search_notes(
        self, user_id: int, folder_name: str | None = None, tag_name: str | None = None
    ) -> list[sqlite3.Row]:
        if not folder_name and not tag_name:
            raise OrganizationError("フォルダ名またはタグ名を指定してください。")
        clauses = ["n.user_id = ?"]
        params: list[object] = [user_id]
        joins = ""
        if folder_name:
            joins += " JOIN note_folder_map fm ON fm.note_id = n.id AND fm.user_id = n.user_id"
            joins += " JOIN note_folders f ON f.id = fm.folder_id AND f.user_id = fm.user_id"
            clauses.append("f.name = ?")
            params.append(self._validate_name(folder_name, "フォルダ"))
        if tag_name:
            joins += " JOIN note_tag_map tm ON tm.note_id = n.id AND tm.user_id = n.user_id"
            joins += " JOIN note_tags t ON t.id = tm.tag_id AND t.user_id = tm.user_id"
            clauses.append("t.name = ?")
            params.append(self._validate_name(tag_name, "タグ"))
        with closing(self._connect()) as db:
            return list(db.execute(
                f"""SELECT DISTINCT n.id, n.title, n.created_at FROM notes n
                    {joins} WHERE {' AND '.join(clauses)}
                    ORDER BY n.id DESC LIMIT 100""",
                params,
            ))


class NoteOrganizationCog(commands.Cog):
    """Slash commands for organizing private notes."""

    archive = app_commands.Group(name="archive", description="メモをフォルダとタグで整理します")

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.store = NoteOrganizationStore(
            os.getenv("USER_DATA_DB", "data/user_data.sqlite3")
        )

    async def cog_load(self) -> None:
        await asyncio.to_thread(self.store.initialize)

    @archive.command(name="folder-create", description="メモ用フォルダを作成します")
    async def folder_create(self, interaction: discord.Interaction, name: str) -> None:
        try:
            folder_id = await asyncio.to_thread(
                self.store.create_folder, interaction.user.id, name
            )
        except OrganizationError as error:
            await interaction.response.send_message(str(error), ephemeral=True)
            return
        await interaction.response.send_message(
            f"フォルダ「{discord.utils.escape_markdown(name.strip())}」を作成しました（ID: {folder_id}）。",
            ephemeral=True,
        )

    @archive.command(name="folders", description="自分のフォルダ一覧を表示します")
    async def folders(self, interaction: discord.Interaction) -> None:
        rows = await asyncio.to_thread(self.store.list_folders, interaction.user.id)
        if not rows:
            await interaction.response.send_message("フォルダはまだありません。", ephemeral=True)
            return
        lines = [
            f"**{discord.utils.escape_markdown(row['name'])}** — {row['note_count']}件（ID: {row['id']}）"
            for row in rows
        ]
        embed = discord.Embed(title="メモフォルダ", description="\n".join(lines))
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @archive.command(name="folder-delete", description="フォルダを削除します（メモ本体は残ります）")
    async def folder_delete(
        self, interaction: discord.Interaction, folder_id: app_commands.Range[int, 1]
    ) -> None:
        deleted = await asyncio.to_thread(
            self.store.delete_folder, interaction.user.id, folder_id
        )
        message = (
            "フォルダを削除しました。メモ本体とタグは保持されています。"
            if deleted else "フォルダが見つかりません。"
        )
        await interaction.response.send_message(message, ephemeral=True)

    @archive.command(name="organize", description="メモにフォルダとタグを設定します")
    @app_commands.describe(
        note_id="整理するメモID",
        folder="フォルダ名（空欄にするとフォルダを解除）",
        tags="カンマ区切りのタグ。空欄にするとタグを解除",
    )
    async def organize(
        self,
        interaction: discord.Interaction,
        note_id: app_commands.Range[int, 1],
        folder: str | None = None,
        tags: str | None = None,
    ) -> None:
        tag_names = [part.strip() for part in (tags or "").split(",") if part.strip()]
        try:
            await asyncio.to_thread(
                self.store.organize_note, interaction.user.id, note_id, folder, tag_names
            )
        except OrganizationError as error:
            await interaction.response.send_message(str(error), ephemeral=True)
            return
        await interaction.response.send_message(
            f"メモ ID {note_id} の整理内容を更新しました。", ephemeral=True
        )

    @archive.command(name="search", description="フォルダ名またはタグ名でメモを検索します")
    @app_commands.describe(folder="フォルダ名", tag="タグ名")
    async def search(
        self, interaction: discord.Interaction, folder: str | None = None, tag: str | None = None
    ) -> None:
        try:
            rows = await asyncio.to_thread(
                self.store.search_notes, interaction.user.id, folder, tag
            )
        except OrganizationError as error:
            await interaction.response.send_message(str(error), ephemeral=True)
            return
        if not rows:
            await interaction.response.send_message("条件に一致するメモはありません。", ephemeral=True)
            return
        lines = [
            f"`{row['id']}` **{discord.utils.escape_markdown(row['title'])}**"
            for row in rows
        ]
        embed = discord.Embed(title="メモ検索結果", description="\n".join(lines))
        embed.set_footer(text=f"{len(rows)}件")
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(NoteOrganizationCog(bot))

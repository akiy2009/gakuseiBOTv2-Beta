import pytest

from cogs.normal.archive_organization import (
    NoteOrganizationStore,
    OrganizationError,
)


def make_stores(tmp_path):
    database = tmp_path / "data" / "archive.sqlite3"
    import sqlite3

    database.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(database) as db:
        db.execute(
            """CREATE TABLE notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            )"""
        )
    store = NoteOrganizationStore(database)
    store.initialize()
    return store, database


def add_note(database, user_id, title="note"):
    import sqlite3

    with sqlite3.connect(database) as db:
        cursor = db.execute(
            "INSERT INTO notes(user_id, title, content, created_at) VALUES (?, ?, ?, ?)",
            (user_id, title, "content", "2026-11-09T00:00:00+00:00"),
        )
        return cursor.lastrowid


def test_folder_and_tag_organization_is_owner_scoped(tmp_path):
    store, database = make_stores(tmp_path)
    note_id = add_note(database, 10, "Research")
    store.create_folder(10, "研究")
    store.organize_note(10, note_id, "研究", ["太陽", "X線"])

    assert [row["id"] for row in store.search_notes(10, folder_name="研究")] == [note_id]
    assert [row["id"] for row in store.search_notes(10, tag_name="太陽")] == [note_id]
    assert store.search_notes(20, folder_name="研究") == []
    assert store.search_notes(20, tag_name="太陽") == []


def test_folder_deletion_keeps_note_and_removes_organization(tmp_path):
    store, database = make_stores(tmp_path)
    note_id = add_note(database, 10)
    folder_id = store.create_folder(10, "一時")
    store.organize_note(10, note_id, "一時", [])
    assert store.delete_folder(10, folder_id) is True
    assert store.search_notes(10, folder_name="一時") == []
    assert add_note(database, 10) > note_id


def test_organize_rejects_other_users_notes_and_missing_folders(tmp_path):
    store, database = make_stores(tmp_path)
    note_id = add_note(database, 10)
    store.create_folder(20, "private")
    with pytest.raises(OrganizationError, match="見つかりません"):
        store.organize_note(10, note_id, "private", [])
    with pytest.raises(OrganizationError, match="見つかりません"):
        store.organize_note(20, note_id, None, ["tag"])


def test_tag_validation_and_limit(tmp_path):
    store, database = make_stores(tmp_path)
    note_id = add_note(database, 10)
    tags = [f"tag{i}" for i in range(11)]
    with pytest.raises(OrganizationError, match="最大10個"):
        store.organize_note(10, note_id, None, tags)
    with pytest.raises(OrganizationError):
        store.organize_note(10, note_id, None, ["ok", "ok"])


def test_folder_limit_and_duplicate_names(tmp_path):
    store, _ = make_stores(tmp_path)
    store.create_folder(10, "folder0")
    with pytest.raises(OrganizationError, match="既にあります"):
        store.create_folder(10, "FOLDER0")
    for index in range(1, 20):
        store.create_folder(10, f"folder{index}")
    with pytest.raises(OrganizationError, match="最大20個"):
        store.create_folder(10, "overflow")

import pytest

from cogs.normal.information import ArchiveError, PersonalArchiveStore


def make_store(tmp_path):
    store = PersonalArchiveStore(tmp_path / "data" / "archive.sqlite3")
    store.initialize()
    return store


def test_notes_persist_and_are_isolated_by_user(tmp_path):
    store = make_store(tmp_path)
    note_id = store.add_note(1001, "研究メモ", "観測データを確認する")

    restarted_store = PersonalArchiveStore(tmp_path / "data" / "archive.sqlite3")
    assert restarted_store.get_note(1001, note_id)["content"] == "観測データを確認する"
    assert restarted_store.get_note(2002, note_id) is None
    assert restarted_store.delete_note(2002, note_id) is False
    assert restarted_store.get_note(1001, note_id) is not None


def test_note_search_and_delete_are_scoped_to_owner(tmp_path):
    store = make_store(tmp_path)
    first_id = store.add_note(1, "授業", "電気回路の復習")
    store.add_note(2, "授業", "別ユーザーのメモ")

    assert [row["id"] for row in store.search_notes(1, "電気回路")] == [first_id]
    assert store.delete_note(1, first_id) is True
    assert store.get_note(1, first_id) is None


def test_note_validation_and_per_user_limit(tmp_path):
    store = make_store(tmp_path)
    with pytest.raises(ArchiveError):
        store.add_note(1, " ", "本文")
    with pytest.raises(ArchiveError):
        store.add_note(1, "タイトル", " ")

    for index in range(100):
        store.add_note(1, f"メモ{index}", "本文")
    with pytest.raises(ArchiveError, match="保存上限"):
        store.add_note(1, "上限超過", "本文")

    # Limits are per user, not global.
    assert store.add_note(2, "別ユーザー", "本文") > 0


def test_bookmarks_validate_urls_and_are_user_scoped(tmp_path):
    store = make_store(tmp_path)
    with pytest.raises(ArchiveError):
        store.add_bookmark(1, "危険なURL", "javascript:alert(1)")
    with pytest.raises(ArchiveError):
        store.add_bookmark(1, "不正なURL", "https://example.com><@everyone")

    bookmark_id = store.add_bookmark(1, "Python", "https://docs.python.org/3/")
    assert store.list_bookmarks(1)[0]["id"] == bookmark_id
    assert store.search_bookmarks(1, "python")[0]["id"] == bookmark_id
    assert store.list_bookmarks(2) == []
    assert store.delete_bookmark(2, bookmark_id) is False
    assert store.delete_bookmark(1, bookmark_id) is True

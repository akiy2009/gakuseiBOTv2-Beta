import sqlite3

import pytest

from cogs.normal.health import parse_ids, safe_supabase_url, sqlite_check_sync


def test_parse_ids_ignores_invalid_and_duplicates():
    assert parse_ids("123, 456,invalid,123,-1,0") == {123, 456}


def test_safe_supabase_url_requires_https():
    assert (
        safe_supabase_url("https://example.supabase.co/")
        == "https://example.supabase.co"
    )
    with pytest.raises(ValueError):
        safe_supabase_url("http://example.supabase.co")
    with pytest.raises(ValueError):
        safe_supabase_url("https://user:pass@example.supabase.co")


def test_sqlite_check_passes_for_valid_database(tmp_path):
    path = tmp_path / "health.sqlite3"
    connection = sqlite3.connect(path)
    connection.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY)")
    connection.commit()
    connection.close()

    assert sqlite_check_sync(str(path)) == "SQLite quick_check: ok"


def test_sqlite_check_does_not_create_missing_database(tmp_path):
    path = tmp_path / "missing.sqlite3"
    with pytest.raises(FileNotFoundError):
        sqlite_check_sync(str(path))
    assert not path.exists()

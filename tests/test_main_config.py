import json

import main


def test_missing_heavy_cog_file_returns_empty_list(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "HEAVY_COGS_PATH", tmp_path / "data" / "heavy_cogs.json")

    assert main.load_heavy_cog_list() == []


def test_malformed_heavy_cog_file_returns_empty_list(tmp_path, monkeypatch):
    config_path = tmp_path / "heavy_cogs.json"
    config_path.write_text("{broken json", encoding="utf-8")
    monkeypatch.setattr(main, "HEAVY_COGS_PATH", config_path)

    assert main.load_heavy_cog_list() == []


def test_non_string_heavy_cog_entries_are_rejected(tmp_path, monkeypatch):
    config_path = tmp_path / "heavy_cogs.json"
    config_path.write_text(json.dumps(["cogs.normal.ping", 123]), encoding="utf-8")
    monkeypatch.setattr(main, "HEAVY_COGS_PATH", config_path)

    assert main.load_heavy_cog_list() == []


def test_heavy_cog_config_round_trips_and_creates_parent(tmp_path, monkeypatch):
    config_path = tmp_path / "new" / "data" / "heavy_cogs.json"
    monkeypatch.setattr(main, "HEAVY_COGS_PATH", config_path)

    main.save_heavy_cog_list(["ping", "help"])

    assert config_path.is_file()
    assert main.load_heavy_cog_list() == ["ping", "help"]

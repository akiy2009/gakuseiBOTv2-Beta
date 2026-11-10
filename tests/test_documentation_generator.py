from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "generate_docs", ROOT / "scripts" / "generate_docs.py"
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_command_generation_documents_source() -> None:
    rendered = MODULE.render_commands(
        [
            {
                "name": "status",
                "description": "Show bot status",
                "module": "cogs/admin/status.py",
                "signature": "**verbose** (bool) = **False**",
            }
        ]
    )
    assert "**/status**" in rendered
    assert "Show bot status" in rendered
    assert "cogs/admin/status.py" in rendered


def test_environment_generation_never_exposes_secret_values() -> None:
    rendered = MODULE.render_environment(
        [
            {
                "name": "SERVICE_API_KEY",
                "default": "非公開",
                "description": "Service credential",
            }
        ]
    )
    assert "SERVICE_API_KEY" in rendered
    assert "非公開" in rendered
    assert "super-secret-value" not in rendered


def test_environment_parser_reads_example_and_python_sources(
    tmp_path: Path, monkeypatch
) -> None:
    example = tmp_path / ".env.example"
    example.write_text(
        "# Bot token\nDISCORD_TOKEN=placeholder\nPREFIX=/\n", encoding="utf-8"
    )
    monkeypatch.setattr(MODULE, "ENV_EXAMPLE", example)
    monkeypatch.setattr(MODULE, "ROOT", tmp_path)
    monkeypatch.setattr(MODULE, "COGS", tmp_path / "cogs")
    (tmp_path / "cogs").mkdir()
    (tmp_path / "main.py").write_text(
        'import os\nTOKEN = os.getenv("RUNTIME_ONLY_TOKEN", "")\n',
        encoding="utf-8",
    )
    items = {item["name"]: item for item in MODULE.collect_environment()}
    assert items["DISCORD_TOKEN"]["default"] == "非公開"
    assert items["PREFIX"]["default"] == "/"
    assert items["RUNTIME_ONLY_TOKEN"]["default"] == "コード側で確認"

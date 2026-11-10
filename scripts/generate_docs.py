#!/usr/bin/env python3
"""Generate command and environment-variable references from project sources."""

from __future__ import annotations

import argparse
import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COGS = ROOT / "cogs"
ENV_EXAMPLE = ROOT / ".env.example"
OUTPUT = ROOT / "docs" / "generated"
SENSITIVE_NAME = re.compile(r"(TOKEN|SECRET|PASSWORD|KEY|CREDENTIAL)", re.IGNORECASE)


def literal_string(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def decorator_command(node: ast.expr) -> bool:
    target = node.func if isinstance(node, ast.Call) else node
    if isinstance(target, ast.Attribute):
        return target.attr in {"command", "hybrid_command", "slash_command"}
    return isinstance(target, ast.Name) and target.id in {
        "command",
        "hybrid_command",
        "slash_command",
    }


def collect_commands() -> list[dict[str, str]]:
    commands: list[dict[str, str]] = []
    if not COGS.exists():
        return commands
    for path in sorted(COGS.rglob("*.py")):
        if path.name == "__init__.py" or "tests" in path.parts:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, SyntaxError) as error:
            raise RuntimeError(
                f"Cannot parse {path.relative_to(ROOT)}: {error}"
            ) from error
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for decorator in node.decorator_list:
                if not decorator_command(decorator):
                    continue
                call = decorator if isinstance(decorator, ast.Call) else None
                keywords = (
                    {item.arg: item.value for item in call.keywords if item.arg}
                    if call
                    else {}
                )
                name = literal_string(keywords.get("name")) or node.name
                description = (
                    literal_string(keywords.get("description"))
                    or ast.get_docstring(node)
                    or ""
                )
                args = []
                positional = node.args.args
                defaults = [None] * (len(positional) - len(node.args.defaults)) + list(
                    node.args.defaults
                )
                for argument, default in zip(positional, defaults):
                    if argument.arg in {"self", "cls", "ctx", "interaction"}:
                        continue
                    annotation = (
                        ast.unparse(argument.annotation) if argument.annotation else ""
                    )
                    rendered = f"**{argument.arg}**"
                    if annotation:
                        rendered += f" ({annotation})"
                    if default is not None:
                        rendered += f" = **{ast.unparse(default)}**"
                    args.append(rendered)
                commands.append(
                    {
                        "name": name,
                        "description": " ".join(description.strip().split()),
                        "module": str(path.relative_to(ROOT)),
                        "signature": ", ".join(args),
                    }
                )
                break
    unique = {
        (item["module"], item["name"], item["signature"]): item for item in commands
    }
    return sorted(unique.values(), key=lambda item: (item["name"], item["module"]))


def collect_environment() -> list[dict[str, str]]:
    example: dict[str, dict[str, str]] = {}
    if ENV_EXAMPLE.exists():
        comments: list[str] = []
        for raw_line in ENV_EXAMPLE.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line:
                comments.clear()
                continue
            if line.startswith("#"):
                comments.append(line.lstrip("# ").strip())
                continue
            match = re.match(r"^([A-Z][A-Z0-9_]*)=(.*)$", line)
            if match:
                name, value = match.groups()
                example[name] = {
                    "name": name,
                    "default": "非公開"
                    if SENSITIVE_NAME.search(name) and value
                    else (value or "未設定"),
                    "description": " ".join(comments) or "説明は未記載です。",
                }
            comments.clear()

    discovered: set[str] = set()
    source_files = (
        [ROOT / "main.py", *COGS.rglob("*.py")] if COGS.exists() else [ROOT / "main.py"]
    )
    for path in source_files:
        if not path.is_file():
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, SyntaxError) as error:
            raise RuntimeError(
                f"Cannot parse {path.relative_to(ROOT)}: {error}"
            ) from error
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            is_getenv = (
                isinstance(func, ast.Attribute)
                and func.attr == "getenv"
                and isinstance(func.value, ast.Name)
                and func.value.id == "os"
            )
            is_env_get = (
                isinstance(func, ast.Attribute)
                and func.attr == "get"
                and isinstance(func.value, ast.Attribute)
                and func.value.attr == "environ"
                and isinstance(func.value.value, ast.Name)
                and func.value.value.id == "os"
            )
            if (is_getenv or is_env_get) and node.args:
                name = literal_string(node.args[0])
                if name:
                    discovered.add(name)
            if isinstance(func, ast.Subscript):
                value = func.value
                if (
                    isinstance(value, ast.Attribute)
                    and value.attr == "environ"
                    and isinstance(value.value, ast.Name)
                    and value.value.id == "os"
                ):
                    name = literal_string(func.slice)
                    if name:
                        discovered.add(name)

    for name in discovered:
        example.setdefault(
            name,
            {
                "name": name,
                "default": "コード側で確認",
                "description": ".env.example に説明を追加してください。",
            },
        )
    return sorted(example.values(), key=lambda item: item["name"])


def render_commands(items: list[dict[str, str]]) -> str:
    lines = [
        "# コマンドリファレンス（自動生成）",
        "",
        "> このページは scripts/generate_docs.py により Cog のデコレーターと docstring から生成されます。手編集せず、ソースコード側を更新してください。",
        "",
        f"検出したコマンド定義: **{len(items)} 件**",
        "",
    ]
    if not items:
        lines.append("コマンド定義は検出されませんでした。")
    for item in items:
        lines.extend(
            [
                f"## **/{item['name']}**",
                "",
                item["description"] or "説明は未設定です。",
                "",
                f"- 定義元: **{item['module']}**",
            ]
        )
        if item["signature"]:
            lines.append(f"- 引数: {item['signature']}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_environment(items: list[dict[str, str]]) -> str:
    lines = [
        "# 環境変数リファレンス（自動生成）",
        "",
        "> .env.example と Python ソースコードから生成されます。秘密情報の値は出力しません。",
        "",
        "| 変数 | サンプル既定値 | 説明 |",
        "| --- | --- | --- |",
    ]
    for item in items:
        description = item["description"].replace("|", "\\|")
        default = item["default"].replace("|", "\\|")
        lines.append(f"| **{item['name']}** | {default} | {description} |")
    return "\n".join(lines) + "\n"


def generate(output: Path = OUTPUT) -> list[Path]:
    output.mkdir(parents=True, exist_ok=True)
    generated = {
        "commands.md": render_commands(collect_commands()),
        "environment.md": render_environment(collect_environment()),
    }
    written = []
    for filename, content in generated.items():
        destination = output / filename
        destination.write_text(content, encoding="utf-8")
        written.append(destination)
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    for path in generate(args.output):
        print(f"Generated {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

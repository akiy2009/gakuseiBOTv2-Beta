import asyncio
from pathlib import Path

import discord
from discord.ext import commands


def _runtime_cog_modules() -> list[str]:
    modules = []
    for path in sorted(Path("cogs").rglob("*.py")):
        if (
            path.name == "__init__.py"
            or path.stem.startswith("test_")
            or path.stem.endswith("_test")
            or "tests" in path.parts
        ):
            continue
        modules.append(".".join(path.with_suffix("").parts))
    return modules


def test_runtime_cogs_load_without_registration_errors():
    async def load_all() -> list[str]:
        test_bot = commands.Bot(
            command_prefix="/",
            intents=discord.Intents.none(),
        )
        failures = []
        try:
            for module in _runtime_cog_modules():
                try:
                    await test_bot.load_extension(module)
                except Exception as error:
                    failures.append(f"{module}: {type(error).__name__}: {error}")
        finally:
            await test_bot.close()
        return failures

    failures = asyncio.run(load_all())
    assert not failures, "Cog loading failed:\n" + "\n".join(failures)

import discord
from discord.ext import commands

from cogs.error import ErrorHandler


def test_application_check_failure_has_a_safe_user_message():
    error_id, message, color = ErrorHandler.get_app_error_info(
        discord.app_commands.CheckFailure()
    )

    assert error_id == "E003"
    assert "条件" in message
    assert isinstance(color, discord.Color)


def test_unknown_application_error_uses_generic_message():
    error_id, message, _ = ErrorHandler.get_app_error_info(
        discord.app_commands.AppCommandError("unexpected")
    )

    assert error_id == "E999"
    assert "不明" in message


def test_prefix_command_not_found_is_silently_ignored():
    assert ErrorHandler.get_prefix_error_message(
        commands.CommandNotFound("!not-a-command")
    ) is None


def test_prefix_missing_permissions_has_a_user_facing_message():
    message = ErrorHandler.get_prefix_error_message(
        commands.MissingPermissions(["manage_messages"])
    )

    assert message is not None
    assert "権限" in message


def test_transaction_ids_are_short_and_unique():
    ids = {ErrorHandler.generate_tx_id() for _ in range(100)}

    assert len(ids) == 100
    assert all(value.startswith("TX-") and len(value) == 11 for value in ids)

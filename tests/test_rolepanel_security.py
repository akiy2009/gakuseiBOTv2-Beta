from types import SimpleNamespace

from cogs.normal.feedback import _channel_id_from_env as feedback_channel_id
from cogs.normal.report import _channel_id_from_env as report_channel_id
from cogs.normal.rolepanel import _is_safe_self_assignable


_PERMISSION_NAMES = (
    "administrator",
    "manage_guild",
    "manage_roles",
    "manage_channels",
    "manage_webhooks",
    "manage_messages",
    "manage_nicknames",
    "manage_events",
    "manage_threads",
    "manage_expressions",
    "create_guild_expressions",
    "view_audit_log",
    "moderate_members",
    "mention_everyone",
    "kick_members",
    "ban_members",
)


class FakeRole:
    def __init__(self, role_id: int, position: int, **permissions: bool):
        self.id = role_id
        self.name = f"role-{role_id}"
        self.position = position
        self.permissions = SimpleNamespace(
            **{name: permissions.get(name, False) for name in _PERMISSION_NAMES}
        )

    def is_default(self) -> bool:
        return False

    def is_bot_managed(self) -> bool:
        return False

    def is_integration(self) -> bool:
        return False

    def is_premium_subscriber(self) -> bool:
        return False

    def __ge__(self, other: "FakeRole") -> bool:
        return self.position >= other.position


def test_feedback_and_report_channels_have_no_hardcoded_fallback(monkeypatch):
    monkeypatch.delenv("FEEDBACK_CHANNEL_ID", raising=False)
    monkeypatch.delenv("REPORT_CHANNEL_ID", raising=False)

    assert feedback_channel_id("FEEDBACK_CHANNEL_ID") is None
    assert report_channel_id("REPORT_CHANNEL_ID") is None


def test_feedback_and_report_channel_ids_are_validated(monkeypatch):
    monkeypatch.setenv("FEEDBACK_CHANNEL_ID", "not-an-id")
    monkeypatch.setenv("REPORT_CHANNEL_ID", "-42")

    assert feedback_channel_id("FEEDBACK_CHANNEL_ID") is None
    assert report_channel_id("REPORT_CHANNEL_ID") is None

    monkeypatch.setenv("FEEDBACK_CHANNEL_ID", "12345")
    monkeypatch.setenv("REPORT_CHANNEL_ID", "67890")

    assert feedback_channel_id("FEEDBACK_CHANNEL_ID") == 12345
    assert report_channel_id("REPORT_CHANNEL_ID") == 67890


def test_role_panel_rejects_privileged_and_unmanageable_roles():
    bot_member = SimpleNamespace(top_role=FakeRole(999, 10))
    safe_role = FakeRole(1, 3)
    privileged_role = FakeRole(2, 2, administrator=True)
    too_high_role = FakeRole(3, 12)

    assert _is_safe_self_assignable(safe_role, bot_member)
    assert not _is_safe_self_assignable(privileged_role, bot_member)
    assert not _is_safe_self_assignable(too_high_role, bot_member)

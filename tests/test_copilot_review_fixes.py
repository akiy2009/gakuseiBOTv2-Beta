from types import SimpleNamespace

from cogs.normal.embed import _valid_image_url
from cogs.normal.rolepanel import _is_safe_self_assignable
from cogs.normal.shorten import _valid_http_url
from cogs.normal.timetable import format_lessons


_PERMISSION_NAMES = (
    "administrator", "manage_guild", "manage_roles", "manage_channels",
    "manage_webhooks", "manage_messages", "manage_nicknames", "manage_events",
    "manage_threads", "manage_expressions", "create_guild_expressions",
    "view_audit_log", "moderate_members", "mention_everyone", "kick_members", "ban_members",
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


def test_role_panel_rejects_privileged_and_unmanageable_roles():
    bot_member = SimpleNamespace(top_role=FakeRole(999, 10))
    creator = SimpleNamespace(top_role=FakeRole(998, 7))
    safe_role = FakeRole(1, 3)
    privileged_role = FakeRole(2, 2, administrator=True)
    above_creator = FakeRole(3, 8)
    above_bot = FakeRole(4, 12)

    assert _is_safe_self_assignable(safe_role, bot_member, creator, False)
    assert not _is_safe_self_assignable(privileged_role, bot_member, creator, False)
    assert not _is_safe_self_assignable(above_creator, bot_member, creator, False)
    assert not _is_safe_self_assignable(above_bot, bot_member, creator, True)


def test_role_panel_allows_guild_owner_hierarchy_exception():
    bot_member = SimpleNamespace(top_role=FakeRole(999, 10))
    owner = SimpleNamespace(top_role=FakeRole(998, 2))
    role = FakeRole(1, 5)

    assert _is_safe_self_assignable(role, bot_member, owner, True)


def test_malformed_urls_are_rejected_without_raising():
    assert not _valid_http_url("https://[broken")
    assert not _valid_image_url("https://[broken/image.png")
    assert _valid_http_url("https://example.com/path")
    assert _valid_image_url("https://example.com/image.png")


def test_timetable_description_stays_within_discord_limit():
    lessons = [
        SimpleNamespace(name="N" * 100, place="P" * 100, is_event=True)
        for _ in range(20)
    ]
    description = format_lessons(lessons)

    assert len(description) <= 4096
    assert "文字数制限" in description or "行事" in description

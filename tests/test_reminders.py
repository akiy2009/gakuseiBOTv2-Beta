from datetime import UTC, datetime, timedelta, timezone

import pytest

from cogs.normal.reminders import ReminderError, ReminderStore, parse_due_at


def make_store(tmp_path):
    store = ReminderStore(tmp_path / "data" / "reminders.sqlite3")
    store.initialize()
    return store


def test_reminder_persists_and_is_owner_scoped(tmp_path):
    store = make_store(tmp_path)
    due = datetime.now(UTC) + timedelta(hours=1)
    reminder_id = store.add(10, "研究発表の準備", due)

    restarted = ReminderStore(tmp_path / "data" / "reminders.sqlite3")
    restarted.initialize()
    assert restarted.list_for_user(10)[0]["id"] == reminder_id
    assert restarted.list_for_user(20) == []
    assert restarted.cancel(20, reminder_id) is False
    assert restarted.cancel(10, reminder_id) is True


def test_due_reminders_are_claimed_once_and_recovered_after_lease(tmp_path):
    store = make_store(tmp_path)
    now = datetime.now(UTC)
    reminder_id = store.add(10, "通知", now + timedelta(seconds=1))
    due_now = now + timedelta(seconds=2)

    claimed = store.claim_due(now=due_now)
    assert [row["id"] for row in claimed] == [reminder_id]
    assert store.claim_due(now=due_now) == []

    # Simulate a process restart after the lease expires.
    recovered = store.claim_due(now=due_now + timedelta(seconds=121))
    assert [row["id"] for row in recovered] == [reminder_id]


def test_complete_and_snooze_are_owner_scoped(tmp_path):
    store = make_store(tmp_path)
    reminder_id = store.add(10, "課題", datetime.now(UTC) + timedelta(hours=1))
    assert store.snooze(20, reminder_id, 10) is False
    assert store.complete(20, reminder_id) is False
    assert store.snooze(10, reminder_id, 10) is True
    assert store.complete(10, reminder_id) is True


def test_reminder_validation_and_limits(tmp_path):
    store = make_store(tmp_path)
    with pytest.raises(ReminderError):
        store.add(10, " ", datetime.now(UTC) + timedelta(hours=1))
    with pytest.raises(ReminderError):
        store.add(10, "x" * 1001, datetime.now(UTC) + timedelta(hours=1))
    with pytest.raises(ReminderError):
        store.snooze(10, 1, 10081)
    with pytest.raises(ReminderError):
        parse_due_at("not a date")


def test_parse_due_at_uses_japan_time():
    from datetime import datetime
    from zoneinfo import ZoneInfo

    future = datetime.now(ZoneInfo("Asia/Tokyo")) + timedelta(days=30)
    value = parse_due_at(future.strftime("%Y-%m-%d %H:%M"))
    assert value.tzinfo is not None
    assert value.astimezone(timezone(timedelta(hours=9))).hour == future.hour

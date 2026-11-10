from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from scripts.supabase_keepalive import (
    KeepaliveError,
    run_keepalive,
    validate_project_url,
)


def test_project_url_requires_https_and_no_credentials():
    assert (
        validate_project_url("https://example.supabase.co/")
        == "https://example.supabase.co"
    )
    for value in (
        "http://example.supabase.co",
        "https://user:pass@example.supabase.co",
        "https://example.supabase.co?token=secret",
        "not-a-url",
    ):
        with pytest.raises(KeepaliveError):
            validate_project_url(value)


def test_monday_run_writes_then_verifies(monkeypatch):
    calls = []

    def fake_request(url, method, api_key, payload=None):
        calls.append((url, method, payload))
        if method == "POST":
            return None
        return [
            {
                "key": "github-actions",
                "workflow_run_id": "12345",
                "check_type": "monday_weekly",
            }
        ]

    monkeypatch.setattr("scripts.supabase_keepalive.request_json", fake_request)
    now = datetime(2026, 11, 9, 6, 0, tzinfo=ZoneInfo("Asia/Tokyo"))
    result = run_keepalive("https://example.supabase.co", "test-key", now, "12345")

    assert result["status"] == "success"
    assert result["check_type"] == "monday_weekly"
    assert len(calls) == 2
    assert calls[0][1] == "POST"
    assert calls[0][2]["key"] == "github-actions"
    assert calls[0][2]["check_type"] == "monday_weekly"
    assert calls[1][1] == "GET"


def test_non_monday_run_is_scheduled(monkeypatch):
    def fake_request(url, method, api_key, payload=None):
        if method == "POST":
            return None
        return [{"key": "github-actions", "workflow_run_id": "77"}]

    monkeypatch.setattr("scripts.supabase_keepalive.request_json", fake_request)
    now = datetime(2026, 11, 10, 6, 0, tzinfo=ZoneInfo("Asia/Tokyo"))
    result = run_keepalive("https://example.supabase.co", "test-key", now, "77")
    assert result["check_type"] == "scheduled"


def test_readback_mismatch_fails(monkeypatch):
    def fake_request(url, method, api_key, payload=None):
        return None if method == "POST" else []

    monkeypatch.setattr("scripts.supabase_keepalive.request_json", fake_request)
    now = datetime(2026, 11, 9, 6, 0, tzinfo=ZoneInfo("Asia/Tokyo"))
    with pytest.raises(KeepaliveError, match="read-back"):
        run_keepalive("https://example.supabase.co", "test-key", now, "123")

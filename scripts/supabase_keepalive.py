#!/usr/bin/env python3
"""Record and verify a small heartbeat through the Supabase Data API.

The upsert is idempotent and uses a dedicated table. Never print credentials or
HTTP response bodies because provider error messages can contain sensitive data.
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

JST = ZoneInfo("Asia/Tokyo")
TABLE = "ops_heartbeat"
HEARTBEAT_KEY = "github-actions"
TIMEOUT_SECONDS = 15
MAX_ATTEMPTS = 3


class KeepaliveError(RuntimeError):
    """A safe-to-display keepalive failure."""


def validate_project_url(value: str) -> str:
    parsed = urlsplit(value.strip())
    if parsed.scheme != "https" or not parsed.hostname:
        raise KeepaliveError("SUPABASE_URL must be a valid HTTPS project URL.")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise KeepaliveError("SUPABASE_URL must not contain credentials, query, or fragment.")
    return value.strip().rstrip("/")


def request_json(
    url: str,
    method: str,
    api_key: str,
    payload: dict[str, Any] | None = None,
) -> Any:
    body = None if payload is None else json.dumps(payload, separators=(",", ":")).encode("utf-8")
    headers = {
        "apikey": api_key,
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "Cache-Control": "no-cache",
    }
    if body is not None:
        headers["Content-Type"] = "application/json"
        headers["Prefer"] = "resolution=merge-duplicates,return=minimal"
    request = Request(url, data=body, headers=headers, method=method)

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
                raw = response.read()
                if not raw:
                    return None
                return json.loads(raw.decode("utf-8"))
        except HTTPError as error:
            retryable = error.code == 429 or 500 <= error.code <= 599
            if not retryable or attempt == MAX_ATTEMPTS:
                raise KeepaliveError(f"Supabase returned HTTP {error.code}.") from None
        except (URLError, TimeoutError, OSError):
            if attempt == MAX_ATTEMPTS:
                raise KeepaliveError("Supabase request failed after 3 attempts.") from None
        time.sleep(2 ** (attempt - 1))

    raise KeepaliveError("Supabase request failed.")


def run_keepalive(
    project_url: str,
    api_key: str,
    now: datetime | None = None,
    run_id: str = "local",
) -> dict[str, str]:
    if not api_key.strip():
        raise KeepaliveError("SUPABASE_SERVICE_ROLE_KEY is not configured.")
    base_url = validate_project_url(project_url)
    local_now = (now or datetime.now(JST)).astimezone(JST)
    check_type = "monday_weekly" if local_now.weekday() == 0 else "scheduled"
    checked_at = local_now.isoformat(timespec="seconds")

    endpoint = f"{base_url}/rest/v1/{TABLE}"
    request_json(
        f"{endpoint}?on_conflict=key",
        "POST",
        api_key,
        {
            "key": HEARTBEAT_KEY,
            "checked_at": checked_at,
            "workflow_run_id": str(run_id)[:100],
            "check_type": check_type,
        },
    )

    query = urlencode(
        {
            "select": "key,checked_at,workflow_run_id,check_type",
            "key": f"eq.{HEARTBEAT_KEY}",
            "limit": "1",
        }
    )
    rows = request_json(f"{endpoint}?{query}", "GET", api_key)
    if not isinstance(rows, list) or len(rows) != 1:
        raise KeepaliveError("Heartbeat write completed, but read-back verification failed.")
    row = rows[0]
    if row.get("key") != HEARTBEAT_KEY or row.get("workflow_run_id") != str(run_id)[:100]:
        raise KeepaliveError("Heartbeat read-back did not match this workflow run.")

    return {
        "status": "success",
        "checked_at": checked_at,
        "check_type": check_type,
        "verified": "true",
    }


def main() -> int:
    project_url = os.getenv("SUPABASE_URL", "")
    api_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    if not project_url or not api_key:
        print("Supabase keepalive skipped: required GitHub Secrets are not configured.")
        return 0

    try:
        result = run_keepalive(
            project_url,
            api_key,
            run_id=os.getenv("GITHUB_RUN_ID", "manual"),
        )
    except KeepaliveError as error:
        print(f"::error::{error}", file=sys.stderr)
        return 1

    print(
        "Supabase heartbeat verified: "
        f"{result['checked_at']} ({result['check_type']}, "
        f"read-back={result['verified']})."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

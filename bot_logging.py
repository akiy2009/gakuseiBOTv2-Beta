"""Central logging configuration for gakuseiBOT.

Logs are emitted to stdout and, when enabled, a rotating UTF-8 log file.
A bounded in-memory handler retains recent startup messages for the optional
Discord startup report.
"""

from __future__ import annotations

import logging
import os
import sys
from collections import deque
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import TextIO


_DEFAULT_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"
_STARTUP_BUFFER: "StartupBufferHandler | None" = None


class StartupBufferHandler(logging.Handler):
    """Keep a bounded, formatted copy of recent records for startup reporting."""

    def __init__(self, capacity: int = 200) -> None:
        super().__init__()
        self.records: deque[str] = deque(maxlen=max(1, capacity))

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.records.append(self.format(record))
        except Exception:
            self.handleError(record)

    def getvalue(self) -> str:
        return "\n".join(self.records)


def _positive_int(value: str | None, default: int, setting: str) -> int:
    if value is None or not value.strip():
        return default
    try:
        parsed = int(value)
    except ValueError:
        sys.stderr.write(f"Invalid {setting}; using {default}.\n")
        return default
    if parsed <= 0:
        sys.stderr.write(f"{setting} must be positive; using {default}.\n")
        return default
    return parsed


def _nonnegative_int(value: str | None, default: int, setting: str) -> int:
    if value is None or not value.strip():
        return default
    try:
        parsed = int(value)
    except ValueError:
        sys.stderr.write(f"Invalid {setting}; using {default}.\n")
        return default
    if parsed < 0:
        sys.stderr.write(f"{setting} must not be negative; using {default}.\n")
        return default
    return parsed


def configure_logging(
    *,
    stream: TextIO | None = None,
    log_file: str | Path | None = None,
    level: str | None = None,
    max_bytes: int | None = None,
    backup_count: int | None = None,
    buffer_capacity: int = 200,
) -> StartupBufferHandler:
    """Configure root logging and return the bounded startup-log handler.

    Passing an empty log_file disables file logging. The default stream is
    stderr, which works with Docker and common process supervisors.
    """
    global _STARTUP_BUFFER

    resolved_level = (level or os.getenv("LOG_LEVEL", "INFO")).upper().strip()
    numeric_level = getattr(logging, resolved_level, None)
    if not isinstance(numeric_level, int):
        sys.stderr.write(f"Invalid LOG_LEVEL={resolved_level!r}; using INFO.\n")
        numeric_level = logging.INFO

    root = logging.getLogger()
    for existing in root.handlers[:]:
        root.removeHandler(existing)
    root.setLevel(numeric_level)

    resolved_max_bytes = (
        max_bytes
        if max_bytes is not None
        else _positive_int(os.getenv("LOG_MAX_BYTES"), 5 * 1024 * 1024, "LOG_MAX_BYTES")
    )
    resolved_backup_count = (
        backup_count
        if backup_count is not None
        else _nonnegative_int(os.getenv("LOG_BACKUP_COUNT"), 5, "LOG_BACKUP_COUNT")
    )

    formatter = logging.Formatter(_DEFAULT_FORMAT)
    console_handler = logging.StreamHandler(stream or sys.stderr)
    console_handler.setFormatter(formatter)
    root.addHandler(console_handler)

    target = log_file
    if target is None:
        target = os.getenv("LOG_FILE", "logs/gakuseibot.log")
    target_text = str(target).strip()
    if target_text:
        path = Path(target_text)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            file_handler = RotatingFileHandler(
                path,
                maxBytes=max(1, resolved_max_bytes),
                backupCount=max(0, resolved_backup_count),
                encoding="utf-8",
            )
            file_handler.setFormatter(formatter)
            root.addHandler(file_handler)
        except OSError as error:
            sys.stderr.write(
                f"Could not enable file logging at {path}: "
                f"{type(error).__name__}. Continuing with console logging.\n"
            )

    startup_handler = StartupBufferHandler(capacity=buffer_capacity)
    startup_handler.setFormatter(formatter)
    startup_handler.setLevel(logging.INFO)
    root.addHandler(startup_handler)
    _STARTUP_BUFFER = startup_handler
    return startup_handler


def get_startup_log() -> str:
    """Return recent startup/runtime records captured by the buffer handler."""
    if _STARTUP_BUFFER is None:
        return ""
    return _STARTUP_BUFFER.getvalue()

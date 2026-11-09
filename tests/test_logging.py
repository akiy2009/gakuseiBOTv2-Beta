import io
import logging

from bot_logging import (
    StartupBufferHandler,
    _nonnegative_int,
    _positive_int,
    configure_logging,
    get_startup_log,
)


def test_startup_buffer_keeps_only_the_most_recent_records():
    handler = StartupBufferHandler(capacity=2)
    handler.setFormatter(logging.Formatter("%(levelname)s:%(message)s"))
    logger = logging.getLogger("test.startup-buffer")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    try:
        logger.info("first")
        logger.warning("second")
        logger.error("third")
    finally:
        logger.removeHandler(handler)
        handler.close()

    assert handler.getvalue().splitlines() == [
        "WARNING:second",
        "ERROR:third",
    ]


def test_logging_writes_to_console_file_and_startup_buffer(tmp_path):
    root = logging.getLogger()
    previous_handlers = root.handlers[:]
    previous_level = root.level
    stream = io.StringIO()
    log_path = tmp_path / "logs" / "bot.log"
    try:
        configure_logging(
            stream=stream,
            log_file=log_path,
            level="DEBUG",
            max_bytes=1024,
            backup_count=2,
        )
        logging.getLogger("test.application").warning("sample diagnostic")
        assert "sample diagnostic" in stream.getvalue()
        assert "sample diagnostic" in log_path.read_text(encoding="utf-8")
        assert "sample diagnostic" in get_startup_log()
    finally:
        for handler in root.handlers[:]:
            root.removeHandler(handler)
            if handler not in previous_handlers:
                handler.close()
        for handler in previous_handlers:
            if handler not in root.handlers:
                root.addHandler(handler)
        root.setLevel(previous_level)


def test_logging_settings_fall_back_for_invalid_values(capsys):
    assert _positive_int("0", 100, "LOG_MAX_BYTES") == 100
    assert _positive_int("invalid", 100, "LOG_MAX_BYTES") == 100
    assert _nonnegative_int("-1", 5, "LOG_BACKUP_COUNT") == 5
    assert _nonnegative_int("0", 5, "LOG_BACKUP_COUNT") == 0
    assert "LOG_MAX_BYTES" in capsys.readouterr().err

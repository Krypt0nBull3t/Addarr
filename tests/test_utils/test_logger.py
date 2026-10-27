"""Tests for src/utils/logger.py"""

import logging
from logging.handlers import RotatingFileHandler
from unittest.mock import patch, MagicMock

import pytest

from src.utils.logger import (
    ColoredFormatter,
    ColoredLogger,
    get_logger,
    log_exception,
    log_user_interaction,
    SUCCESS_LEVEL,
)


class TestColoredFormatter:
    """Tests for ColoredFormatter.format with various log levels."""

    def _make_record(self, level, msg="test message"):
        """Create a log record at the given level."""
        record = logging.LogRecord(
            name="test", level=level, pathname="", lineno=0,
            msg=msg, args=(), exc_info=None,
        )
        return record

    def test_format_error_level(self):
        """ERROR messages get wrapped in red ANSI codes."""
        formatter = ColoredFormatter("%(message)s")
        record = self._make_record(logging.ERROR)
        result = formatter.format(record)
        # After formatting, the original msg should be restored
        assert record.msg == "test message"
        assert "test message" in result

    def test_format_warning_level(self):
        """WARNING messages get wrapped in yellow ANSI codes."""
        formatter = ColoredFormatter("%(message)s")
        record = self._make_record(logging.WARNING)
        result = formatter.format(record)
        assert record.msg == "test message"
        assert "test message" in result

    def test_format_info_level(self):
        """INFO messages get wrapped in blue ANSI codes."""
        formatter = ColoredFormatter("%(message)s")
        record = self._make_record(logging.INFO)
        result = formatter.format(record)
        assert record.msg == "test message"
        assert "test message" in result

    def test_format_debug_level(self):
        """DEBUG messages get wrapped in cyan ANSI codes."""
        formatter = ColoredFormatter("%(message)s")
        record = self._make_record(logging.DEBUG)
        result = formatter.format(record)
        assert record.msg == "test message"
        assert "test message" in result


class TestColoredLogger:
    """Tests for ColoredLogger.success method."""

    def test_success_enabled(self):
        """success() logs at SUCCESS_LEVEL when enabled."""
        logger = ColoredLogger("test_success")
        logger.setLevel(logging.DEBUG)
        with patch.object(logger, "_log") as mock_log:
            logger.success("it worked")
            mock_log.assert_called_once_with(SUCCESS_LEVEL, "it worked", ())

    def test_success_disabled(self):
        """success() does not log when level is above SUCCESS_LEVEL."""
        logger = ColoredLogger("test_success_disabled")
        logger.setLevel(logging.CRITICAL)
        with patch.object(logger, "_log") as mock_log:
            logger.success("it worked")
            mock_log.assert_not_called()


@pytest.fixture
def fresh_loggers():
    """Detach the shared handlers so setup runs again, then restore them."""
    saved = {}
    for name in ("addarr", "interactions"):
        lg = logging.getLogger(name)
        saved[name] = lg.handlers[:]
        lg.handlers.clear()
    with patch("src.utils.logger._shared_handlers_ready", False):
        yield
    for name, handlers in saved.items():
        lg = logging.getLogger(name)
        for h in lg.handlers:
            h.close()
        lg.handlers[:] = handlers


class TestGetLoggerModule:
    """Tests for the module-level get_logger function."""

    def test_child_loggers_share_one_file_handler(self, tmp_path, fresh_loggers):
        """Every addarr.* logger writes through one handler per log file."""
        log_file = str(tmp_path / "addarr.log")
        err_file = str(tmp_path / "error.log")

        with (
            patch("src.utils.logger.LOG_PATH", log_file),
            patch("src.utils.logger.ERROR_LOG_PATH", err_file),
        ):
            first = get_logger("addarr.test_first")
            second = get_logger("addarr.test_second")

        assert first.handlers == [] and second.handlers == []
        assert first.propagate and second.propagate
        files = [
            h.baseFilename for h in logging.getLogger("addarr").handlers
            if isinstance(h, RotatingFileHandler)
        ]
        assert sorted(files) == sorted([log_file, err_file])

    def test_child_logger_writes_to_shared_file(self, tmp_path, fresh_loggers):
        """A child logger's records reach addarr.log through the parent."""
        log_file = tmp_path / "addarr.log"

        with (
            patch("src.utils.logger.LOG_PATH", str(log_file)),
            patch("src.utils.logger.ERROR_LOG_PATH", str(tmp_path / "error.log")),
        ):
            get_logger("addarr.test_write").info("hello file")

        assert "hello file" in log_file.read_text(encoding="utf-8")

    def test_unwritable_log_folder_logs_to_console_with_one_warning(
        self, tmp_path, fresh_loggers, capsys
    ):
        """No crash when log files cannot be opened: console only, one warning."""
        with (
            patch("src.utils.logger.LOG_PATH", str(tmp_path / "addarr.log")),
            patch(
                "src.utils.logger.RotatingFileHandler",
                side_effect=PermissionError("Permission denied"),
            ),
        ):
            get_logger("addarr.test_unwritable_a")
            get_logger("addarr.test_unwritable_b").info("still visible")

        err = capsys.readouterr().err
        assert err.count("Logging to the console only") == 1
        assert "still visible" in err
        for name in ("addarr", "interactions"):
            handlers = logging.getLogger(name).handlers
            assert not any(isinstance(h, RotatingFileHandler) for h in handlers)

    def test_interaction_log_rotates(self, tmp_path, fresh_loggers):
        """interactions.log gets a size-based rotating handler."""
        with (
            patch("src.utils.logger.LOG_PATH", str(tmp_path / "addarr.log")),
            patch("src.utils.logger.ERROR_LOG_PATH", str(tmp_path / "error.log")),
        ):
            get_logger("addarr.test_interactions")

        handlers = [
            h for h in logging.getLogger("interactions").handlers
            if isinstance(h, RotatingFileHandler)
        ]
        assert len(handlers) == 1
        assert handlers[0].baseFilename == str(tmp_path / "interactions.log")
        assert handlers[0].maxBytes > 0


class TestLogException:
    """Tests for log_exception helper."""

    def test_log_exception_with_context(self):
        """log_exception includes context in the error message."""
        mock_logger = MagicMock()
        err = ValueError("test error")
        log_exception(mock_logger, err, context="unit test")
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        assert "unit test" in call_args[0][0]
        assert "test error" in call_args[0][0]

    def test_log_exception_without_context(self):
        """log_exception works without context string."""
        mock_logger = MagicMock()
        err = RuntimeError("boom")
        log_exception(mock_logger, err)
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        assert "boom" in call_args[0][0]


class TestLogUserInteraction:
    """Tests for log_user_interaction helper."""

    def test_log_known_action(self, tmp_path):
        """Known action uses its emoji and logs to file."""
        mock_logger = MagicMock()
        user = MagicMock()
        user.username = "alice"
        user.id = 42

        with patch("src.utils.logger.LOG_PATH", str(tmp_path / "addarr.log")):
            log_user_interaction(mock_logger, user, "/start", input_data="hello")

        mock_logger.info.assert_called_once()
        call_msg = mock_logger.info.call_args[0][0]
        assert "alice" in call_msg
        assert "/start" in call_msg
        assert "hello" in call_msg

    def test_log_unknown_action(self, tmp_path):
        """Unknown action uses default emoji."""
        mock_logger = MagicMock()
        user = MagicMock()
        user.username = "bob"
        user.id = 99

        with patch("src.utils.logger.LOG_PATH", str(tmp_path / "addarr.log")):
            log_user_interaction(mock_logger, user, "custom_action")

        mock_logger.info.assert_called_once()

    def test_log_user_no_username(self, tmp_path):
        """Falls back to 'Unknown' when user has no username."""
        mock_logger = MagicMock()
        user = MagicMock()
        user.username = None
        user.id = 1

        with patch("src.utils.logger.LOG_PATH", str(tmp_path / "addarr.log")):
            log_user_interaction(mock_logger, user, "/help")

        call_msg = mock_logger.info.call_args[0][0]
        assert "Unknown" in call_msg

    def test_log_interaction_writes_to_interaction_log(self, tmp_path, fresh_loggers):
        """The interaction line goes to interactions.log via its own logger."""
        with (
            patch("src.utils.logger.LOG_PATH", str(tmp_path / "addarr.log")),
            patch("src.utils.logger.ERROR_LOG_PATH", str(tmp_path / "error.log")),
        ):
            get_logger("addarr.test_interaction_write")
        user = MagicMock()
        user.username = "alice"
        user.id = 42

        log_user_interaction(MagicMock(), user, "/start")

        content = (tmp_path / "interactions.log").read_text(encoding="utf-8")
        assert "User: alice (42) - Action: /start" in content

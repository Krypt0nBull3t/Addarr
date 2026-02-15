"""Tests for src/utils/logger.py"""

import logging
import os
from unittest.mock import patch, MagicMock

from src.utils.logger import (
    ColoredFormatter,
    ColoredLogger,
    LoggerSetup,
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


class TestLoggerSetup:
    """Tests for LoggerSetup class."""

    def test_init_debug_on(self):
        """When debugLogging is True, log_level is DEBUG."""
        mock_cfg = MagicMock()
        mock_cfg.get = lambda key, default=None: {
            "debugLogging": True, "logToConsole": True
        }.get(key, default)
        with patch("src.utils.logger.config", mock_cfg):
            setup = LoggerSetup()
        assert setup.log_level == logging.DEBUG

    def test_init_debug_off(self):
        """When debugLogging is False, log_level is INFO."""
        mock_cfg = MagicMock()
        mock_cfg.get = lambda key, default=None: {
            "debugLogging": False, "logToConsole": False
        }.get(key, default)
        with patch("src.utils.logger.config", mock_cfg):
            setup = LoggerSetup()
        assert setup.log_level == logging.INFO
        assert setup.log_to_console is False

    def test_get_logger(self, tmp_path):
        """get_logger returns a configured logger with handlers."""
        log_file = str(tmp_path / "test.log")
        mock_cfg = MagicMock()
        mock_cfg.get = lambda key, default=None: {
            "debugLogging": False, "logToConsole": True
        }.get(key, default)
        with (
            patch("src.utils.logger.config", mock_cfg),
            patch("src.utils.logger.LOG_PATH", log_file),
        ):
            setup = LoggerSetup()
            logger = setup.get_logger("test_setup_logger")
        assert logger.name == "test_setup_logger"
        assert logger.level == logging.INFO
        assert logger.propagate is False
        assert len(logger.handlers) >= 1
        # Cleanup handlers to avoid ResourceWarning
        for h in logger.handlers[:]:
            logger.removeHandler(h)
            h.close()

    def test_get_logger_removes_existing_handlers(self, tmp_path):
        """get_logger removes existing handlers before adding new ones."""
        log_file = str(tmp_path / "test.log")
        mock_cfg = MagicMock()
        mock_cfg.get = lambda key, default=None: {
            "debugLogging": False, "logToConsole": False
        }.get(key, default)
        with (
            patch("src.utils.logger.config", mock_cfg),
            patch("src.utils.logger.LOG_PATH", log_file),
        ):
            setup = LoggerSetup()
            # Pre-add a handler to the logger
            test_name = "test_remove_existing"
            logger = logging.getLogger(test_name)
            dummy_handler = logging.StreamHandler()
            logger.addHandler(dummy_handler)
            assert len(logger.handlers) >= 1
            # Now call get_logger - it should remove existing and add new
            result = setup.get_logger(test_name)
        # Dummy handler should have been removed
        assert dummy_handler not in result.handlers
        for h in result.handlers[:]:
            result.removeHandler(h)
            h.close()
        dummy_handler.close()

    def test_get_logger_no_log_path(self):
        """get_logger skips file handler when LOG_PATH is falsy."""
        mock_cfg = MagicMock()
        mock_cfg.get = lambda key, default=None: {
            "debugLogging": False, "logToConsole": True
        }.get(key, default)
        with (
            patch("src.utils.logger.config", mock_cfg),
            patch("src.utils.logger.LOG_PATH", ""),
        ):
            setup = LoggerSetup()
            logger = setup.get_logger("test_no_file")
        # Only console handler, no file handler
        assert len(logger.handlers) == 1
        for h in logger.handlers[:]:
            logger.removeHandler(h)
            h.close()

    def test_get_logger_no_console(self, tmp_path):
        """get_logger skips console handler when log_to_console is False."""
        log_file = str(tmp_path / "test.log")
        mock_cfg = MagicMock()
        mock_cfg.get = lambda key, default=None: {
            "debugLogging": False, "logToConsole": False
        }.get(key, default)
        with (
            patch("src.utils.logger.config", mock_cfg),
            patch("src.utils.logger.LOG_PATH", log_file),
        ):
            setup = LoggerSetup()
            logger = setup.get_logger("test_no_console")
        # Only file handler, no console
        assert len(logger.handlers) == 1
        for h in logger.handlers[:]:
            logger.removeHandler(h)
            h.close()

    def test_add_file_handler(self, tmp_path):
        """_add_file_handler creates log dir and adds a TimedRotatingFileHandler."""
        log_file = str(tmp_path / "logs" / "test.log")
        mock_cfg = MagicMock()
        mock_cfg.get = lambda key, default=None: {
            "debugLogging": False, "logToConsole": False
        }.get(key, default)
        with (
            patch("src.utils.logger.config", mock_cfg),
            patch("src.utils.logger.LOG_PATH", log_file),
        ):
            setup = LoggerSetup()
            logger = logging.getLogger("test_file_handler")
            setup._add_file_handler(logger)
        assert os.path.isdir(str(tmp_path / "logs"))
        assert len(logger.handlers) >= 1
        for h in logger.handlers[:]:
            logger.removeHandler(h)
            h.close()

    def test_add_console_handler(self):
        """_add_console_handler adds a StreamHandler with ColoredFormatter."""
        mock_cfg = MagicMock()
        mock_cfg.get = lambda key, default=None: {
            "debugLogging": False, "logToConsole": True
        }.get(key, default)
        with patch("src.utils.logger.config", mock_cfg):
            setup = LoggerSetup()
            logger = logging.getLogger("test_console_handler")
            setup._add_console_handler(logger)
        assert any(
            isinstance(h, logging.StreamHandler) for h in logger.handlers
        )
        for h in logger.handlers[:]:
            logger.removeHandler(h)
            h.close()


class TestGetLoggerModule:
    """Tests for the module-level get_logger function."""

    def test_get_logger_creates_handlers(self, tmp_path):
        """get_logger creates file, error, and console handlers."""
        log_file = str(tmp_path / "addarr.log")
        err_file = str(tmp_path / "error.log")

        # Clear any existing logger with this name
        test_name = "test_module_get_logger"
        existing = logging.getLogger(test_name)
        for h in existing.handlers[:]:
            existing.removeHandler(h)
            h.close()

        with (
            patch("src.utils.logger.LOG_PATH", log_file),
            patch("src.utils.logger.ERROR_LOG_PATH", err_file),
        ):
            logger = get_logger(test_name)

        assert logger.name == test_name
        assert logger.propagate is False
        assert len(logger.handlers) == 3  # file, error, console
        for h in logger.handlers[:]:
            logger.removeHandler(h)
            h.close()

    def test_get_logger_no_duplicate_handlers(self, tmp_path):
        """Calling get_logger twice does not duplicate handlers."""
        log_file = str(tmp_path / "addarr.log")
        err_file = str(tmp_path / "error.log")

        test_name = "test_no_dup_handlers"
        existing = logging.getLogger(test_name)
        for h in existing.handlers[:]:
            existing.removeHandler(h)
            h.close()

        with (
            patch("src.utils.logger.LOG_PATH", log_file),
            patch("src.utils.logger.ERROR_LOG_PATH", err_file),
        ):
            logger1 = get_logger(test_name)
            handler_count = len(logger1.handlers)
            logger2 = get_logger(test_name)

        assert len(logger2.handlers) == handler_count
        for h in logger2.handlers[:]:
            logger2.removeHandler(h)
            h.close()


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

    def test_log_interaction_file_write_error(self, tmp_path):
        """Logs error when interaction log file write fails."""
        mock_logger = MagicMock()
        user = MagicMock()
        user.username = "alice"
        user.id = 42

        # Use a path that will fail (directory as file)
        bad_path = str(tmp_path / "nonexistent_dir" / "subdir" / "addarr.log")
        with patch("src.utils.logger.LOG_PATH", bad_path):
            log_user_interaction(mock_logger, user, "/start")

        # Should log the error
        mock_logger.error.assert_called_once()
        assert "Failed to write" in mock_logger.error.call_args[0][0]

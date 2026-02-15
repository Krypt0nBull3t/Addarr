"""Tests for src/utils/error_handler.py"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, mock_open

from telegram.error import BadRequest, Forbidden, InvalidToken, NetworkError

from src.utils.error_handler import (
    AddarrError,
    ConfigError,
    ValidationError,
    ServiceNotEnabledError,
    handle_token_error,
    handle_missing_token_error,
    handle_network_error,
    handle_initialization_error,
    handle_telegram_error,
    send_error_message,
)


# ---- Custom exception classes ----


class TestAddarrError:
    """Tests for the AddarrError base exception."""

    def test_addarr_error(self):
        """user_message defaults to message when not provided."""
        err = AddarrError("something broke")
        assert str(err) == "something broke"
        assert err.user_message == "something broke"

    def test_addarr_error_custom_user_message(self):
        """Internal and user-facing messages can differ."""
        err = AddarrError("internal detail", user_message="Please try again")
        assert str(err) == "internal detail"
        assert err.user_message == "Please try again"


class TestExceptionSubclasses:
    """Tests for AddarrError subclasses."""

    def test_config_error_inherits(self):
        """ConfigError is a subclass of AddarrError."""
        err = ConfigError("bad config")
        assert isinstance(err, AddarrError)

    def test_validation_error_inherits(self):
        """ValidationError is a subclass of AddarrError."""
        err = ValidationError("invalid data")
        assert isinstance(err, AddarrError)

    def test_service_not_enabled_error(self):
        """ServiceNotEnabledError is a subclass of AddarrError."""
        err = ServiceNotEnabledError("radarr disabled")
        assert isinstance(err, AddarrError)


# ---- handle_token_error ----


class TestHandleTokenError:
    """Tests for handle_token_error."""

    def test_user_says_yes_valid_token(self):
        """Returns True when user enters y and provides valid token."""
        yaml_data = {"telegram": {"token": "old-token"}}
        with (
            patch("builtins.input", side_effect=["y", "new-valid-token"]),
            patch("builtins.open", mock_open(read_data="telegram:\n  token: old\n")),
            patch("yaml.safe_load", return_value=yaml_data),
            patch("yaml.dump"),
        ):
            result = handle_token_error("old-token")
        assert result is True
        # Verify token was updated in the config dict
        assert yaml_data["telegram"]["token"] == "new-valid-token"

    def test_user_says_yes_empty_token_then_yes_valid(self):
        """Retries when user enters empty token, then succeeds."""
        yaml_data = {"telegram": {"token": "old"}}
        with (
            patch("builtins.input", side_effect=["y", "  ", "y", "good-token"]),
            patch("builtins.open", mock_open(read_data="telegram:\n  token: old\n")),
            patch("yaml.safe_load", return_value=yaml_data),
            patch("yaml.dump"),
        ):
            result = handle_token_error("old")
        assert result is True

    def test_user_says_yes_no_telegram_section(self):
        """Creates telegram section if missing in config."""
        yaml_data = {}
        with (
            patch("builtins.input", side_effect=["y", "new-token"]),
            patch("builtins.open", mock_open(read_data="{}")),
            patch("yaml.safe_load", return_value=yaml_data),
            patch("yaml.dump"),
        ):
            result = handle_token_error("bad")
        assert result is True
        assert yaml_data["telegram"]["token"] == "new-token"

    def test_user_says_yes_file_error(self):
        """Returns False when file operation fails."""
        with (
            patch("builtins.input", side_effect=["y", "new-token"]),
            patch("builtins.open", side_effect=IOError("disk full")),
        ):
            result = handle_token_error("bad")
        assert result is False

    def test_user_says_no(self):
        """Returns False when user declines."""
        with patch("builtins.input", return_value="n"):
            result = handle_token_error("bad-token")
        assert result is False

    def test_invalid_then_no(self):
        """Prompts again after invalid input, then user says n."""
        with patch("builtins.input", side_effect=["maybe", "n"]):
            result = handle_token_error("bad-token")
        assert result is False


# ---- handle_missing_token_error ----


class TestHandleMissingTokenError:
    """Tests for handle_missing_token_error."""

    def test_prints_instructions(self):
        """Prints setup instructions without raising."""
        handle_missing_token_error()  # should not raise


# ---- handle_network_error ----


class TestHandleNetworkError:
    """Tests for handle_network_error."""

    def test_prints_instructions(self):
        """Prints troubleshooting instructions without raising."""
        handle_network_error()  # should not raise


# ---- handle_initialization_error ----


class TestHandleInitializationError:
    """Tests for handle_initialization_error."""

    def test_prints_error_details(self):
        """Prints error details and troubleshooting steps."""
        error = RuntimeError("failed to start")
        handle_initialization_error(error)  # should not raise


# ---- handle_telegram_error ----


class TestHandleTelegramError:
    """Tests for async handle_telegram_error."""

    @pytest.mark.asyncio
    async def test_handle_invalid_token(self):
        """InvalidToken triggers handle_token_error."""
        update = MagicMock()
        update.effective_message = None
        error = InvalidToken("bad token")
        with patch("src.utils.error_handler.handle_token_error") as mock_handle:
            await handle_telegram_error(update, error)
            mock_handle.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_network_error_type(self):
        """NetworkError triggers handle_network_error."""
        update = MagicMock()
        update.effective_message = None
        error = NetworkError("network down")
        with patch("src.utils.error_handler.handle_network_error") as mock_handle:
            await handle_telegram_error(update, error)
            mock_handle.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_telegram_error_bad_request(self):
        """BadRequest is a NetworkError subclass, so it takes the network error path."""
        update = MagicMock()
        update.effective_message = AsyncMock()
        update.effective_message.reply_text = AsyncMock()

        error = BadRequest("bad request")

        with patch(
            "src.utils.error_handler.handle_network_error"
        ) as mock_handle:
            await handle_telegram_error(update, error)
            mock_handle.assert_called_once()

        # reply_text should NOT be called -- network errors just print
        update.effective_message.reply_text.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_handle_telegram_error_forbidden(self):
        """Forbidden error logs and replies via effective_message."""
        update = MagicMock()
        update.effective_message = AsyncMock()
        update.effective_message.reply_text = AsyncMock()

        error = Forbidden("forbidden")
        await handle_telegram_error(update, error)

        update.effective_message.reply_text.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_handle_telegram_error_unknown(self):
        """Generic Exception logs and replies via effective_message."""
        update = MagicMock()
        update.effective_message = AsyncMock()
        update.effective_message.reply_text = AsyncMock()

        error = Exception("unexpected")
        await handle_telegram_error(update, error)

        update.effective_message.reply_text.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_handle_telegram_error_no_message(self):
        """No crash when update.effective_message is None."""
        update = MagicMock()
        update.effective_message = None

        error = BadRequest("bad request")
        await handle_telegram_error(update, error)  # should not raise

    @pytest.mark.asyncio
    async def test_handle_telegram_error_unknown_no_message(self):
        """Unknown error with no effective_message does not crash."""
        update = MagicMock()
        update.effective_message = None

        error = Exception("boom")
        await handle_telegram_error(update, error)  # should not raise

    @pytest.mark.asyncio
    async def test_handle_telegram_error_none_update(self):
        """None update does not crash for unknown error."""
        update = MagicMock()
        update.effective_message = None
        error = Exception("unexpected")
        await handle_telegram_error(update, error)


# ---- send_error_message ----


class TestSendErrorMessage:
    """Tests for async send_error_message."""

    @pytest.mark.asyncio
    async def test_send_error_message_text(self):
        """Calls edit_text when message.photo is falsy."""
        message = AsyncMock()
        message.photo = None
        message.edit_text = AsyncMock()

        await send_error_message(message, "error text")

        message.edit_text.assert_awaited_once_with(
            text="error text", reply_markup=None
        )

    @pytest.mark.asyncio
    async def test_send_error_message_photo(self):
        """Calls edit_caption when message.photo is truthy."""
        message = AsyncMock()
        message.photo = [MagicMock()]  # truthy list
        message.edit_caption = AsyncMock()

        await send_error_message(message, "error text")

        message.edit_caption.assert_awaited_once_with(
            caption="error text", reply_markup=None
        )

    @pytest.mark.asyncio
    async def test_send_error_message_fallback(self):
        """Falls back to reply_text when edit_text raises an exception."""
        message = AsyncMock()
        message.photo = None
        message.edit_text = AsyncMock(side_effect=Exception("edit failed"))
        message.reply_text = AsyncMock()

        await send_error_message(message, "error text")

        message.reply_text.assert_awaited_once_with(
            "error text", reply_markup=None
        )

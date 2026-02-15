"""Tests for src/utils/error_handler.py"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from telegram.error import BadRequest, Forbidden

from src.utils.error_handler import (
    AddarrError,
    ConfigError,
    ValidationError,
    ServiceNotEnabledError,
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


# ---- handle_telegram_error ----


class TestHandleTelegramError:
    """Tests for async handle_telegram_error."""

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

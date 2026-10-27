"""
Tests for src/bot/handlers/transmission.py - TransmissionHandler.

TransmissionHandler uses a module-level `transmission_service` global from
src.services.transmission. The handler checks is_enabled() before proceeding.
Service methods get_status/set_alt_speed/test_connection are async.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock


@pytest.fixture(autouse=True)
def _authenticated():
    """Handlers require auth; authenticate the default test user 12345."""
    from src.bot.handlers.auth import AuthHandler
    AuthHandler._authenticated_users = {12345}


# ---------------------------------------------------------------------------
# transmission_command
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("src.bot.handlers.transmission.TranslationService")
@patch("src.bot.handlers.transmission.transmission_service")
async def test_transmission_not_enabled(
    mock_service, mock_ts_class, make_update, make_context
):
    """When transmission is not enabled, reply with 'not enabled' message."""
    mock_service.is_enabled = MagicMock(return_value=False)
    mock_translation = MagicMock()
    mock_translation.get_text = MagicMock(return_value="not enabled")
    mock_ts_class.return_value = mock_translation

    from src.bot.handlers.transmission import TransmissionHandler

    handler = TransmissionHandler()
    handler.service = mock_service

    update = make_update(text="/transmission")
    context = make_context()

    await handler.transmission_command(update, context)

    update.message.reply_text.assert_called_once()
    mock_translation.get_text.assert_any_call("TransmissionNotEnabled")


@pytest.mark.asyncio
@patch("src.bot.handlers.transmission.TranslationService")
@patch("src.bot.handlers.transmission.transmission_service")
async def test_transmission_not_connected(
    mock_service, mock_ts_class, make_update, make_context
):
    """When transmission is enabled but not connected, show error."""
    mock_service.is_enabled = MagicMock(return_value=True)
    mock_service.get_status = AsyncMock(return_value={
        "connected": False,
        "error": "Connection refused"
    })
    mock_translation = MagicMock()
    mock_translation.get_text = MagicMock(return_value="connection error")
    mock_ts_class.return_value = mock_translation

    from src.bot.handlers.transmission import TransmissionHandler

    handler = TransmissionHandler()
    handler.service = mock_service

    update = make_update(text="/transmission")
    context = make_context()

    await handler.transmission_command(update, context)

    update.message.reply_text.assert_called_once()
    mock_translation.get_text.assert_any_call(
        "TransmissionConnectionError", error="Connection refused"
    )


@pytest.mark.asyncio
@patch("src.bot.handlers.transmission.get_yes_no_keyboard")
@patch("src.bot.handlers.transmission.transmission_service")
async def test_transmission_connected(
    mock_service, mock_keyboard, make_update, make_context
):
    """When connected, show status with toggle keyboard."""
    mock_service.is_enabled = MagicMock(return_value=True)
    mock_service.get_status = AsyncMock(return_value={
        "connected": True,
        "alt_speed_enabled": False,
        "version": "3.0.0"
    })
    mock_keyboard.return_value = MagicMock()

    from src.bot.handlers.transmission import TransmissionHandler

    handler = TransmissionHandler()
    handler.service = mock_service

    update = make_update(text="/transmission")
    context = make_context()

    await handler.transmission_command(update, context)

    update.message.reply_text.assert_called_once()


# ---------------------------------------------------------------------------
# handle_callback
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("src.bot.handlers.transmission.transmission_service")
async def test_handle_callback_toggle_yes_success(
    mock_service, make_update, make_context
):
    """Toggle yes with success toggles turtle mode."""
    mock_service.get_status = AsyncMock(return_value={
        "alt_speed_enabled": False,
    })
    mock_service.set_alt_speed = AsyncMock(return_value=True)

    from src.bot.handlers.transmission import TransmissionHandler

    handler = TransmissionHandler()
    handler.service = mock_service

    update = make_update(callback_data="transmission_toggle_yes")
    context = make_context()

    await handler.handle_callback(update, context)

    update.callback_query.answer.assert_called_once()
    update.callback_query.edit_message_text.assert_called_once()
    call_args = update.callback_query.edit_message_text.call_args
    assert "enabled" in str(call_args).lower()


@pytest.mark.asyncio
@patch("src.bot.handlers.transmission.TranslationService")
@patch("src.bot.handlers.transmission.transmission_service")
async def test_handle_callback_toggle_yes_failure(
    mock_service, mock_ts_class, make_update, make_context
):
    """Toggle yes with failure shows error."""
    mock_service.get_status = AsyncMock(return_value={
        "alt_speed_enabled": False,
    })
    mock_service.set_alt_speed = AsyncMock(return_value=False)
    mock_translation = MagicMock()
    mock_translation.get_text = MagicMock(return_value="toggle failed")
    mock_ts_class.return_value = mock_translation

    from src.bot.handlers.transmission import TransmissionHandler

    handler = TransmissionHandler()
    handler.service = mock_service

    update = make_update(callback_data="transmission_toggle_yes")
    context = make_context()

    await handler.handle_callback(update, context)

    update.callback_query.edit_message_text.assert_called_once()
    mock_translation.get_text.assert_any_call("TransmissionToggleFailed")


@pytest.mark.asyncio
@patch("src.bot.handlers.transmission.transmission_service")
async def test_handle_callback_toggle_no(
    mock_service, make_update, make_context
):
    """Toggle no keeps current settings."""
    from src.bot.handlers.transmission import TransmissionHandler

    handler = TransmissionHandler()
    handler.service = mock_service

    update = make_update(callback_data="transmission_toggle_no")
    context = make_context()

    await handler.handle_callback(update, context)

    update.callback_query.answer.assert_called_once()
    update.callback_query.edit_message_text.assert_called_once()
    call_args = update.callback_query.edit_message_text.call_args
    assert "Keeping" in str(call_args)


# ---------------------------------------------------------------------------
# get_handler
# ---------------------------------------------------------------------------


@patch("src.bot.handlers.transmission.transmission_service")
def test_get_handler_returns_list(mock_service):
    """get_handler returns a list of handlers."""
    from src.bot.handlers.transmission import TransmissionHandler

    handler = TransmissionHandler()
    handlers = handler.get_handler()

    assert isinstance(handlers, list)
    assert len(handlers) > 0


# ---------------------------------------------------------------------------
# Access control
# ---------------------------------------------------------------------------

TRANSMISSION_ENTRY_POINTS = [
    ("transmission_command", {"text": "/transmission"}),
    ("handle_callback", {"callback_data": "transmission_toggle_yes"}),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("method, update_kwargs", TRANSMISSION_ENTRY_POINTS)
@patch("src.bot.handlers.transmission.transmission_service")
async def test_unauthenticated_user_is_refused(
    mock_service, method, update_kwargs, make_update, make_context
):
    """Unauthenticated users cannot use Transmission (audit item 5)."""
    from src.bot.handlers.auth import AuthHandler
    from src.bot.handlers.transmission import TransmissionHandler

    AuthHandler._authenticated_users = set()
    handler = TransmissionHandler()
    handler.service = mock_service

    await getattr(handler, method)(make_update(**update_kwargs), make_context())

    assert mock_service.method_calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize("method, update_kwargs", TRANSMISSION_ENTRY_POINTS)
@patch("src.bot.handlers.transmission.transmission_service")
async def test_non_admin_is_refused_when_only_admin(
    mock_service, method, update_kwargs, admin_mode, make_update, make_context
):
    """Admin mode plus transmission.onlyAdmin refuses non-admins (audit item 6)."""
    from src.bot.handlers.transmission import TransmissionHandler

    handler = TransmissionHandler()
    handler.service = mock_service

    await getattr(handler, method)(make_update(**update_kwargs), make_context())

    assert mock_service.method_calls == []

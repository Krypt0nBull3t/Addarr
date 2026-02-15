"""
Tests for src/bot/handlers/transmission.py - TransmissionHandler.

TransmissionHandler uses a module-level `transmission_service` global from
src.services.transmission. The handler checks is_enabled() before proceeding.
"""

import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# transmission_command - not enabled
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("src.bot.handlers.transmission.transmission_service")
async def test_transmission_not_enabled(
    mock_service, make_update, make_context
):
    """When transmission is not enabled, reply with 'not enabled' message."""
    mock_service.is_enabled = MagicMock(return_value=False)

    from src.bot.handlers.transmission import TransmissionHandler

    handler = TransmissionHandler()
    # Override service with our mock since __init__ captures the global
    handler.service = mock_service

    update = make_update(text="/transmission")
    context = make_context()

    await handler.transmission_command(update, context)

    update.message.reply_text.assert_called_once()
    call_args = update.message.reply_text.call_args
    assert "not enabled" in str(call_args).lower()


# ---------------------------------------------------------------------------
# transmission_command - enabled but not connected
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("src.bot.handlers.transmission.transmission_service")
async def test_transmission_not_connected(
    mock_service, make_update, make_context
):
    """When transmission is enabled but not connected, show error."""
    mock_service.is_enabled = MagicMock(return_value=True)
    mock_service.get_status = MagicMock(return_value={
        "connected": False,
        "error": "Connection refused"
    })

    from src.bot.handlers.transmission import TransmissionHandler

    handler = TransmissionHandler()
    handler.service = mock_service

    update = make_update(text="/transmission")
    context = make_context()

    await handler.transmission_command(update, context)

    update.message.reply_text.assert_called_once()
    call_args = update.message.reply_text.call_args
    assert "Cannot connect" in str(call_args) or "connect" in str(call_args).lower()


# ---------------------------------------------------------------------------
# transmission_command - enabled and connected
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("src.bot.handlers.transmission.get_yes_no_keyboard")
@patch("src.bot.handlers.transmission.transmission_service")
async def test_transmission_connected(
    mock_service, mock_keyboard, make_update, make_context
):
    """When transmission is enabled and connected, show status with toggle keyboard."""
    mock_service.is_enabled = MagicMock(return_value=True)
    mock_service.get_status = MagicMock(return_value={
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
    call_args = update.message.reply_text.call_args
    msg_text = call_args[0][0] if call_args[0] else str(call_args)
    assert "Transmission" in msg_text or "Status" in msg_text


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

"""
Tests for src/bot/handlers/status.py - StatusHandler.

StatusHandler has a simple __init__ that sets self.command = "status".
_handle_status reads bot_instance from context.application for health checks.
"""

import pytest
from unittest.mock import MagicMock


# ---------------------------------------------------------------------------
# _handle_status - direct command
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_status_command(make_update, make_context):
    """_handle_status replies with system status via direct command."""
    from src.bot.handlers.status import StatusHandler

    handler = StatusHandler()

    update = make_update(text="/status")
    context = make_context()

    # Mock the bot_instance and health_checker on context.application
    mock_health = MagicMock()
    mock_health.get_status.return_value = {
        "running": True,
        "check_interval": 5,
        "last_check": None,
        "unhealthy_services": []
    }
    mock_bot_instance = MagicMock()
    mock_bot_instance.health_checker = mock_health
    context.application = MagicMock()
    context.application.bot_instance = mock_bot_instance

    await handler._handle_status(update, context)

    update.message.reply_text.assert_called_once()
    call_args = update.message.reply_text.call_args
    status_text = call_args[0][0] if call_args[0] else str(call_args)
    assert "Status" in status_text or "healthy" in status_text.lower()


# ---------------------------------------------------------------------------
# _handle_status - callback query
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_status_callback(make_update, make_context):
    """_handle_status edits message when invoked via callback query."""
    from src.bot.handlers.status import StatusHandler

    handler = StatusHandler()

    update = make_update(callback_data="system_status")
    context = make_context()

    mock_health = MagicMock()
    mock_health.get_status.return_value = {
        "running": True,
        "check_interval": 5,
        "last_check": None,
        "unhealthy_services": []
    }
    mock_bot_instance = MagicMock()
    mock_bot_instance.health_checker = mock_health
    context.application = MagicMock()
    context.application.bot_instance = mock_bot_instance

    await handler._handle_status(update, context)

    update.callback_query.message.edit_text.assert_called_once()


# ---------------------------------------------------------------------------
# _handle_status - error
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_status_error(make_update, make_context):
    """_handle_status replies with error message when exception occurs."""
    from src.bot.handlers.status import StatusHandler

    handler = StatusHandler()

    update = make_update(text="/status")
    context = make_context()

    # Make application.bot_instance raise an exception
    context.application = MagicMock()
    context.application.bot_instance = MagicMock(
        health_checker=MagicMock(
            get_status=MagicMock(side_effect=Exception("Health check failed"))
        )
    )

    await handler._handle_status(update, context)

    update.message.reply_text.assert_called_once()
    call_args = update.message.reply_text.call_args
    error_text = call_args[0][0] if call_args[0] else str(call_args)
    assert "Error" in error_text or "error" in error_text.lower()


# ---------------------------------------------------------------------------
# get_handler
# ---------------------------------------------------------------------------


def test_get_handler_returns_list():
    """get_handler returns a list of CommandHandler instances."""
    from src.bot.handlers.status import StatusHandler

    handler = StatusHandler()
    handlers = handler.get_handler()

    assert isinstance(handlers, list)
    assert len(handlers) > 0

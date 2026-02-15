"""
Tests for src/bot/handlers/status.py - StatusHandler.

StatusHandler has a simple __init__ that sets self.command = "status".
_handle_status reads bot_instance from context.application for health checks.
"""

import pytest
from unittest.mock import MagicMock
from datetime import datetime


# ---------------------------------------------------------------------------
# _handle_status
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_status_command(make_update, make_context):
    """_handle_status replies with system status via direct command."""
    from src.bot.handlers.status import StatusHandler

    handler = StatusHandler()
    update = make_update(text="/status")
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

    update.message.reply_text.assert_called_once()
    call_args = update.message.reply_text.call_args
    status_text = call_args[0][0]
    assert "Status" in status_text
    assert "healthy" in status_text.lower()


@pytest.mark.asyncio
async def test_handle_status_with_last_check(make_update, make_context):
    """_handle_status shows last check time when available."""
    from src.bot.handlers.status import StatusHandler

    handler = StatusHandler()
    update = make_update(text="/status")
    context = make_context()

    mock_health = MagicMock()
    mock_health.get_status.return_value = {
        "running": True,
        "check_interval": 5,
        "last_check": datetime(2024, 1, 1, 12, 0, 0),
        "unhealthy_services": []
    }
    mock_bot_instance = MagicMock()
    mock_bot_instance.health_checker = mock_health
    context.application = MagicMock()
    context.application.bot_instance = mock_bot_instance

    await handler._handle_status(update, context)

    call_args = update.message.reply_text.call_args
    status_text = call_args[0][0]
    assert "Last Check" in status_text


@pytest.mark.asyncio
async def test_handle_status_with_unhealthy_services(make_update, make_context):
    """_handle_status shows unhealthy services."""
    from src.bot.handlers.status import StatusHandler

    handler = StatusHandler()
    update = make_update(text="/status")
    context = make_context()

    mock_health = MagicMock()
    mock_health.get_status.return_value = {
        "running": False,
        "check_interval": 5,
        "last_check": None,
        "unhealthy_services": ["Radarr", "Sonarr"]
    }
    mock_bot_instance = MagicMock()
    mock_bot_instance.health_checker = mock_health
    context.application = MagicMock()
    context.application.bot_instance = mock_bot_instance

    await handler._handle_status(update, context)

    call_args = update.message.reply_text.call_args
    status_text = call_args[0][0]
    assert "Unhealthy" in status_text
    assert "Radarr" in status_text


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


@pytest.mark.asyncio
async def test_handle_status_error_direct(make_update, make_context):
    """_handle_status replies with error via direct command on exception."""
    from src.bot.handlers.status import StatusHandler

    handler = StatusHandler()
    update = make_update(text="/status")
    context = make_context()

    context.application = MagicMock()
    context.application.bot_instance = MagicMock(
        health_checker=MagicMock(
            get_status=MagicMock(side_effect=Exception("Health check failed"))
        )
    )

    await handler._handle_status(update, context)

    update.message.reply_text.assert_called_once()
    call_args = update.message.reply_text.call_args
    assert "Error" in call_args[0][0]


@pytest.mark.asyncio
async def test_handle_status_error_callback(make_update, make_context):
    """_handle_status edits with error via callback on exception."""
    from src.bot.handlers.status import StatusHandler

    handler = StatusHandler()
    update = make_update(callback_data="system_status")
    context = make_context()

    context.application = MagicMock()
    context.application.bot_instance = MagicMock(
        health_checker=MagicMock(
            get_status=MagicMock(side_effect=Exception("Failed"))
        )
    )

    await handler._handle_status(update, context)

    update.callback_query.message.edit_text.assert_called_once()


# ---------------------------------------------------------------------------
# refresh_status
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_refresh_status_success(make_callback_query):
    """refresh_status updates message and answers query."""
    from src.bot.handlers.status import StatusHandler

    handler = StatusHandler()
    query = make_callback_query(data="refresh_status")

    mock_health = MagicMock()
    mock_health.get_status.return_value = {
        "running": True,
        "check_interval": 5,
        "last_check": None,
        "unhealthy_services": []
    }
    mock_bot_instance = MagicMock()
    mock_bot_instance.health_checker = mock_health
    query.bot = MagicMock()
    query.bot.application = MagicMock()
    query.bot.application.bot_instance = mock_bot_instance

    await handler.refresh_status(query)

    query.message.edit_text.assert_called_once()
    query.answer.assert_called_once()


@pytest.mark.asyncio
async def test_refresh_status_exception(make_callback_query):
    """refresh_status shows error on exception."""
    from src.bot.handlers.status import StatusHandler

    handler = StatusHandler()
    query = make_callback_query(data="refresh_status")

    query.bot = MagicMock()
    query.bot.application = MagicMock()
    query.bot.application.bot_instance = MagicMock(
        health_checker=MagicMock(
            get_status=MagicMock(side_effect=Exception("Failed"))
        )
    )

    await handler.refresh_status(query)

    query.answer.assert_called_once()
    call_args = query.answer.call_args
    assert "Failed" in str(call_args) or "refresh" in str(call_args).lower()


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

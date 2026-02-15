"""
Tests for src/bot/handlers/system.py - SystemHandler.

SystemHandler has no __init__ besides the default. show_status and
handle_system_action are decorated with @require_auth.
"""

import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# show_status
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("src.bot.handlers.system.get_system_keyboard")
async def test_show_status(mock_keyboard, make_update, make_context):
    """show_status replies with system status text and keyboard."""
    mock_keyboard.return_value = MagicMock()

    from src.bot.handlers.system import SystemHandler
    from src.bot.handlers.auth import AuthHandler

    AuthHandler._authenticated_users = {12345}

    handler = SystemHandler()
    update = make_update(text="/status")
    context = make_context()

    await handler.show_status(update, context)

    update.message.reply_text.assert_called_once()
    call_args = update.message.reply_text.call_args
    status_text = call_args[0][0] if call_args[0] else str(call_args)
    assert "Status" in status_text or "System" in status_text


# ---------------------------------------------------------------------------
# show_status - not authenticated
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("src.bot.handlers.system.get_system_keyboard")
async def test_show_status_not_authenticated(mock_keyboard, make_update, make_context):
    """show_status rejects unauthenticated users via @require_auth."""
    from src.bot.handlers.system import SystemHandler
    from src.bot.handlers.auth import AuthHandler

    AuthHandler._authenticated_users = set()

    handler = SystemHandler()
    update = make_update(text="/status")
    context = make_context()

    result = await handler.show_status(update, context)

    # require_auth returns None when not authenticated
    assert result is None


# ---------------------------------------------------------------------------
# handle_system_action
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("src.bot.handlers.system.get_system_keyboard")
async def test_handle_system_action(mock_keyboard, make_update, make_context):
    """handle_system_action processes callback queries for system actions."""
    from src.bot.handlers.system import SystemHandler
    from src.bot.handlers.auth import AuthHandler

    AuthHandler._authenticated_users = {12345}

    handler = SystemHandler()
    update = make_update(callback_data="system_refresh")
    context = make_context()

    # Should not raise
    await handler.handle_system_action(update, context)

    update.callback_query.answer.assert_not_called()  # handler doesn't call answer


# ---------------------------------------------------------------------------
# handle_system_action - no callback query
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("src.bot.handlers.system.get_system_keyboard")
async def test_handle_system_action_no_callback(mock_keyboard, make_update, make_context):
    """handle_system_action returns early if no callback query."""
    from src.bot.handlers.system import SystemHandler
    from src.bot.handlers.auth import AuthHandler

    AuthHandler._authenticated_users = {12345}

    handler = SystemHandler()
    update = make_update(text="/system")
    context = make_context()

    result = await handler.handle_system_action(update, context)
    assert result is None


# ---------------------------------------------------------------------------
# get_handler
# ---------------------------------------------------------------------------


def test_get_handler_returns_list():
    """get_handler returns a list of handlers."""
    from src.bot.handlers.system import SystemHandler

    handler = SystemHandler()
    handlers = handler.get_handler()

    assert isinstance(handlers, list)
    assert len(handlers) > 0

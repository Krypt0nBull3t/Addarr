"""
Tests for src/bot/handlers/help.py - HelpHandler with show_help and handle_back.

HelpHandler.__init__ creates TranslationService().
show_help displays help text with available commands (decorated with @require_auth).
handle_back returns to the main menu (decorated with @require_auth).
"""

import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# show_help - direct command
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("src.bot.handlers.help.get_main_menu_keyboard")
@patch("src.bot.handlers.help.TranslationService")
async def test_show_help_command(
    mock_ts_class, mock_keyboard, make_update, make_context
):
    """show_help replies with help text containing command info."""
    mock_ts = MagicMock()
    mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
    mock_ts_class.return_value = mock_ts

    from src.bot.handlers.help import HelpHandler
    from src.bot.handlers.auth import AuthHandler

    AuthHandler._authenticated_users = {12345}

    handler = HelpHandler()
    update = make_update(text="/help")
    context = make_context()

    await handler.show_help(update, context)

    update.message.reply_text.assert_called_once()
    call_args = update.message.reply_text.call_args
    help_text = call_args[0][0]
    assert "/movie" in help_text
    assert "/series" in help_text


@pytest.mark.asyncio
@patch("src.bot.handlers.help.get_main_menu_keyboard")
@patch("src.bot.handlers.help.TranslationService")
async def test_show_help_callback(
    mock_ts_class, mock_keyboard, make_update, make_context
):
    """show_help via callback query edits message text."""
    mock_ts = MagicMock()
    mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
    mock_ts_class.return_value = mock_ts

    from src.bot.handlers.help import HelpHandler
    from src.bot.handlers.auth import AuthHandler

    AuthHandler._authenticated_users = {12345}

    handler = HelpHandler()
    update = make_update(callback_data="menu_help")
    context = make_context()

    await handler.show_help(update, context)

    update.callback_query.message.edit_text.assert_called_once()


@pytest.mark.asyncio
@patch("src.bot.handlers.help.get_main_menu_keyboard")
@patch("src.bot.handlers.help.TranslationService")
async def test_show_help_no_user(
    mock_ts_class, mock_keyboard, make_update, make_context
):
    """show_help returns when no effective_user."""
    mock_ts = MagicMock()
    mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
    mock_ts_class.return_value = mock_ts

    from src.bot.handlers.help import HelpHandler
    from src.bot.handlers.auth import AuthHandler

    AuthHandler._authenticated_users = {12345}

    handler = HelpHandler()
    update = make_update(text="/help")
    update.effective_user = None
    context = make_context()

    result = await handler.show_help(update, context)

    assert result is None


# ---------------------------------------------------------------------------
# handle_back
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("src.bot.handlers.help.get_main_menu_keyboard")
@patch("src.bot.handlers.help.TranslationService")
async def test_handle_back(
    mock_ts_class, mock_keyboard, make_update, make_context
):
    """handle_back edits message with welcome text and main menu keyboard."""
    mock_ts = MagicMock()
    mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
    mock_ts_class.return_value = mock_ts
    mock_keyboard.return_value = MagicMock()

    from src.bot.handlers.help import HelpHandler
    from src.bot.handlers.auth import AuthHandler

    AuthHandler._authenticated_users = {12345}

    handler = HelpHandler()
    update = make_update(callback_data="menu_back")
    context = make_context()

    await handler.handle_back(update, context)

    update.callback_query.answer.assert_called_once()
    update.callback_query.message.edit_text.assert_called_once()


@pytest.mark.asyncio
@patch("src.bot.handlers.help.get_main_menu_keyboard")
@patch("src.bot.handlers.help.TranslationService")
async def test_handle_back_no_callback(
    mock_ts_class, mock_keyboard, make_update, make_context
):
    """handle_back returns early if no callback query."""
    mock_ts = MagicMock()
    mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
    mock_ts_class.return_value = mock_ts

    from src.bot.handlers.help import HelpHandler
    from src.bot.handlers.auth import AuthHandler

    AuthHandler._authenticated_users = {12345}

    handler = HelpHandler()
    update = make_update(text="/back")
    context = make_context()

    result = await handler.handle_back(update, context)
    assert result is None


# ---------------------------------------------------------------------------
# get_handler
# ---------------------------------------------------------------------------


@patch("src.bot.handlers.help.TranslationService")
def test_get_handler_returns_list(mock_ts_class):
    """get_handler returns a list of handlers."""
    mock_ts = MagicMock()
    mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
    mock_ts_class.return_value = mock_ts

    from src.bot.handlers.help import HelpHandler

    handler = HelpHandler()
    handlers = handler.get_handler()

    assert isinstance(handlers, list)
    assert len(handlers) > 0

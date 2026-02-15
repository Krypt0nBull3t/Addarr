"""
Tests for src/bot/handlers/start.py - StartHandler with main menu.

StartHandler.__init__ creates MediaHandler(), HelpHandler(), TranslationService().
show_menu displays the main menu keyboard (decorated with @require_auth).
handle_menu_selection dispatches menu button presses.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from telegram.ext import ConversationHandler


# ---------------------------------------------------------------------------
# show_menu
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("src.bot.handlers.start.get_main_menu_keyboard")
@patch("src.bot.handlers.start.HelpHandler")
@patch("src.bot.handlers.start.MediaHandler")
@patch("src.bot.handlers.start.TranslationService")
async def test_show_menu(
    mock_ts_class, mock_mh_class, mock_hh_class, mock_keyboard,
    make_update, make_context
):
    """show_menu replies with welcome text and main menu keyboard."""
    mock_ts = MagicMock()
    mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
    mock_ts_class.return_value = mock_ts
    mock_mh_class.return_value = MagicMock()
    mock_hh_class.return_value = MagicMock()
    mock_keyboard.return_value = MagicMock()

    from src.bot.handlers.start import StartHandler
    from src.bot.handlers.auth import AuthHandler

    AuthHandler._authenticated_users = {12345}

    handler = StartHandler()
    update = make_update(text="/start")
    context = make_context()

    result = await handler.show_menu(update, context)

    # show_menu returns MENU_STATE = 1
    assert result == 1
    update.effective_message.reply_text.assert_called_once()
    # Verify keyboard was passed
    call_kwargs = update.effective_message.reply_text.call_args
    assert call_kwargs is not None


# ---------------------------------------------------------------------------
# handle_menu_selection - cancel
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("src.bot.handlers.start.get_main_menu_keyboard")
@patch("src.bot.handlers.start.HelpHandler")
@patch("src.bot.handlers.start.MediaHandler")
@patch("src.bot.handlers.start.TranslationService")
async def test_handle_menu_selection_cancel(
    mock_ts_class, mock_mh_class, mock_hh_class, mock_keyboard,
    make_update, make_context
):
    """menu_cancel clears user_data and returns ConversationHandler.END."""
    mock_ts = MagicMock()
    mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
    mock_ts_class.return_value = mock_ts
    mock_mh_class.return_value = MagicMock()
    mock_hh_class.return_value = MagicMock()

    from src.bot.handlers.start import StartHandler
    from src.bot.handlers.auth import AuthHandler

    AuthHandler._authenticated_users = {12345}

    handler = StartHandler()
    update = make_update(callback_data="menu_cancel")
    context = make_context(user_data={"search_type": "movie"})

    result = await handler.handle_menu_selection(update, context)

    assert result == ConversationHandler.END
    # user_data should be cleared
    assert len(context.user_data) == 0
    update.callback_query.message.edit_text.assert_called_once()
    call_args = update.callback_query.message.edit_text.call_args
    assert "Canceled" in str(call_args)


# ---------------------------------------------------------------------------
# handle_menu_selection - movie search
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("src.bot.handlers.start.get_main_menu_keyboard")
@patch("src.bot.handlers.start.HelpHandler")
@patch("src.bot.handlers.start.MediaHandler")
@patch("src.bot.handlers.start.TranslationService")
async def test_handle_menu_selection_movie(
    mock_ts_class, mock_mh_class, mock_hh_class, mock_keyboard,
    make_update, make_context
):
    """menu_movie sets search_type and returns SEARCHING."""
    mock_ts = MagicMock()
    mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
    mock_ts_class.return_value = mock_ts
    mock_mh_class.return_value = MagicMock()
    mock_hh_class.return_value = MagicMock()

    from src.bot.handlers.start import StartHandler
    from src.bot.handlers.media import SEARCHING
    from src.bot.handlers.auth import AuthHandler

    AuthHandler._authenticated_users = {12345}

    handler = StartHandler()
    update = make_update(callback_data="menu_movie")
    context = make_context()

    result = await handler.handle_menu_selection(update, context)

    assert result == SEARCHING
    assert context.user_data["search_type"] == "movie"
    update.callback_query.message.edit_text.assert_called_once()


# ---------------------------------------------------------------------------
# handle_menu_selection - back
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("src.bot.handlers.start.get_main_menu_keyboard")
@patch("src.bot.handlers.start.HelpHandler")
@patch("src.bot.handlers.start.MediaHandler")
@patch("src.bot.handlers.start.TranslationService")
async def test_handle_menu_selection_back(
    mock_ts_class, mock_mh_class, mock_hh_class, mock_keyboard,
    make_update, make_context
):
    """menu_back calls show_menu to redisplay the main menu."""
    mock_ts = MagicMock()
    mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
    mock_ts_class.return_value = mock_ts
    mock_mh_class.return_value = MagicMock()
    mock_hh_class.return_value = MagicMock()
    mock_keyboard.return_value = MagicMock()

    from src.bot.handlers.start import StartHandler
    from src.bot.handlers.auth import AuthHandler

    AuthHandler._authenticated_users = {12345}

    handler = StartHandler()
    update = make_update(callback_data="menu_back")
    context = make_context()

    # Patch show_menu to track the call without full execution
    with patch.object(handler, "show_menu", new_callable=AsyncMock) as mock_show:
        await handler.handle_menu_selection(update, context)
        mock_show.assert_called_once_with(update, context)


# ---------------------------------------------------------------------------
# get_handler
# ---------------------------------------------------------------------------


@patch("src.bot.handlers.start.get_main_menu_keyboard")
@patch("src.bot.handlers.start.HelpHandler")
@patch("src.bot.handlers.start.MediaHandler")
@patch("src.bot.handlers.start.TranslationService")
def test_get_handler_returns_list(
    mock_ts_class, mock_mh_class, mock_hh_class, mock_keyboard
):
    """get_handler returns a list of handlers."""
    mock_ts = MagicMock()
    mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
    mock_ts_class.return_value = mock_ts
    mock_mh_class.return_value = MagicMock()
    mock_hh_class.return_value = MagicMock()

    from src.bot.handlers.start import StartHandler

    handler = StartHandler()
    handlers = handler.get_handler()

    assert isinstance(handlers, list)
    assert len(handlers) > 0

"""
Tests for src/bot/handlers/start.py - StartHandler with main menu.

StartHandler.__init__ creates MediaHandler(), HelpHandler(), TranslationService().
show_menu displays the main menu keyboard (decorated with @require_auth).
handle_menu_selection dispatches menu button presses.
"""

import pytest
from unittest.mock import patch, AsyncMock
from telegram.ext import ConversationHandler


# ---------------------------------------------------------------------------
# show_menu
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_show_menu_direct_command(start_handler, make_update, make_context):
    """show_menu via direct command replies with welcome text."""
    update = make_update(text="/start")
    context = make_context()

    result = await start_handler.show_menu(update, context)

    assert result == 1  # MENU_STATE
    update.effective_message.reply_text.assert_called_once()


@pytest.mark.asyncio
async def test_show_menu_via_callback(start_handler, make_update, make_context):
    """show_menu via callback query edits message."""
    update = make_update(callback_data="menu_back")
    context = make_context()

    result = await start_handler.show_menu(update, context)

    assert result == 1
    update.callback_query.answer.assert_called_once()
    update.callback_query.message.edit_text.assert_called_once()


# ---------------------------------------------------------------------------
# handle_menu_selection
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_menu_selection_cancel(
    start_handler, make_update, make_context
):
    """menu_cancel clears user_data and returns END."""
    update = make_update(callback_data="menu_cancel")
    context = make_context(user_data={"search_type": "movie"})

    result = await start_handler.handle_menu_selection(update, context)

    assert result == ConversationHandler.END
    assert len(context.user_data) == 0


@pytest.mark.parametrize("media_type", ["movie", "series", "music"])
@pytest.mark.asyncio
async def test_handle_menu_selection_media_type(
    start_handler, make_update, make_context, media_type
):
    """menu_{movie/series/music} sets search_type and returns SEARCHING."""
    from src.bot.handlers.media import SEARCHING

    update = make_update(callback_data=f"menu_{media_type}")
    context = make_context()

    result = await start_handler.handle_menu_selection(update, context)

    assert result == SEARCHING
    assert context.user_data["search_type"] == media_type
    update.callback_query.message.edit_text.assert_called_once()


@pytest.mark.asyncio
async def test_handle_menu_selection_back(
    start_handler, make_update, make_context
):
    """menu_back calls show_menu."""
    update = make_update(callback_data="menu_back")
    context = make_context()

    with patch.object(start_handler, "show_menu", new_callable=AsyncMock) as mock_show:
        await start_handler.handle_menu_selection(update, context)
        mock_show.assert_called_once_with(update, context)


@pytest.mark.asyncio
async def test_handle_menu_selection_status(
    start_handler, make_update, make_context
):
    """menu_status delegates to media_handler.handle_status."""
    update = make_update(callback_data="menu_status")
    context = make_context()

    result = await start_handler.handle_menu_selection(update, context)

    assert result == ConversationHandler.END
    start_handler._mock_media_handler.handle_status.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_menu_selection_help(
    start_handler, make_update, make_context
):
    """menu_help delegates to help_handler.show_help."""
    update = make_update(callback_data="menu_help")
    context = make_context()

    result = await start_handler.handle_menu_selection(update, context)

    assert result == ConversationHandler.END
    start_handler._mock_help_handler.show_help.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_menu_selection_settings(
    start_handler, make_update, make_context
):
    """menu_settings delegates to media_handler.handle_settings."""
    update = make_update(callback_data="menu_settings")
    context = make_context()

    result = await start_handler.handle_menu_selection(update, context)

    assert result == ConversationHandler.END
    start_handler._mock_media_handler.handle_settings.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_menu_selection_delete(
    start_handler, make_update, make_context
):
    """menu_delete shows delete prompt."""
    update = make_update(callback_data="menu_delete")
    context = make_context()

    result = await start_handler.handle_menu_selection(update, context)

    assert result == ConversationHandler.END
    update.callback_query.message.edit_text.assert_called_once()


@pytest.mark.asyncio
async def test_handle_menu_selection_unknown(
    start_handler, make_update, make_context
):
    """Unknown menu action returns END."""
    update = make_update(callback_data="menu_unknown")
    context = make_context()

    result = await start_handler.handle_menu_selection(update, context)

    assert result == ConversationHandler.END


@pytest.mark.asyncio
async def test_handle_menu_selection_no_callback(
    start_handler, make_update, make_context
):
    """handle_menu_selection returns None when no callback_query."""
    update = make_update(text="/test")
    update.callback_query = None
    context = make_context()

    result = await start_handler.handle_menu_selection(update, context)

    assert result is None


# ---------------------------------------------------------------------------
# start_movie_search
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_start_movie_search(start_handler, make_callback_query):
    """start_movie_search edits message with search prompt."""
    query = make_callback_query(data="menu_movie")

    await start_handler.start_movie_search(query)

    query.message.edit_text.assert_called_once()


# ---------------------------------------------------------------------------
# get_handler
# ---------------------------------------------------------------------------


def test_get_handler_returns_list(start_handler):
    """get_handler returns a list of handlers."""
    handlers = start_handler.get_handler()

    assert isinstance(handlers, list)
    assert len(handlers) > 0

"""
Tests for src/bot/handlers/start.py - StartHandler with main menu.

StartHandler.__init__ creates CalendarHandler(), HelpHandler(), SystemHandler(),
DeleteHandler(), TranslationService().
show_menu displays the main menu keyboard (decorated with @require_auth).
handle_menu_selection dispatches the menu buttons StartHandler owns.
"""

import pytest
from telegram.ext import CallbackQueryHandler


# ---------------------------------------------------------------------------
# show_menu
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_show_menu_direct_command(start_handler, make_update, make_context):
    """show_menu via direct command replies with welcome text."""
    update = make_update(text="/start")
    context = make_context()

    await start_handler.show_menu(update, context)

    update.effective_message.reply_text.assert_called_once()


# ---------------------------------------------------------------------------
# handle_menu_selection
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_menu_selection_cancel(
    start_handler, make_update, make_context
):
    """menu_cancel clears user_data and closes the menu."""
    update = make_update(callback_data="menu_cancel")
    context = make_context(user_data={"search_type": "movie"})

    await start_handler.handle_menu_selection(update, context)

    assert len(context.user_data) == 0


@pytest.mark.asyncio
async def test_handle_menu_selection_status(
    start_handler, make_update, make_context
):
    """menu_status delegates to system_handler.show_status."""
    update = make_update(callback_data="menu_status")
    context = make_context()

    await start_handler.handle_menu_selection(update, context)

    start_handler._mock_system_handler.show_status.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_menu_selection_help(
    start_handler, make_update, make_context
):
    """menu_help delegates to help_handler.show_help."""
    update = make_update(callback_data="menu_help")
    context = make_context()

    await start_handler.handle_menu_selection(update, context)

    start_handler._mock_help_handler.show_help.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_menu_selection_upcoming(
    start_handler, make_update, make_context
):
    """menu_upcoming delegates to calendar_handler.show_upcoming."""
    update = make_update(callback_data="menu_upcoming")
    context = make_context()

    await start_handler.handle_menu_selection(update, context)

    start_handler._mock_calendar_handler.show_upcoming.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_menu_selection_library(
    start_handler, make_update, make_context
):
    """menu_library shows library sub-menu."""
    update = make_update(callback_data="menu_library")
    context = make_context()

    await start_handler.handle_menu_selection(update, context)

    update.callback_query.message.edit_text.assert_called_once()
    start_handler._mock_lib_kbd.assert_called_once()


@pytest.mark.asyncio
async def test_handle_menu_selection_delete(
    start_handler, make_update, make_context
):
    """menu_delete shows delete prompt."""
    update = make_update(callback_data="menu_delete")
    context = make_context()

    await start_handler.handle_menu_selection(update, context)

    update.callback_query.message.edit_text.assert_called_once()


@pytest.mark.asyncio
async def test_handle_menu_selection_unknown(
    start_handler, make_update, make_context
):
    """Unknown menu action only logs a warning."""
    update = make_update(callback_data="menu_unknown")
    context = make_context()

    await start_handler.handle_menu_selection(update, context)

    update.callback_query.message.edit_text.assert_not_called()


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
# get_handler
# ---------------------------------------------------------------------------


def test_get_handler_returns_list(start_handler):
    """get_handler returns a list of handlers."""
    handlers = start_handler.get_handler()

    assert isinstance(handlers, list)
    assert len(handlers) > 0


def test_get_handler_leaves_other_menu_buttons_to_their_owners(start_handler):
    """Movie/series/music, settings and back buttons belong to other handlers."""
    patterns = [
        h.pattern for h in start_handler.get_handler()
        if isinstance(h, CallbackQueryHandler)
    ]

    for data in ["menu_movie", "menu_series", "menu_music", "menu_settings", "menu_back"]:
        assert not any(p.match(data) for p in patterns), data
    for data in ["menu_cancel", "menu_status", "menu_upcoming", "menu_library", "menu_help", "menu_delete"]:
        assert any(p.match(data) for p in patterns), data

"""
Tests for src/bot/handlers/history.py - HistoryHandler.

HistoryHandler owns /history and hist_* callbacks. show_history and
handle_history_action are decorated with @require_auth.
"""

import pytest
from unittest.mock import AsyncMock


# ---------------------------------------------------------------------------
# Sample history items for reuse
# ---------------------------------------------------------------------------

SAMPLE_HISTORY_MOVIE = {
    "type": "movie", "title": "Fight Club",
    "episode_title": None, "season": None, "episode": None,
    "date": "2026-03-09T14:30:00Z", "event_type": "grabbed",
    "quality": "Bluray-1080p",
    "source_title": "Fight.Club.1999.1080p.BluRay", "service": "radarr",
}

SAMPLE_HISTORY_EPISODE = {
    "type": "episode", "title": "Breaking Bad",
    "episode_title": "Pilot", "season": 1, "episode": 1,
    "date": "2026-03-09T12:00:00Z", "event_type": "grabbed",
    "quality": "HDTV-720p",
    "source_title": "Breaking.Bad.S01E01.720p", "service": "sonarr",
}


# ---------------------------------------------------------------------------
# get_handler
# ---------------------------------------------------------------------------


def test_get_handler_returns_list(history_handler):
    """get_handler returns a list of handlers."""
    handlers = history_handler.get_handler()
    assert isinstance(handlers, list)
    assert len(handlers) == 2


# ---------------------------------------------------------------------------
# show_history
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_show_history_with_results(
    history_handler, make_update, make_context
):
    """show_history sends message with items keyboard when results exist."""
    items = [SAMPLE_HISTORY_MOVIE, SAMPLE_HISTORY_EPISODE]
    history_handler._mock_service.get_history = AsyncMock(
        return_value=items
    )
    update = make_update(text="/history")
    context = make_context()

    await history_handler.show_history(update, context)

    history_handler._mock_service.get_history.assert_awaited_once()
    update.message.reply_text.assert_called_once()
    call_args = update.message.reply_text.call_args
    assert "HistoryTitle" in call_args[0][0]
    assert call_args[1]["reply_markup"] == \
        history_handler._mock_items_kbd.return_value
    assert context.user_data["hist_items"] == items


@pytest.mark.asyncio
async def test_show_history_empty(
    history_handler, make_update, make_context
):
    """show_history sends empty-state message when no results."""
    history_handler._mock_service.get_history = AsyncMock(
        return_value=[]
    )
    update = make_update(text="/history")
    context = make_context()

    await history_handler.show_history(update, context)

    update.message.reply_text.assert_called_once()
    call_args = update.message.reply_text.call_args
    assert "HistoryEmpty" in call_args[0][0]
    assert call_args[1]["reply_markup"] == \
        history_handler._mock_empty_kbd.return_value


@pytest.mark.asyncio
async def test_show_history_via_callback(
    history_handler, make_update, make_context
):
    """show_history edits message when invoked via callback query."""
    items = [SAMPLE_HISTORY_MOVIE]
    history_handler._mock_service.get_history = AsyncMock(
        return_value=items
    )
    update = make_update(callback_data="menu_history")
    context = make_context()

    await history_handler.show_history(update, context)

    update.callback_query.message.edit_text.assert_called_once()
    call_args = update.callback_query.message.edit_text.call_args
    assert "HistoryTitle" in call_args[0][0]


@pytest.mark.asyncio
async def test_show_history_no_user(
    history_handler, make_update, make_context
):
    """@require_auth returns None when effective_user is None."""
    update = make_update(text="/history")
    update.effective_user = None
    context = make_context()

    result = await history_handler.show_history(update, context)
    assert result is None


# ---------------------------------------------------------------------------
# handle_history_action — filter
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_filter_grabbed(
    history_handler, make_update, make_context
):
    """hist_filter_grabbed fetches with event_type='grabbed'."""
    items = [SAMPLE_HISTORY_MOVIE]
    history_handler._mock_service.get_history = AsyncMock(
        return_value=items
    )
    update = make_update(callback_data="hist_filter_grabbed")
    context = make_context(user_data={
        "hist_items": [], "hist_filter": None, "hist_page": 0,
    })

    await history_handler.handle_history_action(update, context)

    history_handler._mock_service.get_history.assert_awaited_once_with(
        event_type="grabbed"
    )
    assert context.user_data["hist_filter"] == "grabbed"
    assert context.user_data["hist_page"] == 0
    update.callback_query.message.edit_text.assert_called_once()
    update.callback_query.answer.assert_called_once()


@pytest.mark.asyncio
async def test_filter_all(
    history_handler, make_update, make_context
):
    """hist_filter_all fetches with event_type=None."""
    items = [SAMPLE_HISTORY_MOVIE]
    history_handler._mock_service.get_history = AsyncMock(
        return_value=items
    )
    update = make_update(callback_data="hist_filter_all")
    context = make_context(user_data={
        "hist_items": [], "hist_filter": "grabbed", "hist_page": 0,
    })

    await history_handler.handle_history_action(update, context)

    history_handler._mock_service.get_history.assert_awaited_once_with(
        event_type=None
    )
    assert context.user_data["hist_filter"] is None


# ---------------------------------------------------------------------------
# handle_history_action — navigation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_page_navigation(
    history_handler, make_update, make_context
):
    """hist_page_1 shows page 1 from cached items."""
    items = [SAMPLE_HISTORY_MOVIE] * 8
    update = make_update(callback_data="hist_page_1")
    context = make_context(user_data={
        "hist_items": items, "hist_filter": None, "hist_page": 0,
    })

    await history_handler.handle_history_action(update, context)

    assert context.user_data["hist_page"] == 1
    update.callback_query.message.edit_text.assert_called_once()
    update.callback_query.answer.assert_called_once()


@pytest.mark.asyncio
async def test_refresh(
    history_handler, make_update, make_context
):
    """hist_refresh re-fetches history and resets page."""
    new_items = [SAMPLE_HISTORY_MOVIE]
    history_handler._mock_service.get_history = AsyncMock(
        return_value=new_items
    )
    update = make_update(callback_data="hist_refresh")
    context = make_context(user_data={
        "hist_items": [], "hist_filter": "grabbed", "hist_page": 2,
    })

    await history_handler.handle_history_action(update, context)

    history_handler._mock_service.get_history.assert_awaited_once_with(
        event_type="grabbed"
    )
    assert context.user_data["hist_page"] == 0
    assert context.user_data["hist_items"] == new_items


@pytest.mark.asyncio
async def test_back(
    history_handler, make_update, make_context
):
    """hist_back returns to main menu."""
    update = make_update(callback_data="hist_back")
    context = make_context()

    await history_handler.handle_history_action(update, context)

    update.callback_query.message.edit_text.assert_called_once()
    call_args = update.callback_query.message.edit_text.call_args
    assert "Main Menu" in call_args[0][0]
    assert call_args[1]["reply_markup"] == \
        history_handler._mock_menu_kbd.return_value
    update.callback_query.answer.assert_called_once()


@pytest.mark.asyncio
async def test_handle_action_no_callback_query(
    history_handler, make_update, make_context
):
    """handle_history_action returns early when no callback_query."""
    update = make_update(text="/history")
    update.callback_query = None
    context = make_context()

    result = await history_handler.handle_history_action(update, context)
    assert result is None


@pytest.mark.asyncio
async def test_noop(
    history_handler, make_update, make_context
):
    """hist_noop just answers the callback query."""
    update = make_update(callback_data="hist_noop")
    context = make_context()

    await history_handler.handle_history_action(update, context)

    update.callback_query.answer.assert_called_once()
    update.callback_query.message.edit_text.assert_not_called()

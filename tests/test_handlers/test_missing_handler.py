"""
Tests for src/bot/handlers/missing.py - MissingHandler.

MissingHandler owns /missing and missing_* callbacks. show_missing and
handle_missing_action are decorated with @require_auth.
"""

import pytest
from unittest.mock import AsyncMock


# ---------------------------------------------------------------------------
# Sample missing items for reuse
# ---------------------------------------------------------------------------

SAMPLE_MISSING_MOVIE = {
    "type": "movie", "title": "Fight Club", "series_title": None,
    "year": 1999, "season": None, "episode": None,
    "media_id": "550", "internal_id": 1, "service": "radarr",
}

SAMPLE_MISSING_EPISODE = {
    "type": "episode", "title": "Pilot", "series_title": "Breaking Bad",
    "year": 2008, "season": 1, "episode": 5,
    "media_id": "81189", "internal_id": 101, "service": "sonarr",
}

SAMPLE_CUTOFF_MOVIE = {
    "type": "movie", "title": "Inception", "series_title": None,
    "year": 2010, "season": None, "episode": None,
    "media_id": "27205", "internal_id": 3, "service": "radarr",
}


# ---------------------------------------------------------------------------
# show_missing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_show_missing_with_results(
    missing_handler, make_update, make_context
):
    """show_missing sends message with items keyboard when results exist."""
    items = [SAMPLE_MISSING_MOVIE, SAMPLE_MISSING_EPISODE]
    missing_handler._mock_service.get_missing_media = AsyncMock(
        return_value=items
    )
    update = make_update(text="/missing")
    context = make_context()

    await missing_handler.show_missing(update, context)

    missing_handler._mock_service.get_missing_media.assert_awaited_once()
    update.message.reply_text.assert_called_once()
    call_args = update.message.reply_text.call_args
    assert "MissingTitle" in call_args[0][0]
    assert call_args[1]["reply_markup"] == \
        missing_handler._mock_items_kbd.return_value
    assert context.user_data["missing_items"] == items


@pytest.mark.asyncio
async def test_show_missing_empty_results(
    missing_handler, make_update, make_context
):
    """show_missing sends empty-state message when no results."""
    missing_handler._mock_service.get_missing_media = AsyncMock(
        return_value=[]
    )
    update = make_update(text="/missing")
    context = make_context()

    await missing_handler.show_missing(update, context)

    update.message.reply_text.assert_called_once()
    call_args = update.message.reply_text.call_args
    assert "MissingEmpty" in call_args[0][0]
    assert call_args[1]["reply_markup"] == \
        missing_handler._mock_empty_kbd.return_value


@pytest.mark.asyncio
async def test_show_missing_via_callback(
    missing_handler, make_update, make_context
):
    """show_missing edits message when invoked via callback query."""
    items = [SAMPLE_MISSING_MOVIE]
    missing_handler._mock_service.get_missing_media = AsyncMock(
        return_value=items
    )
    update = make_update(callback_data="menu_missing")
    context = make_context()

    await missing_handler.show_missing(update, context)

    update.callback_query.message.edit_text.assert_called_once()
    call_args = update.callback_query.message.edit_text.call_args
    assert "MissingTitle" in call_args[0][0]


@pytest.mark.asyncio
async def test_show_missing_no_user(
    missing_handler, make_update, make_context
):
    """show_missing returns None when effective_user is None."""
    update = make_update(text="/missing")
    update.effective_user = None
    context = make_context()

    result = await missing_handler.show_missing(update, context)
    assert result is None


# ---------------------------------------------------------------------------
# handle_missing_action — filter
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_filter_movie(
    missing_handler, make_update, make_context
):
    """missing_filter_movie sets filter and rebuilds keyboard."""
    items = [SAMPLE_MISSING_MOVIE, SAMPLE_MISSING_EPISODE]
    update = make_update(callback_data="missing_filter_movie")
    context = make_context(user_data={
        "missing_items": items, "missing_filter": "all"
    })

    await missing_handler.handle_missing_action(update, context)

    assert context.user_data["missing_filter"] == "movie"
    update.callback_query.message.edit_text.assert_called_once()
    update.callback_query.answer.assert_called_once()


@pytest.mark.asyncio
async def test_filter_series(
    missing_handler, make_update, make_context
):
    """missing_filter_series sets filter to episode type."""
    items = [SAMPLE_MISSING_MOVIE, SAMPLE_MISSING_EPISODE]
    update = make_update(callback_data="missing_filter_series")
    context = make_context(user_data={
        "missing_items": items, "missing_filter": "all"
    })

    await missing_handler.handle_missing_action(update, context)

    assert context.user_data["missing_filter"] == "episode"
    update.callback_query.message.edit_text.assert_called_once()


@pytest.mark.asyncio
async def test_filter_cutoff(
    missing_handler, make_update, make_context
):
    """missing_filter_cutoff fetches cutoff-unmet and replaces items."""
    cutoff_items = [SAMPLE_CUTOFF_MOVIE]
    missing_handler._mock_service.get_cutoff_unmet_media = AsyncMock(
        return_value=cutoff_items
    )
    update = make_update(callback_data="missing_filter_cutoff")
    context = make_context(user_data={
        "missing_items": [], "missing_filter": "all"
    })

    await missing_handler.handle_missing_action(update, context)

    missing_handler._mock_service.get_cutoff_unmet_media.assert_awaited_once()
    assert context.user_data["missing_filter"] == "cutoff"
    assert context.user_data["missing_items"] == cutoff_items


@pytest.mark.asyncio
async def test_filter_all(
    missing_handler, make_update, make_context
):
    """missing_filter_all re-fetches missing media."""
    items = [SAMPLE_MISSING_MOVIE]
    missing_handler._mock_service.get_missing_media = AsyncMock(
        return_value=items
    )
    update = make_update(callback_data="missing_filter_all")
    context = make_context(user_data={
        "missing_items": [], "missing_filter": "cutoff"
    })

    await missing_handler.handle_missing_action(update, context)

    missing_handler._mock_service.get_missing_media.assert_awaited_once()
    assert context.user_data["missing_filter"] == "all"
    assert context.user_data["missing_items"] == items


# ---------------------------------------------------------------------------
# handle_missing_action — navigation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_page_change(
    missing_handler, make_update, make_context
):
    """missing_page_1 shows second page from cached items."""
    items = [
        {**SAMPLE_MISSING_MOVIE, "title": f"Movie {i}", "internal_id": i}
        for i in range(8)
    ]
    update = make_update(callback_data="missing_page_1")
    context = make_context(user_data={
        "missing_items": items, "missing_filter": "all"
    })

    await missing_handler.handle_missing_action(update, context)

    update.callback_query.message.edit_text.assert_called_once()
    update.callback_query.answer.assert_called_once()
    missing_handler._mock_items_kbd.assert_called_once()
    kbd_call = missing_handler._mock_items_kbd.call_args
    assert kbd_call[0][1] == 1  # page argument


@pytest.mark.asyncio
async def test_refresh(
    missing_handler, make_update, make_context
):
    """missing_refresh re-fetches missing media and updates display."""
    new_items = [SAMPLE_MISSING_MOVIE]
    missing_handler._mock_service.get_missing_media = AsyncMock(
        return_value=new_items
    )
    update = make_update(callback_data="missing_refresh")
    context = make_context(user_data={
        "missing_items": [], "missing_filter": "all"
    })

    await missing_handler.handle_missing_action(update, context)

    missing_handler._mock_service.get_missing_media.assert_awaited_once()
    assert context.user_data["missing_items"] == new_items


@pytest.mark.asyncio
async def test_refresh_cutoff_mode(
    missing_handler, make_update, make_context
):
    """missing_refresh in cutoff mode re-fetches cutoff-unmet data."""
    cutoff_items = [SAMPLE_CUTOFF_MOVIE]
    missing_handler._mock_service.get_cutoff_unmet_media = AsyncMock(
        return_value=cutoff_items
    )
    update = make_update(callback_data="missing_refresh")
    context = make_context(user_data={
        "missing_items": [], "missing_filter": "cutoff"
    })

    await missing_handler.handle_missing_action(update, context)

    missing_handler._mock_service.get_cutoff_unmet_media.assert_awaited_once()
    assert context.user_data["missing_items"] == cutoff_items


@pytest.mark.asyncio
async def test_back_to_menu(
    missing_handler, make_update, make_context
):
    """missing_back returns to main menu."""
    update = make_update(callback_data="missing_back")
    context = make_context(user_data={
        "missing_items": [], "missing_filter": "all"
    })

    await missing_handler.handle_missing_action(update, context)

    update.callback_query.message.edit_text.assert_called_once()
    call_args = update.callback_query.message.edit_text.call_args
    assert call_args[1]["reply_markup"] == \
        missing_handler._mock_menu_kbd.return_value
    update.callback_query.answer.assert_called_once()


@pytest.mark.asyncio
async def test_noop_callback(
    missing_handler, make_update, make_context
):
    """Unknown missing_ action just answers the query."""
    update = make_update(callback_data="missing_noop")
    context = make_context()

    await missing_handler.handle_missing_action(update, context)

    update.callback_query.answer.assert_called_once()


# ---------------------------------------------------------------------------
# handle_missing_action — search
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_success(
    missing_handler, make_update, make_context
):
    """missing_search_radarr_1 triggers search and shows success alert."""
    missing_handler._mock_service.trigger_missing_search = AsyncMock(
        return_value=True
    )
    update = make_update(callback_data="missing_search_radarr_1")
    context = make_context(user_data={
        "missing_items": [], "missing_filter": "all"
    })

    await missing_handler.handle_missing_action(update, context)

    missing_handler._mock_service.trigger_missing_search.assert_awaited_once_with(
        "radarr", 1
    )
    # Should call answer twice: first "Searching...", then result alert
    assert update.callback_query.answer.call_count == 2


@pytest.mark.asyncio
async def test_search_failure(
    missing_handler, make_update, make_context
):
    """missing_search shows failure alert when trigger returns False."""
    missing_handler._mock_service.trigger_missing_search = AsyncMock(
        return_value=False
    )
    update = make_update(callback_data="missing_search_sonarr_101")
    context = make_context(user_data={
        "missing_items": [], "missing_filter": "all"
    })

    await missing_handler.handle_missing_action(update, context)

    missing_handler._mock_service.trigger_missing_search.assert_awaited_once_with(
        "sonarr", 101
    )
    assert update.callback_query.answer.call_count == 2


# ---------------------------------------------------------------------------
# handle_missing_action — no callback query
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_no_callback(
    missing_handler, make_update, make_context
):
    """handle_missing_action returns None when no callback query."""
    update = make_update(text="/missing")
    context = make_context()

    result = await missing_handler.handle_missing_action(update, context)
    assert result is None


# ---------------------------------------------------------------------------
# get_handler
# ---------------------------------------------------------------------------


def test_get_handler_returns_list(missing_handler):
    """get_handler returns a list of handlers."""
    handlers = missing_handler.get_handler()
    assert isinstance(handlers, list)
    assert len(handlers) >= 2

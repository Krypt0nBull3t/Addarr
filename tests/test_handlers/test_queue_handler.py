"""
Tests for src/bot/handlers/queue.py - QueueHandler.

QueueHandler owns /queue and queue_* callbacks. show_queue and
handle_queue_action are decorated with @require_auth.
"""

import pytest
from unittest.mock import AsyncMock


# ---------------------------------------------------------------------------
# Sample queue items for reuse
# ---------------------------------------------------------------------------

SAMPLE_QUEUE_MOVIE = {
    "type": "movie", "title": "Fight Club", "year": 1999,
    "series_title": None, "season": None, "episode": None,
    "status": "downloading", "progress": 50,
    "timeleft": "00:15:00", "protocol": "usenet",
    "download_client": "SABnzbd",
    "media_id": "550", "internal_id": 1, "service": "radarr",
}

SAMPLE_QUEUE_EPISODE = {
    "type": "episode", "title": "Pilot", "year": 2008,
    "series_title": "Breaking Bad", "season": 1, "episode": 5,
    "status": "downloading", "progress": 80,
    "timeleft": "00:05:00", "protocol": "torrent",
    "download_client": "qBittorrent",
    "media_id": "81189", "internal_id": 101, "service": "sonarr",
}

SAMPLE_QUEUE_ALBUM = {
    "type": "album", "title": "OK Computer", "year": None,
    "series_title": None, "season": None, "episode": None,
    "status": "downloading", "progress": 50,
    "timeleft": "00:03:00", "protocol": "usenet",
    "download_client": "SABnzbd",
    "media_id": "", "internal_id": 301, "service": "lidarr",
}


# ---------------------------------------------------------------------------
# show_queue
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_show_queue_with_results(
    queue_handler, make_update, make_context
):
    """show_queue sends message with items keyboard when results exist."""
    items = [SAMPLE_QUEUE_MOVIE, SAMPLE_QUEUE_EPISODE]
    queue_handler._mock_service.get_queue_media = AsyncMock(
        return_value=items
    )
    update = make_update(text="/queue")
    context = make_context()

    await queue_handler.show_queue(update, context)

    queue_handler._mock_service.get_queue_media.assert_awaited_once()
    update.message.reply_text.assert_called_once()
    call_args = update.message.reply_text.call_args
    assert "QueueTitle" in call_args[0][0]
    assert call_args[1]["reply_markup"] == \
        queue_handler._mock_items_kbd.return_value
    assert context.user_data["queue_items"] == items


@pytest.mark.asyncio
async def test_show_queue_empty_results(
    queue_handler, make_update, make_context
):
    """show_queue sends empty-state message when no results."""
    queue_handler._mock_service.get_queue_media = AsyncMock(
        return_value=[]
    )
    update = make_update(text="/queue")
    context = make_context()

    await queue_handler.show_queue(update, context)

    update.message.reply_text.assert_called_once()
    call_args = update.message.reply_text.call_args
    assert "QueueEmpty" in call_args[0][0]
    assert call_args[1]["reply_markup"] == \
        queue_handler._mock_empty_kbd.return_value


@pytest.mark.asyncio
async def test_show_queue_via_callback(
    queue_handler, make_update, make_context
):
    """show_queue edits message when invoked via callback query."""
    items = [SAMPLE_QUEUE_MOVIE]
    queue_handler._mock_service.get_queue_media = AsyncMock(
        return_value=items
    )
    update = make_update(callback_data="menu_queue")
    context = make_context()

    await queue_handler.show_queue(update, context)

    update.callback_query.message.edit_text.assert_called_once()
    call_args = update.callback_query.message.edit_text.call_args
    assert "QueueTitle" in call_args[0][0]


@pytest.mark.asyncio
async def test_show_queue_no_user(
    queue_handler, make_update, make_context
):
    """show_queue returns None when effective_user is None."""
    update = make_update(text="/queue")
    update.effective_user = None
    context = make_context()

    result = await queue_handler.show_queue(update, context)
    assert result is None


# ---------------------------------------------------------------------------
# handle_queue_action — filter
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_filter_movie(
    queue_handler, make_update, make_context
):
    """queue_filter_movie sets filter and rebuilds keyboard."""
    items = [SAMPLE_QUEUE_MOVIE, SAMPLE_QUEUE_EPISODE]
    update = make_update(callback_data="queue_filter_movie")
    context = make_context(user_data={
        "queue_items": items, "queue_filter": "all"
    })

    await queue_handler.handle_queue_action(update, context)

    assert context.user_data["queue_filter"] == "movie"
    update.callback_query.message.edit_text.assert_called_once()
    update.callback_query.answer.assert_called_once()


@pytest.mark.asyncio
async def test_filter_episode(
    queue_handler, make_update, make_context
):
    """queue_filter_episode sets filter to episode type."""
    items = [SAMPLE_QUEUE_MOVIE, SAMPLE_QUEUE_EPISODE]
    update = make_update(callback_data="queue_filter_episode")
    context = make_context(user_data={
        "queue_items": items, "queue_filter": "all"
    })

    await queue_handler.handle_queue_action(update, context)

    assert context.user_data["queue_filter"] == "episode"
    update.callback_query.message.edit_text.assert_called_once()


@pytest.mark.asyncio
async def test_filter_album(
    queue_handler, make_update, make_context
):
    """queue_filter_album sets filter to album type."""
    items = [SAMPLE_QUEUE_MOVIE, SAMPLE_QUEUE_ALBUM]
    update = make_update(callback_data="queue_filter_album")
    context = make_context(user_data={
        "queue_items": items, "queue_filter": "all"
    })

    await queue_handler.handle_queue_action(update, context)

    assert context.user_data["queue_filter"] == "album"
    update.callback_query.message.edit_text.assert_called_once()


@pytest.mark.asyncio
async def test_filter_all(
    queue_handler, make_update, make_context
):
    """queue_filter_all re-fetches queue media."""
    items = [SAMPLE_QUEUE_MOVIE]
    queue_handler._mock_service.get_queue_media = AsyncMock(
        return_value=items
    )
    update = make_update(callback_data="queue_filter_all")
    context = make_context(user_data={
        "queue_items": [], "queue_filter": "movie"
    })

    await queue_handler.handle_queue_action(update, context)

    queue_handler._mock_service.get_queue_media.assert_awaited_once()
    assert context.user_data["queue_filter"] == "all"
    assert context.user_data["queue_items"] == items


# ---------------------------------------------------------------------------
# handle_queue_action — navigation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_page_change(
    queue_handler, make_update, make_context
):
    """queue_page_1 shows second page from cached items."""
    items = [
        {**SAMPLE_QUEUE_MOVIE, "title": f"Movie {i}", "internal_id": i}
        for i in range(8)
    ]
    update = make_update(callback_data="queue_page_1")
    context = make_context(user_data={
        "queue_items": items, "queue_filter": "all"
    })

    await queue_handler.handle_queue_action(update, context)

    update.callback_query.message.edit_text.assert_called_once()
    update.callback_query.answer.assert_called_once()
    queue_handler._mock_items_kbd.assert_called_once()
    kbd_call = queue_handler._mock_items_kbd.call_args
    assert kbd_call[0][1] == 1  # page argument


@pytest.mark.asyncio
async def test_refresh(
    queue_handler, make_update, make_context
):
    """queue_refresh re-fetches queue media and updates display."""
    new_items = [SAMPLE_QUEUE_MOVIE]
    queue_handler._mock_service.get_queue_media = AsyncMock(
        return_value=new_items
    )
    update = make_update(callback_data="queue_refresh")
    context = make_context(user_data={
        "queue_items": [], "queue_filter": "all"
    })

    await queue_handler.handle_queue_action(update, context)

    queue_handler._mock_service.get_queue_media.assert_awaited_once()
    assert context.user_data["queue_items"] == new_items


@pytest.mark.asyncio
async def test_back_to_menu(
    queue_handler, make_update, make_context
):
    """queue_back returns to main menu."""
    update = make_update(callback_data="queue_back")
    context = make_context(user_data={
        "queue_items": [], "queue_filter": "all"
    })

    await queue_handler.handle_queue_action(update, context)

    update.callback_query.message.edit_text.assert_called_once()
    call_args = update.callback_query.message.edit_text.call_args
    assert call_args[1]["reply_markup"] == \
        queue_handler._mock_menu_kbd.return_value
    update.callback_query.answer.assert_called_once()


@pytest.mark.asyncio
async def test_noop_callback(
    queue_handler, make_update, make_context
):
    """Unknown queue_ action just answers the query."""
    update = make_update(callback_data="queue_noop")
    context = make_context()

    await queue_handler.handle_queue_action(update, context)

    update.callback_query.answer.assert_called_once()


# ---------------------------------------------------------------------------
# handle_queue_action — no callback query
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_no_callback(
    queue_handler, make_update, make_context
):
    """handle_queue_action returns None when no callback query."""
    update = make_update(text="/queue")
    context = make_context()

    result = await queue_handler.handle_queue_action(update, context)
    assert result is None


# ---------------------------------------------------------------------------
# get_handler
# ---------------------------------------------------------------------------


def test_get_handler_returns_list(queue_handler):
    """get_handler returns a list of handlers."""
    handlers = queue_handler.get_handler()
    assert isinstance(handlers, list)
    assert len(handlers) >= 2

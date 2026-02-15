"""
Tests for src/bot/handlers/media.py - MediaHandler with full conversation flow.

MediaHandler.__init__ creates MediaService() and TranslationService().
handle_movie/series/music set context.user_data["search_type"] and return SEARCHING.
handle_search dispatches to the appropriate search method.
handle_selection processes callback_data like "select_0", "select_cancel".
cancel_search returns ConversationHandler.END.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from telegram.ext import ConversationHandler


# ---------------------------------------------------------------------------
# handle_movie / handle_series / handle_music
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("src.bot.handlers.media.MediaService")
@patch("src.bot.handlers.media.TranslationService")
async def test_handle_movie_sets_search_type(
    mock_ts_class, mock_ms_class, make_update, make_context
):
    """handle_movie sets user_data['search_type'] to 'movie' and returns SEARCHING."""
    mock_ts = MagicMock()
    mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
    mock_ts_class.return_value = mock_ts
    mock_ms_class.return_value = MagicMock()

    from src.bot.handlers.media import MediaHandler, SEARCHING
    from src.bot.handlers.auth import AuthHandler

    AuthHandler._authenticated_users = {12345}

    handler = MediaHandler()
    update = make_update(text="/movie")
    context = make_context()

    result = await handler.handle_movie(update, context)

    assert result == SEARCHING
    assert context.user_data["search_type"] == "movie"
    update.message.reply_text.assert_called_once()


@pytest.mark.asyncio
@patch("src.bot.handlers.media.MediaService")
@patch("src.bot.handlers.media.TranslationService")
async def test_handle_series_sets_search_type(
    mock_ts_class, mock_ms_class, make_update, make_context
):
    """handle_series sets user_data['search_type'] to 'series' and returns SEARCHING."""
    mock_ts = MagicMock()
    mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
    mock_ts_class.return_value = mock_ts
    mock_ms_class.return_value = MagicMock()

    from src.bot.handlers.media import MediaHandler, SEARCHING
    from src.bot.handlers.auth import AuthHandler

    AuthHandler._authenticated_users = {12345}

    handler = MediaHandler()
    update = make_update(text="/series")
    context = make_context()

    result = await handler.handle_series(update, context)

    assert result == SEARCHING
    assert context.user_data["search_type"] == "series"
    update.message.reply_text.assert_called_once()


@pytest.mark.asyncio
@patch("src.bot.handlers.media.MediaService")
@patch("src.bot.handlers.media.TranslationService")
async def test_handle_music_sets_search_type(
    mock_ts_class, mock_ms_class, make_update, make_context
):
    """handle_music sets user_data['search_type'] to 'music' and returns SEARCHING."""
    mock_ts = MagicMock()
    mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
    mock_ts_class.return_value = mock_ts
    mock_ms_class.return_value = MagicMock()

    from src.bot.handlers.media import MediaHandler, SEARCHING
    from src.bot.handlers.auth import AuthHandler

    AuthHandler._authenticated_users = {12345}

    handler = MediaHandler()
    update = make_update(text="/music")
    context = make_context()

    result = await handler.handle_music(update, context)

    assert result == SEARCHING
    assert context.user_data["search_type"] == "music"
    update.message.reply_text.assert_called_once()


# ---------------------------------------------------------------------------
# handle_search
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("src.bot.handlers.media.MediaService")
@patch("src.bot.handlers.media.TranslationService")
async def test_handle_search_no_results(
    mock_ts_class, mock_ms_class, make_update, make_context
):
    """Empty search results replies with not-found message and returns END."""
    mock_ts = MagicMock()
    mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
    mock_ts_class.return_value = mock_ts

    mock_service = MagicMock()
    mock_service.search_movies = AsyncMock(return_value=[])
    mock_ms_class.return_value = mock_service

    from src.bot.handlers.media import MediaHandler

    handler = MediaHandler()
    update = make_update(text="Nonexistent Movie")
    context = make_context(user_data={"search_type": "movie"})

    result = await handler.handle_search(update, context)

    assert result == ConversationHandler.END
    update.message.reply_text.assert_called_once()
    call_args = update.message.reply_text.call_args
    assert "No" in str(call_args) or "not found" in str(call_args).lower() or "No movie found" in str(call_args)


@pytest.mark.asyncio
@patch("src.bot.handlers.media.MediaService")
@patch("src.bot.handlers.media.TranslationService")
async def test_handle_search_with_results(
    mock_ts_class, mock_ms_class, make_update, make_context
):
    """Search returning results stores them in user_data and returns SELECTING."""
    mock_ts = MagicMock()
    mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
    mock_ts_class.return_value = mock_ts

    mock_service = MagicMock()
    mock_service.search_movies = AsyncMock(return_value=[
        {"id": "123", "title": "Test Movie", "overview": "A test movie", "year": 2024}
    ])
    mock_ms_class.return_value = mock_service

    from src.bot.handlers.media import MediaHandler, SELECTING

    handler = MediaHandler()

    update = make_update(text="Test Movie")
    context = make_context(user_data={"search_type": "movie"})

    # Patch _show_result to avoid complex poster/caption logic
    with patch.object(handler, "_show_result", new_callable=AsyncMock):
        result = await handler.handle_search(update, context)

    assert result == SELECTING
    assert len(context.user_data["search_results"]) == 1
    assert context.user_data["current_index"] == 0


# ---------------------------------------------------------------------------
# handle_selection
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("src.bot.handlers.media.MediaService")
@patch("src.bot.handlers.media.TranslationService")
async def test_handle_selection_cancel(
    mock_ts_class, mock_ms_class, make_update, make_context
):
    """Callback data 'select_cancel' ends the conversation."""
    mock_ts = MagicMock()
    mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
    mock_ts_class.return_value = mock_ts
    mock_ms_class.return_value = MagicMock()

    from src.bot.handlers.media import MediaHandler

    handler = MediaHandler()

    update = make_update(callback_data="select_cancel")
    # The query.message needs photo attribute
    update.callback_query.message.photo = None
    context = make_context()

    result = await handler.handle_selection(update, context)

    assert result == ConversationHandler.END
    update.callback_query.answer.assert_called_once()


# ---------------------------------------------------------------------------
# handle_menu_callback
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("src.bot.handlers.media.MediaService")
@patch("src.bot.handlers.media.TranslationService")
async def test_handle_menu_callback_cancel(
    mock_ts_class, mock_ms_class, make_update, make_context
):
    """menu_cancel callback edits message with 'Canceled' and returns END."""
    mock_ts = MagicMock()
    mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
    mock_ts_class.return_value = mock_ts
    mock_ms_class.return_value = MagicMock()

    from src.bot.handlers.media import MediaHandler

    handler = MediaHandler()

    update = make_update(callback_data="menu_cancel")
    context = make_context()

    result = await handler.handle_menu_callback(update, context)

    assert result == ConversationHandler.END
    update.callback_query.message.edit_text.assert_called_once()
    call_args = update.callback_query.message.edit_text.call_args
    assert "Canceled" in str(call_args)


@pytest.mark.asyncio
@patch("src.bot.handlers.media.MediaService")
@patch("src.bot.handlers.media.TranslationService")
async def test_handle_menu_callback_movie(
    mock_ts_class, mock_ms_class, make_update, make_context
):
    """menu_movie callback sets search_type and returns SEARCHING."""
    mock_ts = MagicMock()
    mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
    mock_ts_class.return_value = mock_ts
    mock_ms_class.return_value = MagicMock()

    from src.bot.handlers.media import MediaHandler, SEARCHING

    handler = MediaHandler()

    update = make_update(callback_data="menu_movie")
    context = make_context()

    result = await handler.handle_menu_callback(update, context)

    assert result == SEARCHING
    assert context.user_data["search_type"] == "movie"


# ---------------------------------------------------------------------------
# cancel_search
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("src.bot.handlers.media.MediaService")
@patch("src.bot.handlers.media.TranslationService")
async def test_cancel_search(
    mock_ts_class, mock_ms_class, make_update, make_context
):
    """cancel_search replies with cancellation message and returns END."""
    mock_ts = MagicMock()
    mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
    mock_ts_class.return_value = mock_ts
    mock_ms_class.return_value = MagicMock()

    from src.bot.handlers.media import MediaHandler

    handler = MediaHandler()
    update = make_update(text="/cancel")
    context = make_context()

    result = await handler.cancel_search(update, context)

    assert result == ConversationHandler.END
    update.message.reply_text.assert_called_once()


# ---------------------------------------------------------------------------
# get_handler
# ---------------------------------------------------------------------------


@patch("src.bot.handlers.media.MediaService")
@patch("src.bot.handlers.media.TranslationService")
def test_get_handler_returns_list(mock_ts_class, mock_ms_class):
    """get_handler returns a list of handlers."""
    mock_ts = MagicMock()
    mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
    mock_ts_class.return_value = mock_ts
    mock_ms_class.return_value = MagicMock()

    from src.bot.handlers.media import MediaHandler

    handler = MediaHandler()
    handlers = handler.get_handler()

    assert isinstance(handlers, list)
    assert len(handlers) > 0

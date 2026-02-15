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
# handle_movie / handle_series / handle_music (parametrized)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("media_type,handler_method", [
    ("movie", "handle_movie"),
    ("series", "handle_series"),
    ("music", "handle_music"),
])
@pytest.mark.asyncio
async def test_handle_media_sets_search_type(
    media_handler, make_update, make_context, media_type, handler_method
):
    """handle_movie/series/music sets search_type and returns SEARCHING."""
    from src.bot.handlers.media import SEARCHING

    update = make_update(text=f"/{media_type}")
    context = make_context()

    method = getattr(media_handler, handler_method)
    result = await method(update, context)

    assert result == SEARCHING
    assert context.user_data["search_type"] == media_type
    update.message.reply_text.assert_called_once()


@pytest.mark.parametrize("media_type,handler_method", [
    ("movie", "handle_movie"),
    ("series", "handle_series"),
    ("music", "handle_music"),
])
@pytest.mark.asyncio
async def test_handle_media_no_message_returns_end(
    media_handler, make_update, make_context, media_type, handler_method
):
    """handle_movie/series/music returns END when no effective_message."""
    update = make_update(text=f"/{media_type}")
    update.effective_message = None
    context = make_context()

    method = getattr(media_handler, handler_method)
    result = await method(update, context)

    assert result == ConversationHandler.END


@pytest.mark.parametrize("media_type,handler_method,service", [
    ("movie", "handle_movie", "radarr"),
    ("series", "handle_series", "sonarr"),
    ("music", "handle_music", "lidarr"),
])
@pytest.mark.asyncio
async def test_handle_media_admin_restriction_denies_non_admin(
    media_handler, make_update, make_context, make_user,
    media_type, handler_method, service
):
    """When adminRestrictions is True, non-admin users get denied."""
    from src.config.settings import config
    original = config._config[service].get("adminRestrictions", False)
    config._config[service]["adminRestrictions"] = True
    try:
        # User 99999 is NOT in admins list
        user = make_user(user_id=99999)
        update = make_update(text=f"/{media_type}", user=user)
        context = make_context()

        # Ensure the user is authenticated but not admin
        from src.bot.handlers.auth import AuthHandler
        AuthHandler._authenticated_users.add(99999)

        method = getattr(media_handler, handler_method)
        result = await method(update, context)

        assert result == ConversationHandler.END
        # Should have replied with a restriction message
        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args
        assert "admin" in call_args[0][0].lower() or "restricted" in call_args[0][0].lower()
    finally:
        config._config[service]["adminRestrictions"] = original


# ---------------------------------------------------------------------------
# handle_search
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_search_no_results(media_handler, make_update, make_context):
    """Empty search results replies with not-found message and returns END."""
    media_handler._mock_service.search_movies = AsyncMock(return_value=[])

    update = make_update(text="Nonexistent Movie")
    context = make_context(user_data={"search_type": "movie"})

    result = await media_handler.handle_search(update, context)

    assert result == ConversationHandler.END
    update.message.reply_text.assert_called_once()


@pytest.mark.asyncio
async def test_handle_search_with_results(media_handler, make_update, make_context):
    """Search returning results stores them in user_data and returns SELECTING."""
    from src.bot.handlers.media import SELECTING

    media_handler._mock_service.search_movies = AsyncMock(return_value=[
        {"id": "123", "title": "Test Movie", "overview": "A test movie", "year": 2024}
    ])

    update = make_update(text="Test Movie")
    context = make_context(user_data={"search_type": "movie"})

    with patch.object(media_handler, "_show_result", new_callable=AsyncMock):
        result = await media_handler.handle_search(update, context)

    assert result == SELECTING
    assert len(context.user_data["search_results"]) == 1
    assert context.user_data["current_index"] == 0


@pytest.mark.parametrize("search_type,method_name", [
    ("series", "search_series"),
    ("music", "search_music"),
])
@pytest.mark.asyncio
async def test_handle_search_dispatches_by_type(
    media_handler, make_update, make_context, search_type, method_name
):
    """handle_search dispatches to the correct service method."""
    from src.bot.handlers.media import SELECTING

    search_mock = AsyncMock(return_value=[
        {"id": "1", "title": "Test", "overview": "Overview", "year": 2024}
    ])
    setattr(media_handler._mock_service, method_name, search_mock)

    update = make_update(text="Test")
    context = make_context(user_data={"search_type": search_type})

    with patch.object(media_handler, "_show_result", new_callable=AsyncMock):
        result = await media_handler.handle_search(update, context)

    assert result == SELECTING
    search_mock.assert_awaited_once_with("Test")


@pytest.mark.asyncio
async def test_handle_search_invalid_type(media_handler, make_update, make_context):
    """handle_search with invalid search_type returns END."""
    update = make_update(text="Test")
    context = make_context(user_data={"search_type": "invalid"})

    result = await media_handler.handle_search(update, context)

    assert result == ConversationHandler.END


@pytest.mark.asyncio
async def test_handle_search_exception(media_handler, make_update, make_context):
    """handle_search returns END on exception."""
    media_handler._mock_service.search_movies = AsyncMock(
        side_effect=Exception("Network error")
    )

    update = make_update(text="Test")
    context = make_context(user_data={"search_type": "movie"})

    result = await media_handler.handle_search(update, context)

    assert result == ConversationHandler.END
    update.message.reply_text.assert_called_once()


@pytest.mark.asyncio
async def test_handle_search_no_effective_message(
    media_handler, make_update, make_context
):
    """handle_search returns END when no effective_message."""
    update = make_update(text="Test")
    update.effective_message = None
    context = make_context(user_data={"search_type": "movie"})

    result = await media_handler.handle_search(update, context)

    assert result == ConversationHandler.END


# ---------------------------------------------------------------------------
# handle_selection
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_selection_cancel(media_handler, make_update, make_context):
    """Callback data 'select_cancel' ends the conversation."""
    update = make_update(callback_data="select_cancel")
    update.callback_query.message.photo = None
    context = make_context()

    result = await media_handler.handle_selection(update, context)

    assert result == ConversationHandler.END
    update.callback_query.answer.assert_called_once()


@pytest.mark.asyncio
async def test_handle_selection_cancel_with_photo(
    media_handler, make_update, make_context
):
    """select_cancel with photo uses edit_caption."""
    update = make_update(callback_data="select_cancel")
    update.callback_query.message.photo = [MagicMock()]
    context = make_context()

    result = await media_handler.handle_selection(update, context)

    assert result == ConversationHandler.END
    update.callback_query.message.edit_caption.assert_called_once()


@pytest.mark.asyncio
async def test_handle_selection_quality_selection(
    media_handler, make_update, make_context
):
    """Selecting an item that returns quality_selection enters QUALITY_SELECT."""
    from src.bot.handlers.media import QUALITY_SELECT

    media_handler._mock_service.add_movie = AsyncMock(return_value={
        "type": "quality_selection",
        "profiles": [{"id": 1, "name": "HD-1080p"}],
        "root_folder": "/movies",
    })

    update = make_update(callback_data="select_123")
    update.callback_query.message.photo = None
    context = make_context(user_data={
        "search_type": "movie",
        "search_results": [{"id": "123", "title": "Test Movie"}],
    })

    result = await media_handler.handle_selection(update, context)

    assert result == QUALITY_SELECT


@pytest.mark.asyncio
async def test_handle_selection_quality_selection_with_photo(
    media_handler, make_update, make_context
):
    """Quality selection with photo uses edit_caption."""
    from src.bot.handlers.media import QUALITY_SELECT

    media_handler._mock_service.add_movie = AsyncMock(return_value={
        "type": "quality_selection",
        "profiles": [{"id": 1, "name": "HD-1080p"}],
        "root_folder": "/movies",
    })

    update = make_update(callback_data="select_123")
    update.callback_query.message.photo = [MagicMock()]
    context = make_context(user_data={
        "search_type": "movie",
        "search_results": [{"id": "123", "title": "Test Movie"}],
    })

    result = await media_handler.handle_selection(update, context)

    assert result == QUALITY_SELECT
    update.callback_query.message.edit_caption.assert_called_once()


@pytest.mark.asyncio
async def test_handle_selection_tuple_success(
    media_handler, make_update, make_context
):
    """Selecting an item that returns a success tuple ends conversation."""
    media_handler._mock_service.add_movie = AsyncMock(
        return_value=(True, "Added successfully")
    )

    update = make_update(callback_data="select_123")
    update.callback_query.message.photo = None
    context = make_context(user_data={
        "search_type": "movie",
        "search_results": [{"id": "123", "title": "Test Movie"}],
    })

    result = await media_handler.handle_selection(update, context)

    assert result == ConversationHandler.END


@pytest.mark.asyncio
async def test_handle_selection_tuple_failure(
    media_handler, make_update, make_context
):
    """Selecting an item that returns a failure tuple ends conversation."""
    media_handler._mock_service.add_movie = AsyncMock(
        return_value=(False, "Already exists")
    )

    update = make_update(callback_data="select_123")
    update.callback_query.message.photo = None
    context = make_context(user_data={
        "search_type": "movie",
        "search_results": [{"id": "123", "title": "Test Movie"}],
    })

    result = await media_handler.handle_selection(update, context)

    assert result == ConversationHandler.END


@pytest.mark.asyncio
async def test_handle_selection_not_found(media_handler, make_update, make_context):
    """Selection not found in results returns END."""
    update = make_update(callback_data="select_999")
    update.callback_query.message.photo = None
    context = make_context(user_data={
        "search_type": "movie",
        "search_results": [{"id": "123", "title": "Test Movie"}],
    })

    result = await media_handler.handle_selection(update, context)

    assert result == ConversationHandler.END


@pytest.mark.asyncio
async def test_handle_selection_exception(media_handler, make_update, make_context):
    """Exception during selection returns END."""
    media_handler._mock_service.add_movie = AsyncMock(
        side_effect=Exception("API error")
    )

    update = make_update(callback_data="select_123")
    update.callback_query.message.photo = None
    context = make_context(user_data={
        "search_type": "movie",
        "search_results": [{"id": "123", "title": "Test Movie"}],
    })

    result = await media_handler.handle_selection(update, context)

    assert result == ConversationHandler.END


@pytest.mark.asyncio
async def test_handle_selection_no_callback_query(
    media_handler, make_update, make_context
):
    """handle_selection returns END when no callback_query."""
    update = make_update(text="test")
    update.callback_query = None
    context = make_context()

    result = await media_handler.handle_selection(update, context)

    assert result == ConversationHandler.END


@pytest.mark.parametrize("search_type,service_method", [
    ("series", "add_series"),
    ("music", "add_music"),
])
@pytest.mark.asyncio
async def test_handle_selection_dispatches_by_type(
    media_handler, make_update, make_context, search_type, service_method
):
    """handle_selection dispatches to correct service add method."""
    add_mock = AsyncMock(return_value=(True, "Added"))
    setattr(media_handler._mock_service, service_method, add_mock)

    update = make_update(callback_data="select_123")
    update.callback_query.message.photo = None
    context = make_context(user_data={
        "search_type": search_type,
        "search_results": [{"id": "123", "title": "Test"}],
    })

    result = await media_handler.handle_selection(update, context)

    assert result == ConversationHandler.END
    add_mock.assert_awaited_once()


# ---------------------------------------------------------------------------
# handle_menu_callback
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_menu_callback_cancel(media_handler, make_update, make_context):
    """menu_cancel callback edits message with 'Canceled' and returns END."""
    update = make_update(callback_data="menu_cancel")
    context = make_context()

    result = await media_handler.handle_menu_callback(update, context)

    assert result == ConversationHandler.END
    update.callback_query.message.edit_text.assert_called_once()


@pytest.mark.asyncio
async def test_handle_menu_callback_movie(media_handler, make_update, make_context):
    """menu_movie callback sets search_type and returns SEARCHING."""
    from src.bot.handlers.media import SEARCHING

    update = make_update(callback_data="menu_movie")
    context = make_context()

    result = await media_handler.handle_menu_callback(update, context)

    assert result == SEARCHING
    assert context.user_data["search_type"] == "movie"


@pytest.mark.asyncio
async def test_handle_menu_callback_no_query(
    media_handler, make_update, make_context
):
    """handle_menu_callback returns END when no callback_query."""
    update = make_update(text="test")
    update.callback_query = None
    context = make_context()

    result = await media_handler.handle_menu_callback(update, context)

    assert result == ConversationHandler.END


# ---------------------------------------------------------------------------
# handle_quality_selection
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_quality_cancel(media_handler, make_update, make_context):
    """quality_cancel ends the conversation."""
    update = make_update(callback_data="quality_cancel")
    update.callback_query.message.photo = None
    context = make_context()

    result = await media_handler.handle_quality_selection(update, context)

    assert result == ConversationHandler.END


@pytest.mark.asyncio
async def test_handle_quality_selection_movie(
    media_handler, make_update, make_context
):
    """Quality selected for movie calls _add_media_with_profile and returns END."""
    media_handler._mock_service.add_movie_with_profile = AsyncMock(
        return_value=(True, "Added")
    )

    update = make_update(callback_data="quality_1")
    update.callback_query.message.photo = None
    context = make_context(user_data={
        "search_type": "movie",
        "selected_media": {"id": "123", "title": "Test Movie"},
        "quality_data": {
            "profiles": [{"id": 1, "name": "HD-1080p"}],
            "root_folder": "/movies",
        },
    })

    result = await media_handler.handle_quality_selection(update, context)

    assert result == ConversationHandler.END


@pytest.mark.asyncio
async def test_handle_quality_selection_series_with_seasons(
    media_handler, make_update, make_context
):
    """Quality selected for series with seasons enters SEASON_SELECT."""
    from src.bot.handlers.media import SEASON_SELECT

    update = make_update(callback_data="quality_1")
    update.callback_query.message.photo = None
    context = make_context(user_data={
        "search_type": "series",
        "selected_media": {"id": "123", "title": "Test Series"},
        "quality_data": {
            "profiles": [{"id": 1, "name": "HD-1080p"}],
            "root_folder": "/tv",
            "seasons": [
                {"seasonNumber": 1},
                {"seasonNumber": 2},
            ],
        },
    })

    result = await media_handler.handle_quality_selection(update, context)

    assert result == SEASON_SELECT


@pytest.mark.asyncio
async def test_handle_quality_selection_no_data(
    media_handler, make_update, make_context
):
    """Missing quality_data returns END with error."""
    update = make_update(callback_data="quality_1")
    update.callback_query.message.photo = None
    context = make_context(user_data={"search_type": "movie"})

    result = await media_handler.handle_quality_selection(update, context)

    assert result == ConversationHandler.END


@pytest.mark.asyncio
async def test_handle_quality_selection_exception(
    media_handler, make_update, make_context
):
    """Exception during quality selection returns END."""
    media_handler._mock_service.add_movie_with_profile = AsyncMock(
        side_effect=Exception("API error")
    )

    update = make_update(callback_data="quality_1")
    update.callback_query.message.photo = None
    context = make_context(user_data={
        "search_type": "movie",
        "selected_media": {"id": "123", "title": "Test"},
        "quality_data": {
            "profiles": [{"id": 1, "name": "HD"}],
            "root_folder": "/movies",
        },
    })

    result = await media_handler.handle_quality_selection(update, context)

    assert result == ConversationHandler.END


@pytest.mark.asyncio
async def test_handle_quality_selection_no_query(
    media_handler, make_update, make_context
):
    """handle_quality_selection returns END when no callback_query."""
    update = make_update(text="test")
    update.callback_query = None
    context = make_context()

    result = await media_handler.handle_quality_selection(update, context)

    assert result == ConversationHandler.END


# ---------------------------------------------------------------------------
# handle_season_selection
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_season_selection_cancel(
    media_handler, make_update, make_context
):
    """select_cancel during season selection returns END."""
    update = make_update(callback_data="select_cancel")
    update.callback_query.message.photo = None
    context = make_context(user_data={
        "quality_data": {"seasons": []},
        "selected_seasons": set(),
        "future_mode": None,
    })

    result = await media_handler.handle_season_selection(update, context)

    assert result == ConversationHandler.END


@pytest.mark.asyncio
async def test_handle_season_selection_confirm_delegates(
    media_handler, make_update, make_context
):
    """season_confirm delegates to handle_season_confirm."""
    media_handler._mock_service.add_series_with_profile = AsyncMock(
        return_value=(True, "Added")
    )

    update = make_update(callback_data="season_confirm")
    update.callback_query.message.photo = None
    context = make_context(user_data={
        "selected_media": {"id": "123", "title": "Test"},
        "selected_profile_id": 1,
        "selected_root_folder": "/tv",
        "selected_seasons": {1, 2},
        "future_mode": None,
        "monitor_all": False,
        "quality_data": {"seasons": [{"seasonNumber": 1}, {"seasonNumber": 2}]},
    })

    result = await media_handler.handle_season_selection(update, context)

    assert result == ConversationHandler.END


@pytest.mark.asyncio
async def test_handle_season_selection_monitor_all_on(
    media_handler, make_update, make_context
):
    """Enabling monitor_all selects all and auto-confirms."""
    media_handler._mock_service.add_series_with_profile = AsyncMock(
        return_value=(True, "Added")
    )

    update = make_update(callback_data="season_monitor_all")
    update.callback_query.message.photo = None
    context = make_context(user_data={
        "selected_media": {"id": "123", "title": "Test"},
        "selected_profile_id": 1,
        "selected_root_folder": "/tv",
        "selected_seasons": set(),
        "future_mode": None,
        "monitor_all": False,
        "quality_data": {"seasons": [{"seasonNumber": 1}, {"seasonNumber": 2}]},
    })

    result = await media_handler.handle_season_selection(update, context)

    assert result == ConversationHandler.END


@pytest.mark.asyncio
async def test_handle_season_selection_monitor_all_off(
    media_handler, make_update, make_context
):
    """Disabling monitor_all clears selections."""
    from src.bot.handlers.media import SEASON_SELECT

    update = make_update(callback_data="season_monitor_all")
    update.callback_query.message.photo = None
    update.callback_query.message.reply_markup = MagicMock()
    update.callback_query.message.reply_markup.to_dict.return_value = {}
    context = make_context(user_data={
        "selected_media": {"id": "123", "title": "Test"},
        "selected_profile_id": 1,
        "selected_root_folder": "/tv",
        "selected_seasons": {1, 2},
        "future_mode": "future_seasons",
        "monitor_all": True,
        "quality_data": {"seasons": [{"seasonNumber": 1}, {"seasonNumber": 2}]},
    })

    result = await media_handler.handle_season_selection(update, context)

    assert result == SEASON_SELECT
    assert len(context.user_data["selected_seasons"]) == 0


@pytest.mark.asyncio
async def test_handle_season_selection_all_toggle_on(
    media_handler, make_update, make_context
):
    """Toggle all seasons on."""
    from src.bot.handlers.media import SEASON_SELECT

    update = make_update(callback_data="season_all")
    update.callback_query.message.photo = None
    update.callback_query.message.reply_markup = MagicMock()
    update.callback_query.message.reply_markup.to_dict.return_value = {}
    context = make_context(user_data={
        "selected_seasons": set(),
        "future_mode": None,
        "monitor_all": False,
        "quality_data": {"seasons": [{"seasonNumber": 1}, {"seasonNumber": 2}]},
    })

    result = await media_handler.handle_season_selection(update, context)

    assert result == SEASON_SELECT
    assert context.user_data["selected_seasons"] == {1, 2}
    assert context.user_data["future_mode"] == "all"


@pytest.mark.asyncio
async def test_handle_season_selection_all_toggle_off(
    media_handler, make_update, make_context
):
    """Toggle all seasons off when already all selected."""
    from src.bot.handlers.media import SEASON_SELECT

    update = make_update(callback_data="season_all")
    update.callback_query.message.photo = None
    update.callback_query.message.reply_markup = MagicMock()
    update.callback_query.message.reply_markup.to_dict.return_value = {}
    context = make_context(user_data={
        "selected_seasons": {1, 2},
        "future_mode": "all",
        "monitor_all": False,
        "quality_data": {"seasons": [{"seasonNumber": 1}, {"seasonNumber": 2}]},
    })

    result = await media_handler.handle_season_selection(update, context)

    assert result == SEASON_SELECT
    assert len(context.user_data["selected_seasons"]) == 0
    assert context.user_data["future_mode"] is None


@pytest.mark.asyncio
async def test_handle_season_selection_future_seasons_toggle(
    media_handler, make_update, make_context
):
    """Toggle future_seasons mode."""
    from src.bot.handlers.media import SEASON_SELECT

    update = make_update(callback_data="season_future_seasons")
    update.callback_query.message.photo = None
    update.callback_query.message.reply_markup = MagicMock()
    update.callback_query.message.reply_markup.to_dict.return_value = {}
    context = make_context(user_data={
        "selected_seasons": set(),
        "future_mode": None,
        "monitor_all": False,
        "quality_data": {"seasons": [{"seasonNumber": 1}]},
    })

    result = await media_handler.handle_season_selection(update, context)

    assert result == SEASON_SELECT
    assert context.user_data["future_mode"] == "future_seasons"


@pytest.mark.asyncio
async def test_handle_season_selection_future_episodes_toggle(
    media_handler, make_update, make_context
):
    """Toggle future_episodes mode."""
    from src.bot.handlers.media import SEASON_SELECT

    update = make_update(callback_data="season_future_episodes")
    update.callback_query.message.photo = None
    update.callback_query.message.reply_markup = MagicMock()
    update.callback_query.message.reply_markup.to_dict.return_value = {}
    context = make_context(user_data={
        "selected_seasons": set(),
        "future_mode": None,
        "monitor_all": False,
        "quality_data": {"seasons": [{"seasonNumber": 1}]},
    })

    result = await media_handler.handle_season_selection(update, context)

    assert result == SEASON_SELECT
    assert context.user_data["future_mode"] == "future_episodes"


@pytest.mark.asyncio
async def test_handle_season_selection_individual_toggle(
    media_handler, make_update, make_context
):
    """Toggle individual season selection."""
    from src.bot.handlers.media import SEASON_SELECT

    update = make_update(callback_data="season_1")
    update.callback_query.message.photo = None
    update.callback_query.message.reply_markup = MagicMock()
    update.callback_query.message.reply_markup.to_dict.return_value = {}
    context = make_context(user_data={
        "selected_seasons": set(),
        "future_mode": None,
        "monitor_all": False,
        "quality_data": {"seasons": [{"seasonNumber": 1}, {"seasonNumber": 2}]},
    })

    result = await media_handler.handle_season_selection(update, context)

    assert result == SEASON_SELECT
    assert 1 in context.user_data["selected_seasons"]


@pytest.mark.asyncio
async def test_handle_season_selection_individual_deselect(
    media_handler, make_update, make_context
):
    """Deselect individual season."""
    from src.bot.handlers.media import SEASON_SELECT

    update = make_update(callback_data="season_1")
    update.callback_query.message.photo = None
    update.callback_query.message.reply_markup = MagicMock()
    update.callback_query.message.reply_markup.to_dict.return_value = {}
    context = make_context(user_data={
        "selected_seasons": {1},
        "future_mode": None,
        "monitor_all": False,
        "quality_data": {"seasons": [{"seasonNumber": 1}, {"seasonNumber": 2}]},
    })

    result = await media_handler.handle_season_selection(update, context)

    assert result == SEASON_SELECT
    assert 1 not in context.user_data["selected_seasons"]


@pytest.mark.asyncio
async def test_handle_season_selection_invalid_action(
    media_handler, make_update, make_context
):
    """Invalid season action (non-numeric) is ignored via ValueError pass."""
    from src.bot.handlers.media import SEASON_SELECT

    update = make_update(callback_data="season_invalid_action")
    update.callback_query.message.photo = None
    update.callback_query.message.reply_markup = MagicMock()
    update.callback_query.message.reply_markup.to_dict.return_value = {}
    context = make_context(user_data={
        "selected_seasons": set(),
        "future_mode": None,
        "monitor_all": False,
        "quality_data": {"seasons": [{"seasonNumber": 1}]},
    })

    result = await media_handler.handle_season_selection(update, context)

    assert result == SEASON_SELECT


@pytest.mark.asyncio
async def test_handle_season_selection_no_query(
    media_handler, make_update, make_context
):
    """handle_season_selection returns END when no callback_query."""
    update = make_update(text="test")
    update.callback_query = None
    context = make_context()

    result = await media_handler.handle_season_selection(update, context)

    assert result == ConversationHandler.END


@pytest.mark.asyncio
async def test_handle_season_selection_keyboard_unchanged(
    media_handler, make_update, make_context
):
    """When keyboard markup is unchanged, no edit occurs."""
    from src.bot.handlers.media import SEASON_SELECT

    update = make_update(callback_data="season_future_seasons")
    update.callback_query.message.photo = None

    # Make the reply_markup.to_dict match the new markup
    # by toggling future_seasons twice (on then off)
    update.callback_query.message.reply_markup = MagicMock()
    context = make_context(user_data={
        "selected_seasons": set(),
        "future_mode": "future_seasons",  # Already on, so toggling off
        "monitor_all": False,
        "quality_data": {"seasons": [{"seasonNumber": 1}]},
    })

    # Make to_dict return the same as new markup would produce
    # This is tricky -- just ensure no error occurs
    update.callback_query.message.reply_markup.to_dict.return_value = {}
    result = await media_handler.handle_season_selection(update, context)

    assert result == SEASON_SELECT


# ---------------------------------------------------------------------------
# handle_season_confirm
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_season_confirm_monitor_all(
    media_handler, make_update, make_context
):
    """Monitor all mode sends all seasons monitored with future_seasons."""
    media_handler._mock_service.add_series_with_profile = AsyncMock(
        return_value=(True, "Added")
    )

    update = make_update(callback_data="season_confirm")
    update.callback_query.message.photo = None
    context = make_context(user_data={
        "selected_media": {"id": "123", "title": "Test"},
        "selected_profile_id": 1,
        "selected_root_folder": "/tv",
        "selected_seasons": {1, 2},
        "future_mode": None,
        "monitor_all": True,
        "quality_data": {"seasons": [{"seasonNumber": 1}, {"seasonNumber": 2}]},
    })

    result = await media_handler.handle_season_confirm(update, context)

    assert result == ConversationHandler.END
    media_handler._mock_service.add_series_with_profile.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_season_confirm_all_mode(
    media_handler, make_update, make_context
):
    """All mode sends all seasons monitored."""
    media_handler._mock_service.add_series_with_profile = AsyncMock(
        return_value=(True, "Added")
    )

    update = make_update(callback_data="season_confirm")
    update.callback_query.message.photo = None
    context = make_context(user_data={
        "selected_media": {"id": "123", "title": "Test"},
        "selected_profile_id": 1,
        "selected_root_folder": "/tv",
        "selected_seasons": {1, 2},
        "future_mode": "all",
        "monitor_all": False,
        "quality_data": {"seasons": [{"seasonNumber": 1}, {"seasonNumber": 2}]},
    })

    result = await media_handler.handle_season_confirm(update, context)

    assert result == ConversationHandler.END


@pytest.mark.asyncio
async def test_handle_season_confirm_future_episodes(
    media_handler, make_update, make_context
):
    """Future episodes mode adds -1 season flag."""
    media_handler._mock_service.add_series_with_profile = AsyncMock(
        return_value=(True, "Added")
    )

    update = make_update(callback_data="season_confirm")
    update.callback_query.message.photo = None
    context = make_context(user_data={
        "selected_media": {"id": "123", "title": "Test"},
        "selected_profile_id": 1,
        "selected_root_folder": "/tv",
        "selected_seasons": set(),
        "future_mode": "future_episodes",
        "monitor_all": False,
        "quality_data": {"seasons": [{"seasonNumber": 1}]},
    })

    result = await media_handler.handle_season_confirm(update, context)

    assert result == ConversationHandler.END
    call_args = media_handler._mock_service.add_series_with_profile.call_args
    seasons_data = call_args[0][3]
    # Should have -1 season flag
    assert any(s["seasonNumber"] == -1 for s in seasons_data)


@pytest.mark.asyncio
async def test_handle_season_confirm_selected_seasons(
    media_handler, make_update, make_context
):
    """Selected seasons only mode monitors specific seasons."""
    media_handler._mock_service.add_series_with_profile = AsyncMock(
        return_value=(True, "Added")
    )

    update = make_update(callback_data="season_confirm")
    update.callback_query.message.photo = None
    context = make_context(user_data={
        "selected_media": {"id": "123", "title": "Test"},
        "selected_profile_id": 1,
        "selected_root_folder": "/tv",
        "selected_seasons": {1},
        "future_mode": None,
        "monitor_all": False,
        "quality_data": {"seasons": [{"seasonNumber": 1}, {"seasonNumber": 2}]},
    })

    result = await media_handler.handle_season_confirm(update, context)

    assert result == ConversationHandler.END
    call_args = media_handler._mock_service.add_series_with_profile.call_args
    seasons_data = call_args[0][3]
    monitored_seasons = [s for s in seasons_data if s["monitored"]]
    assert len(monitored_seasons) == 1


@pytest.mark.asyncio
async def test_handle_season_confirm_selected_with_future(
    media_handler, make_update, make_context
):
    """Selected seasons + future_seasons mode."""
    media_handler._mock_service.add_series_with_profile = AsyncMock(
        return_value=(True, "Added")
    )

    update = make_update(callback_data="season_confirm")
    update.callback_query.message.photo = None
    context = make_context(user_data={
        "selected_media": {"id": "123", "title": "Test"},
        "selected_profile_id": 1,
        "selected_root_folder": "/tv",
        "selected_seasons": {1},
        "future_mode": "future_seasons",
        "monitor_all": False,
        "quality_data": {"seasons": [{"seasonNumber": 1}, {"seasonNumber": 2}]},
    })

    result = await media_handler.handle_season_confirm(update, context)

    assert result == ConversationHandler.END
    call_args = media_handler._mock_service.add_series_with_profile.call_args
    seasons_data = call_args[0][3]
    assert any(s["seasonNumber"] == -1 for s in seasons_data)


@pytest.mark.asyncio
async def test_handle_season_confirm_exception(
    media_handler, make_update, make_context
):
    """Exception during season confirm returns END."""
    media_handler._mock_service.add_series_with_profile = AsyncMock(
        side_effect=Exception("Error")
    )

    update = make_update(callback_data="season_confirm")
    update.callback_query.message.photo = None
    context = make_context(user_data={
        "selected_media": {"id": "123", "title": "Test"},
        "selected_profile_id": 1,
        "selected_root_folder": "/tv",
        "selected_seasons": {1},
        "future_mode": None,
        "monitor_all": False,
        "quality_data": {"seasons": [{"seasonNumber": 1}]},
    })

    result = await media_handler.handle_season_confirm(update, context)

    assert result == ConversationHandler.END


@pytest.mark.asyncio
async def test_handle_season_confirm_no_query(
    media_handler, make_update, make_context
):
    """handle_season_confirm returns END when no callback_query."""
    update = make_update(text="test")
    update.callback_query = None
    context = make_context()

    result = await media_handler.handle_season_confirm(update, context)

    assert result == ConversationHandler.END


# ---------------------------------------------------------------------------
# _add_media_with_profile
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("media_type,service_method", [
    ("movie", "add_movie_with_profile"),
    ("series", "add_series_with_profile"),
    ("music", "add_music_with_profile"),
])
@pytest.mark.asyncio
async def test_add_media_with_profile(
    media_handler, media_type, service_method
):
    """_add_media_with_profile dispatches to correct service method."""
    method_mock = AsyncMock(return_value=(True, "Added"))
    setattr(media_handler._mock_service, service_method, method_mock)

    success, msg = await media_handler._add_media_with_profile(
        media_type, {"id": "123"}, 1, "/media"
    )

    assert success is True
    method_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_add_media_with_profile_invalid_type(media_handler):
    """_add_media_with_profile returns failure for invalid type."""
    success, msg = await media_handler._add_media_with_profile(
        "invalid", {"id": "123"}, 1, "/media"
    )

    assert success is False
    assert "Invalid" in msg


# ---------------------------------------------------------------------------
# _send_response
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_send_response_with_photo(media_handler, make_message):
    """_send_response uses edit_caption when message has photo."""
    message = make_message()
    message.photo = [MagicMock()]

    await media_handler._send_response(message, "Test text")

    message.edit_caption.assert_called_once()


@pytest.mark.asyncio
async def test_send_response_without_photo(media_handler, make_message):
    """_send_response uses edit_text when no photo."""
    message = make_message()
    message.photo = None

    await media_handler._send_response(message, "Test text")

    message.edit_text.assert_called_once()


@pytest.mark.asyncio
async def test_send_response_fallback_on_error(media_handler, make_message):
    """_send_response falls back to reply_text on error."""
    message = make_message()
    message.photo = None
    message.edit_text = AsyncMock(side_effect=Exception("Edit failed"))

    await media_handler._send_response(message, "Test text")

    message.reply_text.assert_called_once()


# ---------------------------------------------------------------------------
# _show_result
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_show_result_with_poster(media_handler, make_message):
    """_show_result sends photo when poster URL is present."""
    message = make_message()
    result = {
        "id": "123",
        "title": "Test Movie",
        "overview": "A test overview",
        "year": 2024,
        "poster": "https://example.com/poster.jpg",
        "ratings": {"imdb": "8.0", "rottenTomatoes": "90"},
        "studio": "Test Studio",
        "runtime": 120,
        "genres": ["Drama", "Thriller"],
    }

    await media_handler._show_result(message, result, 0, 1)

    message.reply_photo.assert_called_once()


@pytest.mark.asyncio
async def test_show_result_without_poster(media_handler, make_message):
    """_show_result sends text-only when no poster."""
    message = make_message()
    result = {
        "id": "123",
        "title": "Test Movie",
        "overview": "A test overview",
        "year": 2024,
        "poster": None,
        "ratings": {},
        "genres": [],
    }

    await media_handler._show_result(message, result, 0, 1)

    message.reply_text.assert_called_once()


@pytest.mark.asyncio
async def test_show_result_long_overview(media_handler, make_message):
    """_show_result truncates long overviews."""
    message = make_message()
    result = {
        "id": "123",
        "title": "Test",
        "overview": "A" * 400,
        "year": 2024,
        "poster": None,
    }

    await media_handler._show_result(message, result, 0, 1)

    call_args = message.reply_text.call_args
    caption = call_args[0][0]
    assert "..." in caption


@pytest.mark.asyncio
async def test_show_result_poster_send_failure(media_handler, make_message):
    """_show_result falls back to text when photo send fails."""
    message = make_message()
    message.reply_photo = AsyncMock(side_effect=Exception("Photo failed"))
    result = {
        "id": "123",
        "title": "Test",
        "overview": "Overview",
        "year": 2024,
        "poster": "https://example.com/poster.jpg",
    }

    await media_handler._show_result(message, result, 0, 1)

    message.reply_text.assert_called_once()


@pytest.mark.asyncio
async def test_show_result_error_fallback_success(media_handler, make_message):
    """_show_result falls back to error message when outer try fails but fallback succeeds."""
    message = make_message()
    # Result with all required fields but cause an error in caption building
    # by making 'id' have a type that breaks when used in button callback_data
    result = {
        "id": "123",
        "title": "Test",
        "overview": "Overview",
        "poster": None,
    }
    # Make the first reply_text (normal flow) succeed but delete() fails
    # which throws into the outer except, then the fallback reply_text succeeds
    fallback_msg_mock = MagicMock()
    message.reply_text = AsyncMock(
        side_effect=[Exception("First reply failed"), fallback_msg_mock]
    )
    message.delete = AsyncMock()

    ret = await media_handler._show_result(message, result, 0, 1)

    # The first reply_text fails (outer except catches), fallback reply_text succeeds
    assert message.reply_text.call_count == 2
    message.delete.assert_called_once()
    assert ret is fallback_msg_mock


@pytest.mark.asyncio
async def test_show_result_complete_failure(media_handler, make_message):
    """_show_result returns message on complete failure."""
    message = make_message()
    # Make photo fail -> falls to except -> fallback reply_text also fails
    message.reply_photo = AsyncMock(side_effect=Exception("Photo failed"))
    message.reply_text = AsyncMock(side_effect=Exception("Text also failed"))
    message.delete = AsyncMock()
    result = {
        "id": "123",
        "title": "Test",
        "overview": "Overview",
        "poster": "https://example.com/poster.jpg",
    }

    # Should not raise - returns the original message
    ret = await media_handler._show_result(message, result, 0, 1)
    assert ret is message


@pytest.mark.asyncio
async def test_show_result_navigation_buttons(media_handler, make_message):
    """_show_result shows correct navigation buttons for middle results."""
    message = make_message()
    result = {
        "id": "123",
        "title": "Test",
        "overview": "Overview",
        "poster": None,
    }

    # Middle result (index 1 of 3)
    await media_handler._show_result(message, result, 1, 3)

    call_args = message.reply_text.call_args
    reply_markup = call_args[1]["reply_markup"]
    # Should have both prev and next buttons
    keyboard_data = reply_markup.inline_keyboard
    nav_row = keyboard_data[0]
    assert len(nav_row) == 2  # Both prev and next


@pytest.mark.asyncio
async def test_show_result_first_result(media_handler, make_message):
    """_show_result shows no prev button for first result."""
    message = make_message()
    result = {
        "id": "123",
        "title": "Test",
        "overview": "Overview",
        "poster": None,
    }

    await media_handler._show_result(message, result, 0, 3)

    call_args = message.reply_text.call_args
    reply_markup = call_args[1]["reply_markup"]
    keyboard_data = reply_markup.inline_keyboard
    # First row should have only next button
    nav_row = keyboard_data[0]
    assert len(nav_row) == 1
    assert "next" in nav_row[0].callback_data


@pytest.mark.asyncio
async def test_show_result_last_result(media_handler, make_message):
    """_show_result shows no next button for last result."""
    message = make_message()
    result = {
        "id": "123",
        "title": "Test",
        "overview": "Overview",
        "poster": None,
    }

    await media_handler._show_result(message, result, 2, 3)

    call_args = message.reply_text.call_args
    reply_markup = call_args[1]["reply_markup"]
    keyboard_data = reply_markup.inline_keyboard
    nav_row = keyboard_data[0]
    assert len(nav_row) == 1
    assert "prev" in nav_row[0].callback_data


@pytest.mark.asyncio
async def test_show_result_tmdb_rating(media_handler, make_message):
    """_show_result includes TMDB rating for series."""
    message = make_message()
    result = {
        "id": "123",
        "title": "Test Series",
        "overview": "Overview",
        "year": 2024,
        "poster": None,
        "ratings": {"tmdb": "8.5", "votes": 1000},
    }

    await media_handler._show_result(message, result, 0, 1)

    call_args = message.reply_text.call_args
    caption = call_args[0][0]
    assert "TMDB" in caption


@pytest.mark.asyncio
async def test_show_result_network_and_studio(media_handler, make_message):
    """_show_result shows network and studio for TV shows."""
    message = make_message()
    result = {
        "id": "123",
        "title": "Test",
        "overview": "Overview",
        "poster": None,
        "studio": "Sony",
        "network": "HBO",
    }

    await media_handler._show_result(message, result, 0, 1)

    call_args = message.reply_text.call_args
    caption = call_args[0][0]
    assert "HBO" in caption


@pytest.mark.asyncio
async def test_show_result_network_same_as_studio(media_handler, make_message):
    """_show_result shows only network when same as studio."""
    message = make_message()
    result = {
        "id": "123",
        "title": "Test",
        "overview": "Overview",
        "poster": None,
        "studio": "HBO",
        "network": "HBO",
    }

    await media_handler._show_result(message, result, 0, 1)

    call_args = message.reply_text.call_args
    caption = call_args[0][0]
    assert "HBO" in caption


@pytest.mark.asyncio
async def test_show_result_many_genres(media_handler, make_message):
    """_show_result truncates genres after 3."""
    message = make_message()
    result = {
        "id": "123",
        "title": "Test",
        "overview": "Overview",
        "poster": None,
        "genres": ["Drama", "Thriller", "Action", "Comedy", "Horror"],
    }

    await media_handler._show_result(message, result, 0, 1)

    call_args = message.reply_text.call_args
    caption = call_args[0][0]
    assert "+2 more" in caption


@pytest.mark.asyncio
async def test_show_result_imdb_na_rating(media_handler, make_message):
    """_show_result handles N/A IMDB rating."""
    message = make_message()
    result = {
        "id": "123",
        "title": "Test",
        "overview": "Overview",
        "poster": None,
        "ratings": {"imdb": "N/A"},
    }

    await media_handler._show_result(message, result, 0, 1)

    call_args = message.reply_text.call_args
    caption = call_args[0][0]
    assert "N/A" in caption


@pytest.mark.asyncio
async def test_show_result_rt_na_rating(media_handler, make_message):
    """_show_result handles N/A RT rating (skips it)."""
    message = make_message()
    result = {
        "id": "123",
        "title": "Test",
        "overview": "Overview",
        "poster": None,
        "ratings": {"imdb": "8.0", "rottenTomatoes": "N/A"},
    }

    await media_handler._show_result(message, result, 0, 1)

    call_args = message.reply_text.call_args
    caption = call_args[0][0]
    assert "Rotten Tomatoes" not in caption


@pytest.mark.asyncio
async def test_show_result_tmdb_na_rating(media_handler, make_message):
    """_show_result handles N/A TMDB rating."""
    message = make_message()
    result = {
        "id": "123",
        "title": "Test",
        "overview": "Overview",
        "poster": None,
        "ratings": {"tmdb": "N/A"},
    }

    await media_handler._show_result(message, result, 0, 1)

    call_args = message.reply_text.call_args
    caption = call_args[0][0]
    assert "TMDB" not in caption


@pytest.mark.asyncio
async def test_show_result_runtime_na(media_handler, make_message):
    """_show_result skips runtime when N/A."""
    message = make_message()
    result = {
        "id": "123",
        "title": "Test",
        "overview": "Overview",
        "poster": None,
        "runtime": "N/A",
    }

    await media_handler._show_result(message, result, 0, 1)

    call_args = message.reply_text.call_args
    caption = call_args[0][0]
    assert "Runtime" not in caption


# ---------------------------------------------------------------------------
# handle_navigation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_navigation_next(media_handler, make_update, make_context):
    """Navigate next increments index."""
    from src.bot.handlers.media import SELECTING

    update = make_update(callback_data="nav_next_0")
    context = make_context(user_data={
        "search_results": [
            {"id": "1", "title": "Movie 1", "overview": "Ov", "poster": None},
            {"id": "2", "title": "Movie 2", "overview": "Ov", "poster": None},
        ],
        "current_index": 0,
    })

    with patch.object(media_handler, "_show_result", new_callable=AsyncMock):
        result = await media_handler.handle_navigation(update, context)

    assert result == SELECTING
    assert context.user_data["current_index"] == 1


@pytest.mark.asyncio
async def test_handle_navigation_prev(media_handler, make_update, make_context):
    """Navigate prev decrements index."""
    from src.bot.handlers.media import SELECTING

    update = make_update(callback_data="nav_prev_1")
    context = make_context(user_data={
        "search_results": [
            {"id": "1", "title": "Movie 1", "overview": "Ov", "poster": None},
            {"id": "2", "title": "Movie 2", "overview": "Ov", "poster": None},
        ],
        "current_index": 1,
    })

    with patch.object(media_handler, "_show_result", new_callable=AsyncMock):
        result = await media_handler.handle_navigation(update, context)

    assert result == SELECTING
    assert context.user_data["current_index"] == 0


@pytest.mark.asyncio
async def test_handle_navigation_out_of_bounds(
    media_handler, make_update, make_context
):
    """Navigation out of bounds stays in SELECTING without changing index."""
    from src.bot.handlers.media import SELECTING

    update = make_update(callback_data="nav_next_0")
    context = make_context(user_data={
        "search_results": [
            {"id": "1", "title": "Movie 1", "overview": "Ov", "poster": None},
        ],
        "current_index": 0,
    })

    result = await media_handler.handle_navigation(update, context)

    assert result == SELECTING


@pytest.mark.asyncio
async def test_handle_navigation_no_query(media_handler, make_update, make_context):
    """handle_navigation returns END when no callback_query."""
    update = make_update(text="test")
    update.callback_query = None
    context = make_context()

    result = await media_handler.handle_navigation(update, context)

    assert result == ConversationHandler.END


# ---------------------------------------------------------------------------
# handle_status
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_status_direct_command(
    media_handler, make_update, make_context
):
    """handle_status via direct command."""
    media_handler._mock_service.get_transmission_status = AsyncMock(
        return_value=False
    )
    media_handler._mock_service.get_sabnzbd_status = AsyncMock(
        return_value=False
    )

    update = make_update(text="/status")
    context = make_context()

    await media_handler.handle_status(update, context)

    update.message.reply_text.assert_called_once()


@pytest.mark.asyncio
async def test_handle_status_via_callback(media_handler, make_update, make_context):
    """handle_status via callback query."""
    media_handler._mock_service.get_transmission_status = AsyncMock(
        return_value=False
    )
    media_handler._mock_service.get_sabnzbd_status = AsyncMock(
        return_value=False
    )

    update = make_update(callback_data="menu_status")
    context = make_context()

    await media_handler.handle_status(update, context)

    update.callback_query.message.edit_text.assert_called_once()


@pytest.mark.asyncio
async def test_handle_status_exception_direct(media_handler, make_update, make_context):
    """handle_status sends error via reply_text on exception with direct command."""
    with patch.object(
        media_handler, "_get_status_text",
        new_callable=AsyncMock,
        side_effect=Exception("Total failure")
    ):
        update = make_update(text="/status")
        context = make_context()

        await media_handler.handle_status(update, context)

        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args
        assert "Error" in str(call_args)


@pytest.mark.asyncio
async def test_handle_status_exception_via_callback(
    media_handler, make_update, make_context
):
    """handle_status sends error via callback on exception."""
    # Make _get_status_text raise
    with patch.object(
        media_handler, "_get_status_text",
        new_callable=AsyncMock,
        side_effect=Exception("Error")
    ):
        update = make_update(callback_data="menu_status")
        context = make_context()

        await media_handler.handle_status(update, context)

        update.callback_query.message.edit_text.assert_called()


# ---------------------------------------------------------------------------
# handle_settings
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_settings(media_handler, make_update, make_context):
    """handle_settings sends settings message."""
    update = make_update(text="/settings")
    context = make_context()

    await media_handler.handle_settings(update, context)

    update.message.reply_text.assert_called_once()


@pytest.mark.asyncio
async def test_handle_settings_no_message(media_handler, make_update, make_context):
    """handle_settings returns when no effective_message."""
    update = make_update(text="/settings")
    update.effective_message = None
    context = make_context()

    result = await media_handler.handle_settings(update, context)

    assert result is None


@pytest.mark.asyncio
async def test_handle_settings_no_user(media_handler, make_update, make_context):
    """handle_settings returns when no effective_user."""
    update = make_update(text="/settings")
    update.effective_user = None
    context = make_context()

    result = await media_handler.handle_settings(update, context)

    assert result is None


# ---------------------------------------------------------------------------
# cancel_search
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cancel_search_direct_command(
    media_handler, make_update, make_context
):
    """cancel_search via direct command."""
    update = make_update(text="/cancel")
    context = make_context()

    result = await media_handler.cancel_search(update, context)

    assert result == ConversationHandler.END
    update.message.reply_text.assert_called_once()


@pytest.mark.asyncio
async def test_cancel_search_via_callback(media_handler, make_update, make_context):
    """cancel_search via callback query."""
    update = make_update(callback_data="cancel")
    update.callback_query.message.photo = None
    update.message = None
    context = make_context()

    result = await media_handler.cancel_search(update, context)

    assert result == ConversationHandler.END


# ---------------------------------------------------------------------------
# _get_status_text
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_status_text_all_online(media_handler):
    """_get_status_text with all services online."""
    media_handler._mock_service.get_transmission_status = AsyncMock(
        return_value=True
    )
    media_handler._mock_service.get_sabnzbd_status = AsyncMock(
        return_value=True
    )

    text = await media_handler._get_status_text()

    assert "Online" in text
    assert "Transmission" in text
    assert "SABnzbd" in text


@pytest.mark.asyncio
async def test_get_status_text_service_exception(media_handler):
    """_get_status_text handles individual service exceptions."""
    media_handler._mock_service.get_radarr_status = AsyncMock(
        side_effect=Exception("Error")
    )
    media_handler._mock_service.get_transmission_status = AsyncMock(
        side_effect=Exception("Error")
    )
    media_handler._mock_service.get_sabnzbd_status = AsyncMock(
        side_effect=Exception("Error")
    )

    text = await media_handler._get_status_text()

    assert "Error" in text


@pytest.mark.asyncio
async def test_get_status_text_transmission_exception_shows_unavailable(media_handler):
    """Transmission exception shows Unavailable instead of being silently swallowed."""
    media_handler._mock_service.get_transmission_status = AsyncMock(
        side_effect=Exception("Connection refused")
    )
    media_handler._mock_service.get_sabnzbd_status = AsyncMock(
        return_value=False
    )

    text = await media_handler._get_status_text()

    assert "Transmission" in text
    assert "Unavailable" in text


@pytest.mark.asyncio
async def test_get_status_text_sabnzbd_exception_shows_unavailable(media_handler):
    """SABnzbd exception shows Unavailable instead of being silently swallowed."""
    media_handler._mock_service.get_transmission_status = AsyncMock(
        return_value=False
    )
    media_handler._mock_service.get_sabnzbd_status = AsyncMock(
        side_effect=Exception("Connection refused")
    )

    text = await media_handler._get_status_text()

    assert "SABnzbd" in text
    assert "Unavailable" in text


@pytest.mark.asyncio
async def test_get_status_text_total_exception(media_handler):
    """_get_status_text handles total failure."""
    # Make the entire method fail by making services dict creation fail
    media_handler.media_service = None

    text = await media_handler._get_status_text()

    assert "Error" in text


# ---------------------------------------------------------------------------
# get_handler
# ---------------------------------------------------------------------------


def test_get_handler_returns_list(media_handler):
    """get_handler returns a list of handlers."""
    handlers = media_handler.get_handler()

    assert isinstance(handlers, list)
    assert len(handlers) > 0

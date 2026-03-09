"""
Tests for src/bot/handlers/calendar.py - CalendarHandler.

CalendarHandler owns /upcoming and cal_* callbacks. show_upcoming and
handle_calendar_action are decorated with @require_auth.
"""

import pytest
from unittest.mock import AsyncMock, patch


# ---------------------------------------------------------------------------
# Sample calendar items for reuse
# ---------------------------------------------------------------------------

SAMPLE_MOVIE = {
    "type": "movie", "title": "Test Movie", "series_title": None,
    "date": "2026-03-10", "date_label": "Cinema", "year": 2026,
    "season": None, "episode": None, "in_library": False,
    "media_id": "12345", "internal_id": None,
}

SAMPLE_EPISODE = {
    "type": "episode", "title": "Test Episode",
    "series_title": "Test Series", "date": "2026-03-12",
    "date_label": "Airing", "year": None, "season": 1,
    "episode": 5, "in_library": True, "media_id": "67890",
    "internal_id": 42,
}


# ---------------------------------------------------------------------------
# show_upcoming
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_show_upcoming_with_results(
    calendar_handler, make_update, make_context
):
    """show_upcoming sends message with calendar text and items keyboard."""
    items = [SAMPLE_MOVIE, SAMPLE_EPISODE]
    calendar_handler._mock_service.get_upcoming = AsyncMock(return_value=items)
    update = make_update(text="/upcoming")
    context = make_context()

    await calendar_handler.show_upcoming(update, context)

    calendar_handler._mock_service.get_upcoming.assert_awaited_once_with(7)
    update.message.reply_text.assert_called_once()
    call_args = update.message.reply_text.call_args
    assert "CalendarTitle" in call_args[0][0]
    assert call_args[1]["reply_markup"] == \
        calendar_handler._mock_items_kbd.return_value
    assert context.user_data["cal_items"] == items
    assert context.user_data["cal_days"] == 7


@pytest.mark.asyncio
async def test_show_upcoming_empty_results(
    calendar_handler, make_update, make_context
):
    """show_upcoming sends 'no upcoming' message with period keyboard."""
    calendar_handler._mock_service.get_upcoming = AsyncMock(return_value=[])
    update = make_update(text="/upcoming")
    context = make_context()

    await calendar_handler.show_upcoming(update, context)

    update.message.reply_text.assert_called_once()
    call_args = update.message.reply_text.call_args
    assert "CalendarEmpty" in call_args[0][0]
    assert call_args[1]["reply_markup"] == \
        calendar_handler._mock_cal_kbd.return_value


@pytest.mark.asyncio
async def test_show_upcoming_via_callback(
    calendar_handler, make_update, make_context
):
    """show_upcoming edits message when invoked via callback query."""
    items = [SAMPLE_MOVIE]
    calendar_handler._mock_service.get_upcoming = AsyncMock(return_value=items)
    update = make_update(callback_data="menu_upcoming")
    context = make_context()

    await calendar_handler.show_upcoming(update, context)

    update.callback_query.message.edit_text.assert_called_once()
    call_args = update.callback_query.message.edit_text.call_args
    assert "CalendarTitle" in call_args[0][0]


@pytest.mark.asyncio
async def test_show_upcoming_no_user(
    calendar_handler, make_update, make_context
):
    """show_upcoming returns None when effective_user is None."""
    update = make_update(text="/upcoming")
    update.effective_user = None
    context = make_context()

    result = await calendar_handler.show_upcoming(update, context)
    assert result is None


# ---------------------------------------------------------------------------
# handle_calendar_action — period change
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_period_change(
    calendar_handler, make_update, make_context
):
    """cal_period_14 changes period, re-fetches, and edits message."""
    items = [SAMPLE_MOVIE]
    calendar_handler._mock_service.get_upcoming = AsyncMock(return_value=items)
    update = make_update(callback_data="cal_period_14")
    context = make_context(user_data={"cal_days": 7, "cal_items": []})

    await calendar_handler.handle_calendar_action(update, context)

    calendar_handler._mock_service.get_upcoming.assert_awaited_once_with(14)
    assert context.user_data["cal_days"] == 14
    assert context.user_data["cal_items"] == items
    update.callback_query.message.edit_text.assert_called_once()
    update.callback_query.answer.assert_called_once()


# ---------------------------------------------------------------------------
# handle_calendar_action — pagination
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pagination(
    calendar_handler, make_update, make_context
):
    """cal_page_1 shows second page from cached items without re-fetching."""
    items = [
        {**SAMPLE_MOVIE, "title": f"Movie {i}", "media_id": str(i)}
        for i in range(8)
    ]
    update = make_update(callback_data="cal_page_1")
    context = make_context(user_data={"cal_days": 7, "cal_items": items})

    await calendar_handler.handle_calendar_action(update, context)

    calendar_handler._mock_service.get_upcoming.assert_not_awaited()
    update.callback_query.message.edit_text.assert_called_once()
    update.callback_query.answer.assert_called_once()
    # Verify keyboard was built with page=1
    calendar_handler._mock_items_kbd.assert_called_once()
    kbd_call = calendar_handler._mock_items_kbd.call_args
    assert kbd_call[0][1] == 1  # page argument


# ---------------------------------------------------------------------------
# handle_calendar_action — refresh
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_refresh(
    calendar_handler, make_update, make_context
):
    """cal_refresh clears cache and re-fetches calendar data."""
    new_items = [SAMPLE_MOVIE]
    calendar_handler._mock_service.get_upcoming = AsyncMock(
        return_value=new_items
    )
    update = make_update(callback_data="cal_refresh")
    context = make_context(user_data={
        "cal_days": 7, "cal_items": [{"old": "data"}]
    })

    await calendar_handler.handle_calendar_action(update, context)

    calendar_handler._mock_service.get_upcoming.assert_awaited_once_with(7)
    assert context.user_data["cal_items"] == new_items
    update.callback_query.message.edit_text.assert_called_once()
    update.callback_query.answer.assert_called_once()


# ---------------------------------------------------------------------------
# handle_calendar_action — back
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_back(
    calendar_handler, make_update, make_context
):
    """cal_back returns to main menu."""
    update = make_update(callback_data="cal_back")
    context = make_context(user_data={"cal_days": 7, "cal_items": []})

    await calendar_handler.handle_calendar_action(update, context)

    update.callback_query.message.edit_text.assert_called_once()
    call_args = update.callback_query.message.edit_text.call_args
    assert call_args[1]["reply_markup"] == \
        calendar_handler._mock_menu_kbd.return_value
    update.callback_query.answer.assert_called_once()


# ---------------------------------------------------------------------------
# handle_calendar_action — add movie
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_add_movie_success(
    calendar_handler, make_update, make_context
):
    """cal_add_movie_12345 calls add_movie_with_profile and shows success toast."""
    update = make_update(callback_data="cal_add_movie_12345")
    context = make_context(user_data={"cal_days": 7, "cal_items": []})

    await calendar_handler.handle_calendar_action(update, context)

    calendar_handler._mock_service.radarr.get_root_folders.assert_awaited_once()
    calendar_handler._mock_service.radarr.get_quality_profiles.assert_awaited_once()
    calendar_handler._mock_service.add_movie_with_profile.assert_awaited_once_with(
        "12345", 1, "/movies"
    )
    update.callback_query.answer.assert_called_once()
    assert "CalendarAddSuccess" in str(update.callback_query.answer.call_args)


@pytest.mark.asyncio
async def test_add_movie_failure(
    calendar_handler, make_update, make_context
):
    """cal_add_movie shows error toast when add fails."""
    calendar_handler._mock_service.add_movie_with_profile = AsyncMock(
        return_value=(False, "Already exists")
    )
    update = make_update(callback_data="cal_add_movie_12345")
    context = make_context(user_data={"cal_days": 7, "cal_items": []})

    await calendar_handler.handle_calendar_action(update, context)

    update.callback_query.answer.assert_called_once()
    assert "CalendarAddFailed" in str(update.callback_query.answer.call_args)


# ---------------------------------------------------------------------------
# handle_calendar_action — add episode (adds series by tvdbId)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_add_episode_success(
    calendar_handler, make_update, make_context
):
    """cal_add_episode_67890 calls add_series_with_profile, shows success toast."""
    update = make_update(callback_data="cal_add_episode_67890")
    context = make_context(user_data={"cal_days": 7, "cal_items": []})

    await calendar_handler.handle_calendar_action(update, context)

    calendar_handler._mock_service.sonarr.get_root_folders.assert_awaited_once()
    calendar_handler._mock_service.sonarr.get_quality_profiles.assert_awaited_once()
    calendar_handler._mock_service.add_series_with_profile.assert_awaited_once_with(
        "67890", 1, "/tv"
    )
    update.callback_query.answer.assert_called_once()
    assert "CalendarAddSuccess" in str(update.callback_query.answer.call_args)


# ---------------------------------------------------------------------------
# handle_calendar_action — add exception
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_add_movie_exception(
    calendar_handler, make_update, make_context
):
    """cal_add_movie shows error toast when add raises exception."""
    calendar_handler._mock_service.add_movie_with_profile = AsyncMock(
        side_effect=Exception("Connection failed")
    )
    update = make_update(callback_data="cal_add_movie_12345")
    context = make_context(user_data={"cal_days": 7, "cal_items": []})

    await calendar_handler.handle_calendar_action(update, context)

    update.callback_query.answer.assert_called_once()
    assert "CalendarAddFailed" in str(update.callback_query.answer.call_args)


# ---------------------------------------------------------------------------
# handle_calendar_action — unauthenticated
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unauthenticated_user(
    make_update, make_context, mock_media_service, mock_translation_service
):
    """show_upcoming rejects unauthenticated users via @require_auth."""
    with (
        patch("src.bot.handlers.calendar.MediaService") as mock_ms_class,
        patch("src.bot.handlers.calendar.TranslationService") as mock_ts_class,
        patch("src.bot.handlers.calendar.get_calendar_keyboard"),
        patch("src.bot.handlers.calendar.get_calendar_items_keyboard"),
        patch("src.bot.handlers.calendar.get_main_menu_keyboard"),
    ):
        mock_ts_class.return_value = mock_translation_service
        mock_ms_class.return_value = mock_media_service

        from src.bot.handlers.calendar import CalendarHandler
        from src.bot.handlers.auth import AuthHandler

        AuthHandler._authenticated_users = set()
        handler = CalendarHandler()
        update = make_update(text="/upcoming")
        context = make_context()

        result = await handler.show_upcoming(update, context)
        assert result is None


# ---------------------------------------------------------------------------
# handle_calendar_action — no callback / edge cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_no_callback(
    calendar_handler, make_update, make_context
):
    """handle_calendar_action returns None when no callback query."""
    update = make_update(text="/upcoming")
    context = make_context()

    result = await calendar_handler.handle_calendar_action(update, context)
    assert result is None


@pytest.mark.asyncio
async def test_handle_unknown_cal_action(
    calendar_handler, make_update, make_context
):
    """Unknown cal_ action answers query without error."""
    update = make_update(callback_data="cal_noop")
    context = make_context()

    await calendar_handler.handle_calendar_action(update, context)

    update.callback_query.answer.assert_called_once()


@pytest.mark.asyncio
async def test_add_unknown_media_type(
    calendar_handler, make_update, make_context
):
    """cal_add with unknown type answers with error."""
    update = make_update(callback_data="cal_add_unknown_123")
    context = make_context(user_data={"cal_days": 7, "cal_items": []})

    await calendar_handler.handle_calendar_action(update, context)

    update.callback_query.answer.assert_called_once()
    calendar_handler._mock_ts.get_text.assert_any_call("UnknownMediaType")


# ---------------------------------------------------------------------------
# get_handler
# ---------------------------------------------------------------------------


def test_get_handler_returns_list(calendar_handler):
    """get_handler returns a list of handlers."""
    handlers = calendar_handler.get_handler()
    assert isinstance(handlers, list)
    assert len(handlers) >= 2

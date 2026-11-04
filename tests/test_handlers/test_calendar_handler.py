"""
Tests for src/bot/handlers/calendar.py - CalendarHandler.

CalendarHandler owns /upcoming and cal_* callbacks. show_upcoming and
handle_calendar_action are decorated with @require_auth.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Sample calendar items for reuse
# ---------------------------------------------------------------------------

SAMPLE_MOVIE = {
    "type": "movie", "title": "Test Movie", "series_title": None,
    "date": "2026-03-10", "date_label": "Cinema", "year": 2026,
    "season": None, "episode": None,
    "media_id": "12345", "internal_id": None,
}

SAMPLE_EPISODE = {
    "type": "episode", "title": "Test Episode",
    "series_title": "Test Series", "date": "2026-03-12",
    "date_label": "Airing", "year": None, "season": 1,
    "episode": 5, "media_id": "67890",
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
@patch("src.services.rate_limit.TranslationService")
async def test_show_upcoming_refuses_once_modify_limit_is_used_up(
    mock_rl_ts_class, calendar_handler, make_update, make_context
):
    """F063: /upcoming is rate-limited as "modify"."""
    mock_rl_ts_class.return_value.get_text = MagicMock(side_effect=lambda key, **kw: key)
    context = make_context()

    with patch("src.services.rate_limit.config") as mock_cfg:
        mock_cfg.get.return_value = {
            "enable": True,
            "limits": {"modify": {"maxRequests": 1, "windowSeconds": 60}},
        }
        await calendar_handler.show_upcoming(make_update(text="/upcoming"), context)
        refused = make_update(text="/upcoming")
        await calendar_handler.show_upcoming(refused, context)

    calendar_handler._mock_service.get_upcoming.assert_awaited_once_with(7)
    refused.message.reply_text.assert_called_once_with("RateLimitExceeded")


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
async def test_refresh_unchanged_message(
    calendar_handler, make_update, make_context, unchanged_edit
):
    """cal_refresh answers first and ignores an unchanged message."""
    calendar_handler._mock_service.get_upcoming = AsyncMock(return_value=[])
    update = make_update(callback_data="cal_refresh")
    calls = unchanged_edit(update.callback_query)
    context = make_context(user_data={"cal_days": 7})

    await calendar_handler.handle_calendar_action(update, context)

    assert calls == ["answer", "edit"]


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
# handle_calendar_action — no add path
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("data", [
    "cal_add_movie_12345", "cal_add_episode_67890", "cal_add_unknown_123",
])
@pytest.mark.asyncio
async def test_cal_add_callback_is_ignored(
    calendar_handler, make_update, make_context, data
):
    """The calendar has no add path: cal_add_* only answers the query."""
    update = make_update(callback_data=data)
    context = make_context(user_data={"cal_days": 7, "cal_items": []})

    await calendar_handler.handle_calendar_action(update, context)

    update.callback_query.answer.assert_called_once_with()
    calendar_handler._mock_service.add_movie_with_profile.assert_not_awaited()
    calendar_handler._mock_service.add_series_with_profile.assert_not_awaited()


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


# ---------------------------------------------------------------------------
# get_handler
# ---------------------------------------------------------------------------


def test_get_handler_returns_list(calendar_handler):
    """get_handler returns a list of handlers."""
    handlers = calendar_handler.get_handler()
    assert isinstance(handlers, list)
    assert len(handlers) >= 2

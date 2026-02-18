"""
Tests for src/bot/handlers/library.py - LibraryHandler.

LibraryHandler.__init__ creates MediaService() and TranslationService().
Command handlers (allMovies, allSeries, allMusic) fetch library items and
display them as paginated text with inline keyboard navigation.
"""

import pytest
from unittest.mock import AsyncMock


# ---------------------------------------------------------------------------
# get_handler
# ---------------------------------------------------------------------------


def test_get_handler_returns_list(library_handler):
    """get_handler returns a list of handlers."""
    handlers = library_handler.get_handler()

    assert isinstance(handlers, list)
    assert len(handlers) > 0


# ---------------------------------------------------------------------------
# Command success tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("command,handler_method,service_method", [
    ("allMovies", "handle_all_movies", "get_movies"),
    ("allSeries", "handle_all_series", "get_series"),
    ("allMusic", "handle_all_music", "get_music"),
])
@pytest.mark.asyncio
async def test_handle_command_success(
    library_handler, make_update, make_context,
    command, handler_method, service_method
):
    """Command fetches items and replies with paginated text."""
    items = [
        {"id": "1", "title": "Alpha"},
        {"id": "2", "title": "Beta"},
        {"id": "3", "title": "Gamma"},
    ]
    setattr(
        library_handler._mock_service, service_method,
        AsyncMock(return_value=items)
    )

    update = make_update(text=f"/{command}")
    context = make_context()

    handler_fn = getattr(library_handler, handler_method)
    await handler_fn(update, context)

    update.message.reply_text.assert_called_once()
    call_args = update.message.reply_text.call_args
    text = call_args[0][0] if call_args[0] else call_args[1].get("text", "")
    # Items should appear alphabetically in the message
    assert "Alpha" in text
    assert "Beta" in text
    assert "Gamma" in text


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_not_authenticated(
    library_handler, make_update, make_context
):
    """Command rejects unauthenticated users via @require_auth."""
    from src.bot.handlers.auth import AuthHandler

    AuthHandler._authenticated_users = set()

    update = make_update(text="/allMovies")
    context = make_context()

    result = await library_handler.handle_all_movies(update, context)

    assert result is None


@pytest.mark.asyncio
async def test_handle_no_message(
    library_handler, make_update, make_context
):
    """Command returns early when no effective_message."""
    update = make_update(text="/allMovies")
    update.effective_message = None
    context = make_context()

    result = await library_handler.handle_all_movies(update, context)

    assert result is None


@pytest.mark.asyncio
async def test_handle_service_not_configured(
    library_handler, make_update, make_context
):
    """Service not configured (ValueError) shows friendly message."""
    library_handler._mock_service.get_movies = AsyncMock(
        side_effect=ValueError("Radarr is not enabled or configured")
    )

    update = make_update(text="/allMovies")
    context = make_context()

    await library_handler.handle_all_movies(update, context)

    update.message.reply_text.assert_called_once()
    call_args = update.message.reply_text.call_args
    assert "LibraryNotEnabled" in str(call_args)


@pytest.mark.asyncio
async def test_handle_empty_library(
    library_handler, make_update, make_context
):
    """Empty library shows 'no items' message."""
    library_handler._mock_service.get_movies = AsyncMock(return_value=[])

    update = make_update(text="/allMovies")
    context = make_context()

    await library_handler.handle_all_movies(update, context)

    update.message.reply_text.assert_called_once()
    call_args = update.message.reply_text.call_args
    assert "LibraryEmpty" in str(call_args)


@pytest.mark.asyncio
async def test_handle_api_error(
    library_handler, make_update, make_context
):
    """Generic API error shows error message."""
    library_handler._mock_service.get_movies = AsyncMock(
        side_effect=Exception("Connection refused")
    )

    update = make_update(text="/allMovies")
    context = make_context()

    await library_handler.handle_all_movies(update, context)

    update.message.reply_text.assert_called_once()
    call_args = update.message.reply_text.call_args
    assert "LibraryError" in str(call_args)


# ---------------------------------------------------------------------------
# Pagination (_build_page_message)
# ---------------------------------------------------------------------------


def test_pagination_single_page(library_handler):
    """Single page (5 items) has no navigation buttons."""
    items = [{"id": str(i), "title": f"Item {i}"} for i in range(5)]
    text, reply_markup = library_handler._build_page_message(items, 0, "m")

    assert "Item 0" in text
    assert "Item 4" in text
    assert reply_markup is None


def test_pagination_first_page_next_only(library_handler):
    """First page of multi-page list has only Next button."""
    items = [{"id": str(i), "title": f"Item {i}"} for i in range(25)]
    text, reply_markup = library_handler._build_page_message(items, 0, "m")

    assert "Page 1/" in text
    buttons = reply_markup.inline_keyboard[0]
    assert len(buttons) == 1
    assert "Next" in buttons[0].text
    assert buttons[0].callback_data == "lib_m_1"


def test_pagination_middle_page_both_buttons(library_handler):
    """Middle page has both Previous and Next buttons."""
    items = [{"id": str(i), "title": f"Item {i}"} for i in range(25)]
    text, reply_markup = library_handler._build_page_message(items, 1, "m")

    assert "Page 2/" in text
    buttons = reply_markup.inline_keyboard[0]
    assert len(buttons) == 2
    assert "Previous" in buttons[0].text
    assert buttons[0].callback_data == "lib_m_0"
    assert "Next" in buttons[1].text
    assert buttons[1].callback_data == "lib_m_2"


def test_pagination_last_page_previous_only(library_handler):
    """Last page has only Previous button."""
    items = [{"id": str(i), "title": f"Item {i}"} for i in range(25)]
    text, reply_markup = library_handler._build_page_message(items, 2, "m")

    assert "Page 3/3" in text
    buttons = reply_markup.inline_keyboard[0]
    assert len(buttons) == 1
    assert "Previous" in buttons[0].text
    assert buttons[0].callback_data == "lib_m_1"


def test_sorting_alphabetical(library_handler):
    """Items passed in random order are numbered correctly when pre-sorted."""
    # Note: _fetch_and_show sorts before calling _build_page_message,
    # so we test that sorted input produces correct numbering.
    items = [
        {"id": "3", "title": "Zulu"},
        {"id": "1", "title": "Alpha"},
        {"id": "2", "title": "Mike"},
    ]
    sorted_items = sorted(items, key=lambda x: x["title"].lower())
    text, _ = library_handler._build_page_message(sorted_items, 0, "m")

    # Verify alphabetical ordering in output
    alpha_pos = text.index("Alpha")
    mike_pos = text.index("Mike")
    zulu_pos = text.index("Zulu")
    assert alpha_pos < mike_pos < zulu_pos


# ---------------------------------------------------------------------------
# Navigation callback (handle_page_navigation)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_navigation_callback(
    library_handler, make_update, make_context
):
    """lib_m_1 callback edits message with page 1 content."""
    items = [{"id": str(i), "title": f"Item {i:02d}"} for i in range(25)]
    update = make_update(callback_data="lib_m_1")
    context = make_context(user_data={"library_m": items})

    await library_handler.handle_page_navigation(update, context)

    update.callback_query.answer.assert_called_once()
    update.callback_query.message.edit_text.assert_called_once()
    call_args = update.callback_query.message.edit_text.call_args
    text = call_args[0][0] if call_args[0] else call_args[1].get("text", "")
    # Page 2 should show items 11-20
    assert "Item 10" in text
    assert "Page 2/" in text


@pytest.mark.asyncio
async def test_navigation_expired_session(
    library_handler, make_update, make_context
):
    """Expired session (no cached data) shows error message."""
    update = make_update(callback_data="lib_m_1")
    context = make_context(user_data={})

    await library_handler.handle_page_navigation(update, context)

    update.callback_query.answer.assert_called_once()
    update.callback_query.message.edit_text.assert_called_once()
    call_args = update.callback_query.message.edit_text.call_args
    assert "LibraryExpired" in str(call_args)


@pytest.mark.asyncio
async def test_navigation_no_callback_query(
    library_handler, make_update, make_context
):
    """handle_page_navigation returns when no callback_query."""
    update = make_update(text="/test")
    update.callback_query = None
    context = make_context()

    result = await library_handler.handle_page_navigation(update, context)

    assert result is None


@pytest.mark.asyncio
async def test_navigation_malformed_callback_data(
    library_handler, make_update, make_context
):
    """Malformed callback data (wrong number of parts) returns early."""
    update = make_update(callback_data="lib_m")
    context = make_context()

    result = await library_handler.handle_page_navigation(update, context)

    assert result is None


@pytest.mark.asyncio
async def test_navigation_non_integer_page(
    library_handler, make_update, make_context
):
    """Non-integer page number returns early."""
    update = make_update(callback_data="lib_m_abc")
    context = make_context()

    result = await library_handler.handle_page_navigation(update, context)

    assert result is None

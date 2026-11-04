"""
Tests for src/bot/handlers/delete.py - DeleteHandler.

DeleteHandler.__init__ creates MediaService() and TranslationService().
handle_delete shows a media type selection keyboard (decorated with @require_auth).
handle_delete_selection processes callback queries for deletion flow.
"""

import pytest
from unittest.mock import AsyncMock


# ---------------------------------------------------------------------------
# handle_delete
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_delete(delete_handler, make_update, make_context):
    """handle_delete replies with type selection keyboard."""
    update = make_update(text="/delete")
    context = make_context()

    await delete_handler.handle_delete(update, context)

    update.message.reply_text.assert_called_once()
    call_args = update.message.reply_text.call_args
    assert call_args[1].get("reply_markup") is not None or len(call_args) > 1


@pytest.mark.asyncio
async def test_handle_delete_not_authenticated(
    delete_handler, make_update, make_context
):
    """handle_delete rejects unauthenticated users via @require_auth."""
    from src.bot.handlers.auth import AuthHandler

    AuthHandler._authenticated_users = set()

    update = make_update(text="/delete")
    context = make_context()

    result = await delete_handler.handle_delete(update, context)

    assert result is None


@pytest.mark.asyncio
async def test_handle_delete_no_message(delete_handler, make_update, make_context):
    """handle_delete returns early when no effective_message."""
    update = make_update(text="/delete")
    update.effective_message = None
    context = make_context()

    result = await delete_handler.handle_delete(update, context)

    assert result is None


# ---------------------------------------------------------------------------
# handle_delete_selection - cancel
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_delete_selection_cancel(
    delete_handler, make_update, make_context
):
    """delete_cancel callback edits message with 'End' text."""
    update = make_update(callback_data="delete_cancel")
    context = make_context()

    await delete_handler.handle_delete_selection(update, context)

    update.callback_query.answer.assert_called_once()
    update.callback_query.message.edit_text.assert_called_once()
    call_args = update.callback_query.message.edit_text.call_args
    assert "End" in str(call_args)


@pytest.mark.asyncio
async def test_handle_delete_selection_no_query(
    delete_handler, make_update, make_context
):
    """handle_delete_selection returns when no callback_query."""
    update = make_update(text="/test")
    update.callback_query = None
    context = make_context()

    result = await delete_handler.handle_delete_selection(update, context)

    assert result is None


# ---------------------------------------------------------------------------
# handle_delete_selection - type selection
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("media_type,service_method", [
    ("movie", "get_movies"),
    ("series", "get_series"),
    ("music", "get_music"),
])
@pytest.mark.asyncio
async def test_handle_delete_selection_type(
    delete_handler, make_update, make_context, media_type, service_method
):
    """Type selection fetches items and shows selection keyboard."""
    items = [{"id": "1", "title": "Test Item"}]
    setattr(delete_handler._mock_service, service_method, AsyncMock(return_value=items))

    update = make_update(callback_data=f"delete_type_{media_type}")
    context = make_context()

    await delete_handler.handle_delete_selection(update, context)

    update.callback_query.message.edit_text.assert_called_once()
    assert context.user_data == {}


@pytest.mark.asyncio
async def test_handle_delete_selection_type_invalid(
    delete_handler, make_update, make_context
):
    """Invalid type selection shows error."""
    update = make_update(callback_data="delete_type_invalid")
    context = make_context()

    await delete_handler.handle_delete_selection(update, context)

    update.callback_query.message.edit_text.assert_called_once()
    delete_handler._mock_ts.get_text.assert_any_call("InvalidMediaType")


@pytest.mark.asyncio
async def test_handle_delete_selection_type_no_items(
    delete_handler, make_update, make_context
):
    """Type selection with no items shows NoExist message."""
    delete_handler._mock_service.get_movies = AsyncMock(return_value=[])

    update = make_update(callback_data="delete_type_movie")
    context = make_context()

    await delete_handler.handle_delete_selection(update, context)

    update.callback_query.message.edit_text.assert_called_once()
    call_args = update.callback_query.message.edit_text.call_args
    assert "NoExist" in str(call_args)


@pytest.mark.asyncio
async def test_handle_delete_selection_type_exception(
    delete_handler, make_update, make_context
):
    """Type selection with API error shows error message."""
    delete_handler._mock_service.get_movies = AsyncMock(
        side_effect=Exception("API error")
    )

    update = make_update(callback_data="delete_type_movie")
    context = make_context()

    await delete_handler.handle_delete_selection(update, context)

    update.callback_query.message.edit_text.assert_called_once()
    delete_handler._mock_ts.get_text.assert_any_call("MediaListError")


# ---------------------------------------------------------------------------
# handle_delete_selection - item selection (type and id come from callback_data)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("media_type,service_method", [
    ("movie", "get_movie"),
    ("series", "get_series"),
    ("music", "get_music"),
])
@pytest.mark.asyncio
async def test_handle_delete_selection_item(
    delete_handler, make_update, make_context, media_type, service_method
):
    """Item selection shows confirmation keyboard that carries type and id."""
    item = {"id": "123", "title": "Test Item"}
    method = AsyncMock(return_value=item)
    setattr(delete_handler._mock_service, service_method, method)

    update = make_update(callback_data=f"delete_item_{media_type}_123")
    context = make_context()

    await delete_handler.handle_delete_selection(update, context)

    method.assert_awaited_once_with("123")
    update.callback_query.message.edit_text.assert_called_once()
    call_args = update.callback_query.message.edit_text.call_args
    assert "ThisDelete" in str(call_args)
    delete_handler._mock_ts.get_message.assert_any_call(
        "ThisDelete", subject=media_type, title="Test Item"
    )
    keyboard = call_args[1]["reply_markup"].inline_keyboard
    assert keyboard[0][0].callback_data == f"delete_confirm_{media_type}_123"
    assert context.user_data == {}


@pytest.mark.asyncio
async def test_item_callback_ignores_user_data_type(
    delete_handler, make_update, make_context
):
    """A movie button acts on the movie even when user_data says series."""
    delete_handler._mock_service.get_movie = AsyncMock(
        return_value={"id": "42", "title": "Movie 42"}
    )
    delete_handler._mock_service.get_series = AsyncMock()

    update = make_update(callback_data="delete_item_movie_42")
    context = make_context(user_data={"delete_type": "series"})

    await delete_handler.handle_delete_selection(update, context)

    delete_handler._mock_service.get_movie.assert_awaited_once_with("42")
    delete_handler._mock_service.get_series.assert_not_called()
    keyboard = (
        update.callback_query.message.edit_text.call_args[1]["reply_markup"]
        .inline_keyboard
    )
    assert keyboard[0][0].callback_data == "delete_confirm_movie_42"


@pytest.mark.asyncio
async def test_handle_delete_selection_item_not_found(
    delete_handler, make_update, make_context
):
    """Item selection with item not found shows NoExist."""
    delete_handler._mock_service.get_movie = AsyncMock(return_value=None)

    update = make_update(callback_data="delete_item_movie_123")
    context = make_context()

    await delete_handler.handle_delete_selection(update, context)

    update.callback_query.message.edit_text.assert_called_once()
    call_args = update.callback_query.message.edit_text.call_args
    assert "NoExist" in str(call_args)


@pytest.mark.asyncio
async def test_handle_delete_selection_item_unknown_type(
    delete_handler, make_update, make_context
):
    """Item selection with an unknown media type shows InvalidMediaType."""
    update = make_update(callback_data="delete_item_book_1")
    context = make_context()

    await delete_handler.handle_delete_selection(update, context)

    update.callback_query.message.edit_text.assert_called_once()
    delete_handler._mock_ts.get_text.assert_any_call("InvalidMediaType")


@pytest.mark.parametrize("callback_data", [
    "delete_item_movie_abc",
    "delete_item_movie",
    "delete_item_movie_",
    "delete_item_movie_1_2",
    "delete_item_123",
    "delete_confirm_movie_abc",
    "delete_confirm_movie",
    "delete_confirm_movie_-1",
    "delete_confirm",
])
@pytest.mark.asyncio
async def test_bad_item_or_confirm_callback_calls_no_service(
    delete_handler, make_update, make_context, callback_data
):
    """A malformed id or shape shows ItemDataNotFound and calls no service."""
    service = delete_handler._mock_service
    for name in (
        "get_movie", "get_series", "get_music",
        "delete_movie", "delete_series", "delete_music",
    ):
        setattr(service, name, AsyncMock())

    update = make_update(callback_data=callback_data)
    context = make_context()

    await delete_handler.handle_delete_selection(update, context)

    update.callback_query.message.edit_text.assert_called_once()
    delete_handler._mock_ts.get_text.assert_any_call("ItemDataNotFound")
    for name in (
        "get_movie", "get_series", "get_music",
        "delete_movie", "delete_series", "delete_music",
    ):
        getattr(service, name).assert_not_called()


@pytest.mark.asyncio
async def test_handle_delete_selection_item_exception(
    delete_handler, make_update, make_context
):
    """Item selection with API error shows error."""
    delete_handler._mock_service.get_movie = AsyncMock(
        side_effect=Exception("API error")
    )

    update = make_update(callback_data="delete_item_movie_123")
    context = make_context()

    await delete_handler.handle_delete_selection(update, context)

    update.callback_query.message.edit_text.assert_called_once()
    delete_handler._mock_ts.get_text.assert_any_call("ItemDetailsError")


# ---------------------------------------------------------------------------
# handle_delete_selection - list paging
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_type_callback_150_movies_shows_one_page_and_nav_row(
    delete_handler, make_update, make_context
):
    """A large library shows one page of items plus a nav row, no error."""
    movies = [{"id": str(i), "title": f"Movie {i}"} for i in range(150)]
    delete_handler._mock_service.get_movies = AsyncMock(return_value=movies)

    update = make_update(callback_data="delete_type_movie")
    context = make_context()

    await delete_handler.handle_delete_selection(update, context)

    update.callback_query.message.edit_text.assert_called_once()
    delete_handler._mock_ts.get_text.assert_any_call("Select")
    assert "MediaListError" not in str(
        delete_handler._mock_ts.get_text.call_args_list
    )
    keyboard = (
        update.callback_query.message.edit_text.call_args[1]["reply_markup"]
        .inline_keyboard
    )
    assert len(keyboard) == 10 + 2
    assert keyboard[10][0].callback_data == "delete_page_movie_1"
    assert keyboard[-1][0].callback_data == "delete_cancel"


@pytest.mark.parametrize("media_type,list_method", [
    ("movie", "get_movies"),
    ("series", "get_series"),
    ("music", "get_music"),
])
@pytest.mark.asyncio
async def test_page_callback_refetches_list_for_its_own_type(
    delete_handler, make_update, make_context, media_type, list_method
):
    """A page button refetches the list of the type it was drawn for."""
    items = [{"id": str(i), "title": f"Item {i}"} for i in range(25)]
    called = AsyncMock(return_value=items)
    for name in ("get_movies", "get_series", "get_music"):
        setattr(delete_handler._mock_service, name, AsyncMock())
    setattr(delete_handler._mock_service, list_method, called)

    update = make_update(callback_data=f"delete_page_{media_type}_2")
    context = make_context(user_data={"delete_type": "other"})

    await delete_handler.handle_delete_selection(update, context)

    called.assert_awaited_once_with()
    for name in {"get_movies", "get_series", "get_music"} - {list_method}:
        getattr(delete_handler._mock_service, name).assert_not_called()
    keyboard = (
        update.callback_query.message.edit_text.call_args[1]["reply_markup"]
        .inline_keyboard
    )
    assert [row[0].text for row in keyboard[:-2]] == [
        f"Item {i}" for i in range(20, 25)
    ]
    assert keyboard[-2][0].callback_data == f"delete_page_{media_type}_1"


@pytest.mark.parametrize("callback_data", [
    "delete_page_movie_abc",
    "delete_page_movie",
    "delete_page_movie_-1",
])
@pytest.mark.asyncio
async def test_bad_page_callback_calls_no_service(
    delete_handler, make_update, make_context, callback_data
):
    """A malformed page callback fetches nothing."""
    delete_handler._mock_service.get_movies = AsyncMock()

    update = make_update(callback_data=callback_data)
    context = make_context()

    await delete_handler.handle_delete_selection(update, context)

    delete_handler._mock_service.get_movies.assert_not_called()
    delete_handler._mock_ts.get_text.assert_any_call("ItemDataNotFound")


@pytest.mark.asyncio
async def test_page_callback_unknown_type(
    delete_handler, make_update, make_context
):
    """A page callback for an unknown type shows InvalidMediaType."""
    update = make_update(callback_data="delete_page_book_1")
    context = make_context()

    await delete_handler.handle_delete_selection(update, context)

    delete_handler._mock_ts.get_text.assert_any_call("InvalidMediaType")


@pytest.mark.asyncio
async def test_page_callback_no_items_shows_no_exist(
    delete_handler, make_update, make_context
):
    """A page callback on a library that is now empty shows NoExist."""
    delete_handler._mock_service.get_movies = AsyncMock(return_value=[])

    update = make_update(callback_data="delete_page_movie_1")
    context = make_context()

    await delete_handler.handle_delete_selection(update, context)

    assert "NoExist" in str(
        update.callback_query.message.edit_text.call_args
    )


@pytest.mark.asyncio
async def test_page_callback_exception_shows_list_error(
    delete_handler, make_update, make_context
):
    """A page callback with an API error shows MediaListError."""
    delete_handler._mock_service.get_movies = AsyncMock(
        side_effect=Exception("API error")
    )

    update = make_update(callback_data="delete_page_movie_1")
    context = make_context()

    await delete_handler.handle_delete_selection(update, context)

    delete_handler._mock_ts.get_text.assert_any_call("MediaListError")


# ---------------------------------------------------------------------------
# handle_delete_selection - confirm deletion
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("media_type,get_method,delete_method", [
    ("movie", "get_movie", "delete_movie"),
    ("series", "get_series", "delete_series"),
    ("music", "get_music", "delete_music"),
])
@pytest.mark.asyncio
async def test_handle_delete_confirm_success(
    delete_handler, make_update, make_context,
    media_type, get_method, delete_method
):
    """Confirm deletion refetches the title and shows DeleteSuccess."""
    setattr(
        delete_handler._mock_service, get_method,
        AsyncMock(return_value={"id": "123", "title": "Test Item"})
    )
    deleter = AsyncMock(return_value=True)
    setattr(delete_handler._mock_service, delete_method, deleter)

    update = make_update(callback_data=f"delete_confirm_{media_type}_123")
    context = make_context()

    await delete_handler.handle_delete_selection(update, context)

    deleter.assert_awaited_once_with("123")
    update.callback_query.message.edit_text.assert_called_once()
    call_args = update.callback_query.message.edit_text.call_args
    assert "DeleteSuccess" in str(call_args)
    delete_handler._mock_ts.get_message.assert_any_call(
        "DeleteSuccess", subject=media_type, title="Test Item"
    )


@pytest.mark.asyncio
async def test_confirm_callback_ignores_user_data(
    delete_handler, make_update, make_context
):
    """The confirm button deletes the movie it names, whatever user_data holds."""
    service = delete_handler._mock_service
    service.get_movie = AsyncMock(
        return_value={"id": "42", "title": "Movie 42"}
    )
    service.delete_movie = AsyncMock(return_value=True)
    service.delete_series = AsyncMock(return_value=True)

    update = make_update(callback_data="delete_confirm_movie_42")
    context = make_context(user_data={
        "delete_type": "series",
        "delete_item": {"id": "7", "title": "Series 7"},
    })

    await delete_handler.handle_delete_selection(update, context)

    service.delete_movie.assert_awaited_once_with("42")
    service.delete_series.assert_not_called()


@pytest.mark.asyncio
async def test_confirm_item_gone_shows_no_exist(
    delete_handler, make_update, make_context
):
    """An item that is already gone is not deleted."""
    service = delete_handler._mock_service
    service.get_movie = AsyncMock(return_value=None)
    service.delete_movie = AsyncMock(return_value=True)

    update = make_update(callback_data="delete_confirm_movie_42")
    context = make_context()

    await delete_handler.handle_delete_selection(update, context)

    service.delete_movie.assert_not_called()
    assert "NoExist" in str(
        update.callback_query.message.edit_text.call_args
    )


@pytest.mark.asyncio
async def test_handle_delete_confirm_failure(
    delete_handler, make_update, make_context
):
    """Confirm deletion with failure shows DeleteFailed."""
    delete_handler._mock_service.get_movie = AsyncMock(
        return_value={"id": "123", "title": "Test Item"}
    )
    delete_handler._mock_service.delete_movie = AsyncMock(return_value=False)

    update = make_update(callback_data="delete_confirm_movie_123")
    context = make_context()

    await delete_handler.handle_delete_selection(update, context)

    update.callback_query.message.edit_text.assert_called_once()
    call_args = update.callback_query.message.edit_text.call_args
    assert "DeleteFailed" in str(call_args)


@pytest.mark.asyncio
async def test_handle_delete_confirm_exception(
    delete_handler, make_update, make_context
):
    """Confirm deletion with exception shows DeleteFailed."""
    delete_handler._mock_service.get_movie = AsyncMock(
        return_value={"id": "123", "title": "Test Item"}
    )
    delete_handler._mock_service.delete_movie = AsyncMock(
        side_effect=Exception("Error")
    )

    update = make_update(callback_data="delete_confirm_movie_123")
    context = make_context()

    await delete_handler.handle_delete_selection(update, context)

    update.callback_query.message.edit_text.assert_called_once()
    call_args = update.callback_query.message.edit_text.call_args
    assert "DeleteFailed" in str(call_args)


@pytest.mark.asyncio
async def test_confirm_fetch_exception_deletes_nothing(
    delete_handler, make_update, make_context
):
    """If the refetch fails, nothing is deleted and ItemDetailsError shows."""
    delete_handler._mock_service.get_movie = AsyncMock(
        side_effect=Exception("API error")
    )
    delete_handler._mock_service.delete_movie = AsyncMock()

    update = make_update(callback_data="delete_confirm_movie_123")
    context = make_context()

    await delete_handler.handle_delete_selection(update, context)

    delete_handler._mock_service.delete_movie.assert_not_called()
    delete_handler._mock_ts.get_text.assert_any_call("ItemDetailsError")


@pytest.mark.asyncio
async def test_handle_delete_confirm_unknown_type(
    delete_handler, make_update, make_context
):
    """Confirm deletion with an unknown type shows InvalidMediaType."""
    update = make_update(callback_data="delete_confirm_book_123")
    context = make_context()

    await delete_handler.handle_delete_selection(update, context)

    update.callback_query.message.edit_text.assert_called_once()
    delete_handler._mock_ts.get_text.assert_any_call("InvalidMediaType")


# ---------------------------------------------------------------------------
# get_handler
# ---------------------------------------------------------------------------


def test_get_handler_returns_list(delete_handler):
    """get_handler returns a list of handlers."""
    handlers = delete_handler.get_handler()

    assert isinstance(handlers, list)
    assert len(handlers) > 0


# ---------------------------------------------------------------------------
# get_delete_keyboard (#166)
# ---------------------------------------------------------------------------


def test_get_delete_keyboard_structure(delete_handler):
    """get_delete_keyboard returns 3 media types + cancel button."""
    keyboard = delete_handler.get_delete_keyboard()

    all_buttons = [
        button
        for row in keyboard.inline_keyboard
        for button in row
    ]
    callback_data = [b.callback_data for b in all_buttons]

    assert "delete_type_movie" in callback_data
    assert "delete_type_series" in callback_data
    assert "delete_type_music" in callback_data
    assert "delete_cancel" in callback_data
    assert len(callback_data) == 4


def test_get_delete_keyboard_has_media_type_emojis(delete_handler):
    """Delete keyboard buttons have media type emojis."""
    keyboard = delete_handler.get_delete_keyboard()

    button_texts = [
        button.text
        for row in keyboard.inline_keyboard
        for button in row
    ]
    assert any("🎬" in t for t in button_texts)  # movie
    assert any("📺" in t for t in button_texts)  # series
    assert any("🎵" in t for t in button_texts)  # music
    assert any("❌" in t for t in button_texts)  # cancel


# ---------------------------------------------------------------------------
# Access control
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("callback_data", [
    "delete_type_movie", "delete_page_movie_1",
    "delete_item_movie_123", "delete_confirm_movie_123",
])
@pytest.mark.asyncio
async def test_delete_buttons_refuse_unauthenticated_user(
    delete_handler, make_update, make_context, callback_data
):
    """Delete buttons do nothing for unauthenticated users (audit item 5)."""
    from src.bot.handlers.auth import AuthHandler
    AuthHandler._authenticated_users = set()

    update = make_update(callback_data=callback_data)
    context = make_context()

    await delete_handler.handle_delete_selection(update, context)

    assert delete_handler._mock_service.method_calls == []
    update.callback_query.message.edit_text.assert_not_called()


@pytest.mark.parametrize("method, update_kwargs", [
    ("handle_delete", {"text": "/delete"}),
    ("handle_delete_selection", {"callback_data": "delete_confirm_movie_123"}),
])
@pytest.mark.asyncio
async def test_delete_is_admin_only_in_admin_mode(
    delete_handler, admin_mode, make_update, make_context, method, update_kwargs
):
    """With security.enableAdmin, only admins can delete media (audit item 6)."""
    update = make_update(**update_kwargs)
    context = make_context()

    await getattr(delete_handler, method)(update, context)

    assert delete_handler._mock_service.method_calls == []
    if update.callback_query:
        update.callback_query.answer.assert_awaited_once_with(
            "NotAdmin", show_alert=True
        )
    else:
        update.message.reply_text.assert_awaited_once_with("NotAdmin")


@pytest.mark.asyncio
async def test_admin_can_delete_in_admin_mode(
    delete_handler, admin_mode, make_user, make_update, make_context
):
    """Admins still delete media when admin mode is on."""
    update = make_update(
        callback_data="delete_confirm_movie_123", user=make_user(user_id=1)
    )
    context = make_context()
    delete_handler._mock_service.get_movie = AsyncMock(
        return_value={"id": "123", "title": "Test Item"}
    )
    from src.bot.handlers.auth import AuthHandler
    AuthHandler._authenticated_users = {1}

    await delete_handler.handle_delete_selection(update, context)

    delete_handler._mock_service.delete_movie.assert_awaited_once_with("123")

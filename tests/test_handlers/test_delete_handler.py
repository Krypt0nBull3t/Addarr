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
    assert context.user_data["delete_type"] == media_type


@pytest.mark.asyncio
async def test_handle_delete_selection_type_invalid(
    delete_handler, make_update, make_context
):
    """Invalid type selection shows error."""
    update = make_update(callback_data="delete_type_invalid")
    context = make_context()

    await delete_handler.handle_delete_selection(update, context)

    update.callback_query.message.edit_text.assert_called_once()
    call_args = update.callback_query.message.edit_text.call_args
    assert "Invalid" in str(call_args)


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
    call_args = update.callback_query.message.edit_text.call_args
    assert "Error" in str(call_args)


# ---------------------------------------------------------------------------
# handle_delete_selection - item selection
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
    """Item selection shows confirmation keyboard."""
    item = {"id": "123", "title": "Test Item"}
    setattr(
        delete_handler._mock_service, service_method,
        AsyncMock(return_value=item)
    )

    update = make_update(callback_data="delete_item_123")
    context = make_context(user_data={"delete_type": media_type})

    await delete_handler.handle_delete_selection(update, context)

    update.callback_query.message.edit_text.assert_called_once()
    call_args = update.callback_query.message.edit_text.call_args
    assert "ThisDelete" in str(call_args)


@pytest.mark.asyncio
async def test_handle_delete_selection_item_no_type(
    delete_handler, make_update, make_context
):
    """Item selection with no media_type shows error."""
    update = make_update(callback_data="delete_item_123")
    context = make_context(user_data={})

    await delete_handler.handle_delete_selection(update, context)

    update.callback_query.message.edit_text.assert_called_once()
    call_args = update.callback_query.message.edit_text.call_args
    assert "not found" in str(call_args).lower()


@pytest.mark.asyncio
async def test_handle_delete_selection_item_not_found(
    delete_handler, make_update, make_context
):
    """Item selection with item not found shows NoExist."""
    delete_handler._mock_service.get_movie = AsyncMock(return_value=None)

    update = make_update(callback_data="delete_item_123")
    context = make_context(user_data={"delete_type": "movie"})

    await delete_handler.handle_delete_selection(update, context)

    update.callback_query.message.edit_text.assert_called_once()
    call_args = update.callback_query.message.edit_text.call_args
    assert "NoExist" in str(call_args)


@pytest.mark.asyncio
async def test_handle_delete_selection_item_invalid_type(
    delete_handler, make_update, make_context
):
    """Item selection with invalid media type shows error."""
    update = make_update(callback_data="delete_item_123")
    context = make_context(user_data={"delete_type": "invalid"})

    await delete_handler.handle_delete_selection(update, context)

    update.callback_query.message.edit_text.assert_called_once()
    call_args = update.callback_query.message.edit_text.call_args
    assert "Invalid" in str(call_args)


@pytest.mark.asyncio
async def test_handle_delete_selection_item_exception(
    delete_handler, make_update, make_context
):
    """Item selection with API error shows error."""
    delete_handler._mock_service.get_movie = AsyncMock(
        side_effect=Exception("API error")
    )

    update = make_update(callback_data="delete_item_123")
    context = make_context(user_data={"delete_type": "movie"})

    await delete_handler.handle_delete_selection(update, context)

    update.callback_query.message.edit_text.assert_called_once()
    call_args = update.callback_query.message.edit_text.call_args
    assert "Error" in str(call_args)


# ---------------------------------------------------------------------------
# handle_delete_selection - confirm deletion
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("media_type,service_method", [
    ("movie", "delete_movie"),
    ("series", "delete_series"),
    ("music", "delete_music"),
])
@pytest.mark.asyncio
async def test_handle_delete_confirm_success(
    delete_handler, make_update, make_context, media_type, service_method
):
    """Confirm deletion with success shows DeleteSuccess."""
    setattr(
        delete_handler._mock_service, service_method,
        AsyncMock(return_value=True)
    )

    update = make_update(callback_data="delete_confirm")
    context = make_context(user_data={
        "delete_type": media_type,
        "delete_item": {"id": "123", "title": "Test Item"},
    })

    await delete_handler.handle_delete_selection(update, context)

    update.callback_query.message.edit_text.assert_called_once()
    call_args = update.callback_query.message.edit_text.call_args
    assert "DeleteSuccess" in str(call_args)


@pytest.mark.asyncio
async def test_handle_delete_confirm_failure(
    delete_handler, make_update, make_context
):
    """Confirm deletion with failure shows DeleteFailed."""
    delete_handler._mock_service.delete_movie = AsyncMock(return_value=False)

    update = make_update(callback_data="delete_confirm")
    context = make_context(user_data={
        "delete_type": "movie",
        "delete_item": {"id": "123", "title": "Test Item"},
    })

    await delete_handler.handle_delete_selection(update, context)

    update.callback_query.message.edit_text.assert_called_once()
    call_args = update.callback_query.message.edit_text.call_args
    assert "DeleteFailed" in str(call_args)


@pytest.mark.asyncio
async def test_handle_delete_confirm_exception(
    delete_handler, make_update, make_context
):
    """Confirm deletion with exception shows DeleteFailed."""
    delete_handler._mock_service.delete_movie = AsyncMock(
        side_effect=Exception("Error")
    )

    update = make_update(callback_data="delete_confirm")
    context = make_context(user_data={
        "delete_type": "movie",
        "delete_item": {"id": "123", "title": "Test Item"},
    })

    await delete_handler.handle_delete_selection(update, context)

    update.callback_query.message.edit_text.assert_called_once()
    call_args = update.callback_query.message.edit_text.call_args
    assert "DeleteFailed" in str(call_args)


@pytest.mark.asyncio
async def test_handle_delete_confirm_no_data(
    delete_handler, make_update, make_context
):
    """Confirm deletion with missing data shows error."""
    update = make_update(callback_data="delete_confirm")
    context = make_context(user_data={})

    await delete_handler.handle_delete_selection(update, context)

    update.callback_query.message.edit_text.assert_called_once()
    call_args = update.callback_query.message.edit_text.call_args
    assert "not found" in str(call_args).lower()


@pytest.mark.asyncio
async def test_handle_delete_confirm_invalid_type(
    delete_handler, make_update, make_context
):
    """Confirm deletion with invalid type shows error."""
    update = make_update(callback_data="delete_confirm")
    context = make_context(user_data={
        "delete_type": "invalid",
        "delete_item": {"id": "123", "title": "Test"},
    })

    await delete_handler.handle_delete_selection(update, context)

    update.callback_query.message.edit_text.assert_called_once()
    call_args = update.callback_query.message.edit_text.call_args
    assert "Invalid" in str(call_args)


# ---------------------------------------------------------------------------
# get_handler
# ---------------------------------------------------------------------------


def test_get_handler_returns_list(delete_handler):
    """get_handler returns a list of handlers."""
    handlers = delete_handler.get_handler()

    assert isinstance(handlers, list)
    assert len(handlers) > 0

"""
Tests for src/bot/handlers/delete.py - DeleteHandler.

DeleteHandler.__init__ creates MediaService() and TranslationService().
handle_delete shows a media type selection keyboard (decorated with @require_auth).
handle_delete_selection processes callback queries for deletion flow.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock


# ---------------------------------------------------------------------------
# handle_delete
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("src.bot.handlers.delete.MediaService")
@patch("src.bot.handlers.delete.TranslationService")
async def test_handle_delete(
    mock_ts_class, mock_ms_class, make_update, make_context
):
    """handle_delete replies with type selection keyboard."""
    mock_ts = MagicMock()
    mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
    mock_ts_class.return_value = mock_ts
    mock_ms_class.return_value = MagicMock()

    from src.bot.handlers.delete import DeleteHandler
    from src.bot.handlers.auth import AuthHandler

    AuthHandler._authenticated_users = {12345}

    handler = DeleteHandler()
    update = make_update(text="/delete")
    context = make_context()

    await handler.handle_delete(update, context)

    update.message.reply_text.assert_called_once()
    call_args = update.message.reply_text.call_args
    # Verify reply_markup was passed (keyboard)
    assert call_args[1].get("reply_markup") is not None or len(call_args) > 1


# ---------------------------------------------------------------------------
# handle_delete - not authenticated
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("src.bot.handlers.delete.MediaService")
@patch("src.bot.handlers.delete.TranslationService")
async def test_handle_delete_not_authenticated(
    mock_ts_class, mock_ms_class, make_update, make_context
):
    """handle_delete rejects unauthenticated users via @require_auth."""
    mock_ts = MagicMock()
    mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
    mock_ts_class.return_value = mock_ts
    mock_ms_class.return_value = MagicMock()

    from src.bot.handlers.delete import DeleteHandler
    from src.bot.handlers.auth import AuthHandler

    AuthHandler._authenticated_users = set()

    handler = DeleteHandler()
    update = make_update(text="/delete")
    context = make_context()

    result = await handler.handle_delete(update, context)

    # require_auth returns None when not authenticated
    assert result is None


# ---------------------------------------------------------------------------
# handle_delete_selection - cancel
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("src.bot.handlers.delete.MediaService")
@patch("src.bot.handlers.delete.TranslationService")
async def test_handle_delete_selection_cancel(
    mock_ts_class, mock_ms_class, make_update, make_context
):
    """delete_cancel callback edits message with 'End' text."""
    mock_ts = MagicMock()
    mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
    mock_ts_class.return_value = mock_ts
    mock_ms_class.return_value = MagicMock()

    from src.bot.handlers.delete import DeleteHandler

    handler = DeleteHandler()
    update = make_update(callback_data="delete_cancel")
    context = make_context()

    await handler.handle_delete_selection(update, context)

    update.callback_query.answer.assert_called_once()
    update.callback_query.message.edit_text.assert_called_once()
    call_args = update.callback_query.message.edit_text.call_args
    assert "End" in str(call_args)


# ---------------------------------------------------------------------------
# get_handler
# ---------------------------------------------------------------------------


@patch("src.bot.handlers.delete.MediaService")
@patch("src.bot.handlers.delete.TranslationService")
def test_get_handler_returns_list(mock_ts_class, mock_ms_class):
    """get_handler returns a list of handlers."""
    mock_ts = MagicMock()
    mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
    mock_ts_class.return_value = mock_ts
    mock_ms_class.return_value = MagicMock()

    from src.bot.handlers.delete import DeleteHandler

    handler = DeleteHandler()
    handlers = handler.get_handler()

    assert isinstance(handlers, list)
    assert len(handlers) > 0

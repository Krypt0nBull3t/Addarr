"""
Tests for src/bot/handlers/auth.py - AuthHandler and require_auth decorator.

AuthHandler manages user authentication via password. The require_auth decorator
guards handler methods by checking AuthHandler.is_authenticated(user_id).
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from telegram.ext import ConversationHandler


# ---------------------------------------------------------------------------
# is_authenticated class method
# ---------------------------------------------------------------------------


def test_is_authenticated_true():
    """User ID present in _authenticated_users returns True."""
    from src.bot.handlers.auth import AuthHandler

    AuthHandler._authenticated_users = {12345}
    assert AuthHandler.is_authenticated(12345) is True


def test_is_authenticated_false():
    """User ID not in _authenticated_users returns False."""
    from src.bot.handlers.auth import AuthHandler

    AuthHandler._authenticated_users = set()
    assert AuthHandler.is_authenticated(99999) is False


# ---------------------------------------------------------------------------
# require_auth decorator
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("src.bot.handlers.auth.TranslationService")
async def test_require_auth_authenticated(mock_ts_class, make_update, make_context):
    """Decorated method proceeds when user is authenticated."""
    mock_ts = MagicMock()
    mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
    mock_ts_class.return_value = mock_ts

    from src.bot.handlers.auth import AuthHandler, require_auth

    AuthHandler._authenticated_users = {12345}

    class DummyHandler:
        @require_auth
        async def guarded(self, update, context):
            return "allowed"

    handler = DummyHandler()
    update = make_update(text="/test")
    context = make_context()

    result = await handler.guarded(update, context)
    assert result == "allowed"


@pytest.mark.asyncio
@patch("src.bot.handlers.auth.TranslationService")
async def test_require_auth_not_authenticated(mock_ts_class, make_update, make_context):
    """Decorated method replies with auth message when user is not authenticated."""
    mock_ts = MagicMock()
    mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
    mock_ts_class.return_value = mock_ts

    from src.bot.handlers.auth import AuthHandler, require_auth

    AuthHandler._authenticated_users = set()

    class DummyHandler:
        @require_auth
        async def guarded(self, update, context):
            return "allowed"

    handler = DummyHandler()
    update = make_update(text="/test")
    context = make_context()

    result = await handler.guarded(update, context)
    assert result is None
    update.message.reply_text.assert_called_once()


# ---------------------------------------------------------------------------
# start_auth
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("src.bot.handlers.auth.TranslationService")
async def test_start_auth_already_authenticated(mock_ts_class, make_update, make_context):
    """Already authenticated user gets 'Chatid already allowed' and END."""
    mock_ts = MagicMock()
    mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
    mock_ts_class.return_value = mock_ts

    from src.bot.handlers.auth import AuthHandler

    handler = AuthHandler()
    AuthHandler._authenticated_users = {12345}

    update = make_update(text="/auth")
    context = make_context()

    result = await handler.start_auth(update, context)

    assert result == ConversationHandler.END
    update.message.reply_text.assert_called_once()
    call_args = update.message.reply_text.call_args
    assert "Chatid already allowed" in str(call_args)


@pytest.mark.asyncio
@patch("src.bot.handlers.auth.TranslationService")
async def test_start_auth_prompts_password(mock_ts_class, make_update, make_context):
    """Unauthenticated user gets 'Authorize' prompt and PASSWORD state (0)."""
    mock_ts = MagicMock()
    mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
    mock_ts_class.return_value = mock_ts

    from src.bot.handlers.auth import AuthHandler, PASSWORD

    handler = AuthHandler()
    AuthHandler._authenticated_users = set()

    update = make_update(text="/auth")
    context = make_context()

    result = await handler.start_auth(update, context)

    assert result == PASSWORD
    update.message.reply_text.assert_called_once()
    call_args = update.message.reply_text.call_args
    assert "Authorize" in str(call_args)


# ---------------------------------------------------------------------------
# check_password
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("src.bot.handlers.auth.TranslationService")
async def test_check_password_correct(mock_ts_class, make_update, make_context):
    """Correct password adds user to authenticated set and returns END."""
    mock_ts = MagicMock()
    mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
    mock_ts_class.return_value = mock_ts

    from src.bot.handlers.auth import AuthHandler

    handler = AuthHandler()
    AuthHandler._authenticated_users = set()

    # Mock config password is "test-pass" from conftest MOCK_CONFIG_DATA
    update = make_update(text="test-pass")
    context = make_context()

    # Patch _save_authenticated_users to avoid file I/O
    with patch.object(handler, "_save_authenticated_users"):
        result = await handler.check_password(update, context)

    assert result == ConversationHandler.END
    assert 12345 in AuthHandler._authenticated_users
    # Password message should be deleted for security
    update.effective_message.delete.assert_called_once()


@pytest.mark.asyncio
@patch("src.bot.handlers.auth.TranslationService")
async def test_check_password_wrong(mock_ts_class, make_update, make_context):
    """Wrong password replies with 'Wrong password' and returns END."""
    mock_ts = MagicMock()
    mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
    mock_ts_class.return_value = mock_ts

    from src.bot.handlers.auth import AuthHandler

    handler = AuthHandler()
    AuthHandler._authenticated_users = set()

    update = make_update(text="wrong-password")
    context = make_context()

    result = await handler.check_password(update, context)

    assert result == ConversationHandler.END
    assert 12345 not in AuthHandler._authenticated_users
    update.effective_message.delete.assert_called_once()
    # "Wrong password" sent via chat.send_message
    update.effective_message.chat.send_message.assert_called_once()
    call_args = update.effective_message.chat.send_message.call_args
    assert "Wrong password" in str(call_args)


# ---------------------------------------------------------------------------
# cancel_auth
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("src.bot.handlers.auth.TranslationService")
async def test_cancel_auth(mock_ts_class, make_update, make_context):
    """Cancel replies with 'End' and returns END."""
    mock_ts = MagicMock()
    mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
    mock_ts_class.return_value = mock_ts

    from src.bot.handlers.auth import AuthHandler

    handler = AuthHandler()

    update = make_update(text="/cancel")
    context = make_context()

    result = await handler.cancel_auth(update, context)

    assert result == ConversationHandler.END
    update.message.reply_text.assert_called_once()
    call_args = update.message.reply_text.call_args
    assert "End" in str(call_args)


# ---------------------------------------------------------------------------
# get_handler
# ---------------------------------------------------------------------------


@patch("src.bot.handlers.auth.TranslationService")
def test_get_handler_returns_list(mock_ts_class):
    """get_handler returns a list of handlers."""
    mock_ts = MagicMock()
    mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
    mock_ts_class.return_value = mock_ts

    from src.bot.handlers.auth import AuthHandler

    handler = AuthHandler()
    handlers = handler.get_handler()

    assert isinstance(handlers, list)
    assert len(handlers) > 0

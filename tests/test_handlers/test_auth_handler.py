"""
Tests for src/bot/handlers/auth.py - AuthHandler and require_auth decorator.

AuthHandler manages user authentication via password. The require_auth decorator
guards handler methods by checking AuthHandler.is_authenticated(user_id).
"""

import pytest
from unittest.mock import patch, MagicMock, mock_open
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


@pytest.mark.asyncio
@patch("src.bot.handlers.auth.TranslationService")
async def test_require_auth_no_user(mock_ts_class, make_update, make_context):
    """require_auth returns None when effective_user is None."""
    mock_ts = MagicMock()
    mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
    mock_ts_class.return_value = mock_ts

    from src.bot.handlers.auth import require_auth

    class DummyHandler:
        @require_auth
        async def guarded(self, update, context):
            return "allowed"

    handler = DummyHandler()
    update = make_update(text="/test")
    update.effective_user = None
    context = make_context()

    result = await handler.guarded(update, context)
    assert result is None


# ---------------------------------------------------------------------------
# _save_authenticated_users
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("src.bot.handlers.auth.TranslationService")
async def test_save_authenticated_users_success(mock_ts_class):
    """_save_authenticated_users writes users to config file."""
    mock_ts = MagicMock()
    mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
    mock_ts_class.return_value = mock_ts

    from src.bot.handlers.auth import AuthHandler

    handler = AuthHandler()
    AuthHandler._authenticated_users = {12345, 67890}

    mock_file_read = mock_open(read_data="authenticated_users: []\n")
    mock_file_write = mock_open()

    with patch("builtins.open", mock_file_read):
        with patch("yaml.safe_load", return_value={"authenticated_users": []}):
            with patch("yaml.safe_dump") as mock_dump:
                # Re-patch open for write
                with patch("builtins.open", mock_file_write):
                    handler._save_authenticated_users()

    # Should have been called (dump the config)
    mock_dump.assert_called_once()


@pytest.mark.asyncio
@patch("src.bot.handlers.auth.TranslationService")
async def test_save_authenticated_users_exception(mock_ts_class):
    """_save_authenticated_users logs error on exception."""
    mock_ts = MagicMock()
    mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
    mock_ts_class.return_value = mock_ts

    from src.bot.handlers.auth import AuthHandler

    handler = AuthHandler()
    AuthHandler._authenticated_users = {12345}

    with patch("builtins.open", side_effect=IOError("Permission denied")):
        # Should not raise
        handler._save_authenticated_users()


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


@pytest.mark.asyncio
@patch("src.bot.handlers.auth.TranslationService")
async def test_start_auth_no_message(mock_ts_class, make_update, make_context):
    """start_auth returns END when no effective_message."""
    mock_ts = MagicMock()
    mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
    mock_ts_class.return_value = mock_ts

    from src.bot.handlers.auth import AuthHandler

    handler = AuthHandler()
    update = make_update(text="/auth")
    update.effective_message = None
    context = make_context()

    result = await handler.start_auth(update, context)

    assert result == ConversationHandler.END


@pytest.mark.asyncio
@patch("src.bot.handlers.auth.TranslationService")
async def test_start_auth_no_user(mock_ts_class, make_update, make_context):
    """start_auth returns END when no effective_user."""
    mock_ts = MagicMock()
    mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
    mock_ts_class.return_value = mock_ts

    from src.bot.handlers.auth import AuthHandler

    handler = AuthHandler()
    update = make_update(text="/auth")
    update.effective_user = None
    context = make_context()

    result = await handler.start_auth(update, context)

    assert result == ConversationHandler.END


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

    update = make_update(text="test-pass")
    context = make_context()

    with patch.object(handler, "_save_authenticated_users"):
        result = await handler.check_password(update, context)

    assert result == ConversationHandler.END
    assert 12345 in AuthHandler._authenticated_users
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

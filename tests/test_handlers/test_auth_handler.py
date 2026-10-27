"""
Tests for src/bot/handlers/auth.py - AuthHandler and require_auth decorator.

AuthHandler manages user authentication via password. The require_auth decorator
guards handler methods by checking AuthHandler.is_authenticated(user_id).
"""

from contextlib import contextmanager
from copy import deepcopy

import pytest
from unittest.mock import patch, MagicMock
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
async def test_require_auth_message_references_auth_not_start(
    mock_ts_class, make_update, make_context
):
    """NotAuthorized message directs users to /auth, not /start (#166)."""
    mock_ts = MagicMock()
    # Return the default text (simulates missing translation key)
    mock_ts.get_text = MagicMock(
        side_effect=lambda key, **kw: kw.get("default", key)
    )
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

    await handler.guarded(update, context)

    call_args = update.message.reply_text.call_args
    message_text = call_args[0][0]
    assert "/auth" in message_text
    assert "/start" not in message_text


# ---------------------------------------------------------------------------
# require_auth — chat type enforcement
# ---------------------------------------------------------------------------


@contextmanager
def _chat_mode_patches(mock_config):
    """Shared patch context for chat mode enforcement tests."""
    with patch("src.bot.handlers.auth.TranslationService") as mock_ts_class, \
         patch("src.bot.handlers.auth.config", mock_config):
        mock_ts = MagicMock()
        mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
        mock_ts_class.return_value = mock_ts
        yield


class _DummyHandler:
    """Test handler for require_auth decorator tests."""
    from src.bot.handlers.auth import require_auth

    @require_auth
    async def guarded(self, update, context):
        return "allowed"


@pytest.mark.asyncio
@pytest.mark.parametrize("chat_type", ["group", "supergroup"])
async def test_require_auth_rejects_non_private_chat(
    chat_type, make_update, make_context, mock_config
):
    """require_auth rejects group/supergroup chats when chatMode is private_only."""
    from src.bot.handlers.auth import AuthHandler
    AuthHandler._authenticated_users = {12345}

    handler = _DummyHandler()
    update = make_update(text="/test", chat_type=chat_type)
    context = make_context()

    with _chat_mode_patches(mock_config):
        result = await handler.guarded(update, context)

    assert result is None
    update.message.reply_text.assert_called_once()


@pytest.mark.asyncio
async def test_require_auth_allows_private_chat(
    make_update, make_context, mock_config
):
    """require_auth allows private chats through to the auth check."""
    from src.bot.handlers.auth import AuthHandler
    AuthHandler._authenticated_users = {12345}

    handler = _DummyHandler()
    update = make_update(text="/test", chat_type="private")
    context = make_context()

    with _chat_mode_patches(mock_config):
        result = await handler.guarded(update, context)

    assert result == "allowed"


@pytest.mark.asyncio
async def test_require_auth_allows_group_when_allow_all(
    make_update, make_context, mock_config
):
    """require_auth allows group chats when chatMode is allow_all."""
    from src.bot.handlers.auth import AuthHandler
    AuthHandler._authenticated_users = {12345}
    mock_config._set("security", {
        "enableAdmin": False, "enableAllowlist": False, "chatMode": "allow_all"
    })

    handler = _DummyHandler()
    update = make_update(text="/test", chat_type="group")
    context = make_context()

    with _chat_mode_patches(mock_config):
        result = await handler.guarded(update, context)

    assert result == "allowed"


@pytest.mark.asyncio
async def test_require_auth_rejects_group_via_callback(
    make_update, make_context, mock_config
):
    """require_auth replies via effective_message in group callback query."""
    from src.bot.handlers.auth import AuthHandler
    AuthHandler._authenticated_users = {12345}

    handler = _DummyHandler()
    update = make_update(callback_data="menu_test", chat_type="group")
    context = make_context()

    with _chat_mode_patches(mock_config):
        result = await handler.guarded(update, context)

    assert result is None
    update.effective_message.reply_text.assert_called_once()


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


@pytest.mark.asyncio
@patch("src.bot.handlers.auth.TranslationService")
async def test_require_auth_refuses_unauthenticated_callback(
    mock_ts_class, make_update, make_context
):
    """A button press from an unauthenticated user is refused (audit item 5).

    update.message is None for callback queries, so the refusal must not use it.
    """
    mock_ts_class.return_value.get_text = MagicMock(side_effect=lambda key, **kw: key)
    from src.bot.handlers.auth import AuthHandler
    AuthHandler._authenticated_users = set()

    update = make_update(callback_data="delete_confirm")

    result = await _DummyHandler().guarded(update, make_context())

    assert result is None
    update.callback_query.answer.assert_awaited_once_with(
        "NotAuthorized", show_alert=True
    )


# ---------------------------------------------------------------------------
# Allowlist and admin mode (audit item 6)
# ---------------------------------------------------------------------------


@contextmanager
def _access_patches(mock_config, **security):
    """Patch translations and the config that the access helpers read."""
    mock_config._set("security", {
        "enableAdmin": False, "enableAllowlist": False,
        "chatMode": "private_only", **security,
    })
    with patch("src.bot.handlers.auth.TranslationService") as mock_ts_class, \
         patch("src.utils.helpers.config", mock_config):
        mock_ts_class.return_value.get_text = MagicMock(
            side_effect=lambda key, **kw: key
        )
        yield


@pytest.mark.asyncio
async def test_require_auth_refuses_user_not_on_allowlist(
    make_update, make_context, mock_config
):
    """An authenticated user who is not on the allowlist is refused."""
    from src.bot.handlers.auth import AuthHandler
    AuthHandler._authenticated_users = {12345}
    mock_config._set("allow_list", [111])

    update = make_update(text="/movie")
    with _access_patches(mock_config, enableAllowlist=True):
        result = await _DummyHandler().guarded(update, make_context())

    assert result is None
    update.message.reply_text.assert_awaited_once_with("NotAllowed")


@pytest.mark.asyncio
@pytest.mark.parametrize("allow_list, admins", [
    ([12345], []),
    ([], [12345]),  # admins are always allowed
])
async def test_require_auth_allows_listed_user(
    allow_list, admins, make_update, make_context, mock_config
):
    """Users on the allowlist, and admins, pass the allowlist."""
    from src.bot.handlers.auth import AuthHandler
    AuthHandler._authenticated_users = {12345}
    mock_config._set("allow_list", allow_list)
    mock_config._set("admins", admins)

    with _access_patches(mock_config, enableAllowlist=True):
        result = await _DummyHandler().guarded(
            make_update(text="/movie"), make_context()
        )

    assert result == "allowed"


@pytest.mark.asyncio
async def test_start_auth_refuses_user_not_on_allowlist(
    make_update, make_context, mock_config
):
    """/auth does not even ask for the password when the allowlist refuses."""
    from src.bot.handlers.auth import AuthHandler

    update = make_update(text="/auth")
    with _access_patches(mock_config, enableAllowlist=True):
        result = await AuthHandler().start_auth(update, make_context())

    assert result == ConversationHandler.END
    update.message.reply_text.assert_awaited_once_with("NotAllowed")


@pytest.mark.asyncio
@pytest.mark.parametrize("enable_admin, admins, service, only_admin, allowed", [
    (False, [], None, True, True),              # admin mode off
    (True, [12345], None, True, True),          # admin
    (True, [], None, True, False),              # non-admin in admin mode
    (True, [], "transmission", False, True),    # service not onlyAdmin
    (True, [], "transmission", True, False),    # service onlyAdmin
    (False, [], "transmission", True, True),    # onlyAdmin needs admin mode
])
async def test_require_admin(
    enable_admin, admins, service, only_admin, allowed,
    make_update, make_context, mock_config
):
    """require_admin refuses non-admins only when admin mode applies."""
    from src.bot.handlers.auth import require_admin
    mock_config._set("admins", admins)
    mock_config._set("transmission", {"onlyAdmin": only_admin})

    class Dummy:
        @require_admin(service)
        async def guarded(self, update, context):
            return "allowed"

    update = make_update(callback_data="transmission_toggle_yes")
    with _access_patches(mock_config, enableAdmin=enable_admin):
        result = await Dummy().guarded(update, make_context())

    if allowed:
        assert result == "allowed"
    else:
        assert result is None
        update.callback_query.answer.assert_awaited_once_with(
            "NotAdmin", show_alert=True
        )


# ---------------------------------------------------------------------------
# _save_authenticated_users
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("src.bot.handlers.auth.register_commands_for_chat")
@patch("src.bot.handlers.auth.TranslationService")
async def test_authenticated_user_survives_later_config_save(
    mock_ts_class, mock_register, make_user, make_update, make_context, mock_config
):
    """A later config.save() (e.g. from /settings) keeps a new user (audit item 4)."""
    mock_ts_class.return_value.get_text = MagicMock(side_effect=lambda key, **kw: key)
    saved = []
    mock_config.save = lambda: saved.append(deepcopy(mock_config._config))

    from src.bot.handlers.auth import AuthHandler

    with patch("src.bot.handlers.auth.config", mock_config):
        handler = AuthHandler()
        update = make_update(text="test-pass", user=make_user(user_id=67890))
        await handler.check_password(update, make_context())
        mock_config.save()  # another feature saves the config later

    assert saved[-1]["authenticated_users"] == [12345, 67890]


@patch("src.bot.handlers.auth.TranslationService")
def test_save_authenticated_users_exception(mock_ts_class, mock_config):
    """_save_authenticated_users logs the error instead of raising."""
    from src.bot.handlers.auth import AuthHandler

    mock_config.save = MagicMock(side_effect=OSError("Read-only file system"))

    with patch("src.bot.handlers.auth.config", mock_config), \
         patch("src.bot.handlers.auth.logger") as mock_logger:
        AuthHandler()._save_authenticated_users()

    mock_logger.error.assert_called_once()


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
    """start_auth starts no conversation when there is no effective_user.

    The auth rate limiter runs first and drops the update (returns None).
    """
    mock_ts = MagicMock()
    mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
    mock_ts_class.return_value = mock_ts

    from src.bot.handlers.auth import AuthHandler

    handler = AuthHandler()
    update = make_update(text="/auth")
    update.effective_user = None
    context = make_context()

    result = await handler.start_auth(update, context)

    assert result is None


# ---------------------------------------------------------------------------
# start_auth — chat type enforcement
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_start_auth_rejects_group_chat(
    make_update, make_context, mock_config
):
    """start_auth rejects group chats in private_only mode and returns END."""
    from src.bot.handlers.auth import AuthHandler

    with _chat_mode_patches(mock_config):
        handler = AuthHandler()
        AuthHandler._authenticated_users = set()

        update = make_update(text="/auth", chat_type="group")
        context = make_context()

        result = await handler.start_auth(update, context)

    assert result == ConversationHandler.END
    update.message.reply_text.assert_called_once()


@pytest.mark.asyncio
async def test_start_auth_allows_private_chat(
    make_update, make_context, mock_config
):
    """start_auth proceeds normally in private chats."""
    from src.bot.handlers.auth import AuthHandler, PASSWORD

    with _chat_mode_patches(mock_config):
        handler = AuthHandler()
        AuthHandler._authenticated_users = set()

        update = make_update(text="/auth", chat_type="private")
        context = make_context()

        result = await handler.start_auth(update, context)

    assert result == PASSWORD


@pytest.mark.asyncio
async def test_start_auth_allows_group_when_allow_all(
    make_update, make_context, mock_config
):
    """start_auth allows group chats when chatMode is allow_all."""
    from src.bot.handlers.auth import AuthHandler, PASSWORD

    mock_config._set("security", {
        "enableAdmin": False, "enableAllowlist": False, "chatMode": "allow_all"
    })

    with _chat_mode_patches(mock_config):
        handler = AuthHandler()
        AuthHandler._authenticated_users = set()

        update = make_update(text="/auth", chat_type="group")
        context = make_context()

        result = await handler.start_auth(update, context)

    assert result == PASSWORD


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


@pytest.mark.asyncio
@patch("src.bot.handlers.auth.TranslationService")
async def test_check_password_accepts_numeric_password(
    mock_ts_class, make_update, make_context, mock_config
):
    """YAML loads `password: 123456` as an int; typing 123456 works (audit item 14)."""
    mock_ts_class.return_value.get_text = MagicMock(side_effect=lambda key, **kw: key)
    from src.bot.handlers.auth import AuthHandler
    mock_config._set("authenticated_users", [])
    mock_config._set("telegram", {"token": "t", "password": 123456})

    with patch("src.bot.handlers.auth.config", mock_config):
        handler = AuthHandler()
    with patch.object(handler, "_save_authenticated_users"):
        await handler.check_password(make_update(text="123456"), make_context())

    assert 12345 in AuthHandler._authenticated_users


@pytest.mark.asyncio
@patch("src.bot.handlers.auth.TranslationService")
async def test_check_password_without_configured_password_rejects_all(
    mock_ts_class, make_update, make_context, mock_config
):
    """An empty `password:` (None) never matches, not even the text 'None'."""
    mock_ts_class.return_value.get_text = MagicMock(side_effect=lambda key, **kw: key)
    from src.bot.handlers.auth import AuthHandler
    mock_config._set("authenticated_users", [])
    mock_config._set("telegram", {"token": "t", "password": None})

    with patch("src.bot.handlers.auth.config", mock_config):
        handler = AuthHandler()
    await handler.check_password(make_update(text="None"), make_context())

    assert 12345 not in AuthHandler._authenticated_users


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


# ---------------------------------------------------------------------------
# check_password triggers command registration
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("src.bot.handlers.auth.TranslationService")
@patch("src.bot.handlers.auth.register_commands_for_chat")
async def test_successful_auth_registers_commands(
    mock_register, mock_ts_class, make_update, make_context
):
    """Successful auth calls register_commands_for_chat with chat_id and bot."""
    mock_ts = MagicMock()
    mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
    mock_ts_class.return_value = mock_ts

    from src.bot.handlers.auth import AuthHandler

    handler = AuthHandler()
    AuthHandler._authenticated_users = set()

    update = make_update(text="test-pass")
    context = make_context()

    with patch.object(handler, "_save_authenticated_users"):
        await handler.check_password(update, context)

    mock_register.assert_awaited_once_with(
        context.bot, update.effective_message.chat.id
    )

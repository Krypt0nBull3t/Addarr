"""Tests for WebhooksHandler — webhook setup wizard."""

import secrets
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from telegram import InlineKeyboardMarkup
from telegram.ext import ConversationHandler


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def webhook_handler_config(mock_config):
    """Config with webhooks enabled and secrets set, patched at import site."""
    mock_config._set("webhooks", {
        "enable": True,
        "port": 8080,
        "host": "0.0.0.0",
        "radarr_secret": "existing-radarr-secret",
        "sonarr_secret": None,
        "lidarr_secret": None,
        "events": {
            "grab": True,
            "download": True,
            "upgrade": True,
            "health": True,
            "failure": False,
        },
    })
    mock_config._set("admins", [12345])
    mock_config._set("security", {"enableAdmin": True, "enableAllowlist": False})
    with patch("src.bot.handlers.webhooks.config", mock_config):
        yield mock_config


@pytest.fixture
def disabled_webhook_handler_config(mock_config):
    """Config with webhooks disabled, patched at import site."""
    mock_config._set("webhooks", {
        "enable": False,
        "port": 8080,
        "host": "0.0.0.0",
    })
    mock_config._set("admins", [12345])
    mock_config._set("security", {"enableAdmin": True, "enableAllowlist": False})
    with patch("src.bot.handlers.webhooks.config", mock_config):
        yield mock_config


@pytest.fixture(autouse=True)
def _authenticate_test_users():
    """Ensure test users pass @require_auth."""
    from src.bot.handlers.auth import AuthHandler
    AuthHandler._authenticated_users = {12345, 99999}
    yield
    AuthHandler._authenticated_users = set()


@pytest.fixture
def handler(webhook_handler_config):
    """Create WebhooksHandler with patched config active for entire test."""
    from src.bot.handlers.webhooks import WebhooksHandler
    return WebhooksHandler()


@pytest.fixture
def admin_update(make_update, make_user):
    """Update from an admin user."""
    user = make_user(user_id=12345, username="admin")
    return make_update(text="/webhooks", user=user)


@pytest.fixture
def non_admin_update(make_update, make_user):
    """Update from a non-admin (but authenticated) user."""
    user = make_user(user_id=99999, username="regular")
    return make_update(text="/webhooks", user=user)


@pytest.fixture
def context(make_context):
    """Context with empty user_data."""
    return make_context()


# ---------------------------------------------------------------------------
# Admin gate tests
# ---------------------------------------------------------------------------


class TestAdminGate:
    """Test that non-admin users are rejected."""

    @pytest.mark.asyncio
    async def test_non_admin_rejected(
        self, handler, non_admin_update, context, webhook_handler_config
    ):
        """Non-admin user gets rejected with WebhookNotAdmin message."""
        with patch("src.bot.handlers.webhooks.config", webhook_handler_config):
            with patch("src.bot.handlers.webhooks.is_admin", return_value=False):
                result = await handler.show_menu(non_admin_update, context)
        assert result == ConversationHandler.END


# ---------------------------------------------------------------------------
# Menu display tests
# ---------------------------------------------------------------------------


class TestShowMenu:
    """Test show_menu displays server status and config."""

    @pytest.mark.asyncio
    async def test_show_menu_shows_status(
        self, handler, admin_update, context, webhook_handler_config
    ):
        """show_menu displays server status and per-service config."""
        with patch("src.bot.handlers.webhooks.config", webhook_handler_config):
            with patch("src.bot.handlers.webhooks.is_admin", return_value=True):
                result = await handler.show_menu(admin_update, context)
        # Should return the menu state (not END)
        from src.bot.states import States
        assert result == States.WEBHOOK_MENU
        # Should have sent a message with inline keyboard
        msg = admin_update.effective_message
        msg.reply_text.assert_awaited_once()
        call_kwargs = msg.reply_text.call_args
        assert isinstance(call_kwargs[1]["reply_markup"], InlineKeyboardMarkup)

    @pytest.mark.asyncio
    async def test_show_menu_disabled(
        self, disabled_webhook_handler_config, admin_update, context
    ):
        """show_menu shows not-enabled message when webhooks disabled."""
        with patch(
            "src.bot.handlers.webhooks.config", disabled_webhook_handler_config
        ):
            with patch("src.bot.handlers.webhooks.is_admin", return_value=True):
                from src.bot.handlers.webhooks import WebhooksHandler
                h = WebhooksHandler()
                result = await h.show_menu(admin_update, context)
        assert result == ConversationHandler.END


# ---------------------------------------------------------------------------
# Service setup tests
# ---------------------------------------------------------------------------


class TestSetupService:
    """Test setup_service generates secrets and returns instructions."""

    @pytest.mark.asyncio
    async def test_setup_service_generates_secret(
        self, handler, context, webhook_handler_config, make_update, make_user
    ):
        """setup_service generates a secret, saves to config, returns instructions."""
        user = make_user(user_id=12345)
        update = make_update(callback_data="wh_setup_sonarr", user=user)

        with patch("src.bot.handlers.webhooks.config", webhook_handler_config):
            with patch("src.bot.handlers.webhooks.secrets.token_hex", return_value="abc123"):
                result = await handler.setup_service(update, context)

        update.callback_query.answer.assert_awaited_once()
        # Should have saved the secret
        assert webhook_handler_config.get("webhooks", {}).get("sonarr_secret") == "abc123"
        from src.bot.states import States
        assert result == States.WEBHOOK_MENU


# ---------------------------------------------------------------------------
# Regenerate secret tests
# ---------------------------------------------------------------------------


class TestRegenerateSecret:
    """Test regenerate_secret creates new secret."""

    @pytest.mark.asyncio
    async def test_regenerate_secret(
        self, handler, context, webhook_handler_config, make_update, make_user
    ):
        """regenerate_secret creates new secret and saves to config."""
        user = make_user(user_id=12345)
        update = make_update(callback_data="wh_regen_radarr", user=user)

        with patch("src.bot.handlers.webhooks.config", webhook_handler_config):
            with patch("src.bot.handlers.webhooks.secrets.token_hex", return_value="new-secret"):
                result = await handler.regenerate_secret(update, context)

        assert webhook_handler_config.get("webhooks", {}).get("radarr_secret") == "new-secret"
        from src.bot.states import States
        assert result == States.WEBHOOK_MENU


# ---------------------------------------------------------------------------
# Event toggle tests
# ---------------------------------------------------------------------------


class TestEventToggles:
    """Test show_events and toggle_event."""

    @pytest.mark.asyncio
    async def test_show_events(
        self, handler, context, webhook_handler_config, make_update, make_user
    ):
        """show_events displays toggles matching current config state."""
        user = make_user(user_id=12345)
        update = make_update(callback_data="wh_events", user=user)

        with patch("src.bot.handlers.webhooks.config", webhook_handler_config):
            result = await handler.show_events(update, context)

        from src.bot.states import States
        assert result == States.WEBHOOK_EVENTS

    @pytest.mark.asyncio
    async def test_toggle_event(
        self, handler, context, webhook_handler_config, make_update, make_user
    ):
        """toggle_event flips event type and saves to config."""
        user = make_user(user_id=12345)
        # failure is currently False
        update = make_update(callback_data="wh_toggle_failure", user=user)

        with patch("src.bot.handlers.webhooks.config", webhook_handler_config):
            result = await handler.toggle_event(update, context)

        # Should have flipped failure from False to True
        assert webhook_handler_config.get("webhooks", {}).get("events", {}).get("failure") is True
        from src.bot.states import States
        assert result == States.WEBHOOK_EVENTS


# ---------------------------------------------------------------------------
# Port change tests
# ---------------------------------------------------------------------------


class TestPortChange:
    """Test port prompt and save."""

    @pytest.mark.asyncio
    async def test_prompt_port(
        self, handler, context, webhook_handler_config, make_update, make_user
    ):
        """prompt_port asks for port number."""
        user = make_user(user_id=12345)
        update = make_update(callback_data="wh_port", user=user)

        with patch("src.bot.handlers.webhooks.config", webhook_handler_config):
            result = await handler.prompt_port(update, context)

        from src.bot.states import States
        assert result == States.WEBHOOK_CHANGE_PORT

    @pytest.mark.asyncio
    async def test_save_port_valid(
        self, handler, context, webhook_handler_config, make_update, make_user
    ):
        """save_port validates range and saves."""
        user = make_user(user_id=12345)
        update = make_update(text="9090", user=user)

        with patch("src.bot.handlers.webhooks.config", webhook_handler_config):
            result = await handler.save_port(update, context)

        assert webhook_handler_config.get("webhooks", {}).get("port") == 9090
        from src.bot.states import States
        assert result == States.WEBHOOK_MENU

    @pytest.mark.asyncio
    async def test_save_port_invalid_non_numeric(
        self, handler, context, webhook_handler_config, make_update, make_user
    ):
        """save_port rejects non-numeric input."""
        user = make_user(user_id=12345)
        update = make_update(text="abc", user=user)

        with patch("src.bot.handlers.webhooks.config", webhook_handler_config):
            result = await handler.save_port(update, context)

        # Port should not change
        assert webhook_handler_config.get("webhooks", {}).get("port") == 8080
        from src.bot.states import States
        assert result == States.WEBHOOK_CHANGE_PORT

    @pytest.mark.asyncio
    async def test_save_port_invalid_out_of_range(
        self, handler, context, webhook_handler_config, make_update, make_user
    ):
        """save_port rejects out-of-range port."""
        user = make_user(user_id=12345)
        update = make_update(text="80", user=user)

        with patch("src.bot.handlers.webhooks.config", webhook_handler_config):
            result = await handler.save_port(update, context)

        assert webhook_handler_config.get("webhooks", {}).get("port") == 8080
        from src.bot.states import States
        assert result == States.WEBHOOK_CHANGE_PORT


# ---------------------------------------------------------------------------
# Close/cancel tests
# ---------------------------------------------------------------------------


class TestClose:
    """Test handle_close."""

    @pytest.mark.asyncio
    async def test_handle_close(
        self, handler, context, make_update, make_user
    ):
        """handle_close returns ConversationHandler.END."""
        user = make_user(user_id=12345)
        update = make_update(callback_data="wh_close", user=user)

        result = await handler.handle_close(update, context)
        assert result == ConversationHandler.END


# ---------------------------------------------------------------------------
# get_handler tests
# ---------------------------------------------------------------------------


class TestBackToMenu:
    """Test _back_to_menu callback."""

    @pytest.mark.asyncio
    async def test_back_to_menu(
        self, handler, context, webhook_handler_config, make_update, make_user
    ):
        """_back_to_menu returns to webhook menu state."""
        user = make_user(user_id=12345)
        update = make_update(callback_data="wh_back", user=user)

        with patch("src.bot.handlers.webhooks.config", webhook_handler_config):
            result = await handler._back_to_menu(update, context)

        from src.bot.states import States
        assert result == States.WEBHOOK_MENU

    @pytest.mark.asyncio
    async def test_back_to_menu_no_callback(self, handler, context, make_update, make_user):
        """_back_to_menu with no callback_query returns END."""
        user = make_user(user_id=12345)
        update = make_update(text="/cancel", user=user)
        update.callback_query = None

        result = await handler._back_to_menu(update, context)
        assert result == ConversationHandler.END


class TestGuardClauses:
    """Test guard clauses on handler methods."""

    @pytest.mark.asyncio
    async def test_setup_service_no_callback(self, handler, context, make_update, make_user):
        """setup_service returns END when no callback_query."""
        user = make_user(user_id=12345)
        update = make_update(text="/test", user=user)
        update.callback_query = None

        result = await handler.setup_service(update, context)
        assert result == ConversationHandler.END

    @pytest.mark.asyncio
    async def test_regenerate_secret_no_callback(self, handler, context, make_update, make_user):
        """regenerate_secret returns END when no callback_query."""
        user = make_user(user_id=12345)
        update = make_update(text="/test", user=user)
        update.callback_query = None

        result = await handler.regenerate_secret(update, context)
        assert result == ConversationHandler.END

    @pytest.mark.asyncio
    async def test_show_events_no_callback(self, handler, context, make_update, make_user):
        """show_events returns END when no callback_query."""
        user = make_user(user_id=12345)
        update = make_update(text="/test", user=user)
        update.callback_query = None

        result = await handler.show_events(update, context)
        assert result == ConversationHandler.END

    @pytest.mark.asyncio
    async def test_toggle_event_no_callback(self, handler, context, make_update, make_user):
        """toggle_event returns END when no callback_query."""
        user = make_user(user_id=12345)
        update = make_update(text="/test", user=user)
        update.callback_query = None

        result = await handler.toggle_event(update, context)
        assert result == ConversationHandler.END

    @pytest.mark.asyncio
    async def test_prompt_port_no_callback(self, handler, context, make_update, make_user):
        """prompt_port returns END when no callback_query."""
        user = make_user(user_id=12345)
        update = make_update(text="/test", user=user)
        update.callback_query = None

        result = await handler.prompt_port(update, context)
        assert result == ConversationHandler.END

    @pytest.mark.asyncio
    async def test_save_port_no_message(self, handler, context):
        """save_port returns END when no effective_message."""
        from telegram import Update
        update = MagicMock(spec=Update)
        update.effective_message = None

        result = await handler.save_port(update, context)
        assert result == ConversationHandler.END


class TestHandleCloseCancel:
    """Test handle_close via text command (not callback)."""

    @pytest.mark.asyncio
    async def test_handle_close_via_command(self, handler, context, make_update, make_user):
        """handle_close via /cancel text command."""
        user = make_user(user_id=12345)
        update = make_update(text="/cancel", user=user)
        update.callback_query = None

        result = await handler.handle_close(update, context)
        assert result == ConversationHandler.END
        update.effective_message.reply_text.assert_awaited_once()


class TestGetHandler:
    """Test get_handler returns proper ConversationHandler."""

    def test_get_handler_returns_list(self, handler):
        """get_handler returns a list of handlers."""
        handlers = handler.get_handler()
        assert isinstance(handlers, list)
        assert len(handlers) > 0
        assert isinstance(handlers[0], ConversationHandler)

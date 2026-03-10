"""Tests for src/main.py"""

import signal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telegram.error import InvalidToken, NetworkError

from src.main import AddarrBot, main, run_bot


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def bot():
    """Fresh AddarrBot with mocked application."""
    b = AddarrBot()
    return b


def _mock_handler_class():
    """Create a mock handler class whose get_handler() returns [MagicMock()]."""
    cls = MagicMock()
    cls.return_value.get_handler.return_value = [MagicMock()]
    return cls


def _make_mock_application():
    """Create a mock Application with builder chain and async methods."""
    app = MagicMock()
    app.initialize = AsyncMock()
    app.start = AsyncMock()
    app.stop = AsyncMock()
    app.shutdown = AsyncMock()
    app.add_handler = MagicMock()
    app.bot = AsyncMock()
    app.bot.set_my_commands = AsyncMock()
    app.updater = MagicMock()
    app.updater.start_polling = AsyncMock()
    app.updater.stop = AsyncMock()
    app.updater.running = True
    return app


@pytest.fixture
def mock_app():
    """A fully mocked Application."""
    return _make_mock_application()


def _make_handler_patches():
    """Create fresh mock handler classes (avoids shared mutable state)."""
    return {
        "StartHandler": _mock_handler_class(),
        "AuthHandler": _mock_handler_class(),
        "MediaHandler": _mock_handler_class(),
        "SettingsHandler": _mock_handler_class(),
        "DeleteHandler": _mock_handler_class(),
        "LibraryHandler": _mock_handler_class(),
        "CalendarHandler": _mock_handler_class(),
        "MissingHandler": _mock_handler_class(),
        "QueueHandler": _mock_handler_class(),
        "HistoryHandler": _mock_handler_class(),
        "TransmissionHandler": _mock_handler_class(),
        "SabnzbdHandler": _mock_handler_class(),
        "DownloadsHandler": _mock_handler_class(),
        "HelpHandler": _mock_handler_class(),
        "PreferencesHandler": _mock_handler_class(),
        "SystemHandler": _mock_handler_class(),
        "WebhooksHandler": _mock_handler_class(),
        "BazarrHandler": _mock_handler_class(),
    }


# ---- AddarrBot.__init__ ----


class TestAddarrBotInit:
    """Tests for AddarrBot constructor."""

    def test_application_is_none(self, bot):
        """application starts as None."""
        assert bot.application is None

    def test_running_is_false(self, bot):
        """_running starts as False."""
        assert bot._running is False

    def test_health_checker_is_health_service(self, bot):
        """health_checker is the global health_service singleton."""
        from src.services.health import health_service
        assert bot.health_checker is health_service


# ---- AddarrBot.initialize ----


class TestInitialize:
    """Tests for AddarrBot.initialize()."""

    @pytest.mark.asyncio
    @patch("src.main.show_welcome_screen")
    @patch("src.main.check_config")
    @patch("src.main.health_service")
    @patch("src.main.display_health_status", return_value=True)
    @patch("src.main.Application")
    async def test_happy_path(
        self, mock_app_cls, mock_display, mock_hs, mock_cc, mock_sw
    ):
        """Full initialization lifecycle succeeds."""
        mock_hs.run_health_checks = AsyncMock(return_value={})
        app = _make_mock_application()
        mock_app_cls.builder.return_value.token.return_value.build.return_value = app

        bot = AddarrBot()
        with patch.multiple("src.main", **_make_handler_patches()):
            await bot.initialize()

        mock_sw.assert_called_once()
        mock_cc.assert_called_once()
        mock_hs.run_health_checks.assert_awaited_once()
        app.initialize.assert_awaited_once()
        assert bot.application is app

    @pytest.mark.asyncio
    @patch("src.main.show_welcome_screen")
    @patch("src.main.check_config")
    @patch("src.main.health_service")
    @patch("src.main.display_health_status", return_value=False)
    @patch("src.main.Application")
    async def test_health_checks_fail_continues(
        self, mock_app_cls, mock_display, mock_hs, mock_cc, mock_sw
    ):
        """Initialization continues even when health checks fail."""
        mock_hs.run_health_checks = AsyncMock(return_value={})
        app = _make_mock_application()
        mock_app_cls.builder.return_value.token.return_value.build.return_value = app

        bot = AddarrBot()
        with patch.multiple("src.main", **_make_handler_patches()):
            await bot.initialize()

        # Still initialized despite health failure
        assert bot.application is app

    @pytest.mark.asyncio
    @patch("src.main.show_welcome_screen")
    @patch("src.main.check_config")
    @patch("src.main.health_service")
    @patch("src.main.display_health_status", return_value=True)
    @patch("src.main.handle_missing_token_error")
    @patch("src.main.config")
    async def test_missing_token_raises(
        self, mock_cfg, mock_hte, mock_display, mock_hs, mock_cc, mock_sw
    ):
        """Raises ValueError when token is not configured."""
        mock_hs.run_health_checks = AsyncMock(return_value={})
        mock_cfg.get.return_value = {}  # No telegram config

        bot = AddarrBot()
        with pytest.raises(ValueError, match="Telegram bot token"):
            await bot.initialize()
        mock_hte.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.main.show_welcome_screen")
    @patch("src.main.check_config")
    @patch("src.main.health_service")
    @patch("src.main.display_health_status", return_value=True)
    @patch("src.main.handle_token_error", return_value=True)
    @patch("src.main.os.execl")
    @patch("src.main.Application")
    async def test_invalid_token_restart(
        self, mock_app_cls, mock_execl, mock_hte,
        mock_display, mock_hs, mock_cc, mock_sw
    ):
        """os.execl is called when token error is handled successfully."""
        mock_hs.run_health_checks = AsyncMock(return_value={})
        app = _make_mock_application()
        app.initialize = AsyncMock(side_effect=InvalidToken("bad token"))
        mock_app_cls.builder.return_value.token.return_value.build.return_value = app

        bot = AddarrBot()
        with patch.multiple("src.main", **_make_handler_patches()):
            # os.execl replaces process; the outer except catches the
            # fact that os.execl is mocked and doesn't actually exit.
            # The call to os.execl is what we're verifying.
            try:
                await bot.initialize()
            except Exception:
                pass
        mock_execl.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.main.show_welcome_screen")
    @patch("src.main.check_config")
    @patch("src.main.health_service")
    @patch("src.main.display_health_status", return_value=True)
    @patch("src.main.handle_token_error", return_value=False)
    @patch("src.main.Application")
    async def test_invalid_token_reraise(
        self, mock_app_cls, mock_hte,
        mock_display, mock_hs, mock_cc, mock_sw
    ):
        """Raises InvalidToken when handle_token_error returns False."""
        mock_hs.run_health_checks = AsyncMock(return_value={})
        app = _make_mock_application()

        from telegram.error import InvalidToken
        app.initialize = AsyncMock(side_effect=InvalidToken("bad"))
        mock_app_cls.builder.return_value.token.return_value.build.return_value = app

        bot = AddarrBot()
        with pytest.raises(InvalidToken):
            with patch.multiple("src.main", **_make_handler_patches()):
                await bot.initialize()

    @pytest.mark.asyncio
    @patch("src.main.show_welcome_screen")
    @patch("src.main.check_config")
    @patch("src.main.health_service")
    @patch("src.main.display_health_status", return_value=True)
    @patch("src.main.handle_network_error")
    @patch("src.main.Application")
    async def test_network_error(
        self, mock_app_cls, mock_hne,
        mock_display, mock_hs, mock_cc, mock_sw
    ):
        """Raises NetworkError after calling handle_network_error."""
        mock_hs.run_health_checks = AsyncMock(return_value={})
        app = _make_mock_application()

        app.initialize = AsyncMock(side_effect=NetworkError("timeout"))
        mock_app_cls.builder.return_value.token.return_value.build.return_value = app

        bot = AddarrBot()
        with pytest.raises(NetworkError):
            with patch.multiple("src.main", **_make_handler_patches()):
                await bot.initialize()
        mock_hne.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.main.show_welcome_screen")
    @patch("src.main.check_config")
    @patch("src.main.health_service")
    @patch("src.main.display_health_status", return_value=True)
    @patch("src.main.handle_initialization_error")
    @patch("src.main.Application")
    async def test_generic_init_exception(
        self, mock_app_cls, mock_hie,
        mock_display, mock_hs, mock_cc, mock_sw
    ):
        """Raises generic exception after calling handle_initialization_error."""
        mock_hs.run_health_checks = AsyncMock(return_value={})
        app = _make_mock_application()
        app.initialize = AsyncMock(side_effect=RuntimeError("boom"))
        mock_app_cls.builder.return_value.token.return_value.build.return_value = app

        bot = AddarrBot()
        with pytest.raises(RuntimeError, match="boom"):
            with patch.multiple("src.main", **_make_handler_patches()):
                await bot.initialize()
        mock_hie.assert_called_once()


# ---- AddarrBot._add_handlers ----


class TestAddHandlers:
    """Tests for AddarrBot._add_handlers()."""

    def test_always_on_handlers_registered(self, bot, mock_app):
        """All 15 always-on handlers are registered."""
        bot.application = mock_app
        with patch.multiple("src.main", **_make_handler_patches()):
            bot._add_handlers()

        # 16 always-on handlers (Start, Auth, Media, Settings, Delete,
        # Library, Calendar, Missing, Queue, History, Downloads, Help,
        # Preferences, System, Webhooks, Bazarr — enabled in mock config)
        assert mock_app.add_handler.call_count == 16

    @patch("src.main.config")
    def test_transmission_enabled(self, mock_cfg, bot, mock_app):
        """Transmission handler registered when enabled."""
        def cfg_get(key, default=None):
            if key == "transmission":
                return {"enable": True}
            if key == "sabnzbd":
                return {"enable": False}
            return default
        mock_cfg.get.side_effect = cfg_get

        bot.application = mock_app
        with patch.multiple("src.main", **_make_handler_patches()):
            bot._add_handlers()

        # 15 always-on + 1 transmission
        assert mock_app.add_handler.call_count == 16

    @patch("src.main.config")
    def test_sabnzbd_enabled(self, mock_cfg, bot, mock_app):
        """SABnzbd handler registered when enabled."""
        def cfg_get(key, default=None):
            if key == "transmission":
                return {"enable": False}
            if key == "sabnzbd":
                return {"enable": True}
            return default
        mock_cfg.get.side_effect = cfg_get

        bot.application = mock_app
        with patch.multiple("src.main", **_make_handler_patches()):
            bot._add_handlers()

        # 15 always-on + 1 sabnzbd
        assert mock_app.add_handler.call_count == 16

    @patch("src.main.config")
    def test_both_optional_enabled(self, mock_cfg, bot, mock_app):
        """Both Transmission and SABnzbd registered when enabled."""
        def cfg_get(key, default=None):
            if key == "transmission":
                return {"enable": True}
            if key == "sabnzbd":
                return {"enable": True}
            return default
        mock_cfg.get.side_effect = cfg_get

        bot.application = mock_app
        with patch.multiple("src.main", **_make_handler_patches()):
            bot._add_handlers()

        # 15 + 2
        assert mock_app.add_handler.call_count == 17

    def test_handler_error_reraises(self, bot, mock_app):
        """Exception during handler registration is re-raised."""
        bot.application = mock_app
        broken_handler = MagicMock()
        broken_handler.return_value.get_handler.side_effect = RuntimeError(
            "handler init failed"
        )
        patches = {**_make_handler_patches(), "StartHandler": broken_handler}
        with pytest.raises(RuntimeError, match="handler init failed"):
            with patch.multiple("src.main", **patches):
                bot._add_handlers()


# ---- AddarrBot.start ----


class TestStart:
    """Tests for AddarrBot.start()."""

    @pytest.mark.asyncio
    async def test_starts_app_and_polling(self, bot, mock_app):
        """Starts application, polling, and health checker."""
        bot.application = mock_app
        bot.health_checker = MagicMock()
        bot.health_checker.start = AsyncMock()

        # Break out of while loop after first sleep
        async def stop_after_first_sleep(_):
            bot._running = False

        with patch("src.main.asyncio.sleep", side_effect=stop_after_first_sleep):
            with patch("src.main.asyncio.create_task"):
                await bot.start()

        mock_app.start.assert_awaited_once()
        mock_app.updater.start_polling.assert_awaited_once()
        assert bot._running is False  # Loop exited

    @pytest.mark.asyncio
    async def test_sets_running_true(self, bot, mock_app):
        """Sets _running to True before entering loop."""
        bot.application = mock_app
        bot.health_checker = MagicMock()
        bot.health_checker.start = AsyncMock()

        running_values = []

        async def capture_and_stop(_):
            running_values.append(bot._running)
            bot._running = False

        with patch("src.main.asyncio.sleep", side_effect=capture_and_stop):
            with patch("src.main.asyncio.create_task"):
                await bot.start()

        # _running was True when sleep was first called
        assert running_values[0] is True

    @pytest.mark.asyncio
    async def test_error_reraises(self, bot, mock_app):
        """Exception during start is re-raised."""
        bot.application = mock_app
        mock_app.start = AsyncMock(side_effect=RuntimeError("start failed"))

        with pytest.raises(RuntimeError, match="start failed"):
            await bot.start()


# ---- AddarrBot.stop ----


class TestStop:
    """Tests for AddarrBot.stop()."""

    @pytest.mark.asyncio
    async def test_full_shutdown(self, bot, mock_app):
        """Stops health checker, updater, application, and shuts down."""
        bot.application = mock_app
        bot._running = True
        bot.health_checker = MagicMock()
        bot.health_checker.stop = AsyncMock()

        await bot.stop()

        assert bot._running is False
        bot.health_checker.stop.assert_awaited_once()
        mock_app.updater.stop.assert_awaited_once()
        mock_app.stop.assert_awaited_once()
        mock_app.shutdown.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_application_is_none(self, bot):
        """No-op when application is None."""
        bot.application = None
        await bot.stop()  # Should not raise

    @pytest.mark.asyncio
    async def test_updater_not_running(self, bot, mock_app):
        """Skips updater.stop() when updater is not running."""
        bot.application = mock_app
        mock_app.updater.running = False
        bot.health_checker = MagicMock()
        bot.health_checker.stop = AsyncMock()

        await bot.stop()

        mock_app.updater.stop.assert_not_awaited()
        mock_app.stop.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_error_swallowed(self, bot, mock_app):
        """Exceptions during shutdown are swallowed."""
        bot.application = mock_app
        bot.health_checker = MagicMock()
        bot.health_checker.stop = AsyncMock(
            side_effect=RuntimeError("health stop failed")
        )

        # Should not raise
        await bot.stop()


# ---- Webhook lifecycle integration ----


class TestWebhookLifecycleIntegration:
    """Tests for webhook server start/stop in AddarrBot lifecycle."""

    @pytest.mark.asyncio
    async def test_webhook_starts_when_enabled(self, bot, mock_app):
        """Webhook server starts when webhooks.enable is True."""
        bot.application = mock_app
        bot.health_checker = MagicMock()
        bot.health_checker.start = AsyncMock()

        mock_ws = MagicMock()
        mock_ws.is_enabled.return_value = True
        mock_ws.start = AsyncMock()

        mock_ns = MagicMock()

        async def stop_after_first_sleep(_):
            bot._running = False

        with patch("src.main.asyncio.sleep", side_effect=stop_after_first_sleep):
            with patch("src.main.asyncio.create_task"):
                with patch("src.main.WebhookService", return_value=mock_ws):
                    with patch("src.main.NotificationService", return_value=mock_ns):
                        await bot.start()

        mock_ws.start.assert_awaited_once()
        mock_ns.set_bot.assert_called_once_with(mock_app.bot)

    @pytest.mark.asyncio
    async def test_webhook_does_not_start_when_disabled(self, bot, mock_app):
        """Webhook server does NOT start when webhooks.enable is False."""
        bot.application = mock_app
        bot.health_checker = MagicMock()
        bot.health_checker.start = AsyncMock()

        mock_ws = MagicMock()
        mock_ws.is_enabled.return_value = False
        mock_ws.start = AsyncMock()

        async def stop_after_first_sleep(_):
            bot._running = False

        with patch("src.main.asyncio.sleep", side_effect=stop_after_first_sleep):
            with patch("src.main.asyncio.create_task"):
                with patch("src.main.WebhookService", return_value=mock_ws):
                    with patch("src.main.NotificationService"):
                        await bot.start()

        mock_ws.start.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_stop_calls_webhook_stop(self, bot, mock_app):
        """stop() calls webhook_service.stop() when webhook was started."""
        bot.application = mock_app
        bot._running = True
        bot.health_checker = MagicMock()
        bot.health_checker.stop = AsyncMock()

        mock_ws = MagicMock()
        mock_ws.stop = AsyncMock()
        bot._webhook_service = mock_ws

        await bot.stop()

        mock_ws.stop.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_notification_service_set_bot_called(self, bot, mock_app):
        """NotificationService.set_bot() is called with application.bot."""
        bot.application = mock_app
        bot.health_checker = MagicMock()
        bot.health_checker.start = AsyncMock()

        mock_ns = MagicMock()
        mock_ws = MagicMock()
        mock_ws.is_enabled.return_value = False

        async def stop_after_first_sleep(_):
            bot._running = False

        with patch("src.main.asyncio.sleep", side_effect=stop_after_first_sleep):
            with patch("src.main.asyncio.create_task"):
                with patch("src.main.NotificationService", return_value=mock_ns):
                    with patch("src.main.WebhookService", return_value=mock_ws):
                        await bot.start()

        mock_ns.set_bot.assert_called_once_with(mock_app.bot)


# ---- main() ----


class TestMain:
    """Tests for the main() async entry point."""

    @pytest.mark.asyncio
    @patch("src.main.AddarrBot")
    async def test_start_bot_start_error_stops_and_exits(self, mock_bot_cls):
        """When bot.start() raises, bot is stopped and sys.exit(1) called."""
        mock_bot = MagicMock()
        mock_bot.initialize = AsyncMock()  # succeeds
        mock_bot.start = AsyncMock(side_effect=RuntimeError("start fail"))
        mock_bot.stop = AsyncMock()
        mock_bot_cls.return_value = mock_bot

        with pytest.raises(SystemExit) as exc_info:
            await main()

        mock_bot.stop.assert_awaited()
        assert exc_info.value.code == 1

    @pytest.mark.asyncio
    @patch("src.main.AddarrBot")
    async def test_start_bot_error_stops_and_exits(self, mock_bot_cls):
        """When start_bot raises, bot is stopped and sys.exit(1) called."""
        mock_bot = MagicMock()
        mock_bot.initialize = AsyncMock(side_effect=RuntimeError("init fail"))
        mock_bot.stop = AsyncMock()
        mock_bot.start = AsyncMock()
        mock_bot_cls.return_value = mock_bot

        with pytest.raises(SystemExit) as exc_info:
            await main()

        mock_bot.stop.assert_awaited()
        assert exc_info.value.code == 1

    @pytest.mark.asyncio
    @patch("src.main.AddarrBot")
    async def test_signal_handler_registration(self, mock_bot_cls):
        """Signal handlers are registered for SIGINT and SIGTERM."""
        mock_bot = MagicMock()
        mock_bot.initialize = AsyncMock(
            side_effect=RuntimeError("stop early")
        )
        mock_bot.stop = AsyncMock()
        mock_bot_cls.return_value = mock_bot

        mock_loop = MagicMock()
        mock_loop.add_signal_handler = MagicMock()

        with (
            patch("src.main.asyncio.get_running_loop", return_value=mock_loop),
            pytest.raises(SystemExit),
        ):
            await main()

        # SIGINT and SIGTERM handlers registered
        assert mock_loop.add_signal_handler.call_count == 2
        sig_args = [
            c.args[0] for c in mock_loop.add_signal_handler.call_args_list
        ]
        assert signal.SIGINT in sig_args
        assert signal.SIGTERM in sig_args

    @pytest.mark.asyncio
    @patch("src.main.AddarrBot")
    async def test_windows_signal_fallback(self, mock_bot_cls):
        """Falls back to signal.signal on Windows (NotImplementedError)."""
        mock_bot = MagicMock()
        mock_bot.initialize = AsyncMock(
            side_effect=RuntimeError("stop early")
        )
        mock_bot.stop = AsyncMock()
        mock_bot_cls.return_value = mock_bot

        mock_loop = MagicMock()
        mock_loop.add_signal_handler.side_effect = NotImplementedError

        with (
            patch(
                "src.main.asyncio.get_running_loop", return_value=mock_loop
            ),
            patch("src.main.signal.signal") as mock_signal,
            pytest.raises(SystemExit),
        ):
            await main()

        # Fell back to signal.signal for both SIGINT and SIGTERM
        assert mock_signal.call_count == 2
        sig_args = [c.args[0] for c in mock_signal.call_args_list]
        assert signal.SIGINT in sig_args
        assert signal.SIGTERM in sig_args

    @pytest.mark.asyncio
    @patch("src.main.AddarrBot")
    async def test_keyboard_interrupt_stops_bot(self, mock_bot_cls):
        """KeyboardInterrupt triggers bot.stop()."""
        mock_bot = MagicMock()
        mock_bot.stop = AsyncMock()
        mock_bot_cls.return_value = mock_bot

        # Make start_bot raise KeyboardInterrupt at the top-level try
        with (
            patch(
                "src.main.asyncio.get_running_loop",
                side_effect=KeyboardInterrupt,
            ),
        ):
            await main()

        mock_bot.stop.assert_awaited()

    @pytest.mark.asyncio
    @patch("src.main.AddarrBot")
    async def test_generic_exception_exits(self, mock_bot_cls):
        """Generic exception at top level triggers sys.exit(1)."""
        mock_bot = MagicMock()
        mock_bot_cls.return_value = mock_bot

        with (
            patch(
                "src.main.asyncio.get_running_loop",
                side_effect=RuntimeError("fatal"),
            ),
            pytest.raises(SystemExit) as exc_info,
        ):
            await main()

        assert exc_info.value.code == 1


# ---- run_bot() ----


class TestRunBot:
    """Tests for the run_bot() sync entry point."""

    @patch("src.main.asyncio.run")
    def test_calls_asyncio_run(self, mock_run):
        """run_bot() calls asyncio.run(main())."""
        run_bot()
        mock_run.assert_called_once()
        # Close the unawaited coroutine to suppress RuntimeWarning
        mock_run.call_args[0][0].close()

    @patch("src.main.asyncio.run", side_effect=KeyboardInterrupt)
    def test_keyboard_interrupt(self, mock_run):
        """KeyboardInterrupt is caught gracefully."""
        run_bot()  # Should not raise
        mock_run.call_args[0][0].close()

    @patch("src.main.asyncio.run", side_effect=RuntimeError("fatal"))
    def test_generic_exception_exits(self, mock_run):
        """Generic exception triggers sys.exit(1)."""
        with pytest.raises(SystemExit) as exc_info:
            run_bot()
        assert exc_info.value.code == 1
        mock_run.call_args[0][0].close()


# ---- AddarrBot._register_commands ----


class TestRegisterCommands:
    """Tests for AddarrBot._register_commands()."""

    @pytest.mark.asyncio
    @patch("src.main.show_welcome_screen")
    @patch("src.main.check_config")
    @patch("src.main.health_service")
    @patch("src.main.display_health_status", return_value=True)
    @patch("src.main.Application")
    async def test_register_commands_called_during_initialize(
        self, mock_app_cls, mock_display, mock_hs, mock_cc, mock_sw
    ):
        """_register_commands is called after application.initialize()."""
        mock_hs.run_health_checks = AsyncMock(return_value={})
        app = _make_mock_application()
        app.bot = AsyncMock()
        app.bot.set_my_commands = AsyncMock()
        mock_app_cls.builder.return_value.token.return_value.build.return_value = app

        bot = AddarrBot()
        with patch.multiple("src.main", **_make_handler_patches()):
            await bot.initialize()

        # set_my_commands should have been called at least once (default scope)
        app.bot.set_my_commands.assert_called()

    @pytest.mark.asyncio
    async def test_sets_default_scope_commands(self, bot, mock_app):
        """Sets default (unauthenticated) commands via BotCommandScopeDefault."""
        from telegram import BotCommandScopeDefault

        mock_app.bot = AsyncMock()
        mock_app.bot.set_my_commands = AsyncMock()
        bot.application = mock_app

        from src.bot.handlers.auth import AuthHandler
        AuthHandler._authenticated_users = set()  # No authenticated users

        await bot._register_commands()

        # Called once for default scope (no authenticated users)
        mock_app.bot.set_my_commands.assert_called_once()
        call_args = mock_app.bot.set_my_commands.call_args
        scope = call_args.kwargs.get("scope")
        assert isinstance(scope, BotCommandScopeDefault)

    @pytest.mark.asyncio
    async def test_sets_per_user_commands_for_authenticated(self, bot, mock_app):
        """Sets per-user commands for each authenticated user."""
        from telegram import BotCommandScopeChat

        mock_app.bot = AsyncMock()
        mock_app.bot.set_my_commands = AsyncMock()
        bot.application = mock_app

        from src.bot.handlers.auth import AuthHandler
        AuthHandler._authenticated_users = {111, 222}

        await bot._register_commands()

        # 1 default + 2 per-user = 3 calls
        assert mock_app.bot.set_my_commands.call_count == 3

        # Check that at least one call used BotCommandScopeChat
        scopes = [
            c.kwargs.get("scope")
            for c in mock_app.bot.set_my_commands.call_args_list
        ]
        chat_scopes = [s for s in scopes if isinstance(s, BotCommandScopeChat)]
        assert len(chat_scopes) == 2

    @pytest.mark.asyncio
    async def test_per_user_failure_does_not_block_others(self, bot, mock_app):
        """If one user's set_my_commands fails, others still get commands."""
        mock_app.bot = AsyncMock()

        call_count = 0

        async def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            # Fail on second call (first per-user), succeed on others
            if call_count == 2:
                raise Exception("Chat not found")

        mock_app.bot.set_my_commands = AsyncMock(side_effect=side_effect)
        bot.application = mock_app

        from src.bot.handlers.auth import AuthHandler
        AuthHandler._authenticated_users = {111, 222}

        # Should not raise
        await bot._register_commands()

        # All 3 calls were attempted (1 default + 2 per-user)
        assert call_count == 3

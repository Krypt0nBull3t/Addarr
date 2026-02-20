"""Tests for src/bot/handlers/settings.py"""

import pytest
from unittest.mock import AsyncMock
from telegram.ext import ConversationHandler

from src.bot.states import States


class TestSettingsHandlerBasics:
    """Basic handler structure tests"""

    def test_get_handler_returns_list(self, settings_handler):
        """get_handler() returns a list of handlers"""
        handlers = settings_handler.get_handler()
        assert isinstance(handlers, list)
        assert len(handlers) > 0

    @pytest.mark.asyncio
    async def test_handle_settings_shows_menu(
        self, settings_handler, make_update, make_context
    ):
        """/settings shows settings menu keyboard"""
        update = make_update(text="/settings")
        context = make_context()

        result = await settings_handler.handle_settings(update, context)

        assert result == States.SETTINGS_MENU
        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args
        assert "Settings" in call_args.args[0] or "⚙️" in call_args.args[0]
        assert call_args.kwargs.get("reply_markup") is not None

    @pytest.mark.asyncio
    async def test_handle_settings_rejects_non_admin(
        self, settings_handler, make_update, make_context
    ):
        """Non-admin users are rejected via text message"""
        settings_handler._mock_is_admin.return_value = False

        update = make_update(text="/settings")
        context = make_context()

        result = await settings_handler.handle_settings(update, context)

        assert result == ConversationHandler.END

    @pytest.mark.asyncio
    async def test_handle_settings_rejects_non_admin_callback(
        self, settings_handler, make_update, make_context
    ):
        """Non-admin users are rejected via callback query"""
        settings_handler._mock_is_admin.return_value = False

        update = make_update(callback_data="menu_settings")
        context = make_context()

        result = await settings_handler.handle_settings(update, context)

        assert result == ConversationHandler.END
        update.callback_query.answer.assert_awaited_once()
        update.callback_query.message.edit_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_settings_callback(
        self, settings_handler, make_update, make_context
    ):
        """/settings via callback query works"""
        update = make_update(callback_data="menu_settings")
        context = make_context()

        result = await settings_handler.handle_settings(update, context)

        assert result == States.SETTINGS_MENU
        update.callback_query.message.edit_text.assert_called_once()


class TestLanguageFlow:
    """Language selection flow tests"""

    @pytest.mark.asyncio
    async def test_handle_language_menu_shows_keyboard(
        self, settings_handler, make_update, make_context
    ):
        """Clicking settings_language shows language keyboard"""
        update = make_update(callback_data="settings_language")
        context = make_context()

        result = await settings_handler.handle_language_menu(update, context)

        assert result == States.SETTINGS_LANGUAGE
        update.callback_query.message.edit_text.assert_called_once()
        call_args = update.callback_query.message.edit_text.call_args
        assert call_args.kwargs.get("reply_markup") is not None

    @pytest.mark.asyncio
    async def test_handle_language_select_updates_config(
        self, settings_handler, make_update, make_context
    ):
        """Selecting a language calls config.update_nested and save"""
        update = make_update(callback_data="lang_de-de")
        context = make_context()

        result = await settings_handler.handle_language_select(update, context)

        assert result == States.SETTINGS_MENU
        settings_handler._mock_cfg.update_nested.assert_called_with(
            "language", "de-de"
        )
        settings_handler._mock_cfg.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_language_select_confirms_to_user(
        self, settings_handler, make_update, make_context
    ):
        """Selecting a language sends confirmation message"""
        update = make_update(callback_data="lang_fr-fr")
        context = make_context()

        await settings_handler.handle_language_select(update, context)

        update.callback_query.message.edit_text.assert_called_once()
        call_args = update.callback_query.message.edit_text.call_args
        assert "✅" in call_args.args[0]

    @pytest.mark.asyncio
    async def test_handle_language_back_returns_to_menu(
        self, settings_handler, make_update, make_context
    ):
        """Back button returns to settings menu"""
        update = make_update(callback_data="settings_back")
        context = make_context()

        result = await settings_handler.handle_settings_from_callback(
            update, context
        )

        assert result == States.SETTINGS_MENU


class TestServiceFlow:
    """Service enable/disable flow tests"""

    @pytest.mark.asyncio
    async def test_handle_service_menu_shows_service_settings(
        self, settings_handler, make_update, make_context
    ):
        """Clicking settings_radarr shows service settings"""
        update = make_update(callback_data="settings_radarr")
        context = make_context()

        result = await settings_handler.handle_service_menu(update, context)

        assert result == States.SETTINGS_SERVICE
        update.callback_query.message.edit_text.assert_called_once()
        assert context.user_data["settings_service"] == "radarr"

    @pytest.mark.asyncio
    async def test_handle_service_toggle_enables(
        self, settings_handler, make_update, make_context
    ):
        """Toggling a disabled service enables it"""
        # Radarr is enabled in MOCK_CONFIG_DATA, so toggling disables
        # Let's mock config.get to return disabled
        settings_handler._mock_cfg.get.side_effect = lambda k, d=None: (
            {"enable": False} if k == "radarr" else d
        )

        update = make_update(callback_data="svc_toggle_radarr")
        context = make_context()

        result = await settings_handler.handle_service_toggle(update, context)

        assert result == States.SETTINGS_MENU
        settings_handler._mock_cfg.update_nested.assert_called_with(
            "radarr.enable", True
        )
        settings_handler._mock_cfg.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_service_toggle_disables(
        self, settings_handler, make_update, make_context
    ):
        """Toggling an enabled service disables it"""
        settings_handler._mock_cfg.get.side_effect = lambda k, d=None: (
            {"enable": True} if k == "radarr" else d
        )

        update = make_update(callback_data="svc_toggle_radarr")
        context = make_context()

        result = await settings_handler.handle_service_toggle(update, context)

        assert result == States.SETTINGS_MENU
        settings_handler._mock_cfg.update_nested.assert_called_with(
            "radarr.enable", False
        )
        settings_handler._mock_cfg.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_service_back_returns_to_menu(
        self, settings_handler, make_update, make_context
    ):
        """Back button returns to settings menu"""
        update = make_update(callback_data="settings_back")
        context = make_context()

        result = await settings_handler.handle_settings_from_callback(
            update, context
        )

        assert result == States.SETTINGS_MENU


class TestQualityFlow:
    """Quality profile selection flow tests"""

    @pytest.mark.asyncio
    async def test_handle_quality_menu_fetches_profiles(
        self, settings_handler, make_update, make_context
    ):
        """Clicking quality button fetches profiles from API"""
        mock_profiles = [
            {"id": 1, "name": "Any"},
            {"id": 4, "name": "HD-1080p"},
        ]
        settings_handler._mock_service.radarr.get_quality_profiles = (
            AsyncMock(return_value=mock_profiles)
        )

        update = make_update(callback_data="svc_quality_radarr")
        context = make_context()

        result = await settings_handler.handle_quality_menu(update, context)

        assert result == States.SETTINGS_QUALITY
        settings_handler._mock_service.radarr.get_quality_profiles.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_quality_menu_shows_profiles(
        self, settings_handler, make_update, make_context
    ):
        """Profile buttons are shown"""
        mock_profiles = [
            {"id": 1, "name": "Any"},
            {"id": 4, "name": "HD-1080p"},
        ]
        settings_handler._mock_service.radarr.get_quality_profiles = (
            AsyncMock(return_value=mock_profiles)
        )

        update = make_update(callback_data="svc_quality_radarr")
        context = make_context()

        await settings_handler.handle_quality_menu(update, context)

        call_args = update.callback_query.message.edit_text.call_args
        keyboard = call_args.kwargs.get("reply_markup")
        assert keyboard is not None

    @pytest.mark.asyncio
    async def test_handle_quality_select_saves(
        self, settings_handler, make_update, make_context
    ):
        """Selecting a profile saves to config"""
        update = make_update(callback_data="setquality_radarr_4")
        context = make_context()

        result = await settings_handler.handle_quality_select(update, context)

        assert result == States.SETTINGS_MENU
        settings_handler._mock_cfg.update_nested.assert_called_with(
            "radarr.quality.defaultProfileId", 4
        )
        settings_handler._mock_cfg.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_quality_api_error(
        self, settings_handler, make_update, make_context
    ):
        """API errors are handled gracefully"""
        settings_handler._mock_service.radarr.get_quality_profiles = (
            AsyncMock(side_effect=Exception("Connection error"))
        )

        update = make_update(callback_data="svc_quality_radarr")
        context = make_context()

        result = await settings_handler.handle_quality_menu(update, context)

        assert result == States.SETTINGS_MENU
        call_args = update.callback_query.message.edit_text.call_args
        assert "❌" in call_args.args[0]

    @pytest.mark.asyncio
    async def test_handle_quality_no_profiles(
        self, settings_handler, make_update, make_context
    ):
        """Empty profiles list shows error message"""
        settings_handler._mock_service.radarr.get_quality_profiles = (
            AsyncMock(return_value=[])
        )

        update = make_update(callback_data="svc_quality_radarr")
        context = make_context()

        result = await settings_handler.handle_quality_menu(update, context)

        assert result == States.SETTINGS_MENU

    @pytest.mark.asyncio
    async def test_handle_quality_menu_sonarr(
        self, settings_handler, make_update, make_context
    ):
        """Quality profiles fetched for sonarr"""
        mock_profiles = [{"id": 1, "name": "Any"}]
        settings_handler._mock_service.sonarr.get_quality_profiles = (
            AsyncMock(return_value=mock_profiles)
        )

        update = make_update(callback_data="svc_quality_sonarr")
        context = make_context()

        result = await settings_handler.handle_quality_menu(update, context)

        assert result == States.SETTINGS_QUALITY
        settings_handler._mock_service.sonarr.get_quality_profiles.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_quality_menu_lidarr(
        self, settings_handler, make_update, make_context
    ):
        """Quality profiles fetched for lidarr"""
        mock_profiles = [{"id": 1, "name": "Any"}]
        settings_handler._mock_service.lidarr.get_quality_profiles = (
            AsyncMock(return_value=mock_profiles)
        )

        update = make_update(callback_data="svc_quality_lidarr")
        context = make_context()

        result = await settings_handler.handle_quality_menu(update, context)

        assert result == States.SETTINGS_QUALITY
        settings_handler._mock_service.lidarr.get_quality_profiles.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_quality_menu_unknown_service(
        self, settings_handler, make_update, make_context
    ):
        """Unknown service returns to settings menu with no profiles"""
        update = make_update(callback_data="svc_quality_unknown")
        context = make_context()

        result = await settings_handler.handle_quality_menu(update, context)

        assert result == States.SETTINGS_MENU

    @pytest.mark.asyncio
    async def test_handle_quality_back_returns_to_menu(
        self, settings_handler, make_update, make_context
    ):
        """Back button returns to settings menu"""
        update = make_update(callback_data="settings_back")
        context = make_context()

        result = await settings_handler.handle_settings_from_callback(
            update, context
        )

        assert result == States.SETTINGS_MENU


class TestDownloadsFlow:
    """Downloads sub-menu flow tests"""

    @pytest.mark.asyncio
    async def test_handle_downloads_menu_shows_keyboard(
        self, settings_handler, make_update, make_context
    ):
        """Clicking settings_downloads shows downloads keyboard"""
        update = make_update(callback_data="settings_downloads")
        context = make_context()

        result = await settings_handler.handle_downloads_menu(
            update, context
        )

        assert result == States.SETTINGS_DOWNLOADS
        update.callback_query.message.edit_text.assert_called_once()
        call_args = update.callback_query.message.edit_text.call_args
        assert call_args.kwargs.get("reply_markup") is not None

    @pytest.mark.asyncio
    async def test_handle_transmission_settings(
        self, settings_handler, make_update, make_context
    ):
        """Clicking dl_transmission shows transmission settings keyboard"""
        update = make_update(callback_data="dl_transmission")
        context = make_context()

        result = await settings_handler.handle_transmission_settings(
            update, context
        )

        assert result == States.SETTINGS_DOWNLOADS
        update.callback_query.message.edit_text.assert_called_once()
        call_args = update.callback_query.message.edit_text.call_args
        assert call_args.kwargs.get("reply_markup") is not None

    @pytest.mark.asyncio
    async def test_handle_transmission_toggle(
        self, settings_handler, make_update, make_context
    ):
        """Clicking dl_trans_toggle toggles transmission.enable in config"""
        update = make_update(callback_data="dl_trans_toggle")
        context = make_context()

        result = await settings_handler.handle_transmission_toggle(
            update, context
        )

        assert result == States.SETTINGS_DOWNLOADS
        settings_handler._mock_cfg.update_nested.assert_called_with(
            "transmission.enable", True
        )
        settings_handler._mock_cfg.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_transmission_turtle(
        self, settings_handler, make_update, make_context
    ):
        """Clicking dl_trans_turtle toggles turtle mode via service"""
        update = make_update(callback_data="dl_trans_turtle")
        context = make_context()

        result = await settings_handler.handle_transmission_turtle(
            update, context
        )

        assert result == States.SETTINGS_DOWNLOADS
        settings_handler._mock_trans.set_alt_speed.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_handle_transmission_turtle_error(
        self, settings_handler, make_update, make_context
    ):
        """Turtle mode error is handled gracefully"""
        settings_handler._mock_trans.set_alt_speed = AsyncMock(
            return_value=False
        )
        update = make_update(callback_data="dl_trans_turtle")
        context = make_context()

        result = await settings_handler.handle_transmission_turtle(
            update, context
        )

        assert result == States.SETTINGS_DOWNLOADS
        call_args = update.callback_query.message.edit_text.call_args
        assert "❌" in call_args.args[0]

    @pytest.mark.asyncio
    async def test_handle_sabnzbd_settings(
        self, settings_handler, make_update, make_context
    ):
        """Clicking dl_sabnzbd shows sabnzbd settings keyboard"""
        update = make_update(callback_data="dl_sabnzbd")
        context = make_context()

        result = await settings_handler.handle_sabnzbd_settings(
            update, context
        )

        assert result == States.SETTINGS_DOWNLOADS
        update.callback_query.message.edit_text.assert_called_once()
        call_args = update.callback_query.message.edit_text.call_args
        assert call_args.kwargs.get("reply_markup") is not None

    @pytest.mark.asyncio
    async def test_handle_sabnzbd_toggle(
        self, settings_handler, make_update, make_context
    ):
        """Clicking dl_sab_toggle toggles sabnzbd.enable in config"""
        update = make_update(callback_data="dl_sab_toggle")
        context = make_context()

        result = await settings_handler.handle_sabnzbd_toggle(
            update, context
        )

        assert result == States.SETTINGS_DOWNLOADS
        settings_handler._mock_cfg.update_nested.assert_called_with(
            "sabnzbd.enable", True
        )
        settings_handler._mock_cfg.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_sabnzbd_speed(
        self, settings_handler, make_update, make_context
    ):
        """Clicking dl_sab_speed shows speed limit options"""
        update = make_update(callback_data="dl_sab_speed")
        context = make_context()

        result = await settings_handler.handle_sabnzbd_speed(
            update, context
        )

        assert result == States.SETTINGS_DOWNLOADS
        update.callback_query.message.edit_text.assert_called_once()
        call_args = update.callback_query.message.edit_text.call_args
        assert call_args.kwargs.get("reply_markup") is not None

    @pytest.mark.asyncio
    async def test_handle_sabnzbd_pause(
        self, settings_handler, make_update, make_context
    ):
        """Clicking dl_sab_pause pauses the queue"""
        update = make_update(callback_data="dl_sab_pause")
        context = make_context()

        result = await settings_handler.handle_sabnzbd_pause_resume(
            update, context
        )

        assert result == States.SETTINGS_DOWNLOADS
        settings_handler._mock_sab.pause_queue.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_handle_sabnzbd_resume(
        self, settings_handler, make_update, make_context
    ):
        """Clicking dl_sab_resume resumes the queue"""
        update = make_update(callback_data="dl_sab_resume")
        context = make_context()

        result = await settings_handler.handle_sabnzbd_pause_resume(
            update, context
        )

        assert result == States.SETTINGS_DOWNLOADS
        settings_handler._mock_sab.resume_queue.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_handle_downloads_back(
        self, settings_handler, make_update, make_context
    ):
        """Back from downloads returns to settings menu"""
        update = make_update(callback_data="dl_back")
        context = make_context()

        result = await settings_handler.handle_settings_from_callback(
            update, context
        )

        assert result == States.SETTINGS_MENU


class TestUsersFlow:
    """Users sub-menu flow tests"""

    @pytest.mark.asyncio
    async def test_handle_users_menu_shows_keyboard(
        self, settings_handler, make_update, make_context
    ):
        """Clicking settings_users shows users keyboard"""
        update = make_update(callback_data="settings_users")
        context = make_context()

        result = await settings_handler.handle_users_menu(update, context)

        assert result == States.SETTINGS_USERS
        update.callback_query.message.edit_text.assert_called_once()
        call_args = update.callback_query.message.edit_text.call_args
        assert call_args.kwargs.get("reply_markup") is not None

    @pytest.mark.asyncio
    async def test_handle_users_toggle_admin(
        self, settings_handler, make_update, make_context
    ):
        """Clicking usr_toggle_admin flips security.enableAdmin"""
        update = make_update(callback_data="usr_toggle_admin")
        context = make_context()

        result = await settings_handler.handle_users_toggle(update, context)

        assert result == States.SETTINGS_USERS
        settings_handler._mock_cfg.update_nested.assert_called_with(
            "security.enableAdmin", True
        )
        settings_handler._mock_cfg.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_users_toggle_allowlist(
        self, settings_handler, make_update, make_context
    ):
        """Clicking usr_toggle_allowlist flips security.enableAllowlist"""
        update = make_update(callback_data="usr_toggle_allowlist")
        context = make_context()

        result = await settings_handler.handle_users_toggle(update, context)

        assert result == States.SETTINGS_USERS
        settings_handler._mock_cfg.update_nested.assert_called_with(
            "security.enableAllowlist", True
        )
        settings_handler._mock_cfg.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_users_back(
        self, settings_handler, make_update, make_context
    ):
        """Back from users returns to settings menu"""
        update = make_update(callback_data="usr_back")
        context = make_context()

        result = await settings_handler.handle_settings_from_callback(
            update, context
        )

        assert result == States.SETTINGS_MENU


class TestSabnzbdInitError:
    """SABnzbd service initialization error handling"""

    def test_sabnzbd_service_none_when_valueerror(
        self, mock_media_service, mock_translation_service
    ):
        """SABnzbdService ValueError sets self.sabnzbd_service = None"""
        from unittest.mock import patch, MagicMock
        from tests.conftest import MOCK_CONFIG_DATA

        with (
            patch("src.bot.handlers.settings.TranslationService") as ts_cls,
            patch("src.bot.handlers.settings.MediaService") as ms_cls,
            patch("src.bot.handlers.settings.config") as cfg,
            patch("src.bot.handlers.settings.is_admin"),
            patch("src.bot.handlers.settings.TransmissionService"),
            patch(
                "src.bot.handlers.settings.SABnzbdService",
                side_effect=ValueError("SABnzbd not enabled"),
            ),
        ):
            ts_cls.return_value = mock_translation_service
            ms_cls.return_value = mock_media_service
            cfg.get = MagicMock(
                side_effect=lambda k, d=None: MOCK_CONFIG_DATA.get(k, d)
            )

            from src.bot.handlers.settings import SettingsHandler

            handler = SettingsHandler()
            assert handler.sabnzbd_service is None


class TestDownloadsEdgeCases:
    """Edge cases for downloads sub-menu handlers"""

    @pytest.mark.asyncio
    async def test_handle_sabnzbd_speed_applies_value(
        self, settings_handler, make_update, make_context
    ):
        """Selecting dl_sab_speed_25 applies 25% speed limit"""
        update = make_update(callback_data="dl_sab_speed_25")
        context = make_context()

        result = await settings_handler.handle_sabnzbd_speed(
            update, context
        )

        assert result == States.SETTINGS_DOWNLOADS
        settings_handler._mock_sab.set_speed_limit.assert_awaited_once_with(
            25
        )
        call_args = update.callback_query.message.edit_text.call_args
        assert "25%" in call_args.args[0]

    @pytest.mark.asyncio
    async def test_handle_sabnzbd_pause_when_service_none(
        self, settings_handler, make_update, make_context
    ):
        """Pause with sabnzbd_service=None shows not available message"""
        settings_handler.sabnzbd_service = None
        update = make_update(callback_data="dl_sab_pause")
        context = make_context()

        result = await settings_handler.handle_sabnzbd_pause_resume(
            update, context
        )

        assert result == States.SETTINGS_DOWNLOADS
        call_args = update.callback_query.message.edit_text.call_args
        assert "not available" in call_args.args[0].lower()


class TestUsersEdgeCases:
    """Edge cases for users sub-menu handlers"""

    @pytest.mark.asyncio
    async def test_handle_users_toggle_unknown_flag(
        self, settings_handler, make_update, make_context
    ):
        """Unknown toggle flag returns to users menu without config change"""
        update = make_update(callback_data="usr_toggle_unknown")
        context = make_context()

        result = await settings_handler.handle_users_toggle(update, context)

        assert result == States.SETTINGS_USERS
        settings_handler._mock_cfg.update_nested.assert_not_called()


class TestMisc:
    """Miscellaneous handler tests"""

    @pytest.mark.asyncio
    async def test_handle_back_ends_conversation(
        self, settings_handler, make_update, make_context
    ):
        """Back from settings menu ends conversation"""
        update = make_update(callback_data="settings_back")
        context = make_context()

        result = await settings_handler.handle_back(update, context)

        assert result == ConversationHandler.END

    @pytest.mark.asyncio
    async def test_handle_cancel_callback(
        self, settings_handler, make_update, make_context
    ):
        """Cancel via callback ends conversation"""
        update = make_update(callback_data="menu_cancel")
        context = make_context()

        result = await settings_handler.handle_cancel(update, context)

        assert result == ConversationHandler.END
        update.callback_query.message.edit_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_cancel_text(
        self, settings_handler, make_update, make_context
    ):
        """Cancel via /cancel command ends conversation"""
        update = make_update(text="/cancel")
        context = make_context()

        result = await settings_handler.handle_cancel(update, context)

        assert result == ConversationHandler.END
        update.message.reply_text.assert_called_once()

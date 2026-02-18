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


class TestMisc:
    """Miscellaneous handler tests"""

    @pytest.mark.asyncio
    async def test_handle_coming_soon(
        self, settings_handler, make_update, make_context
    ):
        """Coming soon sections show placeholder message"""
        update = make_update(callback_data="settings_downloads")
        context = make_context()

        result = await settings_handler.handle_coming_soon(update, context)

        assert result == States.SETTINGS_MENU
        call_args = update.callback_query.message.edit_text.call_args
        assert "Coming soon" in call_args.args[0]

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

"""
Shared fixtures for handler tests.

Handlers create service instances in __init__, so we must patch the service
constructors before instantiating handlers.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch


@pytest.fixture
def mock_media_service():
    """Mock MediaService with async methods."""
    service = MagicMock()
    service.search_movies = AsyncMock(return_value=[])
    service.search_series = AsyncMock(return_value=[])
    service.search_music = AsyncMock(return_value=[])
    service.add_movie = AsyncMock(return_value=(False, "Not found"))
    service.add_movie_with_profile = AsyncMock(return_value=(True, "Success"))
    service.add_series = AsyncMock(return_value=(False, "Not found"))
    service.add_series_with_profile = AsyncMock(return_value=(True, "Success"))
    service.add_music = AsyncMock(return_value=(False, "Not found"))
    service.add_music_with_profile = AsyncMock(return_value=(True, "Success"))
    service.get_radarr_status = AsyncMock(return_value=True)
    service.get_sonarr_status = AsyncMock(return_value=True)
    service.get_lidarr_status = AsyncMock(return_value=True)
    service.get_transmission_status = AsyncMock(return_value=False)
    service.get_sabnzbd_status = AsyncMock(return_value=False)
    service.get_movies = AsyncMock(return_value=[])
    service.get_series = AsyncMock(return_value=[])
    service.get_music = AsyncMock(return_value=[])
    service.get_movie = AsyncMock(return_value=None)
    service.delete_movie = AsyncMock(return_value=True)
    service.delete_series = AsyncMock(return_value=True)
    service.delete_music = AsyncMock(return_value=True)
    service.radarr = MagicMock()
    service.sonarr = MagicMock()
    service.lidarr = MagicMock()
    return service


@pytest.fixture
def mock_translation_service():
    """Mock TranslationService that returns keys as text."""
    service = MagicMock()
    service.get_text = MagicMock(side_effect=lambda key, **kw: key)
    service.get_message = MagicMock(side_effect=lambda key, **kw: key)
    service.current_language = "en-us"
    return service


@pytest.fixture
def mock_notification_service():
    """Mock NotificationService."""
    service = MagicMock()
    service.notify_admin = AsyncMock()
    service.notify_user = AsyncMock()
    service.notify_action = AsyncMock()
    return service


# ---------------------------------------------------------------------------
# Handler factory fixtures -- encapsulate patching + mock setup + auth
# ---------------------------------------------------------------------------


@pytest.fixture
def media_handler(mock_media_service, mock_translation_service):
    """Create a MediaHandler with patched services."""
    with (
        patch("src.bot.handlers.media.MediaService") as mock_ms_class,
        patch("src.bot.handlers.media.TranslationService") as mock_ts_class,
    ):
        mock_ts_class.return_value = mock_translation_service
        mock_ms_class.return_value = mock_media_service

        from src.bot.handlers.media import MediaHandler
        from src.bot.handlers.auth import AuthHandler

        AuthHandler._authenticated_users = {12345}
        handler = MediaHandler()
        handler._mock_service = mock_media_service
        handler._mock_ts = mock_translation_service
        yield handler


@pytest.fixture
def delete_handler(mock_media_service, mock_translation_service):
    """Create a DeleteHandler with patched services."""
    with (
        patch("src.bot.handlers.delete.MediaService") as mock_ms_class,
        patch("src.bot.handlers.delete.TranslationService") as mock_ts_class,
    ):
        mock_ts_class.return_value = mock_translation_service
        mock_ms_class.return_value = mock_media_service

        from src.bot.handlers.delete import DeleteHandler
        from src.bot.handlers.auth import AuthHandler

        AuthHandler._authenticated_users = {12345}
        handler = DeleteHandler()
        handler._mock_service = mock_media_service
        handler._mock_ts = mock_translation_service
        yield handler


@pytest.fixture
def start_handler(mock_media_service, mock_translation_service):
    """Create a StartHandler with patched services."""
    with (
        patch("src.bot.handlers.start.MediaHandler") as mock_mh_class,
        patch("src.bot.handlers.start.HelpHandler") as mock_hh_class,
        patch("src.bot.handlers.start.TranslationService") as mock_ts_class,
        patch("src.bot.handlers.start.get_main_menu_keyboard") as mock_kbd,
    ):
        mock_ts_class.return_value = mock_translation_service
        mock_media_handler = MagicMock()
        mock_media_handler.handle_status = AsyncMock()
        mock_media_handler.handle_settings = AsyncMock()
        mock_media_handler.handle_search = AsyncMock()
        mock_media_handler.handle_selection = AsyncMock()
        mock_media_handler.handle_navigation = AsyncMock()
        mock_media_handler.cancel_search = AsyncMock()
        mock_mh_class.return_value = mock_media_handler
        mock_help_handler = MagicMock()
        mock_help_handler.show_help = AsyncMock()
        mock_hh_class.return_value = mock_help_handler
        mock_kbd.return_value = MagicMock()

        from src.bot.handlers.start import StartHandler
        from src.bot.handlers.auth import AuthHandler

        AuthHandler._authenticated_users = {12345}
        handler = StartHandler()
        handler._mock_media_handler = mock_media_handler
        handler._mock_help_handler = mock_help_handler
        handler._mock_ts = mock_translation_service
        handler._mock_kbd = mock_kbd
        yield handler


@pytest.fixture
def status_handler(mock_media_service, mock_translation_service):
    """Create a StatusHandler with patched services."""
    with (
        patch("src.bot.handlers.status.MediaService") as mock_ms_class,
        patch("src.bot.handlers.status.TranslationService") as mock_ts_class,
        patch("src.bot.handlers.status.HealthService") as mock_hs_class,
    ):
        mock_ts_class.return_value = mock_translation_service
        mock_ms_class.return_value = mock_media_service
        mock_health = MagicMock()
        mock_health.get_status = MagicMock(return_value={
            "running": True,
            "check_interval": 5,
            "last_check": "2024-01-01 00:00:00",
            "unhealthy_services": [],
        })
        mock_health.run_health_checks = AsyncMock()
        mock_health.display_health_status = MagicMock(return_value="Status OK")
        mock_hs_class.return_value = mock_health

        from src.bot.handlers.status import StatusHandler
        from src.bot.handlers.auth import AuthHandler

        AuthHandler._authenticated_users = {12345}
        handler = StatusHandler()
        handler._mock_service = mock_media_service
        handler._mock_health = mock_health
        handler._mock_ts = mock_translation_service
        yield handler


@pytest.fixture
def transmission_handler(mock_translation_service):
    """Create a TransmissionHandler with patched services."""
    with (
        patch("src.bot.handlers.transmission.TransmissionService") as mock_ts_svc,
        patch("src.bot.handlers.transmission.TranslationService") as mock_ts_class,
    ):
        mock_ts_class.return_value = mock_translation_service
        mock_trans = MagicMock()
        mock_trans.is_enabled.return_value = True
        mock_trans.get_session = AsyncMock(return_value={"alt-speed-enabled": False})
        mock_trans.toggle_turtle_mode = AsyncMock(return_value=True)
        mock_ts_svc.return_value = mock_trans

        from src.bot.handlers.transmission import TransmissionHandler
        from src.bot.handlers.auth import AuthHandler

        AuthHandler._authenticated_users = {12345}
        handler = TransmissionHandler()
        handler._mock_trans = mock_trans
        handler._mock_ts = mock_translation_service
        yield handler


@pytest.fixture
def sabnzbd_handler(mock_translation_service):
    """Create a SABnzbdHandler with patched services."""
    with (
        patch("src.bot.handlers.sabnzbd.SABnzbdService") as mock_sab_svc,
        patch("src.bot.handlers.sabnzbd.TranslationService") as mock_ts_class,
    ):
        mock_ts_class.return_value = mock_translation_service
        mock_sab = MagicMock()
        mock_sab.is_enabled.return_value = True
        mock_sab.set_speed_limit = AsyncMock(return_value=True)
        mock_sab_svc.return_value = mock_sab

        from src.bot.handlers.sabnzbd import SABnzbdHandler
        from src.bot.handlers.auth import AuthHandler

        AuthHandler._authenticated_users = {12345}
        handler = SABnzbdHandler()
        handler._mock_sab = mock_sab
        handler._mock_ts = mock_translation_service
        yield handler


@pytest.fixture
def auth_handler():
    """Create an AuthHandler with patched dependencies."""
    with (
        patch("src.bot.handlers.auth.TranslationService") as mock_ts_class,
    ):
        mock_ts = MagicMock()
        mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
        mock_ts_class.return_value = mock_ts

        from src.bot.handlers.auth import AuthHandler

        AuthHandler._authenticated_users = set()
        handler = AuthHandler()
        handler._mock_ts = mock_ts
        yield handler


@pytest.fixture
def help_handler(mock_translation_service):
    """Create a HelpHandler with patched services."""
    with (
        patch("src.bot.handlers.help.TranslationService") as mock_ts_class,
    ):
        mock_ts_class.return_value = mock_translation_service

        from src.bot.handlers.help import HelpHandler
        from src.bot.handlers.auth import AuthHandler

        AuthHandler._authenticated_users = {12345}
        handler = HelpHandler()
        handler._mock_ts = mock_translation_service
        yield handler


@pytest.fixture
def system_handler():
    """Create a SystemHandler with patched services."""
    with (
        patch("src.bot.handlers.system.TranslationService") as mock_ts_class,
    ):
        mock_ts = MagicMock()
        mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
        mock_ts_class.return_value = mock_ts

        from src.bot.handlers.system import SystemHandler

        handler = SystemHandler()
        handler._mock_ts = mock_ts
        yield handler

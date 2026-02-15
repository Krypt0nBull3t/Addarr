"""
Shared fixtures for handler tests.

Handlers create service instances in __init__, so we must patch the service
constructors before instantiating handlers.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock


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

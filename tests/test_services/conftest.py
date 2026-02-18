"""
Shared fixtures for service tests.
"""

import pytest
from unittest.mock import AsyncMock


@pytest.fixture
def mock_radarr_client():
    client = AsyncMock()
    client.search = AsyncMock(return_value=[])
    client.get_movie = AsyncMock(return_value=None)
    client.add_movie = AsyncMock(return_value=(True, "Success"))
    client.get_root_folders = AsyncMock(return_value=["/movies"])
    client.get_quality_profiles = AsyncMock(
        return_value=[{"id": 1, "name": "HD-1080p"}]
    )
    client.get_movies = AsyncMock(return_value=[])
    client.get_movie_by_id = AsyncMock(return_value=None)
    client.delete_movie = AsyncMock(return_value=True)
    client.check_status = AsyncMock(return_value=True)
    return client


@pytest.fixture
def mock_sonarr_client():
    client = AsyncMock()
    client.search = AsyncMock(return_value=[])
    client.get_series = AsyncMock(return_value=None)
    client.add_series = AsyncMock(return_value=(True, "Success"))
    client.get_root_folders = AsyncMock(return_value=["/tv"])
    client.get_quality_profiles = AsyncMock(
        return_value=[{"id": 1, "name": "HD-1080p"}]
    )
    client.get_seasons = AsyncMock(return_value=[])
    client.get_all_series = AsyncMock(return_value=[])
    client.get_series_by_id = AsyncMock(return_value=None)
    client.delete_series = AsyncMock(return_value=True)
    client.check_status = AsyncMock(return_value=True)
    return client


@pytest.fixture
def mock_lidarr_client():
    client = AsyncMock()
    client.search = AsyncMock(return_value=[])
    client.get_artist = AsyncMock(return_value=None)
    client.add_artist = AsyncMock(return_value=(True, "Success"))
    client.get_root_folders = AsyncMock(return_value=["/music"])
    client.get_quality_profiles = AsyncMock(
        return_value=[{"id": 1, "name": "Lossless"}]
    )
    client.get_metadata_profiles = AsyncMock(
        return_value=[{"id": 1, "name": "Standard"}]
    )
    client.get_artists = AsyncMock(return_value=[])
    client.get_artist_by_id = AsyncMock(return_value=None)
    client.delete_artist = AsyncMock(return_value=True)
    client.check_status = AsyncMock(return_value=True)
    return client

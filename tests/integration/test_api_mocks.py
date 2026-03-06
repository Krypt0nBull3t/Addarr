"""
Tests for API mock helpers.

Validates that mock helpers correctly intercept aiohttp calls
for Radarr, Sonarr, and Lidarr API clients.
"""

import pytest

from tests.integration.api_mocks import RadarrMockHelper, SonarrMockHelper, LidarrMockHelper


@pytest.mark.asyncio
async def test_radarr_mock_search_returns_results(aio_mock):
    """Radarr mock helper intercepts search and returns configured results."""
    helper = RadarrMockHelper(aio_mock)
    helper.search_returns([
        {"tmdbId": 550, "title": "Fight Club", "year": 1999},
    ])

    from src.api.radarr import RadarrClient
    client = RadarrClient()
    try:
        results = await client.search("fight club")
        assert len(results) == 1
        assert results[0]["title"] == "Fight Club"
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_sonarr_mock_quality_profiles(aio_mock):
    """Sonarr mock helper intercepts quality profile endpoint."""
    helper = SonarrMockHelper(aio_mock)
    profiles = [
        {"id": 1, "name": "HD-1080p"},
        {"id": 2, "name": "Ultra-HD"},
    ]
    helper.quality_profiles(profiles)

    from src.api.sonarr import SonarrClient
    client = SonarrClient()
    try:
        result = await client.get_quality_profiles()
        assert len(result) == 2
        assert result[0]["name"] == "HD-1080p"
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_mock_helper_defaults_return_empty_search(aio_mock):
    """set_defaults() configures empty search results by default."""
    helper = RadarrMockHelper(aio_mock)
    helper.set_defaults()

    from src.api.radarr import RadarrClient
    client = RadarrClient()
    try:
        results = await client.search("nonexistent")
        assert results == []
    finally:
        await client.close()

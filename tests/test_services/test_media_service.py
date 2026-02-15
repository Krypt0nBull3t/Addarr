"""
Tests for src/services/media.py -- MediaService singleton.
"""

import pytest
from unittest.mock import AsyncMock

from src.services.media import MediaService


# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

SAMPLE_MOVIE = {
    "tmdbId": 550,
    "title": "Fight Club",
    "year": 1999,
    "overview": "An insomniac office worker...",
    "images": [],
    "ratings": {},
    "genres": ["Drama"],
    "studio": "Fox",
    "status": "released",
    "runtime": 139,
}

SAMPLE_SERIES = {
    "tvdbId": 81189,
    "title": "Breaking Bad",
    "year": 2008,
    "overview": "A high school chemistry teacher...",
    "images": [],
    "ratings": {},
    "genres": ["Drama"],
    "network": "AMC",
    "studio": "Sony",
    "status": "ended",
    "runtime": 47,
    "seasons": [{"seasonNumber": 1}, {"seasonNumber": 2}],
}

SAMPLE_ARTIST = {
    "foreignArtistId": "some-mbid-123",
    "artistName": "Radiohead",
    "overview": "English rock band...",
    "images": [],
    "ratings": {"value": 9.1},
    "genres": ["Alternative Rock"],
    "statistics": {"yearStart": 1985},
    "artistType": "Group",
    "status": "active",
}


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------


class TestMediaServiceSingleton:
    def test_singleton(self):
        a = MediaService()
        b = MediaService()
        assert a is b


# ---------------------------------------------------------------------------
# search_movies
# ---------------------------------------------------------------------------


class TestSearchMovies:
    @pytest.mark.asyncio
    async def test_search_movies_success(self, mock_radarr_client):
        service = MediaService()
        MediaService._radarr = mock_radarr_client
        mock_radarr_client.search.return_value = [SAMPLE_MOVIE]

        results = await service.search_movies("fight club")

        assert len(results) == 1
        assert results[0]["title"] == "Fight Club (1999)"
        assert results[0]["id"] == "550"
        mock_radarr_client.search.assert_awaited_once_with("fight club")

    @pytest.mark.asyncio
    async def test_search_movies_radarr_disabled(self):
        service = MediaService()
        MediaService._radarr = None

        with pytest.raises(ValueError, match="Radarr is not enabled"):
            await service.search_movies("anything")


# ---------------------------------------------------------------------------
# search_series
# ---------------------------------------------------------------------------


class TestSearchSeries:
    @pytest.mark.asyncio
    async def test_search_series_success(self, mock_sonarr_client):
        service = MediaService()
        MediaService._sonarr = mock_sonarr_client
        mock_sonarr_client.search.return_value = [SAMPLE_SERIES]

        results = await service.search_series("breaking bad")

        assert len(results) == 1
        assert results[0]["title"] == "Breaking Bad (2008)"
        assert results[0]["id"] == "81189"
        mock_sonarr_client.search.assert_awaited_once_with("breaking bad")


# ---------------------------------------------------------------------------
# search_music
# ---------------------------------------------------------------------------


class TestSearchMusic:
    @pytest.mark.asyncio
    async def test_search_music_success(self, mock_lidarr_client):
        service = MediaService()
        MediaService._lidarr = mock_lidarr_client
        mock_lidarr_client.search.return_value = [SAMPLE_ARTIST]

        results = await service.search_music("radiohead")

        assert len(results) == 1
        assert results[0]["title"] == "Radiohead"
        assert results[0]["id"] == "some-mbid-123"
        mock_lidarr_client.search.assert_awaited_once_with("radiohead")


# ---------------------------------------------------------------------------
# add_movie
# ---------------------------------------------------------------------------


class TestAddMovie:
    @pytest.mark.asyncio
    async def test_add_movie_returns_quality_selection(self, mock_radarr_client):
        service = MediaService()
        MediaService._radarr = mock_radarr_client

        mock_radarr_client.get_root_folders.return_value = ["/movies"]
        mock_radarr_client.get_quality_profiles.return_value = [
            {"id": 1, "name": "HD-1080p"}
        ]
        mock_radarr_client.get_movie.return_value = SAMPLE_MOVIE

        result = await service.add_movie("550")

        assert isinstance(result, dict)
        assert result["type"] == "quality_selection"
        assert result["profiles"] == [{"id": 1, "name": "HD-1080p"}]
        assert result["root_folder"] == "/movies"
        assert result["movie"] == SAMPLE_MOVIE

    @pytest.mark.asyncio
    async def test_add_movie_no_root_folders(self, mock_radarr_client):
        service = MediaService()
        MediaService._radarr = mock_radarr_client
        mock_radarr_client.get_root_folders.return_value = []

        result = await service.add_movie("550")

        assert result == (False, "No root folders configured in Radarr")

    @pytest.mark.asyncio
    async def test_add_movie_with_profile(self, mock_radarr_client):
        service = MediaService()
        MediaService._radarr = mock_radarr_client
        mock_radarr_client.add_movie.return_value = (True, "Added successfully")

        success, message = await service.add_movie_with_profile(
            "550", profile_id=1, root_folder="/movies"
        )

        assert success is True
        assert message == "Added successfully"
        mock_radarr_client.add_movie.assert_awaited_once_with(550, "/movies", 1)


# ---------------------------------------------------------------------------
# Status checks
# ---------------------------------------------------------------------------


class TestStatusChecks:
    @pytest.mark.asyncio
    async def test_get_radarr_status(self, mock_radarr_client):
        service = MediaService()
        MediaService._radarr = mock_radarr_client
        mock_radarr_client.check_status.return_value = True

        result = await service.get_radarr_status()
        assert result is True

    @pytest.mark.asyncio
    async def test_get_radarr_status_disabled(self):
        service = MediaService()
        MediaService._radarr = None

        result = await service.get_radarr_status()
        assert result is False

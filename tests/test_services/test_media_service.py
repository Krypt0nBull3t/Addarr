"""
Tests for src/services/media.py -- MediaService singleton.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

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
# _initialize_clients
# ---------------------------------------------------------------------------


class TestInitializeClients:
    def test_radarr_init_exception(self):
        with patch(
            "src.services.media.RadarrClient",
            side_effect=Exception("radarr init fail"),
        ):
            MediaService._radarr = None
            MediaService._initialize_clients()
            assert MediaService._radarr is None

    def test_sonarr_init_exception(self):
        with patch(
            "src.services.media.SonarrClient",
            side_effect=Exception("sonarr init fail"),
        ):
            MediaService._sonarr = None
            MediaService._initialize_clients()
            assert MediaService._sonarr is None

    def test_lidarr_init_exception(self):
        with patch(
            "src.services.media.LidarrClient",
            side_effect=Exception("lidarr init fail"),
        ):
            MediaService._lidarr = None
            MediaService._initialize_clients()
            assert MediaService._lidarr is None


# ---------------------------------------------------------------------------
# __init__ download clients
# ---------------------------------------------------------------------------


class TestInitDownloadClients:
    def test_transmission_enabled(self):
        import sys
        import types

        mock_client = MagicMock()
        mock_trans_module = types.ModuleType("src.api.transmission")
        mock_trans_module.TransmissionClient = MagicMock(return_value=mock_client)

        with patch(
            "src.services.media.config"
        ) as mock_config:
            mock_config.get.side_effect = lambda key, default=None: (
                {"enable": True} if key == "transmission"
                else default
            )
            with patch(
                "src.services.media.RadarrClient"
            ), patch(
                "src.services.media.SonarrClient"
            ), patch(
                "src.services.media.LidarrClient"
            ), patch.dict(sys.modules, {"src.api.transmission": mock_trans_module}):
                MediaService._instance = None
                MediaService._radarr = None
                MediaService._sonarr = None
                MediaService._lidarr = None
                service = MediaService()
                assert service.transmission is mock_client

    def test_transmission_import_error(self):
        """When TransmissionClient can't be imported, transmission stays None."""
        # The real src.api.transmission module has TransmissionAPI, not TransmissionClient.
        # So with the real module in sys.modules, the import in media.py will fail
        # with ImportError. We simulate this by making the module raise ImportError.
        import sys
        import types

        types.ModuleType("src.api.transmission")
        # Don't add TransmissionClient attribute - import will fail

        with patch(
            "src.services.media.config"
        ) as mock_config:
            mock_config.get.side_effect = lambda key, default=None: (
                {"enable": True} if key == "transmission"
                else default
            )
            with patch(
                "src.services.media.RadarrClient"
            ), patch(
                "src.services.media.SonarrClient"
            ), patch(
                "src.services.media.LidarrClient"
            ):
                # Remove the module from sys.modules so the import triggers fresh
                saved = sys.modules.pop("src.api.transmission", None)
                # Patch __import__ to raise ImportError for this module
                real_import = __builtins__["__import__"] if isinstance(__builtins__, dict) else __builtins__.__import__

                def _import(name, *args, **kwargs):
                    if name == "src.api.transmission":
                        raise ImportError("No module")
                    return real_import(name, *args, **kwargs)

                with patch("builtins.__import__", side_effect=_import):
                    MediaService._instance = None
                    MediaService._radarr = None
                    MediaService._sonarr = None
                    MediaService._lidarr = None
                    service = MediaService()
                    assert service.transmission is None

                if saved is not None:
                    sys.modules["src.api.transmission"] = saved

    def test_sabnzbd_enabled(self):
        import sys
        import types

        mock_client = MagicMock()
        mock_sab_module = types.ModuleType("src.api.sabnzbd")
        mock_sab_module.SabnzbdClient = MagicMock(return_value=mock_client)

        with patch(
            "src.services.media.config"
        ) as mock_config:
            mock_config.get.side_effect = lambda key, default=None: (
                {"enable": True} if key == "sabnzbd"
                else {"enable": False} if key == "transmission"
                else default
            )
            with patch(
                "src.services.media.RadarrClient"
            ), patch(
                "src.services.media.SonarrClient"
            ), patch(
                "src.services.media.LidarrClient"
            ), patch.dict(sys.modules, {"src.api.sabnzbd": mock_sab_module}):
                MediaService._instance = None
                MediaService._radarr = None
                MediaService._sonarr = None
                MediaService._lidarr = None
                service = MediaService()
                assert service.sabnzbd is mock_client

    def test_sabnzbd_import_error(self):
        import sys

        with patch(
            "src.services.media.config"
        ) as mock_config:
            mock_config.get.side_effect = lambda key, default=None: (
                {"enable": True} if key == "sabnzbd"
                else {"enable": False} if key == "transmission"
                else default
            )
            with patch(
                "src.services.media.RadarrClient"
            ), patch(
                "src.services.media.SonarrClient"
            ), patch(
                "src.services.media.LidarrClient"
            ):
                saved = sys.modules.pop("src.api.sabnzbd", None)
                real_import = __builtins__["__import__"] if isinstance(__builtins__, dict) else __builtins__.__import__

                def _import(name, *args, **kwargs):
                    if name == "src.api.sabnzbd":
                        raise ImportError("No module")
                    return real_import(name, *args, **kwargs)

                with patch("builtins.__import__", side_effect=_import):
                    MediaService._instance = None
                    MediaService._radarr = None
                    MediaService._sonarr = None
                    MediaService._lidarr = None
                    service = MediaService()
                    assert service.sabnzbd is None

                if saved is not None:
                    sys.modules["src.api.sabnzbd"] = saved


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

    @pytest.mark.asyncio
    async def test_search_movies_exception(self, mock_radarr_client):
        service = MediaService()
        MediaService._radarr = mock_radarr_client
        mock_radarr_client.search.side_effect = Exception("API error")

        with pytest.raises(Exception, match="API error"):
            await service.search_movies("fight club")


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

    @pytest.mark.asyncio
    async def test_search_series_disabled(self):
        service = MediaService()
        MediaService._sonarr = None

        with pytest.raises(ValueError, match="Sonarr is not enabled"):
            await service.search_series("anything")

    @pytest.mark.asyncio
    async def test_search_series_exception(self, mock_sonarr_client):
        service = MediaService()
        MediaService._sonarr = mock_sonarr_client
        mock_sonarr_client.search.side_effect = Exception("API error")

        with pytest.raises(Exception, match="API error"):
            await service.search_series("breaking bad")


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

    @pytest.mark.asyncio
    async def test_search_music_disabled(self):
        service = MediaService()
        MediaService._lidarr = None

        with pytest.raises(ValueError, match="Lidarr is not enabled"):
            await service.search_music("anything")

    @pytest.mark.asyncio
    async def test_search_music_exception(self, mock_lidarr_client):
        service = MediaService()
        MediaService._lidarr = mock_lidarr_client
        mock_lidarr_client.search.side_effect = Exception("API error")

        with pytest.raises(Exception, match="API error"):
            await service.search_music("radiohead")


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
    async def test_add_movie_no_quality_profiles(self, mock_radarr_client):
        service = MediaService()
        MediaService._radarr = mock_radarr_client
        mock_radarr_client.get_root_folders.return_value = ["/movies"]
        mock_radarr_client.get_quality_profiles.return_value = []

        result = await service.add_movie("550")

        assert result == (False, "No quality profiles configured in Radarr")

    @pytest.mark.asyncio
    async def test_add_movie_not_found(self, mock_radarr_client):
        service = MediaService()
        MediaService._radarr = mock_radarr_client
        mock_radarr_client.get_root_folders.return_value = ["/movies"]
        mock_radarr_client.get_quality_profiles.return_value = [
            {"id": 1, "name": "HD-1080p"}
        ]
        mock_radarr_client.get_movie.return_value = None

        result = await service.add_movie("999")

        assert result == (False, "Movie not found")

    @pytest.mark.asyncio
    async def test_add_movie_exception(self, mock_radarr_client):
        service = MediaService()
        MediaService._radarr = mock_radarr_client
        mock_radarr_client.get_root_folders.side_effect = Exception("API error")

        result = await service.add_movie("550")

        assert result == (False, "API error")

    @pytest.mark.asyncio
    async def test_add_movie_disabled(self):
        service = MediaService()
        MediaService._radarr = None

        with pytest.raises(ValueError, match="Radarr is not enabled"):
            await service.add_movie("550")


# ---------------------------------------------------------------------------
# add_movie_with_profile
# ---------------------------------------------------------------------------


class TestAddMovieWithProfile:
    @pytest.mark.asyncio
    async def test_add_movie_with_profile_success(self, mock_radarr_client):
        service = MediaService()
        MediaService._radarr = mock_radarr_client
        mock_radarr_client.add_movie.return_value = (True, "Added successfully")

        success, message = await service.add_movie_with_profile(
            "550", profile_id=1, root_folder="/movies"
        )

        assert success is True
        assert message == "Added successfully"
        mock_radarr_client.add_movie.assert_awaited_once_with(550, "/movies", 1)

    @pytest.mark.asyncio
    async def test_add_movie_with_profile_failure(self, mock_radarr_client):
        service = MediaService()
        MediaService._radarr = mock_radarr_client
        mock_radarr_client.add_movie.return_value = (False, "Already exists")

        success, message = await service.add_movie_with_profile(
            "550", profile_id=1, root_folder="/movies"
        )

        assert success is False
        assert message == "Already exists"

    @pytest.mark.asyncio
    async def test_add_movie_with_profile_exception(self, mock_radarr_client):
        service = MediaService()
        MediaService._radarr = mock_radarr_client
        mock_radarr_client.add_movie.side_effect = Exception("API error")

        success, message = await service.add_movie_with_profile(
            "550", profile_id=1, root_folder="/movies"
        )

        assert success is False
        assert message == "API error"

    @pytest.mark.asyncio
    async def test_add_movie_with_profile_disabled(self):
        service = MediaService()
        MediaService._radarr = None

        with pytest.raises(ValueError, match="Radarr is not enabled"):
            await service.add_movie_with_profile(
                "550", profile_id=1, root_folder="/movies"
            )


# ---------------------------------------------------------------------------
# add_series
# ---------------------------------------------------------------------------


class TestAddSeries:
    @pytest.mark.asyncio
    async def test_add_series_returns_quality_selection(self, mock_sonarr_client):
        service = MediaService()
        MediaService._sonarr = mock_sonarr_client
        mock_sonarr_client.get_root_folders.return_value = ["/tv"]
        mock_sonarr_client.get_quality_profiles.return_value = [
            {"id": 1, "name": "HD-1080p"}
        ]
        mock_sonarr_client.get_series.return_value = SAMPLE_SERIES
        mock_sonarr_client.get_seasons.return_value = [
            {"seasonNumber": 1}, {"seasonNumber": 2}
        ]

        result = await service.add_series("81189")

        assert isinstance(result, dict)
        assert result["type"] == "quality_selection"
        assert result["series"] == SAMPLE_SERIES
        assert len(result["seasons"]) == 2

    @pytest.mark.asyncio
    async def test_add_series_no_root_folders(self, mock_sonarr_client):
        service = MediaService()
        MediaService._sonarr = mock_sonarr_client
        mock_sonarr_client.get_root_folders.return_value = []

        result = await service.add_series("81189")

        assert result == (False, "No root folders configured in Sonarr")

    @pytest.mark.asyncio
    async def test_add_series_no_quality_profiles(self, mock_sonarr_client):
        service = MediaService()
        MediaService._sonarr = mock_sonarr_client
        mock_sonarr_client.get_root_folders.return_value = ["/tv"]
        mock_sonarr_client.get_quality_profiles.return_value = []

        result = await service.add_series("81189")

        assert result == (False, "No quality profiles configured in Sonarr")

    @pytest.mark.asyncio
    async def test_add_series_not_found(self, mock_sonarr_client):
        service = MediaService()
        MediaService._sonarr = mock_sonarr_client
        mock_sonarr_client.get_root_folders.return_value = ["/tv"]
        mock_sonarr_client.get_quality_profiles.return_value = [
            {"id": 1, "name": "HD-1080p"}
        ]
        mock_sonarr_client.get_series.return_value = None

        result = await service.add_series("81189")

        assert result == (False, "Series not found")

    @pytest.mark.asyncio
    async def test_add_series_no_seasons(self, mock_sonarr_client):
        service = MediaService()
        MediaService._sonarr = mock_sonarr_client
        mock_sonarr_client.get_root_folders.return_value = ["/tv"]
        mock_sonarr_client.get_quality_profiles.return_value = [
            {"id": 1, "name": "HD-1080p"}
        ]
        mock_sonarr_client.get_series.return_value = SAMPLE_SERIES
        mock_sonarr_client.get_seasons.return_value = []

        result = await service.add_series("81189")

        assert result == (False, "No seasons found for series")

    @pytest.mark.asyncio
    async def test_add_series_exception(self, mock_sonarr_client):
        service = MediaService()
        MediaService._sonarr = mock_sonarr_client
        mock_sonarr_client.get_root_folders.side_effect = Exception("API error")

        result = await service.add_series("81189")

        assert result == (False, "API error")

    @pytest.mark.asyncio
    async def test_add_series_disabled(self):
        service = MediaService()
        MediaService._sonarr = None

        with pytest.raises(ValueError, match="Sonarr is not enabled"):
            await service.add_series("81189")


# ---------------------------------------------------------------------------
# add_series_with_profile
# ---------------------------------------------------------------------------


class TestAddSeriesWithProfile:
    @pytest.mark.asyncio
    async def test_add_series_with_profile_success(self, mock_sonarr_client):
        service = MediaService()
        MediaService._sonarr = mock_sonarr_client
        mock_sonarr_client.get_seasons.return_value = [
            {"seasonNumber": 1}, {"seasonNumber": 2}
        ]
        mock_sonarr_client.add_series.return_value = (True, "Added successfully")

        success, message = await service.add_series_with_profile(
            "81189", profile_id=1, root_folder="/tv"
        )

        assert success is True
        assert message == "Added successfully"

    @pytest.mark.asyncio
    async def test_add_series_with_profile_selected_seasons(self, mock_sonarr_client):
        service = MediaService()
        MediaService._sonarr = mock_sonarr_client
        mock_sonarr_client.get_seasons.return_value = [
            {"seasonNumber": 1}, {"seasonNumber": 2}, {"seasonNumber": 3}
        ]
        mock_sonarr_client.add_series.return_value = (True, "Added")

        success, message = await service.add_series_with_profile(
            "81189", profile_id=1, root_folder="/tv", selected_seasons=[1, 3]
        )

        assert success is True
        # Verify the season_data was constructed correctly
        call_args = mock_sonarr_client.add_series.call_args
        season_data = call_args[0][3]  # 4th positional arg
        monitored_seasons = [s for s in season_data if s["monitored"]]
        unmonitored_seasons = [s for s in season_data if not s["monitored"]]
        assert len(monitored_seasons) == 2  # seasons 1 and 3
        assert len(unmonitored_seasons) == 1  # season 2

    @pytest.mark.asyncio
    async def test_add_series_with_profile_failure(self, mock_sonarr_client):
        service = MediaService()
        MediaService._sonarr = mock_sonarr_client
        mock_sonarr_client.get_seasons.return_value = [{"seasonNumber": 1}]
        mock_sonarr_client.add_series.return_value = (False, "Already exists")

        success, message = await service.add_series_with_profile(
            "81189", profile_id=1, root_folder="/tv"
        )

        assert success is False
        assert message == "Already exists"

    @pytest.mark.asyncio
    async def test_add_series_with_profile_exception(self, mock_sonarr_client):
        service = MediaService()
        MediaService._sonarr = mock_sonarr_client
        mock_sonarr_client.get_seasons.side_effect = Exception("API error")

        success, message = await service.add_series_with_profile(
            "81189", profile_id=1, root_folder="/tv"
        )

        assert success is False
        assert message == "API error"

    @pytest.mark.asyncio
    async def test_add_series_with_profile_disabled(self):
        service = MediaService()
        MediaService._sonarr = None

        with pytest.raises(ValueError, match="Sonarr is not enabled"):
            await service.add_series_with_profile(
                "81189", profile_id=1, root_folder="/tv"
            )


# ---------------------------------------------------------------------------
# add_music
# ---------------------------------------------------------------------------


class TestAddMusic:
    @pytest.mark.asyncio
    async def test_add_music_returns_quality_selection(self, mock_lidarr_client):
        service = MediaService()
        MediaService._lidarr = mock_lidarr_client
        mock_lidarr_client.get_root_folders.return_value = ["/music"]
        mock_lidarr_client.get_quality_profiles.return_value = [
            {"id": 1, "name": "Lossless"}
        ]
        mock_lidarr_client.get_artist.return_value = SAMPLE_ARTIST

        result = await service.add_music("some-mbid-123")

        assert isinstance(result, dict)
        assert result["type"] == "quality_selection"
        assert result["artist"] == SAMPLE_ARTIST

    @pytest.mark.asyncio
    async def test_add_music_no_root_folders(self, mock_lidarr_client):
        service = MediaService()
        MediaService._lidarr = mock_lidarr_client
        mock_lidarr_client.get_root_folders.return_value = []

        result = await service.add_music("some-mbid-123")

        assert result == (False, "No root folders configured in Lidarr")

    @pytest.mark.asyncio
    async def test_add_music_no_quality_profiles(self, mock_lidarr_client):
        service = MediaService()
        MediaService._lidarr = mock_lidarr_client
        mock_lidarr_client.get_root_folders.return_value = ["/music"]
        mock_lidarr_client.get_quality_profiles.return_value = []

        result = await service.add_music("some-mbid-123")

        assert result == (False, "No quality profiles configured in Lidarr")

    @pytest.mark.asyncio
    async def test_add_music_not_found(self, mock_lidarr_client):
        service = MediaService()
        MediaService._lidarr = mock_lidarr_client
        mock_lidarr_client.get_root_folders.return_value = ["/music"]
        mock_lidarr_client.get_quality_profiles.return_value = [
            {"id": 1, "name": "Lossless"}
        ]
        mock_lidarr_client.get_artist.return_value = None

        result = await service.add_music("bad-id")

        assert result == (False, "Artist not found")

    @pytest.mark.asyncio
    async def test_add_music_exception(self, mock_lidarr_client):
        service = MediaService()
        MediaService._lidarr = mock_lidarr_client
        mock_lidarr_client.get_root_folders.side_effect = Exception("API error")

        result = await service.add_music("some-mbid-123")

        assert result == (False, "API error")

    @pytest.mark.asyncio
    async def test_add_music_disabled(self):
        service = MediaService()
        MediaService._lidarr = None

        with pytest.raises(ValueError, match="Lidarr is not enabled"):
            await service.add_music("some-mbid-123")


# ---------------------------------------------------------------------------
# add_music_with_profile
# ---------------------------------------------------------------------------


class TestAddMusicWithProfile:
    @pytest.mark.asyncio
    async def test_add_music_with_profile_success(self, mock_lidarr_client):
        service = MediaService()
        MediaService._lidarr = mock_lidarr_client
        mock_lidarr_client.add_artist.return_value = (True, "Added successfully")

        success, message = await service.add_music_with_profile(
            "some-mbid-123", profile_id=1, root_folder="/music"
        )

        assert success is True
        assert message == "Added successfully"

    @pytest.mark.asyncio
    async def test_add_music_with_profile_failure(self, mock_lidarr_client):
        service = MediaService()
        MediaService._lidarr = mock_lidarr_client
        mock_lidarr_client.add_artist.return_value = (False, "Already exists")

        success, message = await service.add_music_with_profile(
            "some-mbid-123", profile_id=1, root_folder="/music"
        )

        assert success is False
        assert message == "Already exists"

    @pytest.mark.asyncio
    async def test_add_music_with_profile_exception(self, mock_lidarr_client):
        service = MediaService()
        MediaService._lidarr = mock_lidarr_client
        mock_lidarr_client.add_artist.side_effect = Exception("API error")

        success, message = await service.add_music_with_profile(
            "some-mbid-123", profile_id=1, root_folder="/music"
        )

        assert success is False
        assert message == "API error"

    @pytest.mark.asyncio
    async def test_add_music_with_profile_disabled(self):
        service = MediaService()
        MediaService._lidarr = None

        with pytest.raises(ValueError, match="Lidarr is not enabled"):
            await service.add_music_with_profile(
                "some-mbid-123", profile_id=1, root_folder="/music"
            )


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

    @pytest.mark.asyncio
    async def test_get_radarr_status_exception(self, mock_radarr_client):
        service = MediaService()
        MediaService._radarr = mock_radarr_client
        mock_radarr_client.check_status.side_effect = Exception("fail")

        result = await service.get_radarr_status()
        assert result is False

    @pytest.mark.asyncio
    async def test_get_sonarr_status(self, mock_sonarr_client):
        service = MediaService()
        MediaService._sonarr = mock_sonarr_client
        mock_sonarr_client.check_status.return_value = True

        result = await service.get_sonarr_status()
        assert result is True

    @pytest.mark.asyncio
    async def test_get_sonarr_status_disabled(self):
        service = MediaService()
        MediaService._sonarr = None

        result = await service.get_sonarr_status()
        assert result is False

    @pytest.mark.asyncio
    async def test_get_sonarr_status_exception(self, mock_sonarr_client):
        service = MediaService()
        MediaService._sonarr = mock_sonarr_client
        mock_sonarr_client.check_status.side_effect = Exception("fail")

        result = await service.get_sonarr_status()
        assert result is False

    @pytest.mark.asyncio
    async def test_get_lidarr_status(self, mock_lidarr_client):
        service = MediaService()
        MediaService._lidarr = mock_lidarr_client
        mock_lidarr_client.check_status.return_value = True

        result = await service.get_lidarr_status()
        assert result is True

    @pytest.mark.asyncio
    async def test_get_lidarr_status_disabled(self):
        service = MediaService()
        MediaService._lidarr = None

        result = await service.get_lidarr_status()
        assert result is False

    @pytest.mark.asyncio
    async def test_get_lidarr_status_exception(self, mock_lidarr_client):
        service = MediaService()
        MediaService._lidarr = mock_lidarr_client
        mock_lidarr_client.check_status.side_effect = Exception("fail")

        result = await service.get_lidarr_status()
        assert result is False

    @pytest.mark.asyncio
    async def test_get_transmission_status_enabled(self):
        service = MediaService()
        mock_client = AsyncMock()
        mock_client.check_status.return_value = True
        service.transmission = mock_client

        result = await service.get_transmission_status()
        assert result is True

    @pytest.mark.asyncio
    async def test_get_transmission_status_disabled(self):
        service = MediaService()
        service.transmission = None

        result = await service.get_transmission_status()
        assert result is False

    @pytest.mark.asyncio
    async def test_get_transmission_status_exception(self):
        service = MediaService()
        mock_client = AsyncMock()
        mock_client.check_status.side_effect = Exception("fail")
        service.transmission = mock_client

        result = await service.get_transmission_status()
        assert result is False

    @pytest.mark.asyncio
    async def test_get_sabnzbd_status_enabled(self):
        service = MediaService()
        mock_client = AsyncMock()
        mock_client.check_status.return_value = True
        service.sabnzbd = mock_client

        result = await service.get_sabnzbd_status()
        assert result is True

    @pytest.mark.asyncio
    async def test_get_sabnzbd_status_disabled(self):
        service = MediaService()
        service.sabnzbd = None

        result = await service.get_sabnzbd_status()
        assert result is False

    @pytest.mark.asyncio
    async def test_get_sabnzbd_status_exception(self):
        service = MediaService()
        mock_client = AsyncMock()
        mock_client.check_status.side_effect = Exception("fail")
        service.sabnzbd = mock_client

        result = await service.get_sabnzbd_status()
        assert result is False


# ---------------------------------------------------------------------------
# get_movies
# ---------------------------------------------------------------------------


class TestGetMovies:
    @pytest.mark.asyncio
    async def test_get_movies_success(self, mock_radarr_client):
        service = MediaService()
        MediaService._radarr = mock_radarr_client
        mock_radarr_client.get_movies.return_value = [
            {"id": 1, "title": "Fight Club", "tmdbId": 550},
            {"id": 2, "title": "Pulp Fiction", "tmdbId": 680},
        ]

        results = await service.get_movies()

        assert len(results) == 2
        assert results[0] == {"id": "1", "title": "Fight Club"}
        assert results[1] == {"id": "2", "title": "Pulp Fiction"}
        mock_radarr_client.get_movies.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_movies_disabled(self):
        service = MediaService()
        MediaService._radarr = None

        with pytest.raises(ValueError, match="Radarr is not enabled"):
            await service.get_movies()

    @pytest.mark.asyncio
    async def test_get_movies_exception(self, mock_radarr_client):
        service = MediaService()
        MediaService._radarr = mock_radarr_client
        mock_radarr_client.get_movies.side_effect = Exception("API error")

        with pytest.raises(Exception, match="API error"):
            await service.get_movies()


# ---------------------------------------------------------------------------
# get_movie
# ---------------------------------------------------------------------------


class TestGetMovie:
    @pytest.mark.asyncio
    async def test_get_movie_success(self, mock_radarr_client):
        service = MediaService()
        MediaService._radarr = mock_radarr_client
        mock_radarr_client.get_movie_by_id.return_value = {
            "id": 1, "title": "Fight Club", "tmdbId": 550,
        }

        result = await service.get_movie("1")

        assert result == {"id": "1", "title": "Fight Club"}
        mock_radarr_client.get_movie_by_id.assert_awaited_once_with(1)

    @pytest.mark.asyncio
    async def test_get_movie_not_found(self, mock_radarr_client):
        service = MediaService()
        MediaService._radarr = mock_radarr_client
        mock_radarr_client.get_movie_by_id.return_value = None

        result = await service.get_movie("999")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_movie_disabled(self):
        service = MediaService()
        MediaService._radarr = None

        with pytest.raises(ValueError, match="Radarr is not enabled"):
            await service.get_movie("1")

    @pytest.mark.asyncio
    async def test_get_movie_exception(self, mock_radarr_client):
        service = MediaService()
        MediaService._radarr = mock_radarr_client
        mock_radarr_client.get_movie_by_id.side_effect = Exception("API error")

        with pytest.raises(Exception, match="API error"):
            await service.get_movie("1")


# ---------------------------------------------------------------------------
# get_series (overloaded: list all or single lookup)
# ---------------------------------------------------------------------------


class TestGetSeriesService:
    @pytest.mark.asyncio
    async def test_get_series_list_all(self, mock_sonarr_client):
        service = MediaService()
        MediaService._sonarr = mock_sonarr_client
        mock_sonarr_client.get_all_series.return_value = [
            {"id": 1, "title": "Breaking Bad", "tvdbId": 81189},
            {"id": 2, "title": "Severance", "tvdbId": 295759},
        ]

        results = await service.get_series()

        assert len(results) == 2
        assert results[0] == {"id": "1", "title": "Breaking Bad"}
        assert results[1] == {"id": "2", "title": "Severance"}
        mock_sonarr_client.get_all_series.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_series_single_lookup(self, mock_sonarr_client):
        service = MediaService()
        MediaService._sonarr = mock_sonarr_client
        mock_sonarr_client.get_series_by_id.return_value = {
            "id": 1, "title": "Breaking Bad", "tvdbId": 81189,
        }

        result = await service.get_series("1")

        assert result == {"id": "1", "title": "Breaking Bad"}
        mock_sonarr_client.get_series_by_id.assert_awaited_once_with(1)

    @pytest.mark.asyncio
    async def test_get_series_single_not_found(self, mock_sonarr_client):
        service = MediaService()
        MediaService._sonarr = mock_sonarr_client
        mock_sonarr_client.get_series_by_id.return_value = None

        result = await service.get_series("999")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_series_disabled(self):
        service = MediaService()
        MediaService._sonarr = None

        with pytest.raises(ValueError, match="Sonarr is not enabled"):
            await service.get_series()

    @pytest.mark.asyncio
    async def test_get_series_exception(self, mock_sonarr_client):
        service = MediaService()
        MediaService._sonarr = mock_sonarr_client
        mock_sonarr_client.get_all_series.side_effect = Exception("API error")

        with pytest.raises(Exception, match="API error"):
            await service.get_series()


# ---------------------------------------------------------------------------
# get_music (overloaded: list all or single lookup)
# ---------------------------------------------------------------------------


class TestGetMusicService:
    @pytest.mark.asyncio
    async def test_get_music_list_all(self, mock_lidarr_client):
        service = MediaService()
        MediaService._lidarr = mock_lidarr_client
        mock_lidarr_client.get_artists.return_value = [
            {"id": 1, "artistName": "Linkin Park"},
            {"id": 2, "artistName": "Radiohead"},
        ]

        results = await service.get_music()

        assert len(results) == 2
        assert results[0] == {"id": "1", "title": "Linkin Park"}
        assert results[1] == {"id": "2", "title": "Radiohead"}
        mock_lidarr_client.get_artists.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_music_single_lookup(self, mock_lidarr_client):
        service = MediaService()
        MediaService._lidarr = mock_lidarr_client
        mock_lidarr_client.get_artist_by_id.return_value = {
            "id": 1, "artistName": "Linkin Park",
        }

        result = await service.get_music("1")

        assert result == {"id": "1", "title": "Linkin Park"}
        mock_lidarr_client.get_artist_by_id.assert_awaited_once_with(1)

    @pytest.mark.asyncio
    async def test_get_music_single_not_found(self, mock_lidarr_client):
        service = MediaService()
        MediaService._lidarr = mock_lidarr_client
        mock_lidarr_client.get_artist_by_id.return_value = None

        result = await service.get_music("999")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_music_disabled(self):
        service = MediaService()
        MediaService._lidarr = None

        with pytest.raises(ValueError, match="Lidarr is not enabled"):
            await service.get_music()

    @pytest.mark.asyncio
    async def test_get_music_exception(self, mock_lidarr_client):
        service = MediaService()
        MediaService._lidarr = mock_lidarr_client
        mock_lidarr_client.get_artists.side_effect = Exception("API error")

        with pytest.raises(Exception, match="API error"):
            await service.get_music()


# ---------------------------------------------------------------------------
# delete_movie
# ---------------------------------------------------------------------------


class TestDeleteMovieService:
    @pytest.mark.asyncio
    async def test_delete_movie_success(self, mock_radarr_client):
        service = MediaService()
        MediaService._radarr = mock_radarr_client
        mock_radarr_client.delete_movie.return_value = True

        result = await service.delete_movie("1")

        assert result is True
        mock_radarr_client.delete_movie.assert_awaited_once_with(1)

    @pytest.mark.asyncio
    async def test_delete_movie_failure(self, mock_radarr_client):
        service = MediaService()
        MediaService._radarr = mock_radarr_client
        mock_radarr_client.delete_movie.return_value = False

        result = await service.delete_movie("1")

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_movie_disabled(self):
        service = MediaService()
        MediaService._radarr = None

        with pytest.raises(ValueError, match="Radarr is not enabled"):
            await service.delete_movie("1")

    @pytest.mark.asyncio
    async def test_delete_movie_exception(self, mock_radarr_client):
        service = MediaService()
        MediaService._radarr = mock_radarr_client
        mock_radarr_client.delete_movie.side_effect = Exception("API error")

        with pytest.raises(Exception, match="API error"):
            await service.delete_movie("1")


# ---------------------------------------------------------------------------
# delete_series
# ---------------------------------------------------------------------------


class TestDeleteSeriesService:
    @pytest.mark.asyncio
    async def test_delete_series_success(self, mock_sonarr_client):
        service = MediaService()
        MediaService._sonarr = mock_sonarr_client
        mock_sonarr_client.delete_series.return_value = True

        result = await service.delete_series("1")

        assert result is True
        mock_sonarr_client.delete_series.assert_awaited_once_with(1)

    @pytest.mark.asyncio
    async def test_delete_series_failure(self, mock_sonarr_client):
        service = MediaService()
        MediaService._sonarr = mock_sonarr_client
        mock_sonarr_client.delete_series.return_value = False

        result = await service.delete_series("1")

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_series_disabled(self):
        service = MediaService()
        MediaService._sonarr = None

        with pytest.raises(ValueError, match="Sonarr is not enabled"):
            await service.delete_series("1")

    @pytest.mark.asyncio
    async def test_delete_series_exception(self, mock_sonarr_client):
        service = MediaService()
        MediaService._sonarr = mock_sonarr_client
        mock_sonarr_client.delete_series.side_effect = Exception("API error")

        with pytest.raises(Exception, match="API error"):
            await service.delete_series("1")


# ---------------------------------------------------------------------------
# delete_music
# ---------------------------------------------------------------------------


class TestDeleteMusicService:
    @pytest.mark.asyncio
    async def test_delete_music_success(self, mock_lidarr_client):
        service = MediaService()
        MediaService._lidarr = mock_lidarr_client
        mock_lidarr_client.delete_artist.return_value = True

        result = await service.delete_music("1")

        assert result is True
        mock_lidarr_client.delete_artist.assert_awaited_once_with(1)

    @pytest.mark.asyncio
    async def test_delete_music_failure(self, mock_lidarr_client):
        service = MediaService()
        MediaService._lidarr = mock_lidarr_client
        mock_lidarr_client.delete_artist.return_value = False

        result = await service.delete_music("1")

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_music_disabled(self):
        service = MediaService()
        MediaService._lidarr = None

        with pytest.raises(ValueError, match="Lidarr is not enabled"):
            await service.delete_music("1")

    @pytest.mark.asyncio
    async def test_delete_music_exception(self, mock_lidarr_client):
        service = MediaService()
        MediaService._lidarr = mock_lidarr_client
        mock_lidarr_client.delete_artist.side_effect = Exception("API error")

        with pytest.raises(Exception, match="API error"):
            await service.delete_music("1")

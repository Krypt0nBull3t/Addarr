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

SAMPLE_ALBUM = {
    "foreignAlbumId": "album-id-abc",
    "title": "OK Computer",
    "artist": {
        "foreignArtistId": "some-mbid-123",
        "artistName": "Radiohead",
    },
    "images": [
        {"coverType": "cover", "remoteUrl": "https://example.com/okcomputer.jpg"}
    ],
    "releaseDate": "1997-05-21T00:00:00Z",
    "overview": "Third studio album...",
    "ratings": {"value": 9.5},
    "genres": ["Alternative Rock"],
    "albumType": "Album",
}

SAMPLE_ALBUM_WITH_TRACKS = {
    "foreignAlbumId": "album-id-abc",
    "title": "OK Computer",
    "artist": {
        "foreignArtistId": "some-mbid-123",
        "artistName": "Radiohead",
    },
    "images": [
        {"coverType": "cover", "remoteUrl": "https://example.com/okcomputer.jpg"}
    ],
    "releaseDate": "1997-05-21T00:00:00Z",
    "overview": "Third studio album...",
    "ratings": {"value": 9.5},
    "genres": ["Alternative Rock"],
    "albumType": "Album",
    "media": [
        {
            "mediumNumber": 1,
            "mediumName": "",
            "mediumFormat": "CD",
            "tracks": [
                {"trackNumber": "1", "title": "Airbag"},
                {"trackNumber": "2", "title": "Paranoid Android"},
                {"trackNumber": "3", "title": "Subterranean Homesick Alien"},
            ],
        }
    ],
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


# ---------------------------------------------------------------------------
# search_music — combined artist + album + song search
# ---------------------------------------------------------------------------


class TestSearchMusicCombined:
    @pytest.mark.asyncio
    async def test_combined_results_have_music_type(self, mock_lidarr_client):
        """search_music returns results with music_type on each item."""
        service = MediaService()
        MediaService._lidarr = mock_lidarr_client
        mock_lidarr_client.search.return_value = [SAMPLE_ARTIST]
        mock_lidarr_client.search_albums.return_value = [SAMPLE_ALBUM]

        results = await service.search_music("radiohead")

        artists = [r for r in results if r["music_type"] == "artist"]
        albums = [r for r in results if r["music_type"] == "album"]
        assert len(artists) == 1
        assert len(albums) == 1

    @pytest.mark.asyncio
    async def test_album_ids_prefixed(self, mock_lidarr_client):
        """Album result IDs are prefixed with 'album:'."""
        service = MediaService()
        MediaService._lidarr = mock_lidarr_client
        mock_lidarr_client.search.return_value = []
        mock_lidarr_client.search_albums.return_value = [SAMPLE_ALBUM]

        results = await service.search_music("ok computer")

        assert results[0]["id"] == "album:album-id-abc"
        assert results[0]["album_id"] == "album-id-abc"
        assert results[0]["artist_id"] == "some-mbid-123"

    @pytest.mark.asyncio
    async def test_song_results_from_track_data(self, mock_lidarr_client):
        """Song results extracted when album track data matches query."""
        service = MediaService()
        MediaService._lidarr = mock_lidarr_client
        mock_lidarr_client.search.return_value = []
        mock_lidarr_client.search_albums.return_value = [
            SAMPLE_ALBUM_WITH_TRACKS
        ]

        results = await service.search_music("paranoid android")

        songs = [r for r in results if r["music_type"] == "song"]
        assert len(songs) == 1
        assert songs[0]["title"] == "Paranoid Android"
        assert songs[0]["album_id"] == "album-id-abc"
        assert songs[0]["artist_id"] == "some-mbid-123"

    @pytest.mark.asyncio
    async def test_no_song_when_no_track_data(self, mock_lidarr_client):
        """No song results when album has no media/track data."""
        service = MediaService()
        MediaService._lidarr = mock_lidarr_client
        mock_lidarr_client.search.return_value = []
        mock_lidarr_client.search_albums.return_value = [SAMPLE_ALBUM]

        results = await service.search_music("paranoid android")

        songs = [r for r in results if r["music_type"] == "song"]
        assert len(songs) == 0

    @pytest.mark.asyncio
    async def test_albums_without_foreign_id_skipped(self, mock_lidarr_client):
        """Albums missing foreignAlbumId are filtered out."""
        service = MediaService()
        MediaService._lidarr = mock_lidarr_client
        mock_lidarr_client.search.return_value = []
        mock_lidarr_client.search_albums.return_value = [
            {"title": "No ID Album", "artist": {}},
            SAMPLE_ALBUM,
        ]

        results = await service.search_music("test")

        albums = [r for r in results if r["music_type"] == "album"]
        assert len(albums) == 1
        assert albums[0]["title"] == "OK Computer"

    @pytest.mark.asyncio
    async def test_artists_only_when_albums_empty(self, mock_lidarr_client):
        """When album search returns empty, only artist results returned."""
        service = MediaService()
        MediaService._lidarr = mock_lidarr_client
        mock_lidarr_client.search.return_value = [SAMPLE_ARTIST]
        mock_lidarr_client.search_albums.return_value = []

        results = await service.search_music("radiohead")

        assert len(results) == 1
        assert results[0]["music_type"] == "artist"

    @pytest.mark.asyncio
    async def test_albums_only_when_artists_empty(self, mock_lidarr_client):
        """When artist search returns empty, only album results returned."""
        service = MediaService()
        MediaService._lidarr = mock_lidarr_client
        mock_lidarr_client.search.return_value = []
        mock_lidarr_client.search_albums.return_value = [SAMPLE_ALBUM]

        results = await service.search_music("ok computer")

        assert len(results) == 1
        assert results[0]["music_type"] == "album"

    @pytest.mark.asyncio
    async def test_artist_fields_preserved(self, mock_lidarr_client):
        """Existing artist result fields preserved (backwards compatibility)."""
        service = MediaService()
        MediaService._lidarr = mock_lidarr_client
        mock_lidarr_client.search.return_value = [SAMPLE_ARTIST]
        mock_lidarr_client.search_albums.return_value = []

        results = await service.search_music("radiohead")

        r = results[0]
        assert r["id"] == "some-mbid-123"
        assert r["title"] == "Radiohead"
        assert r["overview"] == "English rock band..."
        assert r["rating"] == 9.1
        assert r["status"] == "active"
        assert r["data"] == SAMPLE_ARTIST

    @pytest.mark.asyncio
    async def test_result_ordering(self, mock_lidarr_client):
        """Results ordered: artists first, then albums, then songs."""
        service = MediaService()
        MediaService._lidarr = mock_lidarr_client
        mock_lidarr_client.search.return_value = [SAMPLE_ARTIST]
        mock_lidarr_client.search_albums.return_value = [
            SAMPLE_ALBUM_WITH_TRACKS
        ]

        results = await service.search_music("radiohead")

        types = [r["music_type"] for r in results]
        # Artists before albums; songs (if any) after albums
        artist_idx = [i for i, t in enumerate(types) if t == "artist"]
        album_idx = [i for i, t in enumerate(types) if t == "album"]
        song_idx = [i for i, t in enumerate(types) if t == "song"]

        if artist_idx and album_idx:
            assert max(artist_idx) < min(album_idx)
        if album_idx and song_idx:
            assert max(album_idx) < min(song_idx)


# ---------------------------------------------------------------------------
# add_music_with_profile — albums_to_monitor pass-through
# ---------------------------------------------------------------------------


class TestAddMusicWithProfileAlbums:
    @pytest.mark.asyncio
    async def test_passes_albums_to_monitor(self, mock_lidarr_client):
        """albums_to_monitor is passed through to lidarr.add_artist()."""
        service = MediaService()
        MediaService._lidarr = mock_lidarr_client
        mock_lidarr_client.add_artist.return_value = (True, "Added")

        success, msg = await service.add_music_with_profile(
            "some-mbid-123", 1, "/music",
            albums_to_monitor=["alb-1", "alb-2"],
        )

        assert success is True
        mock_lidarr_client.add_artist.assert_awaited_once_with(
            "some-mbid-123", "/music", 1,
            albums_to_monitor=["alb-1", "alb-2"],
        )

    @pytest.mark.asyncio
    async def test_no_albums_to_monitor_backwards_compat(
        self, mock_lidarr_client
    ):
        """Without albums_to_monitor, add_artist called without it."""
        service = MediaService()
        MediaService._lidarr = mock_lidarr_client
        mock_lidarr_client.add_artist.return_value = (True, "Added")

        success, msg = await service.add_music_with_profile(
            "some-mbid-123", 1, "/music"
        )

        assert success is True
        mock_lidarr_client.add_artist.assert_awaited_once_with(
            "some-mbid-123", "/music", 1,
        )

    @pytest.mark.asyncio
    async def test_passes_future_albums(self, mock_lidarr_client):
        """future_albums is passed through to lidarr.add_artist()."""
        service = MediaService()
        MediaService._lidarr = mock_lidarr_client
        mock_lidarr_client.add_artist.return_value = (True, "Added")

        success, msg = await service.add_music_with_profile(
            "some-mbid-123", 1, "/music",
            albums_to_monitor=["alb-1"],
            future_albums=True,
        )

        assert success is True
        mock_lidarr_client.add_artist.assert_awaited_once_with(
            "some-mbid-123", "/music", 1,
            albums_to_monitor=["alb-1"],
            future_albums=True,
        )

    @pytest.mark.asyncio
    async def test_future_albums_false_not_passed(self, mock_lidarr_client):
        """future_albums=False is not passed (backwards compat)."""
        service = MediaService()
        MediaService._lidarr = mock_lidarr_client
        mock_lidarr_client.add_artist.return_value = (True, "Added")

        success, msg = await service.add_music_with_profile(
            "some-mbid-123", 1, "/music",
            albums_to_monitor=["alb-1"],
        )

        assert success is True
        mock_lidarr_client.add_artist.assert_awaited_once_with(
            "some-mbid-123", "/music", 1,
            albums_to_monitor=["alb-1"],
        )


# ---------------------------------------------------------------------------
# get_artist_albums
# ---------------------------------------------------------------------------


class TestGetArtistAlbums:
    @pytest.mark.asyncio
    async def test_returns_normalized_albums(self, mock_lidarr_client):
        """get_artist_albums returns normalized album list."""
        service = MediaService()
        MediaService._lidarr = mock_lidarr_client
        mock_lidarr_client.search_albums.return_value = [
            SAMPLE_ALBUM,
            {
                "foreignAlbumId": "album-id-xyz",
                "title": "Kid A",
                "artist": {
                    "foreignArtistId": "some-mbid-123",
                    "artistName": "Radiohead",
                },
                "releaseDate": "2000-10-02T00:00:00Z",
            },
        ]

        albums = await service.get_artist_albums("some-mbid-123")

        assert len(albums) == 2
        assert albums[0]["album_id"] == "album-id-abc"
        assert albums[0]["title"] == "OK Computer"
        assert albums[0]["release_date"] == "1997-05-21T00:00:00Z"
        assert albums[1]["album_id"] == "album-id-xyz"
        assert albums[1]["title"] == "Kid A"

    @pytest.mark.asyncio
    async def test_returns_empty_on_exception(self, mock_lidarr_client):
        """get_artist_albums returns [] on exception."""
        service = MediaService()
        MediaService._lidarr = mock_lidarr_client
        mock_lidarr_client.search_albums.side_effect = Exception("API error")

        albums = await service.get_artist_albums("some-mbid-123")

        assert albums == []

    @pytest.mark.asyncio
    async def test_disabled_returns_empty(self):
        """get_artist_albums returns [] when Lidarr disabled."""
        service = MediaService()
        MediaService._lidarr = None

        albums = await service.get_artist_albums("some-mbid-123")

        assert albums == []

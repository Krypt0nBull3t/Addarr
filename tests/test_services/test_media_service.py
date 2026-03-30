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
    "imdbId": "tt0137523",
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
    "imdbId": "tt0903747",
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

SAMPLE_SERIES_NO_IMDB = {
    "tvdbId": 295759,
    "title": "Severance",
    "year": 2022,
    "overview": "Mark leads a team...",
    "images": [],
    "ratings": {},
    "genres": ["Drama"],
    "network": "Apple TV+",
    "studio": "Apple",
    "status": "continuing",
    "runtime": 55,
    "seasons": [{"seasonNumber": 1}],
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
    async def test_search_movies_external_ids(self, mock_radarr_client):
        """Normalized movie results include external_ids with imdb and tmdb."""
        service = MediaService()
        MediaService._radarr = mock_radarr_client
        mock_radarr_client.search.return_value = [SAMPLE_MOVIE]

        results = await service.search_movies("fight club")

        assert results[0]["external_ids"] == {
            "imdb": "tt0137523",
            "tmdb": 550,
        }

    @pytest.mark.asyncio
    async def test_search_movies_external_ids_no_imdb(self, mock_radarr_client):
        """Movie without imdbId gets None for imdb external_id."""
        service = MediaService()
        MediaService._radarr = mock_radarr_client
        movie_no_imdb = {**SAMPLE_MOVIE}
        del movie_no_imdb["imdbId"]
        mock_radarr_client.search.return_value = [movie_no_imdb]

        results = await service.search_movies("fight club")

        assert results[0]["external_ids"]["imdb"] is None
        assert results[0]["external_ids"]["tmdb"] == 550

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
    async def test_search_series_external_ids(self, mock_sonarr_client):
        """Normalized series results include external_ids with tvdb and imdb."""
        service = MediaService()
        MediaService._sonarr = mock_sonarr_client
        mock_sonarr_client.search.return_value = [SAMPLE_SERIES]

        results = await service.search_series("breaking bad")

        assert results[0]["external_ids"] == {
            "tvdb": 81189,
            "imdb": "tt0903747",
        }

    @pytest.mark.asyncio
    async def test_search_series_external_ids_no_imdb(self, mock_sonarr_client):
        """Series without imdbId gets None for imdb external_id."""
        service = MediaService()
        MediaService._sonarr = mock_sonarr_client
        mock_sonarr_client.search.return_value = [SAMPLE_SERIES_NO_IMDB]

        results = await service.search_series("severance")

        assert results[0]["external_ids"]["tvdb"] == 295759
        assert results[0]["external_ids"]["imdb"] is None

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
    async def test_search_music_artist_external_ids(self, mock_lidarr_client):
        """Normalized artist results include musicbrainz external_id."""
        service = MediaService()
        MediaService._lidarr = mock_lidarr_client
        mock_lidarr_client.search.return_value = [SAMPLE_ARTIST]

        results = await service.search_music("radiohead")

        assert results[0]["external_ids"] == {
            "musicbrainz": "some-mbid-123",
        }

    @pytest.mark.asyncio
    async def test_search_music_album_external_ids(self, mock_lidarr_client):
        """Normalized album results include musicbrainz external_id."""
        service = MediaService()
        MediaService._lidarr = mock_lidarr_client
        mock_lidarr_client.search.return_value = []
        mock_lidarr_client.search_albums.return_value = [SAMPLE_ALBUM]

        results = await service.search_music("ok computer")

        albums = [r for r in results if r.get("music_type") == "album"]
        assert len(albums) == 1
        assert albums[0]["external_ids"] == {
            "musicbrainz": "album-id-abc",
        }

    @pytest.mark.asyncio
    async def test_search_music_song_external_ids(self, mock_lidarr_client):
        """Normalized song results include musicbrainz external_id from parent album."""
        service = MediaService()
        MediaService._lidarr = mock_lidarr_client
        mock_lidarr_client.search.return_value = []
        mock_lidarr_client.search_albums.return_value = [SAMPLE_ALBUM_WITH_TRACKS]

        results = await service.search_music("paranoid android")

        songs = [r for r in results if r.get("music_type") == "song"]
        assert len(songs) == 1
        assert songs[0]["external_ids"] == {
            "musicbrainz": "album-id-abc",
        }

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


# ---------------------------------------------------------------------------
# get_album_tracks
# ---------------------------------------------------------------------------


class TestGetAlbumTracks:
    @pytest.mark.asyncio
    async def test_delegates_to_lidarr_client(self, mock_lidarr_client):
        """get_album_tracks delegates to LidarrClient and returns raw result."""
        service = MediaService()
        MediaService._lidarr = mock_lidarr_client
        sample_tracks = [
            {"trackNumber": "1", "title": "Papercut", "duration": 185000},
            {"trackNumber": "2", "title": "One Step Closer", "duration": 156000},
        ]
        mock_lidarr_client.get_album_tracks.return_value = sample_tracks

        tracks = await service.get_album_tracks("album-id-abc")

        mock_lidarr_client.get_album_tracks.assert_called_once_with("album-id-abc")
        assert tracks == sample_tracks

    @pytest.mark.asyncio
    async def test_returns_empty_on_exception(self, mock_lidarr_client):
        """get_album_tracks returns [] on exception."""
        service = MediaService()
        MediaService._lidarr = mock_lidarr_client
        mock_lidarr_client.get_album_tracks.side_effect = Exception("API error")

        tracks = await service.get_album_tracks("album-id-abc")

        assert tracks == []

    @pytest.mark.asyncio
    async def test_disabled_returns_empty(self):
        """get_album_tracks returns [] when Lidarr disabled."""
        service = MediaService()
        MediaService._lidarr = None

        tracks = await service.get_album_tracks("album-id-abc")

        assert tracks == []


# ---------------------------------------------------------------------------
# get_upcoming — calendar aggregation
# ---------------------------------------------------------------------------


# Sample Radarr calendar data
RADARR_CALENDAR_MOVIE_CINEMA = {
    "id": 1,
    "title": "Movie A",
    "tmdbId": 100,
    "year": 2026,
    "inCinemas": "2026-03-10T00:00:00Z",
    "digitalRelease": "2026-04-10T00:00:00Z",
    "physicalRelease": "2026-05-10T00:00:00Z",
}

RADARR_CALENDAR_MOVIE_DIGITAL = {
    "id": 2,
    "title": "Movie B",
    "tmdbId": 200,
    "year": 2026,
    "digitalRelease": "2026-03-15T00:00:00Z",
}

RADARR_CALENDAR_MOVIE_NO_ID = {
    "title": "Movie C",
    "tmdbId": 300,
    "year": 2026,
    "physicalRelease": "2026-03-05T00:00:00Z",
}

# Sample Sonarr calendar data
SONARR_CALENDAR_EPISODE = {
    "id": 501,
    "title": "Pilot",
    "airDateUtc": "2026-03-08T20:00:00Z",
    "seasonNumber": 1,
    "episodeNumber": 1,
    "series": {"title": "New Show", "tvdbId": 9000, "id": 10},
}

SONARR_CALENDAR_EPISODE_NO_ID = {
    "title": "Unmonitored Ep",
    "airDateUtc": "2026-03-12T20:00:00Z",
    "seasonNumber": 2,
    "episodeNumber": 5,
    "series": {"title": "Another Show", "tvdbId": 9001},
}


class TestGetUpcoming:
    @pytest.mark.asyncio
    async def test_both_services_combined_sorted(
        self, mock_radarr_client, mock_sonarr_client
    ):
        """Both services enabled — returns combined, date-sorted list."""
        service = MediaService()
        MediaService._radarr = mock_radarr_client
        MediaService._sonarr = mock_sonarr_client
        mock_radarr_client.get_calendar.return_value = [
            RADARR_CALENDAR_MOVIE_DIGITAL,  # 2026-03-15
        ]
        mock_sonarr_client.get_calendar.return_value = [
            SONARR_CALENDAR_EPISODE,  # 2026-03-08
        ]

        results = await service.get_upcoming(days=14)

        assert len(results) == 2
        # Sonarr episode (03-08) should come before Radarr movie (03-15)
        assert results[0]["type"] == "episode"
        assert results[0]["title"] == "Pilot"
        assert results[1]["type"] == "movie"
        assert results[1]["title"] == "Movie B"

    @pytest.mark.asyncio
    async def test_only_radarr_enabled(self, mock_radarr_client):
        """Only Radarr enabled — returns only movies."""
        service = MediaService()
        MediaService._radarr = mock_radarr_client
        MediaService._sonarr = None
        mock_radarr_client.get_calendar.return_value = [
            RADARR_CALENDAR_MOVIE_CINEMA,
        ]

        results = await service.get_upcoming(days=7)

        assert len(results) == 1
        assert results[0]["type"] == "movie"
        assert results[0]["title"] == "Movie A"

    @pytest.mark.asyncio
    async def test_only_sonarr_enabled(self, mock_sonarr_client):
        """Only Sonarr enabled — returns only episodes."""
        service = MediaService()
        MediaService._radarr = None
        MediaService._sonarr = mock_sonarr_client
        mock_sonarr_client.get_calendar.return_value = [
            SONARR_CALENDAR_EPISODE,
        ]

        results = await service.get_upcoming(days=7)

        assert len(results) == 1
        assert results[0]["type"] == "episode"
        assert results[0]["series_title"] == "New Show"

    @pytest.mark.asyncio
    async def test_neither_enabled(self):
        """Neither enabled — returns empty list."""
        service = MediaService()
        MediaService._radarr = None
        MediaService._sonarr = None

        results = await service.get_upcoming(days=7)

        assert results == []

    @pytest.mark.asyncio
    async def test_radarr_movie_date_selection_earliest(
        self, mock_radarr_client
    ):
        """Picks earliest of inCinemas/digitalRelease/physicalRelease."""
        service = MediaService()
        MediaService._radarr = mock_radarr_client
        MediaService._sonarr = None
        mock_radarr_client.get_calendar.return_value = [
            RADARR_CALENDAR_MOVIE_CINEMA,
        ]

        results = await service.get_upcoming(days=30)

        assert results[0]["date"] == "2026-03-10"
        assert results[0]["date_label"] == "Cinema"

    @pytest.mark.asyncio
    async def test_radarr_movie_digital_only(self, mock_radarr_client):
        """Movie with only digitalRelease uses that date."""
        service = MediaService()
        MediaService._radarr = mock_radarr_client
        MediaService._sonarr = None
        mock_radarr_client.get_calendar.return_value = [
            RADARR_CALENDAR_MOVIE_DIGITAL,
        ]

        results = await service.get_upcoming(days=30)

        assert results[0]["date"] == "2026-03-15"
        assert results[0]["date_label"] == "Digital"

    @pytest.mark.asyncio
    async def test_in_library_flag(
        self, mock_radarr_client, mock_sonarr_client
    ):
        """Items with 'id' field have in_library=True, without have False."""
        service = MediaService()
        MediaService._radarr = mock_radarr_client
        MediaService._sonarr = mock_sonarr_client
        mock_radarr_client.get_calendar.return_value = [
            RADARR_CALENDAR_MOVIE_CINEMA,   # has id=1
            RADARR_CALENDAR_MOVIE_NO_ID,    # no id
        ]
        mock_sonarr_client.get_calendar.return_value = [
            SONARR_CALENDAR_EPISODE,        # has id=501
            SONARR_CALENDAR_EPISODE_NO_ID,  # no id
        ]

        results = await service.get_upcoming(days=30)

        by_title = {r["title"]: r for r in results}
        assert by_title["Movie A"]["in_library"] is True
        assert by_title["Movie C"]["in_library"] is False
        assert by_title["Pilot"]["in_library"] is True
        assert by_title["Unmonitored Ep"]["in_library"] is False

    @pytest.mark.asyncio
    async def test_api_error_one_service_still_returns_other(
        self, mock_radarr_client, mock_sonarr_client
    ):
        """API error on one service still returns results from the other."""
        service = MediaService()
        MediaService._radarr = mock_radarr_client
        MediaService._sonarr = mock_sonarr_client
        mock_radarr_client.get_calendar.side_effect = Exception("Radarr down")
        mock_sonarr_client.get_calendar.return_value = [
            SONARR_CALENDAR_EPISODE,
        ]

        results = await service.get_upcoming(days=7)

        assert len(results) == 1
        assert results[0]["type"] == "episode"

    @pytest.mark.asyncio
    async def test_radarr_movie_no_dates(self, mock_radarr_client):
        """Movie with no date fields gets empty date and Unknown label."""
        service = MediaService()
        MediaService._radarr = mock_radarr_client
        MediaService._sonarr = None
        mock_radarr_client.get_calendar.return_value = [
            {"title": "No Dates", "tmdbId": 999, "year": 2026},
        ]

        results = await service.get_upcoming(days=7)

        assert results[0]["date"] == ""
        assert results[0]["date_label"] == "Unknown"

    @pytest.mark.asyncio
    async def test_normalized_schema_movie(self, mock_radarr_client):
        """Movie items have all expected schema fields."""
        service = MediaService()
        MediaService._radarr = mock_radarr_client
        MediaService._sonarr = None
        mock_radarr_client.get_calendar.return_value = [
            RADARR_CALENDAR_MOVIE_CINEMA,
        ]

        results = await service.get_upcoming(days=30)
        item = results[0]

        assert item["type"] == "movie"
        assert item["title"] == "Movie A"
        assert item["series_title"] is None
        assert item["date"] == "2026-03-10"
        assert item["date_label"] == "Cinema"
        assert item["year"] == 2026
        assert item["season"] is None
        assert item["episode"] is None
        assert item["in_library"] is True
        assert item["media_id"] == "100"
        assert item["internal_id"] == 1

    @pytest.mark.asyncio
    async def test_normalized_schema_episode(self, mock_sonarr_client):
        """Episode items have all expected schema fields."""
        service = MediaService()
        MediaService._radarr = None
        MediaService._sonarr = mock_sonarr_client
        mock_sonarr_client.get_calendar.return_value = [
            SONARR_CALENDAR_EPISODE,
        ]

        results = await service.get_upcoming(days=30)
        item = results[0]

        assert item["type"] == "episode"
        assert item["title"] == "Pilot"
        assert item["series_title"] == "New Show"
        assert item["date"] == "2026-03-08"
        assert item["date_label"] == "Airing"
        assert item["year"] is None
        assert item["season"] == 1
        assert item["episode"] == 1
        assert item["in_library"] is True
        assert item["media_id"] == "9000"
        assert item["internal_id"] == 10


# ---------------------------------------------------------------------------
# Missing/Wanted — sample data
# ---------------------------------------------------------------------------

RADARR_MISSING_MOVIE_1 = {
    "id": 1,
    "title": "Fight Club",
    "year": 1999,
    "tmdbId": 550,
    "monitored": True,
}

RADARR_MISSING_MOVIE_2 = {
    "id": 2,
    "title": "Pulp Fiction",
    "year": 1994,
    "tmdbId": 680,
    "monitored": True,
}

RADARR_CUTOFF_MOVIE = {
    "id": 3,
    "title": "Inception",
    "year": 2010,
    "tmdbId": 27205,
    "monitored": True,
}

SONARR_MISSING_EPISODE_1 = {
    "id": 101,
    "seriesId": 42,
    "seasonNumber": 1,
    "episodeNumber": 5,
    "title": "Pilot",
    "monitored": True,
    "series": {"id": 42, "title": "Breaking Bad", "year": 2008, "tvdbId": 81189},
}

SONARR_MISSING_EPISODE_2 = {
    "id": 102,
    "seriesId": 42,
    "seasonNumber": 1,
    "episodeNumber": 6,
    "title": "Crazy Handful of Nothin'",
    "monitored": True,
    "series": {"id": 42, "title": "Breaking Bad", "year": 2008, "tvdbId": 81189},
}

SONARR_CUTOFF_EPISODE = {
    "id": 201,
    "seriesId": 50,
    "seasonNumber": 2,
    "episodeNumber": 1,
    "title": "Hello, Ms. Cobel",
    "monitored": True,
    "series": {"id": 50, "title": "Severance", "year": 2022, "tvdbId": 295759},
}


# ---------------------------------------------------------------------------
# _normalize_radarr_missing / _normalize_sonarr_missing
# ---------------------------------------------------------------------------


class TestNormalizeRadarrMissing:
    def test_standard_movie(self):
        """Standard Radarr missing movie normalizes to unified schema."""
        result = MediaService._normalize_radarr_missing(RADARR_MISSING_MOVIE_1)

        assert result["type"] == "movie"
        assert result["title"] == "Fight Club"
        assert result["series_title"] is None
        assert result["year"] == 1999
        assert result["season"] is None
        assert result["episode"] is None
        assert result["media_id"] == "550"
        assert result["internal_id"] == 1
        assert result["service"] == "radarr"

    def test_missing_fields(self):
        """Movie with missing optional fields gets safe defaults."""
        movie = {"id": 99, "monitored": True}
        result = MediaService._normalize_radarr_missing(movie)

        assert result["type"] == "movie"
        assert result["title"] == ""
        assert result["year"] is None
        assert result["media_id"] == ""
        assert result["internal_id"] == 99
        assert result["service"] == "radarr"


class TestNormalizeSonarrMissing:
    def test_episode_with_full_info(self):
        """Sonarr missing episode with full series info normalizes correctly."""
        result = MediaService._normalize_sonarr_missing(SONARR_MISSING_EPISODE_1)

        assert result["type"] == "episode"
        assert result["title"] == "Pilot"
        assert result["series_title"] == "Breaking Bad"
        assert result["year"] == 2008
        assert result["season"] == 1
        assert result["episode"] == 5
        assert result["media_id"] == "81189"
        assert result["internal_id"] == 101
        assert result["service"] == "sonarr"

    def test_missing_season_episode(self):
        """Episode with missing season/episode numbers gets None defaults."""
        ep = {
            "id": 999,
            "title": "Unknown Episode",
            "monitored": True,
            "series": {"id": 1, "title": "Some Show"},
        }
        result = MediaService._normalize_sonarr_missing(ep)

        assert result["type"] == "episode"
        assert result["title"] == "Unknown Episode"
        assert result["series_title"] == "Some Show"
        assert result["season"] is None
        assert result["episode"] is None
        assert result["media_id"] == ""
        assert result["internal_id"] == 999
        assert result["service"] == "sonarr"


# ---------------------------------------------------------------------------
# get_missing_media
# ---------------------------------------------------------------------------


class TestGetMissingMedia:
    @pytest.mark.asyncio
    async def test_both_services_merged_sorted(
        self, mock_radarr_client, mock_sonarr_client
    ):
        """Both services enabled — returns combined, title-sorted list."""
        service = MediaService()
        MediaService._radarr = mock_radarr_client
        MediaService._sonarr = mock_sonarr_client
        mock_radarr_client.get_missing.return_value = [
            RADARR_MISSING_MOVIE_1,
            RADARR_MISSING_MOVIE_2,
        ]
        mock_sonarr_client.get_missing.return_value = [
            SONARR_MISSING_EPISODE_1,
        ]

        results = await service.get_missing_media()

        assert len(results) == 3
        # All items should have service tags
        services = {r["service"] for r in results}
        assert services == {"radarr", "sonarr"}
        # Sorted by title
        titles = [r["title"] for r in results]
        assert titles == sorted(titles, key=str.lower)

    @pytest.mark.asyncio
    async def test_radarr_only(self, mock_radarr_client):
        """Only Radarr enabled — returns only movies."""
        service = MediaService()
        MediaService._radarr = mock_radarr_client
        MediaService._sonarr = None
        mock_radarr_client.get_missing.return_value = [
            RADARR_MISSING_MOVIE_1,
        ]

        results = await service.get_missing_media()

        assert len(results) == 1
        assert results[0]["type"] == "movie"
        assert results[0]["service"] == "radarr"

    @pytest.mark.asyncio
    async def test_sonarr_only(self, mock_sonarr_client):
        """Only Sonarr enabled — returns only episodes."""
        service = MediaService()
        MediaService._radarr = None
        MediaService._sonarr = mock_sonarr_client
        mock_sonarr_client.get_missing.return_value = [
            SONARR_MISSING_EPISODE_1,
        ]

        results = await service.get_missing_media()

        assert len(results) == 1
        assert results[0]["type"] == "episode"
        assert results[0]["service"] == "sonarr"

    @pytest.mark.asyncio
    async def test_no_services_enabled(self):
        """Neither enabled — returns empty list."""
        service = MediaService()
        MediaService._radarr = None
        MediaService._sonarr = None

        results = await service.get_missing_media()

        assert results == []

    @pytest.mark.asyncio
    async def test_one_service_errors(
        self, mock_radarr_client, mock_sonarr_client
    ):
        """Error from one service — still returns results from the other."""
        service = MediaService()
        MediaService._radarr = mock_radarr_client
        MediaService._sonarr = mock_sonarr_client
        mock_radarr_client.get_missing.side_effect = Exception("Radarr down")
        mock_sonarr_client.get_missing.return_value = [
            SONARR_MISSING_EPISODE_1,
        ]

        results = await service.get_missing_media()

        assert len(results) == 1
        assert results[0]["type"] == "episode"


# ---------------------------------------------------------------------------
# get_cutoff_unmet_media
# ---------------------------------------------------------------------------


class TestGetCutoffUnmetMedia:
    @pytest.mark.asyncio
    async def test_both_services(
        self, mock_radarr_client, mock_sonarr_client
    ):
        """Both services return cutoff unmet items — merged and sorted."""
        service = MediaService()
        MediaService._radarr = mock_radarr_client
        MediaService._sonarr = mock_sonarr_client
        mock_radarr_client.get_cutoff_unmet.return_value = [
            RADARR_CUTOFF_MOVIE,
        ]
        mock_sonarr_client.get_cutoff_unmet.return_value = [
            SONARR_CUTOFF_EPISODE,
        ]

        results = await service.get_cutoff_unmet_media()

        assert len(results) == 2
        services = {r["service"] for r in results}
        assert services == {"radarr", "sonarr"}

    @pytest.mark.asyncio
    async def test_one_service_only(self, mock_radarr_client):
        """Only one service has cutoff unmet items."""
        service = MediaService()
        MediaService._radarr = mock_radarr_client
        MediaService._sonarr = None
        mock_radarr_client.get_cutoff_unmet.return_value = [
            RADARR_CUTOFF_MOVIE,
        ]

        results = await service.get_cutoff_unmet_media()

        assert len(results) == 1
        assert results[0]["title"] == "Inception"

    @pytest.mark.asyncio
    async def test_error_returns_other(
        self, mock_radarr_client, mock_sonarr_client
    ):
        """Error from one service — still returns results from the other."""
        service = MediaService()
        MediaService._radarr = mock_radarr_client
        MediaService._sonarr = mock_sonarr_client
        mock_radarr_client.get_cutoff_unmet.side_effect = Exception("down")
        mock_sonarr_client.get_cutoff_unmet.return_value = [
            SONARR_CUTOFF_EPISODE,
        ]

        results = await service.get_cutoff_unmet_media()

        assert len(results) == 1
        assert results[0]["service"] == "sonarr"


# ---------------------------------------------------------------------------
# trigger_missing_search
# ---------------------------------------------------------------------------


class TestTriggerMissingSearch:
    @pytest.mark.asyncio
    async def test_radarr_dispatch(self, mock_radarr_client):
        """Dispatches search to Radarr for service='radarr'."""
        service = MediaService()
        MediaService._radarr = mock_radarr_client
        mock_radarr_client.search_command.return_value = True

        result = await service.trigger_missing_search("radarr", 1)

        assert result is True
        mock_radarr_client.search_command.assert_awaited_once_with(1)

    @pytest.mark.asyncio
    async def test_sonarr_dispatch(self, mock_sonarr_client):
        """Dispatches search to Sonarr for service='sonarr'."""
        service = MediaService()
        MediaService._sonarr = mock_sonarr_client
        mock_sonarr_client.search_command.return_value = True

        result = await service.trigger_missing_search("sonarr", 101)

        assert result is True
        mock_sonarr_client.search_command.assert_awaited_once_with(101)

    @pytest.mark.asyncio
    async def test_unavailable_service(self):
        """Returns False when the requested service is not enabled."""
        service = MediaService()
        MediaService._radarr = None
        MediaService._sonarr = None

        result = await service.trigger_missing_search("radarr", 1)

        assert result is False

    @pytest.mark.asyncio
    async def test_exception(self, mock_radarr_client):
        """Returns False on exception from client."""
        service = MediaService()
        MediaService._radarr = mock_radarr_client
        mock_radarr_client.search_command.side_effect = Exception("boom")

        result = await service.trigger_missing_search("radarr", 1)

        assert result is False


# ---------------------------------------------------------------------------
# Queue normalizers
# ---------------------------------------------------------------------------

RADARR_QUEUE_ITEM = {
    "id": 1, "movieId": 10, "title": "Fight Club",
    "status": "downloading", "trackedDownloadStatus": "ok",
    "trackedDownloadState": "downloading",
    "protocol": "usenet", "size": 1500000000, "sizeleft": 750000000,
    "timeleft": "00:15:00", "downloadClient": "SABnzbd",
    "movie": {"id": 10, "title": "Fight Club", "year": 1999, "tmdbId": 550},
}

SONARR_QUEUE_ITEM = {
    "id": 101, "seriesId": 42, "episodeId": 201, "title": "Pilot",
    "status": "downloading", "trackedDownloadStatus": "ok",
    "trackedDownloadState": "downloading",
    "protocol": "torrent", "size": 500000000, "sizeleft": 100000000,
    "timeleft": "00:05:00", "downloadClient": "qBittorrent",
    "series": {"id": 42, "title": "Breaking Bad", "year": 2008, "tvdbId": 81189},
    "episode": {"id": 201, "seasonNumber": 1, "episodeNumber": 5, "title": "Pilot"},
}

LIDARR_QUEUE_ITEM = {
    "id": 301, "artistId": 5, "albumId": 20, "title": "OK Computer",
    "status": "downloading", "trackedDownloadStatus": "ok",
    "trackedDownloadState": "downloading",
    "protocol": "usenet", "size": 300000000, "sizeleft": 150000000,
    "timeleft": "00:03:00", "downloadClient": "SABnzbd",
}


class TestNormalizeRadarrQueue:
    def test_standard_item(self):
        """Standard Radarr queue item normalizes to unified schema."""
        result = MediaService._normalize_radarr_queue(RADARR_QUEUE_ITEM)

        assert result["type"] == "movie"
        assert result["title"] == "Fight Club"
        assert result["year"] == 1999
        assert result["series_title"] is None
        assert result["status"] == "downloading"
        assert result["progress"] == 50
        assert result["timeleft"] == "00:15:00"
        assert result["protocol"] == "usenet"
        assert result["download_client"] == "SABnzbd"
        assert result["media_id"] == "550"
        assert result["internal_id"] == 1
        assert result["service"] == "radarr"

    def test_missing_fields(self):
        """Item with missing movie/size defaults safely."""
        item = {"id": 99, "status": "queued"}
        result = MediaService._normalize_radarr_queue(item)

        assert result["type"] == "movie"
        assert result["title"] == ""
        assert result["year"] is None
        assert result["progress"] == 0
        assert result["protocol"] == ""
        assert result["download_client"] == ""
        assert result["internal_id"] == 99
        assert result["service"] == "radarr"


class TestNormalizeSonarrQueue:
    def test_standard_item(self):
        """Standard Sonarr queue item normalizes to unified schema."""
        result = MediaService._normalize_sonarr_queue(SONARR_QUEUE_ITEM)

        assert result["type"] == "episode"
        assert result["title"] == "Pilot"
        assert result["series_title"] == "Breaking Bad"
        assert result["year"] == 2008
        assert result["season"] == 1
        assert result["episode"] == 5
        assert result["status"] == "downloading"
        assert result["progress"] == 80
        assert result["timeleft"] == "00:05:00"
        assert result["protocol"] == "torrent"
        assert result["download_client"] == "qBittorrent"
        assert result["media_id"] == "81189"
        assert result["internal_id"] == 101
        assert result["service"] == "sonarr"

    def test_missing_fields(self):
        """Item with missing episode/series defaults safely."""
        item = {"id": 999, "status": "queued"}
        result = MediaService._normalize_sonarr_queue(item)

        assert result["type"] == "episode"
        assert result["title"] == ""
        assert result["series_title"] is None
        assert result["season"] is None
        assert result["episode"] is None
        assert result["progress"] == 0
        assert result["internal_id"] == 999
        assert result["service"] == "sonarr"


class TestNormalizeLidarrQueue:
    def test_standard_item(self):
        """Standard Lidarr queue item normalizes to unified schema."""
        result = MediaService._normalize_lidarr_queue(LIDARR_QUEUE_ITEM)

        assert result["type"] == "album"
        assert result["title"] == "OK Computer"
        assert result["year"] is None
        assert result["status"] == "downloading"
        assert result["progress"] == 50
        assert result["timeleft"] == "00:03:00"
        assert result["protocol"] == "usenet"
        assert result["download_client"] == "SABnzbd"
        assert result["internal_id"] == 301
        assert result["service"] == "lidarr"

    def test_missing_fields(self):
        """Item with missing size/title defaults safely."""
        item = {"id": 500}
        result = MediaService._normalize_lidarr_queue(item)

        assert result["type"] == "album"
        assert result["title"] == ""
        assert result["progress"] == 0
        assert result["protocol"] == ""
        assert result["internal_id"] == 500
        assert result["service"] == "lidarr"


# ---------------------------------------------------------------------------
# get_queue_media
# ---------------------------------------------------------------------------


class TestGetQueueMedia:
    @pytest.mark.asyncio
    async def test_all_services_merged_sorted(
        self, mock_radarr_client, mock_sonarr_client, mock_lidarr_client
    ):
        """All three services enabled — returns combined, title-sorted list."""
        service = MediaService()
        MediaService._radarr = mock_radarr_client
        MediaService._sonarr = mock_sonarr_client
        MediaService._lidarr = mock_lidarr_client
        mock_radarr_client.get_queue.return_value = [RADARR_QUEUE_ITEM]
        mock_sonarr_client.get_queue.return_value = [SONARR_QUEUE_ITEM]
        mock_lidarr_client.get_queue.return_value = [LIDARR_QUEUE_ITEM]

        results = await service.get_queue_media()

        assert len(results) == 3
        services = {r["service"] for r in results}
        assert services == {"radarr", "sonarr", "lidarr"}
        titles = [r["title"] for r in results]
        assert titles == sorted(titles, key=str.lower)

    @pytest.mark.asyncio
    async def test_radarr_only(self, mock_radarr_client):
        """Only Radarr enabled — returns only movies."""
        service = MediaService()
        MediaService._radarr = mock_radarr_client
        MediaService._sonarr = None
        MediaService._lidarr = None
        mock_radarr_client.get_queue.return_value = [RADARR_QUEUE_ITEM]

        results = await service.get_queue_media()

        assert len(results) == 1
        assert results[0]["type"] == "movie"
        assert results[0]["service"] == "radarr"

    @pytest.mark.asyncio
    async def test_no_services_enabled(self):
        """No services enabled — returns empty list."""
        service = MediaService()
        MediaService._radarr = None
        MediaService._sonarr = None
        MediaService._lidarr = None

        results = await service.get_queue_media()

        assert results == []

    @pytest.mark.asyncio
    async def test_one_service_errors(
        self, mock_radarr_client, mock_sonarr_client
    ):
        """Error from one service — still returns results from the other."""
        service = MediaService()
        MediaService._radarr = mock_radarr_client
        MediaService._sonarr = mock_sonarr_client
        MediaService._lidarr = None
        mock_radarr_client.get_queue.side_effect = Exception("Radarr down")
        mock_sonarr_client.get_queue.return_value = [SONARR_QUEUE_ITEM]

        results = await service.get_queue_media()

        assert len(results) == 1
        assert results[0]["type"] == "episode"

    @pytest.mark.asyncio
    async def test_lidarr_included(self, mock_lidarr_client):
        """Lidarr items appear with type 'album'."""
        service = MediaService()
        MediaService._radarr = None
        MediaService._sonarr = None
        MediaService._lidarr = mock_lidarr_client
        mock_lidarr_client.get_queue.return_value = [LIDARR_QUEUE_ITEM]

        results = await service.get_queue_media()

        assert len(results) == 1
        assert results[0]["type"] == "album"
        assert results[0]["service"] == "lidarr"


# ---------------------------------------------------------------------------
# get_history
# ---------------------------------------------------------------------------

RADARR_HISTORY_RECORD = {
    "id": 1, "movieId": 10,
    "sourceTitle": "Fight.Club.1999.1080p.BluRay",
    "quality": {"quality": {"name": "Bluray-1080p"}},
    "date": "2026-03-09T14:30:00Z",
    "eventType": "grabbed",
    "data": {"indexer": "NZBgeek"},
    "movie": {"title": "Fight Club", "year": 1999, "tmdbId": 550},
}

SONARR_HISTORY_RECORD = {
    "id": 101, "seriesId": 42, "episodeId": 201,
    "sourceTitle": "Breaking.Bad.S01E01.720p",
    "quality": {"quality": {"name": "HDTV-720p"}},
    "date": "2026-03-09T12:00:00Z",
    "eventType": "grabbed",
    "data": {"indexer": "NZBgeek"},
    "series": {"title": "Breaking Bad", "year": 2008, "tvdbId": 81189},
    "episode": {"title": "Pilot", "seasonNumber": 1, "episodeNumber": 1},
}


class TestGetHistory:
    @pytest.mark.asyncio
    async def test_both_services_merged_sorted_desc(
        self, mock_radarr_client, mock_sonarr_client
    ):
        """Both services return items — merged and sorted by date descending."""
        service = MediaService()
        MediaService._radarr = mock_radarr_client
        MediaService._sonarr = mock_sonarr_client
        mock_radarr_client.get_history.return_value = [RADARR_HISTORY_RECORD]
        mock_sonarr_client.get_history.return_value = [SONARR_HISTORY_RECORD]

        results = await service.get_history()

        assert len(results) == 2
        # Radarr (14:30) should come before Sonarr (12:00) — newest first
        assert results[0]["service"] == "radarr"
        assert results[0]["title"] == "Fight Club"
        assert results[1]["service"] == "sonarr"
        assert results[1]["title"] == "Breaking Bad"

    @pytest.mark.asyncio
    async def test_radarr_only(self, mock_radarr_client):
        """Only Radarr enabled — returns only movie items."""
        service = MediaService()
        MediaService._radarr = mock_radarr_client
        MediaService._sonarr = None
        mock_radarr_client.get_history.return_value = [RADARR_HISTORY_RECORD]

        results = await service.get_history()

        assert len(results) == 1
        assert results[0]["type"] == "movie"

    @pytest.mark.asyncio
    async def test_sonarr_only(self, mock_sonarr_client):
        """Only Sonarr enabled — returns only episode items."""
        service = MediaService()
        MediaService._radarr = None
        MediaService._sonarr = mock_sonarr_client
        mock_sonarr_client.get_history.return_value = [SONARR_HISTORY_RECORD]

        results = await service.get_history()

        assert len(results) == 1
        assert results[0]["type"] == "episode"

    @pytest.mark.asyncio
    async def test_no_services(self):
        """Neither enabled — returns empty list."""
        service = MediaService()
        MediaService._radarr = None
        MediaService._sonarr = None

        results = await service.get_history()

        assert results == []

    @pytest.mark.asyncio
    async def test_one_exception_partial_result(
        self, mock_radarr_client, mock_sonarr_client
    ):
        """One service raises — other still returns results."""
        service = MediaService()
        MediaService._radarr = mock_radarr_client
        MediaService._sonarr = mock_sonarr_client
        mock_radarr_client.get_history.side_effect = Exception("Radarr down")
        mock_sonarr_client.get_history.return_value = [SONARR_HISTORY_RECORD]

        results = await service.get_history()

        assert len(results) == 1
        assert results[0]["service"] == "sonarr"

    @pytest.mark.asyncio
    async def test_event_type_passthrough(
        self, mock_radarr_client, mock_sonarr_client
    ):
        """Event type parameter passed through to both clients."""
        service = MediaService()
        MediaService._radarr = mock_radarr_client
        MediaService._sonarr = mock_sonarr_client

        await service.get_history(event_type="grabbed")

        mock_radarr_client.get_history.assert_called_once_with(
            1, 20, "grabbed"
        )
        mock_sonarr_client.get_history.assert_called_once_with(
            1, 20, "grabbed"
        )

    @pytest.mark.asyncio
    async def test_normalize_radarr_history(self):
        """Radarr normalizer produces correct schema."""
        result = MediaService._normalize_radarr_history(RADARR_HISTORY_RECORD)

        assert result["type"] == "movie"
        assert result["title"] == "Fight Club"
        assert result["episode_title"] is None
        assert result["season"] is None
        assert result["episode"] is None
        assert result["date"] == "2026-03-09T14:30:00Z"
        assert result["event_type"] == "grabbed"
        assert result["quality"] == "Bluray-1080p"
        assert result["source_title"] == "Fight.Club.1999.1080p.BluRay"
        assert result["service"] == "radarr"

    @pytest.mark.asyncio
    async def test_normalize_sonarr_history(self):
        """Sonarr normalizer produces correct schema."""
        result = MediaService._normalize_sonarr_history(SONARR_HISTORY_RECORD)

        assert result["type"] == "episode"
        assert result["title"] == "Breaking Bad"
        assert result["episode_title"] == "Pilot"
        assert result["season"] == 1
        assert result["episode"] == 1
        assert result["date"] == "2026-03-09T12:00:00Z"
        assert result["event_type"] == "grabbed"
        assert result["quality"] == "HDTV-720p"
        assert result["source_title"] == "Breaking.Bad.S01E01.720p"
        assert result["service"] == "sonarr"

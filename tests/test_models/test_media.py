"""
Tests for src.models.media dataclasses.
"""

import pytest

from src.models.media import (
    Artist,
    MediaItem,
    Movie,
    QualityProfile,
    RootFolder,
    SearchResult,
    Series,
    Tag,
)


# ---------------------------------------------------------------------------
# MediaItem
# ---------------------------------------------------------------------------


class TestMediaItem:
    """Tests for the MediaItem base dataclass."""

    def test_creation_all_fields(self):
        item = MediaItem(
            id="123",
            title="Test Media",
            year=2024,
            overview="A test overview.",
            poster_url="https://example.com/poster.jpg",
        )
        assert item.id == "123"
        assert item.title == "Test Media"
        assert item.year == 2024
        assert item.overview == "A test overview."
        assert item.poster_url == "https://example.com/poster.jpg"

    def test_creation_optional_fields_none(self):
        item = MediaItem(
            id="456",
            title="Minimal",
            year=None,
            overview=None,
            poster_url=None,
        )
        assert item.year is None
        assert item.overview is None
        assert item.poster_url is None

    def test_field_types(self):
        item = MediaItem(
            id="1",
            title="Title",
            year=2020,
            overview="Overview",
            poster_url="https://example.com",
        )
        assert isinstance(item.id, str)
        assert isinstance(item.title, str)
        assert isinstance(item.year, int)
        assert isinstance(item.overview, str)
        assert isinstance(item.poster_url, str)


# ---------------------------------------------------------------------------
# Movie
# ---------------------------------------------------------------------------


class TestMovie:
    """Tests for the Movie dataclass."""

    def test_creation_all_fields(self):
        movie = Movie(
            id="m1",
            title="Test Movie",
            year=2023,
            overview="A movie overview.",
            poster_url="https://example.com/movie.jpg",
            tmdb_id=55555,
            quality_profile_id=3,
            monitored=False,
            minimum_availability="released",
        )
        assert movie.id == "m1"
        assert movie.title == "Test Movie"
        assert movie.year == 2023
        assert movie.overview == "A movie overview."
        assert movie.poster_url == "https://example.com/movie.jpg"
        assert movie.tmdb_id == 55555
        assert movie.quality_profile_id == 3
        assert movie.monitored is False
        assert movie.minimum_availability == "released"

    def test_default_values(self):
        movie = Movie(
            id="m2",
            title="Defaults",
            year=None,
            overview=None,
            poster_url=None,
            tmdb_id=99999,
        )
        assert movie.quality_profile_id is None
        assert movie.monitored is True
        assert movie.minimum_availability == "announced"

    def test_inherits_media_item(self):
        movie = Movie(
            id="m3",
            title="Inheritance",
            year=2020,
            overview=None,
            poster_url=None,
            tmdb_id=11111,
        )
        assert isinstance(movie, MediaItem)

    def test_field_types(self):
        movie = Movie(
            id="m4",
            title="Types",
            year=2024,
            overview="o",
            poster_url="p",
            tmdb_id=100,
            quality_profile_id=2,
            monitored=True,
            minimum_availability="announced",
        )
        assert isinstance(movie.tmdb_id, int)
        assert isinstance(movie.quality_profile_id, int)
        assert isinstance(movie.monitored, bool)
        assert isinstance(movie.minimum_availability, str)


# ---------------------------------------------------------------------------
# Series
# ---------------------------------------------------------------------------


class TestSeries:
    """Tests for the Series dataclass."""

    def test_creation_all_fields(self):
        series = Series(
            id="s1",
            title="Test Series",
            year=2022,
            overview="A series overview.",
            poster_url="https://example.com/series.jpg",
            tvdb_id=77777,
            season_count=5,
            monitored_seasons=[1, 2, 3],
            quality_profile_id=4,
            season_folder=False,
        )
        assert series.id == "s1"
        assert series.title == "Test Series"
        assert series.year == 2022
        assert series.overview == "A series overview."
        assert series.poster_url == "https://example.com/series.jpg"
        assert series.tvdb_id == 77777
        assert series.season_count == 5
        assert series.monitored_seasons == [1, 2, 3]
        assert series.quality_profile_id == 4
        assert series.season_folder is False

    def test_default_values(self):
        series = Series(
            id="s2",
            title="Defaults",
            year=None,
            overview=None,
            poster_url=None,
            tvdb_id=88888,
            season_count=3,
            monitored_seasons=[1],
        )
        assert series.quality_profile_id is None
        assert series.season_folder is True

    def test_inherits_media_item(self):
        series = Series(
            id="s3",
            title="Inheritance",
            year=2021,
            overview=None,
            poster_url=None,
            tvdb_id=11111,
            season_count=1,
            monitored_seasons=[],
        )
        assert isinstance(series, MediaItem)

    def test_monitored_seasons_empty_list(self):
        series = Series(
            id="s4",
            title="Empty Seasons",
            year=2023,
            overview=None,
            poster_url=None,
            tvdb_id=22222,
            season_count=0,
            monitored_seasons=[],
        )
        assert series.monitored_seasons == []

    def test_field_types(self):
        series = Series(
            id="s5",
            title="Types",
            year=2024,
            overview="o",
            poster_url="p",
            tvdb_id=100,
            season_count=3,
            monitored_seasons=[1, 2],
            quality_profile_id=5,
            season_folder=True,
        )
        assert isinstance(series.tvdb_id, int)
        assert isinstance(series.season_count, int)
        assert isinstance(series.monitored_seasons, list)
        assert isinstance(series.quality_profile_id, int)
        assert isinstance(series.season_folder, bool)


# ---------------------------------------------------------------------------
# Artist
# ---------------------------------------------------------------------------


class TestArtist:
    """Tests for the Artist dataclass."""

    def test_creation_all_fields(self):
        artist = Artist(
            id="a1",
            title="Test Artist",
            year=2019,
            overview="An artist overview.",
            poster_url="https://example.com/artist.jpg",
            artist_id="art-001",
            artist_type="solo",
            metadata_profile_id=2,
            album_folder=False,
        )
        assert artist.id == "a1"
        assert artist.title == "Test Artist"
        assert artist.year == 2019
        assert artist.overview == "An artist overview."
        assert artist.poster_url == "https://example.com/artist.jpg"
        assert artist.artist_id == "art-001"
        assert artist.artist_type == "solo"
        assert artist.metadata_profile_id == 2
        assert artist.album_folder is False

    def test_default_values(self):
        artist = Artist(
            id="a2",
            title="Defaults",
            year=None,
            overview=None,
            poster_url=None,
            artist_id="art-002",
            artist_type="group",
        )
        assert artist.metadata_profile_id is None
        assert artist.album_folder is True

    def test_inherits_media_item(self):
        artist = Artist(
            id="a3",
            title="Inheritance",
            year=2020,
            overview=None,
            poster_url=None,
            artist_id="art-003",
            artist_type="band",
        )
        assert isinstance(artist, MediaItem)

    def test_field_types(self):
        artist = Artist(
            id="a4",
            title="Types",
            year=2024,
            overview="o",
            poster_url="p",
            artist_id="art-004",
            artist_type="solo",
            metadata_profile_id=1,
            album_folder=True,
        )
        assert isinstance(artist.artist_id, str)
        assert isinstance(artist.artist_type, str)
        assert isinstance(artist.metadata_profile_id, int)
        assert isinstance(artist.album_folder, bool)


# ---------------------------------------------------------------------------
# QualityProfile
# ---------------------------------------------------------------------------


class TestQualityProfile:
    """Tests for the QualityProfile dataclass."""

    def test_creation(self):
        profile = QualityProfile(id=1, name="HD-1080p")
        assert profile.id == 1
        assert profile.name == "HD-1080p"

    def test_field_types(self):
        profile = QualityProfile(id=7, name="Ultra-HD")
        assert isinstance(profile.id, int)
        assert isinstance(profile.name, str)


# ---------------------------------------------------------------------------
# RootFolder
# ---------------------------------------------------------------------------


class TestRootFolder:
    """Tests for the RootFolder dataclass."""

    def test_creation(self):
        folder = RootFolder(path="/mnt/media/movies", free_space=500000000000)
        assert folder.path == "/mnt/media/movies"
        assert folder.free_space == 500000000000

    def test_field_types(self):
        folder = RootFolder(path="/data", free_space=0)
        assert isinstance(folder.path, str)
        assert isinstance(folder.free_space, int)


# ---------------------------------------------------------------------------
# Tag
# ---------------------------------------------------------------------------


class TestTag:
    """Tests for the Tag dataclass."""

    def test_creation(self):
        tag = Tag(id=1, label="telegram")
        assert tag.id == 1
        assert tag.label == "telegram"

    def test_field_types(self):
        tag = Tag(id=42, label="automated")
        assert isinstance(tag.id, int)
        assert isinstance(tag.label, str)


# ---------------------------------------------------------------------------
# SearchResult
# ---------------------------------------------------------------------------


class TestSearchResult:
    """Tests for the SearchResult dataclass."""

    def test_creation_all_fields(self):
        items = [
            MediaItem(id="1", title="Result 1", year=2020, overview=None, poster_url=None),
            MediaItem(id="2", title="Result 2", year=2021, overview=None, poster_url=None),
        ]
        result = SearchResult(
            media_type="movie",
            items=items,
            total_results=50,
            page=3,
        )
        assert result.media_type == "movie"
        assert result.items == items
        assert len(result.items) == 2
        assert result.total_results == 50
        assert result.page == 3

    def test_default_page(self):
        result = SearchResult(
            media_type="series",
            items=[],
            total_results=0,
        )
        assert result.page == 1

    def test_empty_items(self):
        result = SearchResult(
            media_type="artist",
            items=[],
            total_results=0,
        )
        assert result.items == []
        assert result.total_results == 0

    def test_items_with_movie_subclass(self):
        movie = Movie(
            id="m1",
            title="Movie Result",
            year=2024,
            overview=None,
            poster_url=None,
            tmdb_id=12345,
        )
        result = SearchResult(
            media_type="movie",
            items=[movie],
            total_results=1,
        )
        assert len(result.items) == 1
        assert isinstance(result.items[0], Movie)

    def test_field_types(self):
        result = SearchResult(
            media_type="series",
            items=[],
            total_results=10,
            page=2,
        )
        assert isinstance(result.media_type, str)
        assert isinstance(result.items, list)
        assert isinstance(result.total_results, int)
        assert isinstance(result.page, int)

"""
Tests for the media handler package structure.

Verifies backward-compatible re-exports from src.bot.handlers.media
and the dispatch configuration in src.bot.handlers.media.dispatch.
"""

import pytest


def test_media_handler_importable_from_package():
    """MediaHandler can be imported from src.bot.handlers.media (backward compat)."""
    from src.bot.handlers.media import MediaHandler
    assert MediaHandler is not None
    assert hasattr(MediaHandler, "get_handler")


@pytest.mark.parametrize("name", [
    "SEARCHING", "SELECTING", "QUALITY_SELECT", "SEASON_SELECT", "ALBUM_SELECT",
])
def test_state_constants_importable_from_package(name):
    """State constants are importable from src.bot.handlers.media."""
    import src.bot.handlers.media as media_pkg
    assert hasattr(media_pkg, name)
    value = getattr(media_pkg, name)
    assert isinstance(value, int)


def test_dispatch_media_config_exists():
    """MEDIA_CONFIG is importable from dispatch module."""
    from src.bot.handlers.media.dispatch import MEDIA_CONFIG
    assert isinstance(MEDIA_CONFIG, dict)


@pytest.mark.parametrize("media_type,expected_config_key", [
    ("movie", "radarr"),
    ("series", "sonarr"),
    ("music", "lidarr"),
])
def test_dispatch_media_config_has_correct_keys(media_type, expected_config_key):
    """MEDIA_CONFIG maps each media type to config key and service methods."""
    from src.bot.handlers.media.dispatch import MEDIA_CONFIG

    assert media_type in MEDIA_CONFIG
    cfg = MEDIA_CONFIG[media_type]
    assert cfg["config_key"] == expected_config_key
    assert "search" in cfg
    assert "add" in cfg
    assert "add_with_profile" in cfg


@pytest.mark.parametrize("media_type,search_method", [
    ("movie", "search_movies"),
    ("series", "search_series"),
    ("music", "search_music"),
])
def test_dispatch_search_method_names(media_type, search_method):
    """MEDIA_CONFIG search methods match MediaService method names."""
    from src.bot.handlers.media.dispatch import MEDIA_CONFIG
    assert MEDIA_CONFIG[media_type]["search"] == search_method


@pytest.mark.parametrize("media_type,add_method", [
    ("movie", "add_movie"),
    ("series", "add_series"),
    ("music", "add_music"),
])
def test_dispatch_add_method_names(media_type, add_method):
    """MEDIA_CONFIG add methods match MediaService method names."""
    from src.bot.handlers.media.dispatch import MEDIA_CONFIG
    assert MEDIA_CONFIG[media_type]["add"] == add_method


@pytest.mark.parametrize("media_type,add_profile_method", [
    ("movie", "add_movie_with_profile"),
    ("series", "add_series_with_profile"),
    ("music", "add_music_with_profile"),
])
def test_dispatch_add_with_profile_method_names(media_type, add_profile_method):
    """MEDIA_CONFIG add_with_profile methods match MediaService method names."""
    from src.bot.handlers.media.dispatch import MEDIA_CONFIG
    assert MEDIA_CONFIG[media_type]["add_with_profile"] == add_profile_method


def test_dispatch_state_constants():
    """State constants are importable from dispatch module."""
    from src.bot.handlers.media.dispatch import (
        SEARCHING, SELECTING, QUALITY_SELECT, SEASON_SELECT, ALBUM_SELECT
    )
    assert SEARCHING == 1
    assert SELECTING == 2
    assert QUALITY_SELECT == 3
    assert SEASON_SELECT == 4
    assert ALBUM_SELECT == 5

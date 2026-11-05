"""
Filename: dispatch.py
Author: Christian Blank (https://github.com/Cyneric)
Created Date: 2024-11-08
Description: Media handler dispatch constants and configuration.

State constants for the media conversation handler and dispatch
configuration mapping media types to their service methods.
"""

# States
SEARCHING = 1
SELECTING = 2
QUALITY_SELECT = 3
SEASON_SELECT = 4
ALBUM_SELECT = 5

# Dispatch configuration mapping media types to service methods.
# Used by MediaHandler to route searches and additions to the
# correct MediaService method without if/elif chains.
MEDIA_CONFIG = {
    "movie": {
        "config_key": "radarr",
        "search": "search_movies",
        "add": "add_movie",
        "add_with_profile": "add_movie_with_profile",
    },
    "series": {
        "config_key": "sonarr",
        "search": "search_series",
        "add": "add_series",
        "add_with_profile": "add_series_with_profile",
    },
    "music": {
        "config_key": "lidarr",
        "search": "search_music",
        "add": "add_music",
        "add_with_profile": "add_music_with_profile",
    },
}

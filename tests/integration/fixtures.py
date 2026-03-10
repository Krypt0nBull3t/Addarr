"""
Shared test data and helpers for integration tests.

Provides reusable search results, quality selection results, queue data,
and utility functions used across multiple test files.
"""


def find_response(harness, method):
    """Find the first captured response matching the given API method."""
    for r in harness.responses:
        if r.method == method:
            return r
    return None


MOVIE_SEARCH_RESULTS = [
    {
        "id": "550",
        "title": "Fight Club (1999)",
        "overview": "An insomniac office worker...",
        "year": 1999,
        "poster": None,
        "ratings": {"imdb": 8.8, "rottenTomatoes": 79},
        "studio": "Fox 2000 Pictures",
        "status": "released",
        "runtime": 139,
        "genres": ["Drama", "Thriller"],
        "data": {"tmdbId": 550, "title": "Fight Club"},
    },
]

MOVIE_QUALITY_RESULT = {
    "type": "quality_selection",
    "profiles": [
        {"id": 1, "name": "HD-1080p"},
        {"id": 2, "name": "Ultra-HD"},
    ],
    "root_folder": "/movies",
    "movie": {"tmdbId": 550, "title": "Fight Club"},
}

SERIES_SEARCH_RESULTS = [
    {
        "id": "81189",
        "title": "Breaking Bad (2008)",
        "overview": "A high school chemistry teacher...",
        "year": 2008,
        "poster": None,
        "ratings": {"tmdb": 8.9, "votes": 1000},
        "network": "AMC",
        "studio": "N/A",
        "status": "ended",
        "seasons": 2,
        "runtime": 45,
        "genres": ["Drama", "Thriller"],
        "data": {"tvdbId": 81189, "title": "Breaking Bad"},
    },
]

SERIES_QUALITY_RESULT = {
    "type": "quality_selection",
    "profiles": [
        {"id": 1, "name": "HD-1080p"},
    ],
    "root_folder": "/tv",
    "series": {"tvdbId": 81189, "title": "Breaking Bad"},
    "seasons": [
        {"seasonNumber": 1, "monitored": True},
        {"seasonNumber": 2, "monitored": True},
    ],
}

MUSIC_ARTIST_RESULTS = [
    {
        "id": "f59c5520-5f46-4d2c-b2c4-822eabf53419",
        "title": "Linkin Park",
        "overview": "Linkin Park is an American rock band...",
        "year": 1996,
        "poster": None,
        "rating": 8.5,
        "genres": "Rock, Nu Metal",
        "type": "Group",
        "status": "active",
        "music_type": "artist",
        "data": {
            "foreignArtistId": "f59c5520-5f46-4d2c-b2c4-822eabf53419",
            "artistName": "Linkin Park",
        },
    },
]

MUSIC_QUALITY_RESULT = {
    "type": "quality_selection",
    "profiles": [
        {"id": 1, "name": "Lossless"},
    ],
    "root_folder": "/music",
}

MUSIC_ALBUM_RESULTS = [
    {
        "id": "album:b1ae2a0f",
        "title": "Hybrid Theory",
        "overview": "Debut studio album",
        "year": 2000,
        "poster": None,
        "rating": 8.5,
        "genres": "Rock",
        "type": "Album",
        "status": "released",
        "music_type": "album",
        "artist_name": "Linkin Park",
        "artist_id": "f59c5520-5f46-4d2c-b2c4-822eabf53419",
        "album_id": "b1ae2a0f",
        "data": {},
    },
]

MUSIC_ALBUM_QUALITY_RESULT = {
    "type": "quality_selection",
    "profiles": [
        {"id": 1, "name": "Lossless"},
    ],
    "root_folder": "/music",
}

DOWNLOADS_QUEUE = {
    "paused": False,
    "speed": "5.2 MB/s",
    "size_remaining": "1.5 GB",
    "items_count": 1,
    "items": [
        {
            "id": "abc123",
            "name": "Ubuntu.22.04.nzb",
            "status": "Downloading",
            "progress": 45.0,
            "size": "2.1 GB",
            "speed": "5.2 MB/s",
            "timeleft": "00:04:30",
        },
    ],
}

DOWNLOADS_EMPTY_QUEUE = {
    "paused": False,
    "speed": "0 B/s",
    "size_remaining": "0 MB",
    "items_count": 0,
    "items": [],
}

HISTORY_ITEMS = [
    {
        "id": 1,
        "title": "Fight Club",
        "event_type": "grabbed",
        "date": "2026-03-09T10:00:00Z",
        "quality": "HD-1080p",
    },
    {
        "id": 2,
        "title": "Breaking Bad S01E01",
        "event_type": "downloaded",
        "date": "2026-03-09T09:00:00Z",
        "quality": "HD-720p",
    },
]

CALENDAR_ITEMS = [
    {
        "title": "Upcoming Movie",
        "type": "movie",
        "date": "2026-03-15",
        "service": "radarr",
        "id": 101,
        "media_id": 101,
    },
    {
        "title": "New Episode S02E01",
        "type": "episode",
        "date": "2026-03-12",
        "service": "sonarr",
        "id": 202,
        "media_id": 202,
    },
]

LIBRARY_MOVIES = [
    {"id": str(i), "title": f"Movie {chr(64 + i)}"} for i in range(1, 16)
]

LIBRARY_SERIES = [
    {"id": str(i), "title": f"Series {chr(64 + i)}"} for i in range(1, 6)
]

MISSING_ITEMS = [
    {
        "title": "Missing Movie",
        "type": "movie",
        "service": "radarr",
        "id": 301,
        "internal_id": 301,
    },
    {
        "title": "Missing Episode S01E05",
        "type": "episode",
        "service": "sonarr",
        "id": 302,
        "internal_id": 302,
    },
]

BAZARR_WANTED_MOVIES = [
    {
        "title": "Fight Club",
        "missing_subtitles": [
            {"name": "English", "code2": "en"},
            {"name": "French", "code2": "fr"},
        ],
    },
    {
        "title": "Inception",
        "missing_subtitles": [
            {"name": "Spanish", "code2": "es"},
        ],
    },
]

QUEUE_ITEMS = [
    {
        "title": "Downloading Movie",
        "type": "movie",
        "progress": 45.0,
        "status": "downloading",
        "id": 401,
    },
    {
        "title": "Downloading Episode",
        "type": "episode",
        "progress": 80.0,
        "status": "downloading",
        "id": 402,
    },
]

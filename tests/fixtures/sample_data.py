RADARR_SEARCH_RESULTS = [
    {
        "tmdbId": 550,
        "title": "Fight Club",
        "year": 1999,
        "overview": "An insomniac office worker...",
        "images": [{"coverType": "poster", "remoteUrl": "https://image.tmdb.org/t/p/w500/poster1.jpg"}],
        "ratings": {"imdb": {"value": 8.8}, "rottenTomatoes": {"value": 79}},
        "genres": ["Drama", "Thriller"],
        "studio": "Fox 2000 Pictures",
        "status": "released",
        "runtime": 139,
    },
    {
        "tmdbId": 680,
        "title": "Pulp Fiction",
        "year": 1994,
        "overview": "A burger-loving hit man...",
        "images": [{"coverType": "poster", "remoteUrl": "https://image.tmdb.org/t/p/w500/poster2.jpg"}],
        "ratings": {"imdb": {"value": 8.9}, "rottenTomatoes": {"value": 92}},
        "genres": ["Crime", "Drama"],
        "studio": "Miramax",
        "status": "released",
        "runtime": 154,
    },
]

RADARR_MOVIE_DETAIL = {
    "tmdbId": 550,
    "title": "Fight Club",
    "year": 1999,
    "overview": "An insomniac office worker...",
    "images": [{"coverType": "poster", "remoteUrl": "https://image.tmdb.org/t/p/w500/poster1.jpg"}],
    "ratings": {"imdb": {"value": 8.8}},
    "status": "released",
    "runtime": 139,
    "id": 1,
}

RADARR_ROOT_FOLDERS = [
    {"path": "/movies", "freeSpace": 1000000000000},
    {"path": "/movies2", "freeSpace": 500000000000},
]

RADARR_QUALITY_PROFILES = [
    {"id": 1, "name": "HD-1080p", "upgradeAllowed": True},
    {"id": 2, "name": "Ultra-HD", "upgradeAllowed": False},
]

RADARR_SYSTEM_STATUS = {"version": "5.0.0", "appName": "Radarr"}

SONARR_SEARCH_RESULTS = [
    {
        "tvdbId": 81189,
        "title": "Breaking Bad",
        "year": 2008,
        "overview": "A high school chemistry teacher...",
        "images": [{"coverType": "poster", "remoteUrl": "https://artworks.thetvdb.com/poster1.jpg"}],
        "ratings": {"tmdb": {"value": 8.9, "votes": 1000}},
        "network": "AMC",
        "status": "ended",
        "runtime": 45,
        "genres": ["Drama", "Thriller"],
        "seasons": [
            {"seasonNumber": 0, "monitored": False},
            {"seasonNumber": 1, "monitored": True},
            {"seasonNumber": 2, "monitored": True},
        ],
    },
    {
        "tvdbId": 295759,
        "title": "Severance",
        "year": 2022,
        "overview": "Mark leads a team of office workers...",
        "images": [{"coverType": "poster", "remoteUrl": "https://artworks.thetvdb.com/poster2.jpg"}],
        "ratings": {"tmdb": {"value": 8.4, "votes": 500}},
        "network": "Apple TV+",
        "status": "continuing",
        "runtime": 55,
        "genres": ["Drama", "Thriller", "Sci-Fi"],
        "seasons": [
            {"seasonNumber": 1, "monitored": True},
            {"seasonNumber": 2, "monitored": True},
        ],
    },
]

SONARR_SERIES_DETAIL = {
    "tvdbId": 81189,
    "title": "Breaking Bad",
    "year": 2008,
    "overview": "A high school chemistry teacher...",
    "seasons": [
        {"seasonNumber": 0, "monitored": False},
        {"seasonNumber": 1, "monitored": True},
    ],
    "id": 1,
}

SONARR_SEASONS = [
    {"seasonNumber": 0, "monitored": False},
    {"seasonNumber": 1, "monitored": True},
    {"seasonNumber": 2, "monitored": True},
]

LIDARR_SEARCH_RESULTS = [
    {
        "foreignArtistId": "f59c5520-5f46-4d2c-b2c4-822eabf53419",
        "artistName": "Linkin Park",
        "overview": "Linkin Park is an American rock band...",
        "images": [{"coverType": "poster", "remoteUrl": "https://example.com/poster1.jpg"}],
        "ratings": {"value": 8.5},
        "genres": ["Rock", "Nu Metal"],
        "artistType": "Group",
        "status": "active",
        "statistics": {"yearStart": 1996},
    },
    {
        "foreignArtistId": "a74b1b7f-71a5-4011-9441-d0b5e4122711",
        "artistName": "Radiohead",
        "overview": "Radiohead are an English rock band...",
        "images": [{"coverType": "poster", "remoteUrl": "https://example.com/poster2.jpg"}],
        "ratings": {"value": 9.0},
        "genres": ["Rock", "Alternative"],
        "artistType": "Group",
        "status": "active",
        "statistics": {"yearStart": 1985},
    },
]

LIDARR_METADATA_PROFILES = [
    {"id": 1, "name": "Standard"},
    {"id": 2, "name": "None"},
]

TRANSMISSION_SESSION = {
    "arguments": {
        "alt-speed-enabled": False,
        "version": "4.0.0",
        "download-dir": "/downloads",
    },
    "result": "success",
}

SABNZBD_QUEUE = {
    "queue": {
        "slots": [],
        "noofslots": 0,
        "speed": "0 KB/s",
        "size": "0 MB",
        "status": "Idle",
    }
}

SABNZBD_VERSION = {"version": "4.0.0"}

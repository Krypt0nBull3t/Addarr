RADARR_SEARCH_RESULTS = [
    {
        "tmdbId": 550,
        "imdbId": "tt0137523",
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
        "imdbId": "tt0110912",
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
    "imdbId": "tt0137523",
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
        "imdbId": "tt0903747",
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
    "imdbId": "tt0903747",
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

LIDARR_ALBUM_SEARCH_RESULTS = [
    {
        "foreignAlbumId": "b1ae2a0f-5b83-4d98-93e2-4e7a9f7a7c1d",
        "title": "Hybrid Theory",
        "artist": {
            "foreignArtistId": "f59c5520-5f46-4d2c-b2c4-822eabf53419",
            "artistName": "Linkin Park",
        },
        "images": [{"coverType": "cover", "remoteUrl": "https://example.com/album1.jpg"}],
        "releaseDate": "2000-10-24T00:00:00Z",
        "overview": "Debut studio album by Linkin Park",
        "ratings": {"value": 8.5},
        "genres": ["Rock", "Nu Metal"],
        "albumType": "Album",
    },
    {
        "foreignAlbumId": "c2bf3b1e-6c94-5ea9-a4f3-5e8b0a8b8d2e",
        "title": "Meteora",
        "artist": {
            "foreignArtistId": "f59c5520-5f46-4d2c-b2c4-822eabf53419",
            "artistName": "Linkin Park",
        },
        "images": [{"coverType": "cover", "remoteUrl": "https://example.com/album2.jpg"}],
        "releaseDate": "2003-03-25T00:00:00Z",
        "overview": "Second studio album by Linkin Park",
        "ratings": {"value": 8.3},
        "genres": ["Rock", "Nu Metal"],
        "albumType": "Album",
    },
]

LIDARR_ALBUM_WITH_TRACKS = {
    "foreignAlbumId": "b1ae2a0f-5b83-4d98-93e2-4e7a9f7a7c1d",
    "title": "Hybrid Theory",
    "artist": {
        "foreignArtistId": "f59c5520-5f46-4d2c-b2c4-822eabf53419",
        "artistName": "Linkin Park",
    },
    "images": [{"coverType": "cover", "remoteUrl": "https://example.com/album1.jpg"}],
    "releaseDate": "2000-10-24T00:00:00Z",
    "media": [
        {
            "mediumNumber": 1,
            "mediumName": "",
            "mediumFormat": "CD",
            "tracks": [
                {"trackNumber": "1", "title": "Papercut", "duration": 185000},
                {"trackNumber": "2", "title": "One Step Closer", "duration": 156000},
                {"trackNumber": "3", "title": "With You", "duration": 203000},
            ],
        }
    ],
}

LIDARR_METADATA_PROFILES = [
    {"id": 1, "name": "Standard"},
    {"id": 2, "name": "None"},
]

RADARR_DISK_SPACE = [
    {
        "path": "/movies",
        "label": "Movies Drive",
        "freeSpace": 200000000000,
        "totalSpace": 1000000000000,
    },
    {
        "path": "/tv",
        "label": "TV Drive",
        "freeSpace": 50000000000,
        "totalSpace": 500000000000,
    },
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

SABNZBD_HISTORY = {
    "history": {
        "noofslots": 2,
        "slots": [
            {
                "status": "Completed",
                "nzb_name": "Ubuntu.22.04.nzb",
                "name": "Ubuntu 22.04",
                "category": "software",
                "size": "2.1 GB",
                "completed": 1700000000,
            },
            {
                "status": "Completed",
                "nzb_name": "Fedora.39.nzb",
                "name": "Fedora 39",
                "category": "software",
                "size": "1.8 GB",
                "completed": 1700001000,
            },
        ],
    }
}

# ---------------------------------------------------------------------------
# Library items (internal *arr IDs, used by delete flow)
# ---------------------------------------------------------------------------

RADARR_LIBRARY_MOVIES = [
    {"id": 1, "title": "Fight Club", "tmdbId": 550, "year": 1999},
    {"id": 2, "title": "Pulp Fiction", "tmdbId": 680, "year": 1994},
]

RADARR_LIBRARY_MOVIE_DETAIL = {
    "id": 1,
    "title": "Fight Club",
    "tmdbId": 550,
    "year": 1999,
    "overview": "An insomniac office worker...",
    "path": "/movies/Fight Club (1999)",
}

SONARR_LIBRARY_SERIES = [
    {"id": 1, "title": "Breaking Bad", "tvdbId": 81189, "year": 2008},
    {"id": 2, "title": "Severance", "tvdbId": 295759, "year": 2022},
]

SONARR_LIBRARY_SERIES_DETAIL = {
    "id": 1,
    "title": "Breaking Bad",
    "tvdbId": 81189,
    "year": 2008,
    "overview": "A high school chemistry teacher...",
    "path": "/tv/Breaking Bad",
}

LIDARR_LIBRARY_ARTISTS = [
    {"id": 1, "artistName": "Linkin Park", "foreignArtistId": "f59c5520-5f46-4d2c-b2c4-822eabf53419"},
    {"id": 2, "artistName": "Radiohead", "foreignArtistId": "a74b1b7f-71a5-4011-9441-d0b5e4122711"},
]

LIDARR_LIBRARY_ARTIST_DETAIL = {
    "id": 1,
    "artistName": "Linkin Park",
    "foreignArtistId": "f59c5520-5f46-4d2c-b2c4-822eabf53419",
    "overview": "Linkin Park is an American rock band...",
    "path": "/music/Linkin Park",
}

# ---------------------------------------------------------------------------
# Wanted/Missing items (used by /missing command)
# ---------------------------------------------------------------------------

RADARR_WANTED_MISSING = {
    "page": 1,
    "pageSize": 1000,
    "totalRecords": 2,
    "records": [
        {"id": 1, "title": "Fight Club", "year": 1999, "tmdbId": 550, "monitored": True},
        {"id": 2, "title": "Pulp Fiction", "year": 1994, "tmdbId": 680, "monitored": True},
    ],
}

RADARR_WANTED_CUTOFF = {
    "page": 1,
    "pageSize": 1000,
    "totalRecords": 1,
    "records": [
        {"id": 3, "title": "Inception", "year": 2010, "tmdbId": 27205, "monitored": True},
    ],
}

SONARR_WANTED_MISSING = {
    "page": 1,
    "pageSize": 1000,
    "totalRecords": 2,
    "records": [
        {
            "id": 101, "seriesId": 42, "seasonNumber": 1, "episodeNumber": 5,
            "title": "Pilot", "monitored": True,
            "series": {"id": 42, "title": "Breaking Bad", "year": 2008, "tvdbId": 81189},
        },
        {
            "id": 102, "seriesId": 42, "seasonNumber": 1, "episodeNumber": 6,
            "title": "Crazy Handful of Nothin'", "monitored": True,
            "series": {"id": 42, "title": "Breaking Bad", "year": 2008, "tvdbId": 81189},
        },
    ],
}

SONARR_WANTED_CUTOFF = {
    "page": 1,
    "pageSize": 1000,
    "totalRecords": 1,
    "records": [
        {
            "id": 201, "seriesId": 50, "seasonNumber": 2, "episodeNumber": 1,
            "title": "Hello, Ms. Cobel", "monitored": True,
            "series": {"id": 50, "title": "Severance", "year": 2022, "tvdbId": 295759},
        },
    ],
}


# ---------------------------------------------------------------------------
# Queue data
# ---------------------------------------------------------------------------

RADARR_QUEUE = {
    "page": 1,
    "pageSize": 1000,
    "totalRecords": 2,
    "records": [
        {
            "id": 1, "movieId": 10, "title": "Fight Club",
            "status": "downloading", "trackedDownloadStatus": "ok",
            "trackedDownloadState": "downloading",
            "protocol": "usenet", "size": 1500000000, "sizeleft": 750000000,
            "timeleft": "00:15:00", "downloadClient": "SABnzbd",
            "movie": {"id": 10, "title": "Fight Club", "year": 1999, "tmdbId": 550},
        },
        {
            "id": 2, "movieId": 11, "title": "Inception",
            "status": "completed", "trackedDownloadStatus": "ok",
            "trackedDownloadState": "importPending",
            "protocol": "torrent", "size": 2000000000, "sizeleft": 0,
            "timeleft": "00:00:00", "downloadClient": "qBittorrent",
            "movie": {"id": 11, "title": "Inception", "year": 2010, "tmdbId": 27205},
        },
    ],
}

SONARR_QUEUE = {
    "page": 1,
    "pageSize": 1000,
    "totalRecords": 2,
    "records": [
        {
            "id": 101, "seriesId": 42, "episodeId": 201, "title": "Pilot",
            "status": "downloading", "trackedDownloadStatus": "ok",
            "trackedDownloadState": "downloading",
            "protocol": "torrent", "size": 500000000, "sizeleft": 100000000,
            "timeleft": "00:05:00", "downloadClient": "qBittorrent",
            "series": {"id": 42, "title": "Breaking Bad", "year": 2008, "tvdbId": 81189},
            "episode": {"id": 201, "seasonNumber": 1, "episodeNumber": 5, "title": "Pilot"},
        },
        {
            "id": 102, "seriesId": 42, "episodeId": 202,
            "title": "Crazy Handful of Nothin'",
            "status": "downloading", "trackedDownloadStatus": "ok",
            "trackedDownloadState": "downloading",
            "protocol": "torrent", "size": 450000000, "sizeleft": 225000000,
            "timeleft": "00:10:00", "downloadClient": "qBittorrent",
            "series": {"id": 42, "title": "Breaking Bad", "year": 2008, "tvdbId": 81189},
            "episode": {
                "id": 202, "seasonNumber": 1, "episodeNumber": 6,
                "title": "Crazy Handful of Nothin'",
            },
        },
    ],
}

RADARR_HISTORY = {
    "page": 1,
    "pageSize": 20,
    "totalRecords": 3,
    "records": [
        {
            "id": 1, "movieId": 10,
            "sourceTitle": "Fight.Club.1999.1080p.BluRay",
            "quality": {"quality": {"name": "Bluray-1080p"}},
            "date": "2026-03-09T14:30:00Z",
            "eventType": "grabbed",
            "data": {"indexer": "NZBgeek"},
            "movie": {"title": "Fight Club", "year": 1999, "tmdbId": 550},
        },
        {
            "id": 2, "movieId": 10,
            "sourceTitle": "Fight.Club.1999.1080p.BluRay",
            "quality": {"quality": {"name": "Bluray-1080p"}},
            "date": "2026-03-09T15:00:00Z",
            "eventType": "downloadFolderImported",
            "data": {},
            "movie": {"title": "Fight Club", "year": 1999, "tmdbId": 550},
        },
        {
            "id": 3, "movieId": 20,
            "sourceTitle": "Pulp.Fiction.1994.720p",
            "quality": {"quality": {"name": "Bluray-720p"}},
            "date": "2026-03-08T10:00:00Z",
            "eventType": "downloadFailed",
            "data": {"indexer": "Drunken Slug"},
            "movie": {"title": "Pulp Fiction", "year": 1994, "tmdbId": 680},
        },
    ],
}

SONARR_HISTORY = {
    "page": 1,
    "pageSize": 20,
    "totalRecords": 2,
    "records": [
        {
            "id": 101, "seriesId": 42, "episodeId": 201,
            "sourceTitle": "Breaking.Bad.S01E01.720p",
            "quality": {"quality": {"name": "HDTV-720p"}},
            "date": "2026-03-09T12:00:00Z",
            "eventType": "grabbed",
            "data": {"indexer": "NZBgeek"},
            "series": {"title": "Breaking Bad", "year": 2008, "tvdbId": 81189},
            "episode": {"title": "Pilot", "seasonNumber": 1, "episodeNumber": 1},
        },
        {
            "id": 102, "seriesId": 42, "episodeId": 201,
            "sourceTitle": "Breaking.Bad.S01E01.720p",
            "quality": {"quality": {"name": "HDTV-720p"}},
            "date": "2026-03-09T12:30:00Z",
            "eventType": "downloadFolderImported",
            "data": {},
            "series": {"title": "Breaking Bad", "year": 2008, "tvdbId": 81189},
            "episode": {"title": "Pilot", "seasonNumber": 1, "episodeNumber": 1},
        },
    ],
}

LIDARR_QUEUE = {
    "page": 1,
    "pageSize": 1000,
    "totalRecords": 1,
    "records": [
        {
            "id": 301, "artistId": 5, "albumId": 20, "title": "OK Computer",
            "status": "downloading", "trackedDownloadStatus": "ok",
            "trackedDownloadState": "downloading",
            "protocol": "usenet", "size": 300000000, "sizeleft": 150000000,
            "timeleft": "00:03:00", "downloadClient": "SABnzbd",
        },
    ],
}

"""Sample Bazarr API response data for tests."""

BAZARR_SYSTEM_STATUS = {
    "data": {
        "bazarr_version": "1.4.0",
        "sonarr_version": "4.0.0",
        "radarr_version": "5.0.0",
        "operating_system": "Linux",
        "python_version": "3.11.0",
        "start_time": 1700000000,
    }
}

BAZARR_MOVIES = {
    "data": [
        {
            "title": "Inception",
            "radarrId": 1,
            "audio_language": [{"name": "English"}],
            "missing_subtitles": [
                {"name": "French", "code2": "fr", "code3": "fre"},
            ],
            "subtitles": [
                {
                    "path": "/subs/en.srt",
                    "language": "en",
                    "forced": False,
                    "hi": False,
                },
            ],
            "monitored": True,
            "profileId": 1,
        },
        {
            "title": "The Matrix",
            "radarrId": 2,
            "audio_language": [{"name": "English"}],
            "missing_subtitles": [],
            "subtitles": [
                {
                    "path": "/subs/en.srt",
                    "language": "en",
                    "forced": False,
                    "hi": False,
                },
                {
                    "path": "/subs/fr.srt",
                    "language": "fr",
                    "forced": False,
                    "hi": False,
                },
            ],
            "monitored": True,
            "profileId": 1,
        },
    ],
    "total": 2,
}

BAZARR_MOVIES_WANTED = {
    "data": [
        {
            "title": "Inception",
            "radarrId": 1,
            "missing_subtitles": [
                {"name": "French", "code2": "fr", "code3": "fre"},
            ],
            "sceneName": "Inception.2010.1080p",
            "tags": [],
        },
    ],
    "total": 1,
}

BAZARR_EPISODES_WANTED = {
    "data": [
        {
            "seriesTitle": "Breaking Bad",
            "episode_number": "S01E01",
            "episodeTitle": "Pilot",
            "missing_subtitles": [
                {"name": "Spanish", "code2": "es", "code3": "spa"},
            ],
            "sonarrSeriesId": 10,
            "sonarrEpisodeId": 100,
            "sceneName": "Breaking.Bad.S01E01",
            "tags": [],
            "seriesType": "standard",
        },
    ],
    "total": 1,
}

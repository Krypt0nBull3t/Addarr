"""
Tests for webhook event models and parser functions.

Tests cover:
- WebhookEventType and WebhookSource enums
- WebhookEvent dataclass
- parse_radarr_event() for all event types
- parse_sonarr_event() for all event types + S01E01 formatting
- parse_lidarr_event() for all event types + Lidarr-specific failures
- Missing/malformed field handling
"""

from src.models.webhook import (
    WebhookEvent,
    WebhookEventType,
    WebhookSource,
    parse_lidarr_event,
    parse_radarr_event,
    parse_sonarr_event,
)


# ---------------------------------------------------------------------------
# Radarr parser tests
# ---------------------------------------------------------------------------


class TestParseRadarrEvent:
    """Tests for parse_radarr_event()."""

    def test_grab_event(self):
        payload = {
            "eventType": "Grab",
            "movie": {"title": "Inception", "year": 2010},
            "release": {"quality": "Bluray-1080p", "size": 1234567890},
            "downloadClient": "qBittorrent",
        }
        event = parse_radarr_event(payload)
        assert event.source == WebhookSource.RADARR
        assert event.event_type == WebhookEventType.GRAB
        assert event.title == "Inception"
        assert event.is_upgrade is False
        assert event.details["quality"] == "Bluray-1080p"

    def test_download_event(self):
        payload = {
            "eventType": "Download",
            "movie": {"title": "Inception", "year": 2010},
            "movieFile": {"quality": "Bluray-1080p"},
            "isUpgrade": False,
        }
        event = parse_radarr_event(payload)
        assert event.event_type == WebhookEventType.DOWNLOAD
        assert event.is_upgrade is False
        assert event.title == "Inception"

    def test_upgrade_event(self):
        payload = {
            "eventType": "Download",
            "movie": {"title": "Inception", "year": 2010},
            "movieFile": {"quality": "Bluray-2160p"},
            "isUpgrade": True,
        }
        event = parse_radarr_event(payload)
        assert event.event_type == WebhookEventType.UPGRADE
        assert event.is_upgrade is True
        assert event.details["quality"] == "Bluray-2160p"

    def test_health_event(self):
        payload = {
            "eventType": "Health",
            "level": "warning",
            "message": "No indexers available",
            "type": "IndexerStatusCheck",
        }
        event = parse_radarr_event(payload)
        assert event.event_type == WebhookEventType.HEALTH_ISSUE
        assert event.message == "No indexers available"

    def test_health_restored_event(self):
        payload = {
            "eventType": "HealthRestored",
            "level": "ok",
            "message": "Indexers recovered",
        }
        event = parse_radarr_event(payload)
        assert event.event_type == WebhookEventType.HEALTH_RESTORED
        assert event.message == "Indexers recovered"

    def test_manual_interaction_required_event(self):
        payload = {
            "eventType": "ManualInteractionRequired",
            "movie": {"title": "Inception"},
            "downloadInfo": {"title": "Inception.2010.1080p"},
        }
        event = parse_radarr_event(payload)
        assert event.event_type == WebhookEventType.FAILURE
        assert event.title == "Inception"

    def test_test_event(self):
        payload = {
            "eventType": "Test",
            "instanceName": "Radarr",
        }
        event = parse_radarr_event(payload)
        assert event.event_type == WebhookEventType.TEST
        assert event.source == WebhookSource.RADARR

    def test_unknown_event_type(self):
        payload = {
            "eventType": "Rename",
            "movie": {"title": "Inception"},
        }
        event = parse_radarr_event(payload)
        assert event.event_type == WebhookEventType.OTHER

    def test_missing_movie_field(self):
        """Should not crash when movie field is missing."""
        payload = {
            "eventType": "Grab",
            "release": {"quality": "Bluray-1080p"},
        }
        event = parse_radarr_event(payload)
        assert event.event_type == WebhookEventType.GRAB
        assert event.title == "Unknown"

    def test_missing_quality(self):
        """Should default quality to Unknown."""
        payload = {
            "eventType": "Grab",
            "movie": {"title": "Inception"},
        }
        event = parse_radarr_event(payload)
        assert event.details.get("quality") == "Unknown"

    def test_empty_payload(self):
        """Should handle completely empty payload."""
        event = parse_radarr_event({})
        assert event.event_type == WebhookEventType.OTHER
        assert event.source == WebhookSource.RADARR


# ---------------------------------------------------------------------------
# Sonarr parser tests
# ---------------------------------------------------------------------------


class TestParseSonarrEvent:
    """Tests for parse_sonarr_event()."""

    def test_grab_event(self):
        payload = {
            "eventType": "Grab",
            "series": {"title": "Breaking Bad"},
            "episodes": [
                {"seasonNumber": 1, "episodeNumber": 1, "title": "Pilot"}
            ],
            "release": {"quality": "HDTV-720p"},
        }
        event = parse_sonarr_event(payload)
        assert event.source == WebhookSource.SONARR
        assert event.event_type == WebhookEventType.GRAB
        assert "S01E01" in event.title
        assert "Breaking Bad" in event.title

    def test_grab_multi_episode(self):
        """Multi-episode payload should format as S01E01-E03."""
        payload = {
            "eventType": "Grab",
            "series": {"title": "Breaking Bad"},
            "episodes": [
                {"seasonNumber": 1, "episodeNumber": 1, "title": "Pilot"},
                {"seasonNumber": 1, "episodeNumber": 2, "title": "Cat's in the Bag"},
                {"seasonNumber": 1, "episodeNumber": 3, "title": "...And the Bag's in the River"},
            ],
            "release": {"quality": "HDTV-720p"},
        }
        event = parse_sonarr_event(payload)
        assert "S01E01" in event.title
        assert "E03" in event.title

    def test_download_event(self):
        payload = {
            "eventType": "Download",
            "series": {"title": "Breaking Bad"},
            "episodes": [
                {"seasonNumber": 1, "episodeNumber": 1, "title": "Pilot"}
            ],
            "episodeFile": {"quality": "HDTV-720p"},
            "isUpgrade": False,
        }
        event = parse_sonarr_event(payload)
        assert event.event_type == WebhookEventType.DOWNLOAD
        assert event.is_upgrade is False

    def test_upgrade_event(self):
        payload = {
            "eventType": "Download",
            "series": {"title": "Breaking Bad"},
            "episodes": [
                {"seasonNumber": 1, "episodeNumber": 1, "title": "Pilot"}
            ],
            "episodeFile": {"quality": "Bluray-1080p"},
            "isUpgrade": True,
        }
        event = parse_sonarr_event(payload)
        assert event.event_type == WebhookEventType.UPGRADE
        assert event.is_upgrade is True

    def test_health_event(self):
        payload = {
            "eventType": "Health",
            "message": "No indexers available",
        }
        event = parse_sonarr_event(payload)
        assert event.event_type == WebhookEventType.HEALTH_ISSUE
        assert event.message == "No indexers available"

    def test_health_restored_event(self):
        payload = {
            "eventType": "HealthRestored",
            "message": "Indexers recovered",
        }
        event = parse_sonarr_event(payload)
        assert event.event_type == WebhookEventType.HEALTH_RESTORED

    def test_manual_interaction_required_event(self):
        payload = {
            "eventType": "ManualInteractionRequired",
            "series": {"title": "Breaking Bad"},
        }
        event = parse_sonarr_event(payload)
        assert event.event_type == WebhookEventType.FAILURE

    def test_test_event(self):
        payload = {"eventType": "Test"}
        event = parse_sonarr_event(payload)
        assert event.event_type == WebhookEventType.TEST
        assert event.source == WebhookSource.SONARR

    def test_unknown_event(self):
        payload = {"eventType": "SeriesDelete"}
        event = parse_sonarr_event(payload)
        assert event.event_type == WebhookEventType.OTHER

    def test_missing_series_field(self):
        payload = {
            "eventType": "Grab",
            "release": {"quality": "HDTV-720p"},
        }
        event = parse_sonarr_event(payload)
        assert event.title == "Unknown"

    def test_single_episode_no_title(self):
        """Single episode without title should format without dash suffix."""
        payload = {
            "eventType": "Grab",
            "series": {"title": "Breaking Bad"},
            "episodes": [
                {"seasonNumber": 1, "episodeNumber": 1}
            ],
            "release": {"quality": "HDTV-720p"},
        }
        event = parse_sonarr_event(payload)
        assert event.title == "Breaking Bad S01E01"

    def test_missing_episodes(self):
        """Should handle missing episodes gracefully."""
        payload = {
            "eventType": "Grab",
            "series": {"title": "Breaking Bad"},
            "release": {"quality": "HDTV-720p"},
        }
        event = parse_sonarr_event(payload)
        assert "Breaking Bad" in event.title

    def test_empty_payload(self):
        event = parse_sonarr_event({})
        assert event.event_type == WebhookEventType.OTHER
        assert event.source == WebhookSource.SONARR


# ---------------------------------------------------------------------------
# Lidarr parser tests
# ---------------------------------------------------------------------------


class TestParseLidarrEvent:
    """Tests for parse_lidarr_event()."""

    def test_grab_event(self):
        payload = {
            "eventType": "Grab",
            "artist": {"name": "Pink Floyd"},
            "albums": [{"title": "The Dark Side of the Moon"}],
            "release": {"quality": "FLAC"},
        }
        event = parse_lidarr_event(payload)
        assert event.source == WebhookSource.LIDARR
        assert event.event_type == WebhookEventType.GRAB
        assert "Pink Floyd" in event.title
        assert "The Dark Side of the Moon" in event.title
        assert event.details["quality"] == "FLAC"

    def test_download_event(self):
        payload = {
            "eventType": "Download",
            "artist": {"name": "Pink Floyd"},
            "album": {"title": "The Dark Side of the Moon"},
            "isUpgrade": False,
        }
        event = parse_lidarr_event(payload)
        assert event.event_type == WebhookEventType.DOWNLOAD
        assert event.is_upgrade is False

    def test_upgrade_event(self):
        payload = {
            "eventType": "Download",
            "artist": {"name": "Pink Floyd"},
            "album": {"title": "The Dark Side of the Moon"},
            "isUpgrade": True,
        }
        event = parse_lidarr_event(payload)
        assert event.event_type == WebhookEventType.UPGRADE
        assert event.is_upgrade is True

    def test_download_failure_event(self):
        payload = {
            "eventType": "DownloadFailure",
            "artist": {"name": "Pink Floyd"},
            "message": "Download failed: timeout",
        }
        event = parse_lidarr_event(payload)
        assert event.event_type == WebhookEventType.FAILURE
        assert event.message == "Download failed: timeout"

    def test_import_failure_event(self):
        payload = {
            "eventType": "ImportFailure",
            "artist": {"name": "Pink Floyd"},
            "message": "Import failed: file locked",
        }
        event = parse_lidarr_event(payload)
        assert event.event_type == WebhookEventType.FAILURE

    def test_health_event(self):
        payload = {
            "eventType": "Health",
            "message": "No indexers available",
        }
        event = parse_lidarr_event(payload)
        assert event.event_type == WebhookEventType.HEALTH_ISSUE

    def test_health_restored_event(self):
        payload = {
            "eventType": "HealthRestored",
            "message": "Indexers recovered",
        }
        event = parse_lidarr_event(payload)
        assert event.event_type == WebhookEventType.HEALTH_RESTORED

    def test_test_event(self):
        payload = {"eventType": "Test"}
        event = parse_lidarr_event(payload)
        assert event.event_type == WebhookEventType.TEST
        assert event.source == WebhookSource.LIDARR

    def test_unknown_event(self):
        payload = {"eventType": "ArtistDelete"}
        event = parse_lidarr_event(payload)
        assert event.event_type == WebhookEventType.OTHER

    def test_missing_artist_field(self):
        payload = {
            "eventType": "Grab",
            "albums": [{"title": "Album"}],
            "release": {"quality": "FLAC"},
        }
        event = parse_lidarr_event(payload)
        assert "Unknown" in event.title

    def test_empty_payload(self):
        event = parse_lidarr_event({})
        assert event.event_type == WebhookEventType.OTHER
        assert event.source == WebhookSource.LIDARR


# ---------------------------------------------------------------------------
# WebhookEvent dataclass tests
# ---------------------------------------------------------------------------


class TestWebhookEvent:
    """Tests for the WebhookEvent dataclass."""

    def test_default_values(self):
        event = WebhookEvent(
            source=WebhookSource.RADARR,
            event_type=WebhookEventType.GRAB,
            title="Test Movie",
        )
        assert event.message == ""
        assert event.details == {}
        assert event.is_upgrade is False

    def test_custom_values(self):
        event = WebhookEvent(
            source=WebhookSource.SONARR,
            event_type=WebhookEventType.HEALTH_ISSUE,
            title="",
            message="No indexers",
            details={"level": "warning"},
            is_upgrade=False,
        )
        assert event.message == "No indexers"
        assert event.details["level"] == "warning"

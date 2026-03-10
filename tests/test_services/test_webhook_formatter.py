"""
Tests for webhook message formatter.

Tests cover:
- Each event type produces expected message format
- Sonarr episode info in title
- Missing details (graceful defaults)
"""

from unittest.mock import patch

import pytest

from src.models.webhook import WebhookEvent, WebhookEventType, WebhookSource
from src.services.webhook_formatter import format_webhook_event


class TestFormatWebhookEvent:
    """Tests for format_webhook_event()."""

    def test_grab_event(self):
        event = WebhookEvent(
            source=WebhookSource.RADARR,
            event_type=WebhookEventType.GRAB,
            title="Inception",
            details={"quality": "Bluray-1080p"},
        )
        result = format_webhook_event(event)
        assert "Inception" in result
        assert "Bluray-1080p" in result
        assert "Radarr" in result

    def test_download_event(self):
        event = WebhookEvent(
            source=WebhookSource.SONARR,
            event_type=WebhookEventType.DOWNLOAD,
            title="Breaking Bad S01E01 - Pilot",
            details={"quality": "HDTV-720p"},
        )
        result = format_webhook_event(event)
        assert "Breaking Bad S01E01 - Pilot" in result
        assert "HDTV-720p" in result
        assert "Sonarr" in result

    def test_upgrade_event(self):
        event = WebhookEvent(
            source=WebhookSource.RADARR,
            event_type=WebhookEventType.UPGRADE,
            title="Inception",
            details={"quality": "Bluray-2160p"},
            is_upgrade=True,
        )
        result = format_webhook_event(event)
        assert "Inception" in result
        assert "Bluray-2160p" in result
        assert "Upgraded" in result or "Upgrade" in result

    def test_health_issue_event(self):
        event = WebhookEvent(
            source=WebhookSource.RADARR,
            event_type=WebhookEventType.HEALTH_ISSUE,
            title="",
            message="No indexers available",
        )
        result = format_webhook_event(event)
        assert "No indexers available" in result
        assert "Radarr" in result
        assert "Health" in result

    def test_health_restored_event(self):
        event = WebhookEvent(
            source=WebhookSource.SONARR,
            event_type=WebhookEventType.HEALTH_RESTORED,
            title="",
            message="Indexers recovered",
        )
        result = format_webhook_event(event)
        assert "Indexers recovered" in result
        assert "Restored" in result

    def test_failure_event(self):
        event = WebhookEvent(
            source=WebhookSource.LIDARR,
            event_type=WebhookEventType.FAILURE,
            title="Pink Floyd - The Wall",
            message="Download failed: timeout",
        )
        result = format_webhook_event(event)
        assert "Pink Floyd - The Wall" in result
        assert "Download failed: timeout" in result
        assert "Failed" in result

    def test_test_event(self):
        event = WebhookEvent(
            source=WebhookSource.RADARR,
            event_type=WebhookEventType.TEST,
            title="",
        )
        result = format_webhook_event(event)
        assert "Test" in result
        assert "Radarr" in result

    def test_other_event(self):
        event = WebhookEvent(
            source=WebhookSource.SONARR,
            event_type=WebhookEventType.OTHER,
            title="Breaking Bad",
        )
        result = format_webhook_event(event)
        assert "Breaking Bad" in result
        assert "Sonarr" in result

    def test_missing_quality_defaults_to_unknown(self):
        event = WebhookEvent(
            source=WebhookSource.RADARR,
            event_type=WebhookEventType.GRAB,
            title="Inception",
            details={},
        )
        result = format_webhook_event(event)
        assert "Unknown" in result

    def test_missing_message_for_health(self):
        event = WebhookEvent(
            source=WebhookSource.RADARR,
            event_type=WebhookEventType.HEALTH_ISSUE,
            title="",
            message="",
        )
        result = format_webhook_event(event)
        assert "Radarr" in result

    def test_uses_translation_when_available(self):
        """When translation returns a real string, use it instead of defaults."""
        event = WebhookEvent(
            source=WebhookSource.RADARR,
            event_type=WebhookEventType.GRAB,
            title="Inception",
            details={"quality": "Bluray-1080p"},
        )
        with patch(
            "src.services.webhook_formatter.TranslationService"
        ) as mock_ts_cls:
            mock_ts = mock_ts_cls.return_value
            mock_ts.get_text.return_value = "Custom: Inception Bluray-1080p Radarr"
            result = format_webhook_event(event)
        assert result == "Custom: Inception Bluray-1080p Radarr"

    def test_lidarr_source_name(self):
        event = WebhookEvent(
            source=WebhookSource.LIDARR,
            event_type=WebhookEventType.GRAB,
            title="Pink Floyd - The Dark Side of the Moon",
            details={"quality": "FLAC"},
        )
        result = format_webhook_event(event)
        assert "Lidarr" in result
        assert "FLAC" in result

"""Tests for WebhookService singleton HTTP server."""

import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, TestClient, TestServer


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def _enabled_webhook_data():
    """Webhook config data with webhooks enabled."""
    return {
        "enable": True,
        "port": 9999,
        "host": "0.0.0.0",
        "radarr_secret": "radarr-secret-123",
        "sonarr_secret": "sonarr-secret-456",
        "lidarr_secret": None,
        "events": {
            "grab": True,
            "download": True,
            "upgrade": True,
            "health": True,
            "failure": True,
        },
    }


@pytest.fixture
def webhook_config(mock_config, _enabled_webhook_data):
    """Config with webhooks enabled, patched at import site."""
    mock_config._set("webhooks", _enabled_webhook_data)
    with patch("src.services.webhook.config", mock_config):
        yield mock_config


@pytest.fixture
def disabled_webhook_config(mock_config):
    """Config with webhooks disabled, patched at import site."""
    mock_config._set("webhooks", {
        "enable": False,
        "port": 8080,
        "host": "0.0.0.0",
    })
    with patch("src.services.webhook.config", mock_config):
        yield mock_config


@pytest.fixture
def webhook_service(webhook_config):
    """Create a WebhookService instance with webhooks enabled."""
    from src.services.webhook import WebhookService
    return WebhookService()


@pytest.fixture
def disabled_webhook_service(disabled_webhook_config):
    """Create a WebhookService instance with webhooks disabled."""
    from src.services.webhook import WebhookService
    return WebhookService()


@pytest.fixture
async def webhook_client(webhook_config):
    """Create an aiohttp test client for the webhook service's app."""
    from src.services.webhook import WebhookService
    service = WebhookService()
    app = service._create_app()
    async with TestClient(TestServer(app)) as client:
        yield client


# ---------------------------------------------------------------------------
# Singleton tests
# ---------------------------------------------------------------------------


class TestWebhookServiceSingleton:
    """Test singleton pattern."""

    def test_singleton_returns_same_instance(self, webhook_config):
        from src.services.webhook import WebhookService
        s1 = WebhookService()
        s2 = WebhookService()
        assert s1 is s2

    def test_is_enabled_when_webhooks_enabled(self, webhook_service):
        assert webhook_service.is_enabled() is True

    def test_is_not_enabled_when_webhooks_disabled(self, disabled_webhook_service):
        assert disabled_webhook_service.is_enabled() is False


# ---------------------------------------------------------------------------
# Secret validation tests
# ---------------------------------------------------------------------------


class TestSecretValidation:
    """Test _validate_secret() method."""

    def test_valid_secret(self, webhook_service):
        assert webhook_service._validate_secret("radarr", "radarr-secret-123") is True

    def test_invalid_secret(self, webhook_service):
        assert webhook_service._validate_secret("radarr", "wrong-secret") is False

    def test_no_secret_configured_passes(self, webhook_service):
        """When no secret is configured for a service, any request should pass."""
        assert webhook_service._validate_secret("lidarr", "anything") is True

    def test_no_header_sent_fails_when_secret_configured(self, webhook_service):
        """When a secret IS configured but no header sent, should fail."""
        assert webhook_service._validate_secret("radarr", None) is False

    def test_no_header_sent_passes_when_no_secret_configured(self, webhook_service):
        """When no secret configured and no header sent, should pass."""
        assert webhook_service._validate_secret("lidarr", None) is True


# ---------------------------------------------------------------------------
# Endpoint tests
# ---------------------------------------------------------------------------


class TestWebhookEndpoints:
    """Test webhook HTTP endpoints."""

    @pytest.mark.asyncio
    async def test_radarr_endpoint_valid_payload(self, webhook_client):
        """Valid Radarr payload should return 200 and trigger notification."""
        payload = {
            "eventType": "Download",
            "movie": {"title": "Inception"},
            "movieFile": {"quality": "Bluray-1080p"},
        }
        with patch("src.services.webhook.NotificationService") as mock_ns_cls:
            mock_ns = MagicMock()
            mock_ns.notify_admin = AsyncMock()
            mock_ns_cls.return_value = mock_ns

            resp = await webhook_client.post(
                "/webhooks/radarr",
                json=payload,
                headers={"X-Api-Secret": "radarr-secret-123"},
            )
            assert resp.status == 200
            mock_ns.notify_admin.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_sonarr_endpoint_valid_payload(self, webhook_client):
        """Valid Sonarr payload should return 200 and trigger notification."""
        payload = {
            "eventType": "Grab",
            "series": {"title": "Breaking Bad"},
            "episodes": [{"seasonNumber": 1, "episodeNumber": 1, "title": "Pilot"}],
            "release": {"quality": "HDTV-720p"},
        }
        with patch("src.services.webhook.NotificationService") as mock_ns_cls:
            mock_ns = MagicMock()
            mock_ns.notify_admin = AsyncMock()
            mock_ns_cls.return_value = mock_ns

            resp = await webhook_client.post(
                "/webhooks/sonarr",
                json=payload,
                headers={"X-Api-Secret": "sonarr-secret-456"},
            )
            assert resp.status == 200
            mock_ns.notify_admin.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_lidarr_endpoint_valid_payload(self, webhook_client):
        """Valid Lidarr payload (no secret configured) should return 200."""
        payload = {
            "eventType": "Grab",
            "artist": {"name": "Pink Floyd"},
            "albums": [{"title": "The Wall"}],
            "release": {"quality": "FLAC"},
        }
        with patch("src.services.webhook.NotificationService") as mock_ns_cls:
            mock_ns = MagicMock()
            mock_ns.notify_admin = AsyncMock()
            mock_ns_cls.return_value = mock_ns

            resp = await webhook_client.post(
                "/webhooks/lidarr",
                json=payload,
            )
            assert resp.status == 200
            mock_ns.notify_admin.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_invalid_secret_returns_401(self, webhook_client):
        """Invalid secret should return 401."""
        payload = {"eventType": "Test"}
        resp = await webhook_client.post(
            "/webhooks/radarr",
            json=payload,
            headers={"X-Api-Secret": "wrong-secret"},
        )
        assert resp.status == 401

    @pytest.mark.asyncio
    async def test_missing_secret_returns_401(self, webhook_client):
        """Missing secret header when secret is configured should return 401."""
        payload = {"eventType": "Test"}
        resp = await webhook_client.post(
            "/webhooks/radarr",
            json=payload,
        )
        assert resp.status == 401


# ---------------------------------------------------------------------------
# Event filtering tests
# ---------------------------------------------------------------------------


class TestEventFiltering:
    """Test that disabled event types are filtered out."""

    @pytest.fixture
    def filtered_config(self, mock_config):
        mock_config._set("webhooks", {
            "enable": True,
            "port": 9999,
            "host": "0.0.0.0",
            "radarr_secret": None,
            "sonarr_secret": None,
            "lidarr_secret": None,
            "events": {
                "grab": False,
                "download": True,
                "upgrade": True,
                "health": True,
                "failure": True,
            },
        })
        with patch("src.services.webhook.config", mock_config):
            yield mock_config

    @pytest.fixture
    def filtered_service(self, filtered_config):
        from src.services.webhook import WebhookService
        return WebhookService()

    @pytest.fixture
    async def filtered_client(self, filtered_config):
        from src.services.webhook import WebhookService
        service = WebhookService()
        app = service._create_app()
        async with TestClient(TestServer(app)) as client:
            yield client

    @pytest.mark.asyncio
    async def test_disabled_event_type_not_notified(self, filtered_client):
        """Grab events should not trigger notification when grab is disabled."""
        payload = {
            "eventType": "Grab",
            "movie": {"title": "Test Movie"},
            "release": {"quality": "HDTV"},
        }
        with patch("src.services.webhook.NotificationService") as mock_ns_cls:
            mock_ns = MagicMock()
            mock_ns.notify_admin = AsyncMock()
            mock_ns_cls.return_value = mock_ns

            resp = await filtered_client.post("/webhooks/radarr", json=payload)
            assert resp.status == 200
            mock_ns.notify_admin.assert_not_awaited()


# ---------------------------------------------------------------------------
# Malformed input tests
# ---------------------------------------------------------------------------


class TestMalformedInput:
    """Test handling of malformed/invalid payloads."""

    @pytest.mark.asyncio
    async def test_malformed_json_returns_200(self, webhook_client):
        """Malformed JSON should return 200 (don't trigger *arr retries)."""
        resp = await webhook_client.post(
            "/webhooks/radarr",
            data=b"not valid json{{{",
            headers={
                "Content-Type": "application/json",
                "X-Api-Secret": "radarr-secret-123",
            },
        )
        assert resp.status == 200

    @pytest.mark.asyncio
    async def test_empty_payload_returns_200(self, webhook_client):
        """Empty JSON should return 200."""
        resp = await webhook_client.post(
            "/webhooks/radarr",
            json={},
            headers={"X-Api-Secret": "radarr-secret-123"},
        )
        assert resp.status == 200

    @pytest.mark.asyncio
    async def test_unknown_service_returns_200(self, webhook_client):
        """Request to an unknown service path (defensive) returns 200."""
        from src.services.webhook import WebhookService
        service = WebhookService()

        mock_request = MagicMock()
        mock_request.headers = {"X-Api-Secret": "test"}
        mock_request.json = AsyncMock(return_value={"eventType": "Test"})

        with patch.object(service, "_validate_secret", return_value=True):
            resp = await service._handle_webhook(mock_request, "unknown_service")
        assert resp.status == 200

    @pytest.mark.asyncio
    async def test_parser_exception_returns_200(self, webhook_client):
        """If the parser raises, should return 200 and not crash."""
        bad_parser = MagicMock(side_effect=ValueError("bad payload"))
        with patch.dict("src.services.webhook._PARSERS", {"radarr": bad_parser}):
            resp = await webhook_client.post(
                "/webhooks/radarr",
                json={"eventType": "Test"},
                headers={"X-Api-Secret": "radarr-secret-123"},
            )
            assert resp.status == 200

    @pytest.mark.asyncio
    async def test_notification_error_returns_200(self, webhook_client):
        """If notification sending fails, should still return 200."""
        payload = {
            "eventType": "Download",
            "movie": {"title": "Test"},
            "movieFile": {"quality": "HD"},
        }
        with patch("src.services.webhook.NotificationService") as mock_ns_cls:
            mock_ns = MagicMock()
            mock_ns.notify_admin = AsyncMock(side_effect=Exception("send failed"))
            mock_ns_cls.return_value = mock_ns

            resp = await webhook_client.post(
                "/webhooks/radarr",
                json=payload,
                headers={"X-Api-Secret": "radarr-secret-123"},
            )
            assert resp.status == 200


# ---------------------------------------------------------------------------
# Start when disabled
# ---------------------------------------------------------------------------


class TestStartWhenDisabled:
    """Test start() when webhooks are disabled."""

    @pytest.mark.asyncio
    async def test_start_when_disabled_is_noop(self, disabled_webhook_service):
        """start() when disabled should do nothing."""
        await disabled_webhook_service.start()
        assert disabled_webhook_service._running is False
        assert disabled_webhook_service._runner is None


# ---------------------------------------------------------------------------
# Lifecycle tests
# ---------------------------------------------------------------------------


class TestWebhookLifecycle:
    """Test start/stop lifecycle."""

    @pytest.mark.asyncio
    async def test_start_creates_runner(self, webhook_service):
        """start() should create and set up the aiohttp runner."""
        with patch.object(webhook_service, "_create_app") as mock_app:
            mock_app.return_value = web.Application()
            with patch("aiohttp.web.AppRunner") as mock_runner_cls:
                mock_runner = AsyncMock()
                mock_runner_cls.return_value = mock_runner
                with patch("aiohttp.web.TCPSite") as mock_site_cls:
                    mock_site = AsyncMock()
                    mock_site_cls.return_value = mock_site

                    await webhook_service.start()

                    mock_runner.setup.assert_awaited_once()
                    mock_site.start.assert_awaited_once()
                    assert webhook_service._running is True

    @pytest.mark.asyncio
    async def test_stop_cleans_up(self, webhook_service):
        """stop() should clean up runner."""
        mock_runner = AsyncMock()
        webhook_service._runner = mock_runner
        webhook_service._running = True

        await webhook_service.stop()

        mock_runner.cleanup.assert_awaited_once()
        assert webhook_service._running is False

    @pytest.mark.asyncio
    async def test_stop_when_not_running_is_noop(self, webhook_service):
        """stop() when not running should do nothing."""
        webhook_service._running = False
        webhook_service._runner = None
        await webhook_service.stop()  # Should not raise

    @pytest.mark.asyncio
    async def test_port_in_use_error_handled(self, webhook_service):
        """OSError (port in use) should be caught and logged, not raised."""
        with patch.object(webhook_service, "_create_app") as mock_app:
            mock_app.return_value = web.Application()
            with patch("aiohttp.web.AppRunner") as mock_runner_cls:
                mock_runner = AsyncMock()
                mock_runner_cls.return_value = mock_runner
                with patch("aiohttp.web.TCPSite") as mock_site_cls:
                    mock_site = AsyncMock()
                    mock_site.start.side_effect = OSError("Address already in use")
                    mock_site_cls.return_value = mock_site

                    # Should not raise
                    await webhook_service.start()
                    assert webhook_service._running is False

"""
Filename: webhook.py
Author: Christian Blank (https://github.com/Cyneric)
Created Date: 2024-11-08
Description: Webhook HTTP server for receiving *arr service notifications.
"""

import hmac
from typing import Optional

from aiohttp import web

from src.config.settings import config
from src.models.webhook import (
    WebhookEventType,
    parse_radarr_event,
    parse_sonarr_event,
    parse_lidarr_event,
)
from src.services.notification import NotificationService
from src.services.webhook_formatter import format_webhook_event
from src.utils.logger import get_logger

logger = get_logger("addarr.webhook")

# Map event types to config keys for filtering
_EVENT_TYPE_CONFIG_KEY = {
    WebhookEventType.GRAB: "grab",
    WebhookEventType.DOWNLOAD: "download",
    WebhookEventType.UPGRADE: "upgrade",
    WebhookEventType.HEALTH_ISSUE: "health",
    WebhookEventType.HEALTH_RESTORED: "health",
    WebhookEventType.FAILURE: "failure",
    WebhookEventType.TEST: None,  # Always allow test events
    WebhookEventType.OTHER: None,
}

# Map URL path segments to parser functions
_PARSERS = {
    "radarr": parse_radarr_event,
    "sonarr": parse_sonarr_event,
    "lidarr": parse_lidarr_event,
}


class WebhookService:
    """HTTP server that receives webhook POSTs from *arr services."""

    _instance: Optional["WebhookService"] = None
    _enabled: bool = False
    _running: bool = False
    _runner: Optional[web.AppRunner] = None
    _port: int = 8080
    _host: str = "0.0.0.0"

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(WebhookService, cls).__new__(cls)
            cls._initialize()
        return cls._instance

    @classmethod
    def _initialize(cls):
        """Initialize service state on first instantiation."""
        cls._enabled = False
        cls._running = False
        cls._runner = None
        cls._port = 8080
        cls._host = "0.0.0.0"

        webhook_config = config.get("webhooks", {})
        if not webhook_config.get("enable", False):
            return

        cls._port = webhook_config.get("port", 8080)
        cls._host = webhook_config.get("host", "0.0.0.0")
        cls._enabled = True
        logger.info("WebhookService initialized")

    def is_enabled(self) -> bool:
        """Check if webhooks are enabled."""
        return bool(self._enabled)

    def _validate_secret(self, service: str, provided_secret: Optional[str]) -> bool:
        """Validate the webhook secret for a service.

        Returns True if:
        - No secret is configured for the service (skip validation)
        - The provided secret matches the configured secret
        """
        webhook_config = config.get("webhooks", {})
        configured_secret = webhook_config.get(f"{service}_secret")

        if not configured_secret:
            return True

        if provided_secret is None:
            return False

        return hmac.compare_digest(provided_secret, configured_secret)

    def _is_event_enabled(self, event_type: WebhookEventType) -> bool:
        """Check if the given event type is enabled in config."""
        config_key = _EVENT_TYPE_CONFIG_KEY.get(event_type)
        if config_key is None:
            return True  # Test and Other events always pass through

        webhook_config = config.get("webhooks", {})
        events = webhook_config.get("events", {})
        return events.get(config_key, True)

    def _create_app(self) -> web.Application:
        """Create the aiohttp web application with routes."""
        app = web.Application()
        app.router.add_post("/webhooks/radarr", self._handle_radarr)
        app.router.add_post("/webhooks/sonarr", self._handle_sonarr)
        app.router.add_post("/webhooks/lidarr", self._handle_lidarr)
        return app

    async def _handle_radarr(self, request: web.Request) -> web.Response:
        return await self._handle_webhook(request, "radarr")

    async def _handle_sonarr(self, request: web.Request) -> web.Response:
        return await self._handle_webhook(request, "sonarr")

    async def _handle_lidarr(self, request: web.Request) -> web.Response:
        return await self._handle_webhook(request, "lidarr")

    async def _handle_webhook(
        self, request: web.Request, service: str
    ) -> web.Response:
        """Handle an incoming webhook POST."""
        # Validate secret
        provided_secret = request.headers.get("X-Api-Secret")
        if not self._validate_secret(service, provided_secret):
            return web.Response(status=401, text="Unauthorized")

        # Parse JSON payload
        try:
            payload = await request.json()
        except Exception:
            logger.warning(f"Malformed JSON from {service} webhook")
            return web.Response(status=200, text="OK")

        if not payload:
            return web.Response(status=200, text="OK")

        # Parse event
        parser = _PARSERS.get(service)
        if not parser:
            return web.Response(status=200, text="OK")

        try:
            event = parser(payload)
        except Exception as e:
            logger.error(f"Error parsing {service} webhook: {e}")
            return web.Response(status=200, text="OK")

        # Check if event type is enabled
        if not self._is_event_enabled(event.event_type):
            logger.debug(f"Event type {event.event_type.value} is disabled, skipping")
            return web.Response(status=200, text="OK")

        # Format and send notification
        try:
            message = format_webhook_event(event)
            notification = NotificationService()
            await notification.notify_admin(message)
        except Exception as e:
            logger.error(f"Error sending webhook notification: {e}")

        return web.Response(status=200, text="OK")

    async def start(self):
        """Start the webhook HTTP server."""
        if not self._enabled:
            return

        try:
            app = self._create_app()
            self._runner = web.AppRunner(app)
            await self._runner.setup()
            site = web.TCPSite(self._runner, self._host, self._port)
            await site.start()
            self._running = True
            logger.info(
                f"Webhook server started on {self._host}:{self._port}"
            )
        except OSError as e:
            logger.error(
                f"Failed to start webhook server: {e}. "
                f"Port {self._port} may be in use. "
                f"Try changing the port in config.yaml under webhooks.port"
            )
            self._running = False
            if self._runner:
                await self._runner.cleanup()
                self._runner = None

    async def stop(self):
        """Stop the webhook HTTP server."""
        if not self._running:
            return

        self._running = False
        if self._runner:
            await self._runner.cleanup()
            self._runner = None
            logger.info("Webhook server stopped")


webhook_service = WebhookService()

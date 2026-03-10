"""
Filename: webhook_formatter.py
Author: Christian Blank (https://github.com/Cyneric)
Created Date: 2024-11-08
Description: Format webhook events into human-readable Telegram messages.
"""

from src.models.webhook import WebhookEvent, WebhookEventType
from src.services.translation import TranslationService


# Default English templates (used when translation key is missing)
_DEFAULTS = {
    WebhookEventType.GRAB: "Grabbing: {title}\nQuality: {quality}\nService: {source}",
    WebhookEventType.DOWNLOAD: "Downloaded: {title}\nQuality: {quality}\nService: {source}",
    WebhookEventType.UPGRADE: "Upgraded: {title}\nQuality: {quality}\nService: {source}",
    WebhookEventType.HEALTH_ISSUE: "Health Issue ({source}): {message}",
    WebhookEventType.HEALTH_RESTORED: "Health Restored ({source}): {message}",
    WebhookEventType.FAILURE: "Failed: {title}\nService: {source}\nReason: {message}",
    WebhookEventType.TEST: "Test notification from {source}",
    WebhookEventType.OTHER: "{source} event: {title}",
}

_TRANSLATION_KEYS = {
    WebhookEventType.GRAB: "WebhookGrab",
    WebhookEventType.DOWNLOAD: "WebhookDownload",
    WebhookEventType.UPGRADE: "WebhookUpgrade",
    WebhookEventType.HEALTH_ISSUE: "WebhookHealthIssue",
    WebhookEventType.HEALTH_RESTORED: "WebhookHealthRestored",
    WebhookEventType.FAILURE: "WebhookFailure",
    WebhookEventType.TEST: "WebhookTest",
    WebhookEventType.OTHER: "WebhookUnknown",
}


def format_webhook_event(event: WebhookEvent) -> str:
    """Format a WebhookEvent into a human-readable Telegram message."""
    source = event.source.value
    quality = event.details.get("quality", "Unknown")
    title = event.title or "Unknown"
    message = event.message or ""

    # Try translation first
    translation = TranslationService()
    key = _TRANSLATION_KEYS.get(event.event_type, "WebhookUnknown")
    translated = translation.get_text(
        key,
        title=title,
        quality=quality,
        source=source,
        message=message,
    )

    # If translation returned the key itself (no translation loaded),
    # use the default English template
    if translated == key:
        template = _DEFAULTS.get(event.event_type, "{source} event: {title}")
        return template.format(
            title=title,
            quality=quality,
            source=source,
            message=message,
        )

    return translated

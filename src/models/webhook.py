"""
Filename: webhook.py
Author: Christian Blank (https://github.com/Cyneric)
Created Date: 2024-11-08
Description: Webhook event models and parser functions for *arr services.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List


class WebhookEventType(Enum):
    """Types of webhook events from *arr services."""
    GRAB = "GRAB"
    DOWNLOAD = "DOWNLOAD"
    UPGRADE = "UPGRADE"
    HEALTH_ISSUE = "HEALTH_ISSUE"
    HEALTH_RESTORED = "HEALTH_RESTORED"
    FAILURE = "FAILURE"
    TEST = "TEST"
    OTHER = "OTHER"


class WebhookSource(Enum):
    """Source service for webhook events."""
    RADARR = "Radarr"
    SONARR = "Sonarr"
    LIDARR = "Lidarr"


@dataclass
class WebhookEvent:
    """Webhook event data model."""
    source: WebhookSource
    event_type: WebhookEventType
    title: str
    message: str = ""
    details: Dict = field(default_factory=dict)
    is_upgrade: bool = False


# ---------------------------------------------------------------------------
# Event type mapping
# ---------------------------------------------------------------------------

_COMMON_EVENT_MAP = {
    "Test": WebhookEventType.TEST,
    "Grab": WebhookEventType.GRAB,
    "Health": WebhookEventType.HEALTH_ISSUE,
    "HealthRestored": WebhookEventType.HEALTH_RESTORED,
}


def _map_event_type(event_type_str: str, is_upgrade: bool = False) -> WebhookEventType:
    """Map a raw event type string to WebhookEventType."""
    if event_type_str in _COMMON_EVENT_MAP:
        return _COMMON_EVENT_MAP[event_type_str]
    if event_type_str == "Download":
        return WebhookEventType.UPGRADE if is_upgrade else WebhookEventType.DOWNLOAD
    if event_type_str in ("ManualInteractionRequired", "DownloadFailure", "ImportFailure"):
        return WebhookEventType.FAILURE
    return WebhookEventType.OTHER


# ---------------------------------------------------------------------------
# Radarr parser
# ---------------------------------------------------------------------------


def parse_radarr_event(payload: dict) -> WebhookEvent:
    """Parse a Radarr webhook payload into a WebhookEvent."""
    event_type_str = payload.get("eventType", "")
    is_upgrade = payload.get("isUpgrade", False)
    event_type = _map_event_type(event_type_str, is_upgrade)

    movie = payload.get("movie", {})
    title = movie.get("title", "Unknown")

    message = payload.get("message", "")

    # Extract quality from release (Grab) or movieFile (Download)
    quality = "Unknown"
    release = payload.get("release", {})
    movie_file = payload.get("movieFile", {})
    if release.get("quality"):
        quality = release["quality"]
    elif movie_file.get("quality"):
        quality = movie_file["quality"]

    details: Dict = {"quality": quality}
    if release.get("size"):
        details["size"] = release["size"]
    if payload.get("downloadClient"):
        details["downloadClient"] = payload["downloadClient"]

    return WebhookEvent(
        source=WebhookSource.RADARR,
        event_type=event_type,
        title=title,
        message=message,
        details=details,
        is_upgrade=is_upgrade,
    )


# ---------------------------------------------------------------------------
# Sonarr parser
# ---------------------------------------------------------------------------


def _format_sonarr_title(series_title: str, episodes: List[dict]) -> str:
    """Format Sonarr title with S01E01 notation."""
    if not episodes:
        return series_title

    first = episodes[0]
    season = first.get("seasonNumber", 0)
    first_ep = first.get("episodeNumber", 0)

    if len(episodes) == 1:
        ep_title = first.get("title", "")
        ep_str = f"S{season:02d}E{first_ep:02d}"
        if ep_title:
            return f"{series_title} {ep_str} - {ep_title}"
        return f"{series_title} {ep_str}"

    last = episodes[-1]
    last_ep = last.get("episodeNumber", first_ep)
    return f"{series_title} S{season:02d}E{first_ep:02d}-E{last_ep:02d}"


def parse_sonarr_event(payload: dict) -> WebhookEvent:
    """Parse a Sonarr webhook payload into a WebhookEvent."""
    event_type_str = payload.get("eventType", "")
    is_upgrade = payload.get("isUpgrade", False)
    event_type = _map_event_type(event_type_str, is_upgrade)

    series = payload.get("series", {})
    series_title = series.get("title", "Unknown")
    episodes = payload.get("episodes", [])

    # Build title with episode info for media events
    if event_type in (
        WebhookEventType.GRAB, WebhookEventType.DOWNLOAD,
        WebhookEventType.UPGRADE, WebhookEventType.FAILURE,
    ):
        title = _format_sonarr_title(series_title, episodes)
    else:
        title = series_title

    message = payload.get("message", "")

    # Extract quality
    quality = "Unknown"
    release = payload.get("release", {})
    episode_file = payload.get("episodeFile", {})
    if release.get("quality"):
        quality = release["quality"]
    elif episode_file.get("quality"):
        quality = episode_file["quality"]

    details: Dict = {"quality": quality}

    return WebhookEvent(
        source=WebhookSource.SONARR,
        event_type=event_type,
        title=title,
        message=message,
        details=details,
        is_upgrade=is_upgrade,
    )


# ---------------------------------------------------------------------------
# Lidarr parser
# ---------------------------------------------------------------------------


def _format_lidarr_title(artist_name: str, payload: dict) -> str:
    """Format Lidarr title with artist and album."""
    # Grab uses "albums" (list), Download uses "album" (single)
    albums = payload.get("albums", [])
    album = payload.get("album", {})

    album_title = ""
    if albums:
        album_title = albums[0].get("title", "")
    elif album:
        album_title = album.get("title", "")

    if album_title:
        return f"{artist_name} - {album_title}"
    return artist_name


def parse_lidarr_event(payload: dict) -> WebhookEvent:
    """Parse a Lidarr webhook payload into a WebhookEvent."""
    event_type_str = payload.get("eventType", "")
    is_upgrade = payload.get("isUpgrade", False)
    event_type = _map_event_type(event_type_str, is_upgrade)

    artist = payload.get("artist", {})
    artist_name = artist.get("name", "Unknown")

    title = _format_lidarr_title(artist_name, payload)
    message = payload.get("message", "")

    # Extract quality
    quality = "Unknown"
    release = payload.get("release", {})
    if release.get("quality"):
        quality = release["quality"]

    details: Dict = {"quality": quality}

    return WebhookEvent(
        source=WebhookSource.LIDARR,
        event_type=event_type,
        title=title,
        message=message,
        details=details,
        is_upgrade=is_upgrade,
    )

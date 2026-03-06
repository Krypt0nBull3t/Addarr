"""
Filename: transmission.py
Author: Christian Blank (https://github.com/cyneric)
Created Date: 2024-11-09
Description: Transmission service for Addarr. Handles business logic for Transmission operations.
"""

from typing import Any, Dict, Optional
from ..api.transmission import TransmissionClient
from ..config.settings import config
from ..utils.helpers import format_bytes
from ..utils.logger import get_logger

logger = get_logger("addarr.services.transmission")


class TransmissionService:
    """Service class for Transmission operations"""

    _instance = None

    def __new__(cls):
        """Ensure only one instance of TransmissionService exists"""
        if cls._instance is None:
            cls._instance = super(TransmissionService, cls).__new__(cls)
            cls._initialize()
        return cls._instance

    @classmethod
    def _initialize(cls):
        """Initialize service state on first instantiation."""
        cls._client = None
        cls._config = config.get("transmission", {})

    @property
    def client(self) -> Optional[TransmissionClient]:
        """Get or create Transmission API client"""
        if not self._client and self._config.get("enable"):
            try:
                self._client = TransmissionClient()
            except Exception as e:
                logger.error(f"Failed to initialize Transmission client: {str(e)}")
                return None
        return self._client

    def is_enabled(self) -> bool:
        """Check if Transmission is enabled in config"""
        return bool(self._config.get("enable"))

    async def test_connection(self) -> bool:
        """Test connection to Transmission"""
        if not self.client:
            return False
        return await self.client.test_connection()

    async def set_alt_speed(self, enabled: bool) -> bool:
        """Enable or disable alternative speed limits

        Args:
            enabled: Whether to enable alt speed limits

        Returns:
            True if successful, False otherwise
        """
        if not self.client:
            logger.error("Transmission client not initialized")
            return False

        try:
            await self.client.set_alt_speed_enabled(enabled)
            status = "enabled" if enabled else "disabled"
            logger.info(f"Alternative speed limits {status}")
            return True
        except Exception as e:
            logger.error(f"Failed to set alt speed: {str(e)}")
            return False

    # ------------------------------------------------------------------
    # Queue management (mirrors SABnzbdService interface)
    # ------------------------------------------------------------------

    _STATUS_MAP = {
        0: "Paused",
        1: "Check Wait",
        2: "Checking",
        3: "Queued",
        4: "Downloading",
        5: "Seed Wait",
        6: "Seeding",
    }

    @staticmethod
    def _format_eta(eta_seconds: int) -> str:
        """Format ETA seconds to time string."""
        if eta_seconds < 0:
            return "Unknown"
        hours, remainder = divmod(eta_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours > 0:
            return f"{hours}h {minutes}m"
        if minutes > 0:
            return f"{minutes}m {seconds}s"
        return f"{seconds}s"

    async def get_queue_details(self) -> Dict[str, Any]:
        """Get torrent queue matching SABnzbd's return shape."""
        empty = {
            "paused": False,
            "speed": "0 B/s",
            "size_remaining": "0 MB",
            "items_count": 0,
            "items": [],
        }

        if not self.client:
            return empty

        try:
            response = await self.client.get_torrents()
            torrents = response.get("arguments", {}).get("torrents", [])

            total_download_speed = 0
            total_remaining = 0
            items = []
            all_stopped = True

            for t in torrents:
                status_code = t.get("status", 0)
                if status_code != 0:
                    all_stopped = False

                percent_done = t.get("percentDone", 0.0)
                size_when_done = t.get("sizeWhenDone", 0)
                remaining = int(size_when_done * (1 - percent_done))
                rate = t.get("rateDownload", 0)
                total_download_speed += rate
                total_remaining += remaining

                items.append({
                    "nzo_id": t.get("id", 0),
                    "title": t.get("name", ""),
                    "status": self._STATUS_MAP.get(status_code, "Unknown"),
                    "progress": int(percent_done * 100),
                    "size": format_bytes(size_when_done),
                    "timeleft": self._format_eta(t.get("eta", -1)),
                })

            return {
                "paused": all_stopped and len(torrents) > 0,
                "speed": format_bytes(total_download_speed) + "/s",
                "size_remaining": format_bytes(total_remaining),
                "items_count": len(items),
                "items": items,
            }

        except Exception as e:
            logger.error(f"Failed to get queue details: {str(e)}")
            return empty

    async def pause_item(self, torrent_id: int) -> bool:
        """Pause a single torrent."""
        if not self.client:
            return False
        try:
            await self.client.pause_torrent(torrent_id)
            return True
        except Exception as e:
            logger.error(f"Failed to pause torrent {torrent_id}: {str(e)}")
            return False

    async def resume_item(self, torrent_id: int) -> bool:
        """Resume a single torrent."""
        if not self.client:
            return False
        try:
            await self.client.resume_torrent(torrent_id)
            return True
        except Exception as e:
            logger.error(f"Failed to resume torrent {torrent_id}: {str(e)}")
            return False

    async def pause_queue(self) -> bool:
        """Stop all torrents."""
        if not self.client:
            return False
        try:
            await self.client.stop_all()
            return True
        except Exception as e:
            logger.error(f"Failed to stop all torrents: {str(e)}")
            return False

    async def resume_queue(self) -> bool:
        """Start all torrents."""
        if not self.client:
            return False
        try:
            await self.client.start_all()
            return True
        except Exception as e:
            logger.error(f"Failed to start all torrents: {str(e)}")
            return False

    async def get_status(self) -> dict:
        """Get current Transmission status

        Returns:
            Dict containing status information
        """
        if not self.client:
            return {
                "enabled": False,
                "connected": False,
                "error": "Transmission not initialized"
            }

        try:
            session = await self.client.get_session()
            return {
                "enabled": True,
                "connected": True,
                "alt_speed_enabled": session.get("arguments", {}).get("alt-speed-enabled", False),
                "version": session.get("arguments", {}).get("version", "Unknown")
            }
        except Exception as e:
            return {
                "enabled": True,
                "connected": False,
                "error": str(e)
            }


# Create global service instance
transmission_service = TransmissionService()

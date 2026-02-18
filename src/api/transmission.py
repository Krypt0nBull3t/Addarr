"""
Filename: transmission.py
Author: Christian Blank (https://github.com/cyneric)
Created Date: 2024-11-09
Description: Transmission API client for Addarr. Handles communication with Transmission torrent client.
"""

import aiohttp
from typing import Dict, Any, Optional
from ..config.settings import config
from ..utils.logger import get_logger

logger = get_logger("addarr.api.transmission")


class TransmissionClient:
    """Async API client for Transmission torrent client RPC interface."""

    def __init__(self):
        tx_config = config.get("transmission", {})
        host = tx_config.get("host", "localhost")
        port = tx_config.get("port", 9091)
        ssl = tx_config.get("ssl", False)
        username = tx_config.get("username")
        password = tx_config.get("password")

        protocol = "https" if ssl else "http"
        self.rpc_url = f"{protocol}://{host}:{port}/transmission/rpc"
        self._auth = (
            aiohttp.BasicAuth(username, password)
            if username and password
            else None
        )
        self._session_id: Optional[str] = None

    async def _make_request(
        self, method: str, arguments: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make RPC request with session ID negotiation (max 1 retry on 409)."""
        payload = {"method": method, "arguments": arguments or {}}

        for attempt in range(2):
            headers = {}
            if self._session_id:
                headers["X-Transmission-Session-Id"] = self._session_id

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.rpc_url,
                    json=payload,
                    headers=headers,
                    auth=self._auth,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    if response.status == 409:
                        self._session_id = response.headers.get(
                            "X-Transmission-Session-Id"
                        )
                        continue

                    response.raise_for_status()
                    return await response.json()

        raise aiohttp.ClientError("Session ID negotiation failed after retry")

    async def get_session(self) -> Dict[str, Any]:
        """Get current session information."""
        return await self._make_request("session-get")

    async def set_alt_speed_enabled(self, enabled: bool) -> Dict[str, Any]:
        """Enable or disable alternative speed limits."""
        return await self._make_request(
            "session-set", {"alt-speed-enabled": enabled}
        )

    async def test_connection(self) -> bool:
        """Test connection to Transmission."""
        try:
            await self.get_session()
            return True
        except Exception:
            return False

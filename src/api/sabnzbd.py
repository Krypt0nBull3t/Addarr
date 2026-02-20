"""
Filename: sabnzbd.py
Author: Christian Blank (https://github.com/Cyneric)
Created Date: 2024-11-08
Description: SABnzbd API client module.
"""

import aiohttp
from colorama import Fore

from src.config.settings import config
from src.utils.logger import get_logger

logger = get_logger("addarr.sabnzbd")


class SabnzbdClient:
    """SABnzbd API client"""

    def __init__(self):
        """Initialize SABnzbd API client"""
        sabnzbd_config = config.get("sabnzbd", {})
        server_config = sabnzbd_config.get("server", {})
        auth_config = sabnzbd_config.get("auth", {})

        # Build API URL from server config
        protocol = "https" if server_config.get("ssl", False) else "http"
        addr = server_config.get("addr")
        port = server_config.get("port")
        path = server_config.get("path", "").rstrip('/')

        if not addr or not port:
            logger.error(Fore.RED + "❌ SABnzbd server address or port not configured")
            raise ValueError("SABnzbd server address or port not configured")

        self.api_url = f"{protocol}://{addr}:{port}{path}"
        self.api_key = auth_config.get("apikey")

        if not self.api_key:
            logger.error(Fore.RED + "❌ SABnzbd API key not configured")
            raise ValueError("SABnzbd API key not configured")

        logger.info(Fore.GREEN + f"✅ SABnzbd API client initialized: {self.api_url}")

    async def check_status(self) -> bool:
        """Check if SABnzbd is available"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.api_url}/api?mode=queue&output=json&apikey={self.api_key}"
                async with session.get(url) as response:
                    return response.status == 200
        except Exception as e:
            logger.error(f"Error checking SABnzbd status: {e}")
            return False

    async def set_speed_limit(self, percentage: int) -> bool:
        """Set SABnzbd speed limit percentage"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.api_url}/api?mode=config&name=speedlimit&value={percentage}&output=json&apikey={self.api_key}"
                async with session.get(url) as response:
                    return response.status == 200
        except Exception as e:
            logger.error(f"Error setting SABnzbd speed limit: {e}")
            return False

    async def get_queue(self) -> dict:
        """Get SABnzbd queue data"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.api_url}/api?mode=queue&output=json&apikey={self.api_key}"
                async with session.get(url) as response:
                    if response.status == 200:
                        return await response.json()
                    return {}
        except Exception as e:
            logger.error(f"Error getting SABnzbd queue: {e}")
            return {}

    async def add_nzb(self, url: str, nzbname: str = None, category: str = None) -> bool:
        """Add an NZB to SABnzbd queue"""
        try:
            async with aiohttp.ClientSession() as session:
                api_url = f"{self.api_url}/api?mode=addurl&name={url}&output=json&apikey={self.api_key}"
                if nzbname:
                    api_url += f"&nzbname={nzbname}"
                if category:
                    api_url += f"&cat={category}"
                async with session.get(api_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get('status', False)
                    return False
        except Exception as e:
            logger.error(f"Error adding NZB to SABnzbd: {e}")
            return False

    async def pause_queue(self) -> bool:
        """Pause the SABnzbd download queue"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.api_url}/api?mode=pause&output=json&apikey={self.api_key}"
                async with session.get(url) as response:
                    return response.status == 200
        except Exception as e:
            logger.error(f"Error pausing SABnzbd queue: {e}")
            return False

    async def resume_queue(self) -> bool:
        """Resume the SABnzbd download queue"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.api_url}/api?mode=resume&output=json&apikey={self.api_key}"
                async with session.get(url) as response:
                    return response.status == 200
        except Exception as e:
            logger.error(f"Error resuming SABnzbd queue: {e}")
            return False

    async def get_history(self, limit: int = 10) -> dict:
        """Get SABnzbd download history"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.api_url}/api?mode=history&limit={limit}&output=json&apikey={self.api_key}"
                async with session.get(url) as response:
                    if response.status == 200:
                        return await response.json()
                    return {}
        except Exception as e:
            logger.error(f"Error getting SABnzbd history: {e}")
            return {}

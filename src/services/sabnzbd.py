"""
Filename: sabnzbd.py
Author: Christian Blank (https://github.com/Cyneric)
Created Date: 2024-11-08
Description: SABnzbd service module.

This module handles interactions with the SABnzbd API.
"""

import aiohttp
from typing import Dict, Any, Optional
from src.utils.logger import get_logger
from src.config.settings import config

logger = get_logger("addarr.services.sabnzbd")


class SABnzbdService:
    """Service for handling SABnzbd operations"""

    _instance: Optional["SABnzbdService"] = None
    _enabled: bool = False
    base_url: str = ""
    api_key: str = ""

    def __new__(cls):
        """Ensure only one instance of SABnzbdService exists"""
        if cls._instance is None:
            cls._instance = super(SABnzbdService, cls).__new__(cls)
            cls._initialize()
        return cls._instance

    @classmethod
    def _initialize(cls):
        """Initialize service state on first instantiation."""
        cls._enabled = False
        cls.base_url = ""
        cls.api_key = ""

        sabnzbd_config = config.get('sabnzbd', {})
        if not sabnzbd_config.get('enable', False):
            return

        try:
            server_config = sabnzbd_config['server']
            auth_config = sabnzbd_config['auth']

            protocol = "https" if server_config.get('ssl', False) else "http"
            cls.base_url = f"{protocol}://{server_config['addr']}:{server_config['port']}{server_config['path']}"
            cls.api_key = auth_config.get('apikey')

            if not cls.api_key:
                logger.error("SABnzbd API key not configured")
                cls._enabled = False
                return

            cls._enabled = True
        except Exception as e:
            logger.error(f"Failed to initialize SABnzbd: {e}")
            cls._enabled = False

    def is_enabled(self) -> bool:
        """Check if SABnzbd is enabled and properly configured."""
        return bool(self._enabled)

    async def get_status(self) -> Dict[str, Any]:
        """Get SABnzbd queue status"""
        try:
            params = {
                'mode': 'queue',
                'output': 'json',
                'apikey': self.api_key
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/api", params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        queue = data.get('queue', {})

                        return {
                            'active': len([job for job in queue.get('slots', []) if job.get('status') == 'Downloading']),
                            'queued': queue.get('noofslots', 0),
                            'speed': queue.get('speed', '0 KB/s'),
                            'size': queue.get('size', '0 MB')
                        }
                    else:
                        logger.error(f"SABnzbd API returned status {response.status}")
                        return {
                            'active': 0,
                            'queued': 0,
                            'speed': '0 KB/s',
                            'size': '0 MB'
                        }

        except Exception as e:
            logger.error(f"Error getting SABnzbd status: {e}")
            return {
                'active': 0,
                'queued': 0,
                'speed': '0 KB/s',
                'size': '0 MB'
            }

    async def set_speed_limit(self, percentage: int) -> bool:
        """Set SABnzbd speed limit percentage"""
        try:
            params = {
                'mode': 'config',
                'name': 'speedlimit',
                'value': str(percentage),
                'output': 'json',
                'apikey': self.api_key
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/api", params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get('status', False)
                    else:
                        logger.error(f"SABnzbd API returned status {response.status}")
                        return False

        except Exception as e:
            logger.error(f"Error setting SABnzbd speed limit: {e}")
            return False

    async def add_nzb(self, url: str, name: Optional[str] = None, category: Optional[str] = None) -> bool:
        """Add an NZB to SABnzbd queue"""
        try:
            params = {
                'mode': 'addurl',
                'name': url,
                'output': 'json',
                'apikey': self.api_key
            }

            if name:
                params['nzbname'] = name
            if category:
                params['cat'] = category

            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/api", params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get('status', False)
                    else:
                        logger.error(f"SABnzbd API returned status {response.status}")
                        return False

        except Exception as e:
            logger.error(f"Error adding NZB to SABnzbd: {e}")
            return False

    async def pause_queue(self) -> bool:
        """Pause the SABnzbd download queue"""
        try:
            params = {
                'mode': 'pause',
                'output': 'json',
                'apikey': self.api_key
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/api", params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get('status', False)
                    else:
                        logger.error(f"SABnzbd API returned status {response.status}")
                        return False

        except Exception as e:
            logger.error(f"Error pausing SABnzbd queue: {e}")
            return False

    async def resume_queue(self) -> bool:
        """Resume the SABnzbd download queue"""
        try:
            params = {
                'mode': 'resume',
                'output': 'json',
                'apikey': self.api_key
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/api", params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get('status', False)
                    else:
                        logger.error(f"SABnzbd API returned status {response.status}")
                        return False

        except Exception as e:
            logger.error(f"Error resuming SABnzbd queue: {e}")
            return False

    async def pause_item(self, nzo_id: str) -> bool:
        """Pause an individual queue item"""
        try:
            params = {
                'mode': 'queue',
                'name': 'pause',
                'value': nzo_id,
                'output': 'json',
                'apikey': self.api_key
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/api", params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get('status', False)
                    else:
                        logger.error(f"SABnzbd API returned status {response.status}")
                        return False

        except Exception as e:
            logger.error(f"Error pausing SABnzbd item {nzo_id}: {e}")
            return False

    async def resume_item(self, nzo_id: str) -> bool:
        """Resume an individual queue item"""
        try:
            params = {
                'mode': 'queue',
                'name': 'resume',
                'value': nzo_id,
                'output': 'json',
                'apikey': self.api_key
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/api", params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get('status', False)
                    else:
                        logger.error(f"SABnzbd API returned status {response.status}")
                        return False

        except Exception as e:
            logger.error(f"Error resuming SABnzbd item {nzo_id}: {e}")
            return False

    async def get_queue_details(self) -> Dict[str, Any]:
        """Get detailed SABnzbd queue data for dashboard display"""
        empty = {
            'paused': False,
            'speed': '0 KB/s',
            'size_remaining': '0 MB',
            'items_count': 0,
            'items': []
        }
        try:
            params = {
                'mode': 'queue',
                'output': 'json',
                'apikey': self.api_key
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/api", params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        queue = data.get('queue', {})

                        items = []
                        for slot in queue.get('slots', []):
                            percentage = slot.get('percentage', '0')
                            try:
                                progress = int(percentage)
                            except (ValueError, TypeError):
                                progress = 0

                            items.append({
                                'nzo_id': slot.get('nzo_id', ''),
                                'title': slot.get('filename', ''),
                                'status': slot.get('status', ''),
                                'progress': progress,
                                'size': slot.get('size', ''),
                                'timeleft': slot.get('timeleft', ''),
                            })

                        return {
                            'paused': bool(queue.get('paused', False)),
                            'speed': queue.get('speed', '0 KB/s'),
                            'size_remaining': queue.get('size', '0 MB'),
                            'items_count': int(queue.get('noofslots', 0)),
                            'items': items,
                        }
                    else:
                        logger.error(f"SABnzbd API returned status {response.status}")
                        return empty

        except Exception as e:
            logger.error(f"Error getting SABnzbd queue details: {e}")
            return empty

    async def get_history(self, limit: int = 10) -> Dict[str, Any]:
        """Get SABnzbd download history"""
        try:
            params = {
                'mode': 'history',
                'limit': str(limit),
                'output': 'json',
                'apikey': self.api_key
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/api", params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        history = data.get('history', {})
                        return {
                            'total': history.get('noofslots', 0),
                            'items': history.get('slots', [])
                        }
                    else:
                        logger.error(f"SABnzbd API returned status {response.status}")
                        return {'total': 0, 'items': []}

        except Exception as e:
            logger.error(f"Error getting SABnzbd history: {e}")
            return {'total': 0, 'items': []}

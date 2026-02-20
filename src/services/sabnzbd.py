"""
Filename: sabnzbd.py
Author: Christian Blank (https://github.com/Cyneric)
Created Date: 2024-11-08
Description: SABnzbd service module.

This module handles interactions with the SABnzbd API.
"""

import aiohttp
from typing import Dict, Any
from src.utils.logger import get_logger
from src.config.settings import config

logger = get_logger("addarr.services.sabnzbd")


class SABnzbdService:
    """Service for handling SABnzbd operations"""

    def __init__(self):
        self.config = config
        if not self.config.get('sabnzbd', {}).get('enable', False):
            raise ValueError("SABnzbd is not enabled")

        server_config = self.config['sabnzbd']['server']
        auth_config = self.config['sabnzbd']['auth']

        protocol = "https" if server_config.get('ssl', False) else "http"
        self.base_url = f"{protocol}://{server_config['addr']}:{server_config['port']}{server_config['path']}"
        self.api_key = auth_config.get('apikey')

        if not self.api_key:
            raise ValueError("SABnzbd API key not configured")

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

    async def add_nzb(self, url: str, name: str = None, category: str = None) -> bool:
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

"""
Filename: lidarr.py
Author: Christian Blank (https://github.com/Cyneric)
Created Date: 2024-11-08
Description: Lidarr API client module.
"""

import json
import aiohttp
from typing import Optional, List, Dict
from colorama import Fore

from src.api.base import BaseApiClient, filter_root_folders
from src.config.settings import config
from src.utils.logger import get_logger

logger = get_logger("addarr.lidarr")


class LidarrClient(BaseApiClient):
    """Lidarr API client"""

    API_VERSION = "v1"

    def __init__(self):
        """Initialize Lidarr API client"""
        lidarr_config = config.get("lidarr", {})
        server_config = lidarr_config.get("server", {})
        auth_config = lidarr_config.get("auth", {})

        addr = server_config.get("addr")
        port = server_config.get("port")

        if not addr or not port:
            logger.error(Fore.RED + "❌ Lidarr server address or port not configured")
            raise ValueError("Lidarr server address or port not configured")

        if not auth_config.get("apikey"):
            logger.error(Fore.RED + "❌ Lidarr API key not configured")
            raise ValueError("Lidarr API key not configured")

        super().__init__("lidarr")
        logger.info(Fore.GREEN + f"✅ Lidarr API client initialized: {self.base_url}")

    async def search(self, term: str) -> List[Dict]:
        """Search for artists"""
        try:
            logger.info(Fore.BLUE + f"🔍 Searching Lidarr for: {term}")
            results = await self._request(f"artist/lookup?term={term}")

            if not results:
                logger.warning(Fore.YELLOW + f"⚠️ No results found for: {term}")
                return []

            logger.info(Fore.GREEN + f"✅ Found {len(results)} results for: {term}")
            return results

        except Exception as e:
            logger.error(Fore.RED + f"❌ Search failed: {str(e)}")
            return []

    async def get_artist(self, artist_id: str) -> Optional[Dict]:
        """Get artist by ID"""
        try:
            logger.info(f"🔍 Looking up artist ID: {artist_id}")

            # First try direct lookup with musicbrainz ID
            results = await self._request(f"artist/lookup?term=lidarr:{artist_id}")
            if results and isinstance(results, list) and results[0]:
                logger.info(f"✅ Found artist: {results[0].get('artistName')}")
                return results[0]

            # If that fails, try regular search
            results = await self._request(f"artist/lookup?term={artist_id}")
            if results and isinstance(results, list):
                # Try to find exact match by ID
                for result in results:
                    if result.get("foreignArtistId") == artist_id:
                        logger.info(f"✅ Found artist: {result.get('artistName')}")
                        return result

                # If no exact match but we have results, use first one
                if results[0]:
                    logger.info(f"✅ Found artist: {results[0].get('artistName')}")
                    return results[0]

            logger.warning(f"⚠️ No artist found with ID: {artist_id}")
            return None

        except Exception as e:
            logger.error(f"❌ Failed to get artist: {str(e)}")
            return None

    async def add_artist(self, artist_id: str, root_folder: str = None, quality_profile_id: int = None) -> tuple[bool, str]:
        """Add an artist to Lidarr"""
        try:
            # Get artist details from search results
            lookup_response = await self._request(f"artist/lookup?term=lidarr:{artist_id}")
            if not lookup_response or not isinstance(lookup_response, list):
                # Try regular search if lidarr: prefix fails
                lookup_response = await self._request(f"artist/lookup?term={artist_id}")
                if not lookup_response or not isinstance(lookup_response, list):
                    logger.error(f"❌ No artist found with ID: {artist_id}")
                    return False, "Artist not found"

            # Find the correct artist in results
            artist = None
            for result in lookup_response:
                if result.get("foreignArtistId") == artist_id:
                    artist = result
                    break

            # If no exact match, use first result
            if not artist and lookup_response:
                artist = lookup_response[0]

            if not artist:
                logger.error(f"❌ No artist found with ID: {artist_id}")
                return False, "Artist not found"

            # Read feature options from config
            lidarr_features = config.get("lidarr", {}).get("features", {})
            monitor_option = lidarr_features.get("monitorOption", "all")
            album_folder = lidarr_features.get("albumFolder", False)

            data = {
                "foreignArtistId": artist["foreignArtistId"],
                "artistName": artist["artistName"],
                "qualityProfileId": quality_profile_id or 1,  # Default profile if not specified
                "metadataProfileId": config.get("lidarr", {}).get("metadataProfileId", 1),
                "rootFolderPath": root_folder or "/music",  # Default path if not specified
                "albumFolder": album_folder,
                "monitored": True,
                "addOptions": {
                    "monitor": monitor_option,
                    "searchForMissingAlbums": True
                }
            }

            try:
                session = await self._get_session()
                url = f"{self.base_url}/api/{self.API_VERSION}/artist"
                async with session.post(url, headers=self._get_headers(), json=data) as response:
                    response_text = await response.text()

                    # Check if response can be parsed as JSON
                    try:
                        response_data = json.loads(response_text)

                        # If we get an artist object back, it was successful
                        if isinstance(response_data, dict) and response_data.get("id"):
                            logger.info(f"✅ Successfully added artist: {artist['artistName']}")
                            return True, f"Successfully added {artist['artistName']}"

                        # If we get an error array back
                        if isinstance(response_data, list) and response_data:
                            error_msg = response_data[0].get("errorMessage")
                            if error_msg:
                                if "already exists" in error_msg.lower():
                                    logger.info(f"ℹ️ Artist already exists: {artist['artistName']}")
                                    return False, f"{artist['artistName']} is already in your library"
                                logger.warning(f"⚠️ API Error: {error_msg}")
                                return False, error_msg

                    except json.JSONDecodeError:
                        pass

                    # If we can't parse the response or don't recognize the format
                    if response.status == 201 or response.status == 200:
                        logger.info(f"✅ Successfully added artist: {artist['artistName']}")
                        return True, f"Successfully added {artist['artistName']}"
                    else:
                        logger.error(f"❌ Failed to add artist: {response_text}")
                        return False, f"Failed to add {artist['artistName']}"

            except aiohttp.ClientError as e:
                logger.error(f"❌ Connection error: {str(e)}")
                return False, f"Connection error: {str(e)}"
            except Exception as e:
                logger.error(f"❌ Error adding artist: {str(e)}")
                return False, str(e)

        except Exception as e:
            logger.error(f"❌ Error in add_artist: {str(e)}")
            return False, str(e)

    async def get_root_folders(self) -> List[str]:
        """Get available root folders"""
        try:
            results = await self._request("rootFolder")
            if results:
                paths = [folder["path"] for folder in results]
                return filter_root_folders(paths, config.get("lidarr", {}))
            return []
        except Exception as e:
            logger.error(f"Failed to get root folders: {str(e)}")
            return []

    async def get_quality_profiles(self) -> List[Dict]:
        """Get available quality profiles"""
        try:
            logger.info("🔍 Getting quality profiles from Lidarr")
            results = await self._request("qualityprofile")

            if not results:
                logger.warning("⚠️ No quality profiles found")
                return []

            profiles = [
                {
                    "id": profile["id"],
                    "name": profile["name"],
                    "description": profile.get("upgradeAllowed", False) and "Upgrades allowed" or "No upgrades"
                }
                for profile in results
            ]

            logger.info(f"✅ Found {len(profiles)} quality profiles")
            return profiles

        except Exception as e:
            logger.error(f"❌ Failed to get quality profiles: {str(e)}")
            return []

    async def get_metadata_profiles(self) -> List[Dict]:
        """Get available metadata profiles"""
        try:
            results = await self._request("metadataprofile")
            if results:
                return [{"id": profile["id"], "name": profile["name"]} for profile in results]
            return []
        except Exception as e:
            logger.error(f"Failed to get metadata profiles: {str(e)}")
            return []

    async def get_artists(self) -> List[Dict]:
        """Get all artists in the library"""
        try:
            logger.info(Fore.BLUE + "🔍 Getting all artists from Lidarr")
            results = await self._request("artist")

            if not results:
                logger.warning(Fore.YELLOW + "⚠️ No artists found in library")
                return []

            logger.info(Fore.GREEN + f"✅ Found {len(results)} artists in library")
            return results

        except Exception as e:
            logger.error(Fore.RED + f"❌ Failed to get artists: {str(e)}")
            return []

    async def get_artist_by_id(self, artist_id: int) -> Optional[Dict]:
        """Get artist details by internal Lidarr ID"""
        try:
            logger.info(f"🔍 Looking up artist with ID: {artist_id}")
            result = await self._request(f"artist/{artist_id}")

            if result:
                logger.info(f"✅ Found artist: {result.get('artistName')}")
                return result

            logger.warning(f"⚠️ No artist found with ID: {artist_id}")
            return None

        except Exception as e:
            logger.error(f"❌ Failed to get artist by ID: {str(e)}")
            return None

    async def delete_artist(self, artist_id: int) -> bool:
        """Delete an artist from Lidarr by internal ID"""
        try:
            logger.info(f"🗑️ Deleting artist with ID: {artist_id}")
            url = f"{self.base_url}/api/{self.API_VERSION}/artist/{artist_id}"

            session = await self._get_session()
            async with session.delete(url, headers=self._get_headers()) as response:
                if response.status == 200:
                    logger.info(f"✅ Successfully deleted artist {artist_id}")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(
                        f"❌ Failed to delete artist ({response.status}): {error_text}"
                    )
                    return False

        except aiohttp.ClientError as e:
            logger.error(f"❌ Connection error deleting artist: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"❌ Error deleting artist: {str(e)}")
            return False

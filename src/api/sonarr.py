"""
Filename: sonarr.py
Author: Christian Blank (https://github.com/Cyneric)
Created Date: 2024-11-08
Description: Sonarr API client module.
"""

import json
import aiohttp
from typing import Optional, List, Dict
from colorama import Fore

from src.api.base import BaseApiClient, filter_root_folders
from src.config.settings import config
from src.utils.logger import get_logger

logger = get_logger("addarr.sonarr")


class SonarrClient(BaseApiClient):
    """Sonarr API client"""

    def __init__(self):
        """Initialize Sonarr API client"""
        sonarr_config = config.get("sonarr", {})
        server_config = sonarr_config.get("server", {})
        auth_config = sonarr_config.get("auth", {})

        addr = server_config.get("addr")
        port = server_config.get("port")

        if not addr or not port:
            logger.error(Fore.RED + "❌ Sonarr server address or port not configured")
            raise ValueError("Sonarr server address or port not configured")

        if not auth_config.get("apikey"):
            logger.error(Fore.RED + "❌ Sonarr API key not configured")
            raise ValueError("Sonarr API key not configured")

        super().__init__("sonarr")
        logger.info(Fore.GREEN + f"✅ Sonarr API client initialized: {self.base_url}")

    async def search(self, term: str) -> List[Dict]:
        """Search for TV series"""
        try:
            logger.info(Fore.BLUE + f"🔍 Searching Sonarr for: {term}")
            results = await self._request(f"series/lookup?term={term}")

            if not results:
                logger.warning(Fore.YELLOW + f"⚠️ No results found for: {term}")
                return []

            logger.info(Fore.GREEN + f"✅ Found {len(results)} results for: {term}")
            return results

        except Exception as e:
            logger.error(Fore.RED + f"❌ Search failed: {str(e)}")
            return []

    async def get_root_folders(self) -> List[str]:
        """Get available root folders"""
        try:
            results = await self._request("rootFolder")
            if results:
                paths = [folder["path"] for folder in results]
                return filter_root_folders(paths, config.get("sonarr", {}))
            return []
        except Exception as e:
            logger.error(f"Failed to get root folders: {str(e)}")
            return []

    async def get_quality_profiles(self) -> List[Dict]:
        """Get available quality profiles"""
        try:
            results = await self._request("qualityProfile")
            if results:
                return [{"id": profile["id"], "name": profile["name"]} for profile in results]
            return []
        except Exception as e:
            logger.error(f"Failed to get quality profiles: {str(e)}")
            return []

    async def get_seasons(self, tvdb_id: str) -> List[Dict]:
        """Get available seasons for a series"""
        try:
            logger.info(f"🔍 Getting seasons for series with TVDB ID: {tvdb_id}")
            results = await self._request(f"series/lookup?term=tvdb:{tvdb_id}")

            if results and isinstance(results, list) and results[0]:
                series = results[0]
                seasons = series.get("seasons", [])
                logger.info(f"✅ Found {len(seasons)} seasons")
                return seasons

            logger.warning(f"⚠️ No seasons found for TVDB ID: {tvdb_id}")
            return []

        except Exception as e:
            logger.error(f"❌ Failed to get seasons: {str(e)}")
            return []

    async def add_series(self, tvdb_id: int, root_folder: str, quality_profile_id: int, seasons: List[Dict] = None) -> tuple[bool, str]:
        """Add a TV series to Sonarr with optional season selection"""
        try:
            # Get series details from search results
            lookup_response = await self._request(f"series/lookup?term=tvdb:{tvdb_id}")
            if not lookup_response or not isinstance(lookup_response, list) or not lookup_response[0]:
                logger.error(f"❌ No series found with TVDB ID: {tvdb_id}")
                return False, "Series not found"

            series = lookup_response[0]  # Use first result

            # Read seasonFolder from config
            season_folder = config.get("sonarr", {}).get("features", {}).get("seasonFolder", True)

            data = {
                "tvdbId": series["tvdbId"],
                "title": series["title"],
                "qualityProfileId": quality_profile_id,
                "rootFolderPath": root_folder,
                "seasonFolder": season_folder,
                "monitored": True,
                "addOptions": {
                    "searchForMissingEpisodes": True
                }
            }

            # Add season selection if provided
            if seasons is not None:
                data["seasons"] = seasons

            try:
                session = await self._get_session()
                url = f"{self.base_url}/api/{self.API_VERSION}/series"
                async with session.post(url, headers=self._get_headers(), json=data) as response:
                    response_text = await response.text()

                    # Check if response can be parsed as JSON
                    try:
                        response_data = json.loads(response_text)

                        # If we get a series object back, it was successful
                        if isinstance(response_data, dict) and response_data.get("id"):
                            logger.info(f"✅ Successfully added series: {series['title']}")
                            return True, f"Successfully added {series['title']}"

                        # If we get an error array back
                        if isinstance(response_data, list) and response_data:
                            error_msg = response_data[0].get("errorMessage")
                            if error_msg:
                                if "already" in error_msg.lower():
                                    logger.info(f"ℹ️ Series already exists: {series['title']}")
                                    return False, f"{series['title']} is already in your library"
                                logger.warning(f"⚠️ API Error: {error_msg}")
                                return False, error_msg

                    except json.JSONDecodeError:
                        pass

                    # If we can't parse the response or don't recognize the format
                    if response.status == 201 or response.status == 200:
                        logger.info(f"✅ Successfully added series: {series['title']}")
                        return True, f"Successfully added {series['title']}"
                    else:
                        logger.error(f"❌ Failed to add series: {response_text}")
                        return False, f"Failed to add {series['title']}"

            except aiohttp.ClientError as e:
                logger.error(f"❌ Connection error: {str(e)}")
                return False, f"Connection error: {str(e)}"
            except Exception as e:
                logger.error(f"❌ Error adding series: {str(e)}")
                return False, str(e)

        except Exception as e:
            logger.error(f"❌ Error in add_series: {str(e)}")
            return False, str(e)

    async def get_series(self, tvdb_id: str) -> Optional[Dict]:
        """Get series details by TVDB ID"""
        try:
            logger.info(f"🔍 Looking up series with TVDB ID: {tvdb_id}")
            results = await self._request(f"series/lookup/tvdb/{tvdb_id}")

            if results:
                logger.info(f"✅ Found series: {results.get('title')}")
                return results

            # Fallback to search with tvdb: prefix if direct lookup fails
            results = await self._request(f"series/lookup?term=tvdb:{tvdb_id}")
            if results and len(results) > 0:
                logger.info(f"✅ Found series: {results[0].get('title')}")
                return results[0]

            logger.warning(f"⚠️ No series found with TVDB ID: {tvdb_id}")
            return None

        except Exception as e:
            logger.error(f"❌ Failed to get series: {str(e)}")
            return None

    async def get_all_series(self) -> List[Dict]:
        """Get all series in the library"""
        try:
            logger.info(Fore.BLUE + "🔍 Getting all series from Sonarr")
            results = await self._request("series")

            if not results:
                logger.warning(Fore.YELLOW + "⚠️ No series found in library")
                return []

            logger.info(Fore.GREEN + f"✅ Found {len(results)} series in library")
            return results

        except Exception as e:
            logger.error(Fore.RED + f"❌ Failed to get series: {str(e)}")
            return []

    async def get_series_by_id(self, series_id: int) -> Optional[Dict]:
        """Get series details by internal Sonarr ID"""
        try:
            logger.info(f"🔍 Looking up series with ID: {series_id}")
            result = await self._request(f"series/{series_id}")

            if result:
                logger.info(f"✅ Found series: {result.get('title')}")
                return result

            logger.warning(f"⚠️ No series found with ID: {series_id}")
            return None

        except Exception as e:
            logger.error(f"❌ Failed to get series by ID: {str(e)}")
            return None

    async def delete_series(self, series_id: int) -> bool:
        """Delete a series from Sonarr by internal ID"""
        try:
            logger.info(f"🗑️ Deleting series with ID: {series_id}")
            url = f"{self.base_url}/api/{self.API_VERSION}/series/{series_id}?deleteFiles=true"

            session = await self._get_session()
            async with session.delete(url, headers=self._get_headers()) as response:
                if response.status == 200:
                    logger.info(f"✅ Successfully deleted series {series_id}")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(
                        f"❌ Failed to delete series ({response.status}): {error_text}"
                    )
                    return False

        except aiohttp.ClientError as e:
            logger.error(f"❌ Connection error deleting series: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"❌ Error deleting series: {str(e)}")
            return False

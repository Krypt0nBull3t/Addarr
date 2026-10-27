"""
Filename: sonarr.py
Author: Christian Blank (https://github.com/Cyneric)
Created Date: 2024-11-08
Description: Sonarr API client module.
"""

from typing import Optional, List, Dict
from colorama import Fore

from src.api.base import (
    APIError, BaseApiClient, filter_quality_profiles, filter_root_folders
)
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
        logger.info(Fore.BLUE + f"🔍 Searching Sonarr for: {term}")
        success, results, error = await self._make_request(
            "series/lookup", params={"term": term}
        )
        if not success:
            raise APIError(f"Sonarr search failed: {error}")

        if not results:
            logger.warning(Fore.YELLOW + f"⚠️ No results found for: {term}")
            return []

        logger.info(Fore.GREEN + f"✅ Found {len(results)} results for: {term}")
        return results

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
                profiles = [{"id": profile["id"], "name": profile["name"]} for profile in results]
                return filter_quality_profiles(profiles, config.get("sonarr", {}))
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

    async def add_series(self, tvdb_id: int, root_folder: str, quality_profile_id: int, seasons: Optional[List[Dict]] = None) -> tuple[bool, str]:
        """Add a TV series to Sonarr with optional season selection"""
        try:
            # Get series details from search results
            lookup_response = await self._request(f"series/lookup?term=tvdb:{tvdb_id}")
            if not lookup_response or not isinstance(lookup_response, list) or not lookup_response[0]:
                logger.error(f"❌ No series found with TVDB ID: {tvdb_id}")
                return False, "Series not found"

            series = lookup_response[0]  # Use first result

            features = config.get("sonarr", {}).get("features", {})
            season_folder = features.get("seasonFolder", True)

            data = {
                "tvdbId": series["tvdbId"],
                "title": series["title"],
                "qualityProfileId": quality_profile_id,
                "rootFolderPath": root_folder,
                "seasonFolder": season_folder,
                "monitored": True,
                "addOptions": {
                    "searchForMissingEpisodes": features.get("search", True)
                }
            }

            # Add season selection if provided
            if seasons is not None:
                data["seasons"] = seasons

            success, _result, error = await self._make_request(
                "series", method="POST", data=data, title=series["title"], max_retries=0
            )
            if success:
                logger.info(f"✅ Successfully added series: {series['title']}")
                return True, f"Successfully added {series['title']}"
            return False, error or f"Failed to add {series['title']}"

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

    async def get_missing(self) -> List[Dict]:
        """Get episodes that are wanted but not yet downloaded."""
        try:
            logger.info(Fore.BLUE + "📭 Getting missing episodes from Sonarr")
            result = await self._request(
                "wanted/missing?sortKey=series.title&sortDirection=ascending&pageSize=1000"
            )

            if not result or not isinstance(result, dict):
                logger.warning(Fore.YELLOW + "⚠️ No missing episodes found")
                return []

            records = result.get("records", [])
            logger.info(Fore.GREEN + f"✅ Found {len(records)} missing episodes")
            return records

        except Exception as e:
            logger.error(Fore.RED + f"❌ Failed to get missing episodes: {str(e)}")
            return []

    async def get_queue(self) -> List[Dict]:
        """Get the current download queue from Sonarr."""
        try:
            logger.info(Fore.BLUE + "📥 Getting download queue from Sonarr")
            result = await self._request(
                "queue?sortKey=series.title&sortDirection=ascending&pageSize=1000"
            )

            if not result or not isinstance(result, dict):
                logger.warning(Fore.YELLOW + "⚠️ No queue items found in Sonarr")
                return []

            records = result.get("records", [])
            logger.info(Fore.GREEN + f"✅ Found {len(records)} queue items in Sonarr")
            return records

        except Exception as e:
            logger.error(Fore.RED + f"❌ Failed to get Sonarr queue: {str(e)}")
            return []

    async def get_cutoff_unmet(self) -> List[Dict]:
        """Get episodes that are below the quality cutoff."""
        try:
            logger.info(Fore.BLUE + "⚠️ Getting cutoff unmet episodes from Sonarr")
            result = await self._request(
                "wanted/cutoff?sortKey=series.title&sortDirection=ascending&pageSize=1000"
            )

            if not result or not isinstance(result, dict):
                logger.warning(Fore.YELLOW + "⚠️ No cutoff unmet episodes found")
                return []

            records = result.get("records", [])
            logger.info(Fore.GREEN + f"✅ Found {len(records)} cutoff unmet episodes")
            return records

        except Exception as e:
            logger.error(Fore.RED + f"❌ Failed to get cutoff unmet episodes: {str(e)}")
            return []

    async def search_command(self, episode_id: int) -> bool:
        """Trigger a manual search for a specific episode."""
        try:
            logger.info(Fore.BLUE + f"🔍 Triggering search for episode ID: {episode_id}")
            success, data, error = await self._make_request(
                "command",
                method="POST",
                data={"name": "EpisodeSearch", "episodeIds": [episode_id]},
            )

            if success:
                logger.info(Fore.GREEN + f"✅ Search triggered for episode ID: {episode_id}")
                return True

            logger.error(Fore.RED + f"❌ Failed to trigger search: {error}")
            return False

        except Exception as e:
            logger.error(Fore.RED + f"❌ Failed to trigger search: {str(e)}")
            return False

    async def get_calendar(self, start: str, end: str) -> List[Dict]:
        """Get upcoming episode airings within a date range"""
        try:
            logger.info(Fore.BLUE + f"🔍 Getting Sonarr calendar: {start} to {end}")
            results = await self._request(f"calendar?start={start}&end={end}")

            if not results:
                logger.warning(Fore.YELLOW + "⚠️ No upcoming episodes found")
                return []

            logger.info(Fore.GREEN + f"✅ Found {len(results)} upcoming episodes")
            return results

        except Exception as e:
            logger.error(Fore.RED + f"❌ Failed to get calendar: {str(e)}")
            return []

    async def get_history(self, page: int = 1, page_size: int = 20,
                          event_type: Optional[str] = None) -> List[Dict]:
        """Get recent history from Sonarr."""
        try:
            logger.info(Fore.BLUE + "📜 Getting history from Sonarr")
            endpoint = (
                f"history?sortKey=date&sortDirection=descending"
                f"&page={page}&pageSize={page_size}"
            )
            if event_type:
                endpoint += f"&eventType={event_type}"

            result = await self._request(endpoint)

            if not result or not isinstance(result, dict):
                logger.warning(Fore.YELLOW + "⚠️ No history found in Sonarr")
                return []

            records = result.get("records", [])
            logger.info(Fore.GREEN + f"✅ Found {len(records)} history items in Sonarr")
            return records

        except Exception as e:
            logger.error(Fore.RED + f"❌ Failed to get Sonarr history: {str(e)}")
            return []

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
        logger.info(f"🗑️ Deleting series with ID: {series_id}")
        success, _data, _error = await self._make_request(
            f"series/{series_id}?deleteFiles=true", method="DELETE", max_retries=0
        )
        if success:
            logger.info(f"✅ Successfully deleted series {series_id}")
        return success

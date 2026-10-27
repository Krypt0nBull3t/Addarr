"""
Filename: radarr.py
Author: Christian Blank (https://github.com/Cyneric)
Created Date: 2024-11-08
Description: Radarr API client module.
"""

from typing import Optional, List, Dict
from colorama import Fore

from src.api.base import (
    APIError, BaseApiClient, filter_quality_profiles, filter_root_folders
)
from src.config.settings import config
from src.utils.logger import get_logger

logger = get_logger("addarr.radarr")


class RadarrClient(BaseApiClient):
    """Radarr API client"""

    def __init__(self):
        """Initialize Radarr API client"""
        radarr_config = config.get("radarr", {})
        server_config = radarr_config.get("server", {})
        auth_config = radarr_config.get("auth", {})

        addr = server_config.get("addr")
        port = server_config.get("port")

        if not addr or not port:
            logger.error(Fore.RED + "❌ Radarr server address or port not configured")
            raise ValueError("Radarr server address or port not configured")

        if not auth_config.get("apikey"):
            logger.error(Fore.RED + "❌ Radarr API key not configured")
            raise ValueError("Radarr API key not configured")

        super().__init__("radarr")
        logger.info(Fore.GREEN + f"✅ Radarr API client initialized: {self.base_url}")

    async def search(self, term: str) -> List[Dict]:
        """Search for movies"""
        logger.info(Fore.BLUE + f"🔍 Searching Radarr for: {term}")
        success, results, error = await self._make_request(
            "movie/lookup", params={"term": term}
        )
        if not success:
            raise APIError(f"Radarr search failed: {error}")

        if not results:
            logger.warning(Fore.YELLOW + f"⚠️ No results found for: {term}")
            return []

        logger.info(Fore.GREEN + f"✅ Found {len(results)} results for: {term}")
        return results

    async def get_movie(self, tmdb_id: str) -> Optional[Dict]:
        """Get movie details by TMDB ID"""
        try:
            logger.info(f"🔍 Looking up movie with TMDB ID: {tmdb_id}")
            results = await self._request(f"movie/lookup/tmdb/{tmdb_id}")

            if results:
                logger.info(f"✅ Found movie: {results.get('title')}")
                return results

            # Fallback to search with tmdb: prefix if direct lookup fails
            results = await self._request(f"movie/lookup?term=tmdb:{tmdb_id}")
            if results and len(results) > 0:
                logger.info(f"✅ Found movie: {results[0].get('title')}")
                return results[0]

            logger.warning(f"⚠️ No movie found with TMDB ID: {tmdb_id}")
            return None

        except Exception as e:
            logger.error(f"❌ Failed to get movie: {str(e)}")
            return None

    async def get_root_folders(self) -> List[str]:
        """Get available root folders"""
        try:
            results = await self._request("rootFolder")
            if results:
                paths = [folder["path"] for folder in results]
                return filter_root_folders(paths, config.get("radarr", {}))
            return []
        except Exception as e:
            logger.error(f"Failed to get root folders: {str(e)}")
            return []

    async def get_quality_profiles(self) -> List[Dict]:
        """Get available quality profiles from Radarr"""
        try:
            logger.info("🔍 Getting quality profiles from Radarr")
            results = await self._request("qualityProfile")

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
            profiles = filter_quality_profiles(profiles, config.get("radarr", {}))

            logger.info(f"✅ Found {len(profiles)} quality profiles")
            return profiles

        except Exception as e:
            logger.error(f"❌ Failed to get quality profiles: {str(e)}")
            return []

    async def add_movie(self, tmdb_id: int, root_folder: str, quality_profile_id: int) -> tuple[bool, str]:
        """Add a movie to Radarr"""
        try:
            # Get movie details from search results
            lookup_response = await self._request(f"movie/lookup?term=tmdb:{tmdb_id}")
            if not lookup_response or not isinstance(lookup_response, list) or not lookup_response[0]:
                logger.error(f"❌ No movie found with TMDB ID: {tmdb_id}")
                return False, "Movie not found"

            movie = lookup_response[0]  # Use first result

            features = config.get("radarr", {}).get("features", {})
            data = {
                "tmdbId": movie["tmdbId"],
                "title": movie["title"],
                "qualityProfileId": quality_profile_id,
                "rootFolderPath": root_folder,
                "monitored": True,
                "addOptions": {
                    "searchForMovie": features.get("search", True)
                }
            }
            # Only when configured, so Radarr keeps its own default otherwise
            if "minimumAvailability" in features:
                data["minimumAvailability"] = features["minimumAvailability"]

            success, _result, error = await self._make_request(
                "movie", method="POST", data=data, title=movie["title"], max_retries=0
            )
            if success:
                logger.info(f"✅ Successfully added movie: {movie['title']}")
                return True, f"Successfully added {movie['title']}"
            return False, error or f"Failed to add {movie['title']}"

        except Exception as e:
            logger.error(f"❌ Error in add_movie: {str(e)}")
            return False, str(e)

    async def get_missing(self) -> List[Dict]:
        """Get movies that are wanted but not yet downloaded."""
        try:
            logger.info(Fore.BLUE + "📭 Getting missing movies from Radarr")
            result = await self._request(
                "wanted/missing?sortKey=title&sortDirection=ascending&pageSize=1000"
            )

            if not result or not isinstance(result, dict):
                logger.warning(Fore.YELLOW + "⚠️ No missing movies found")
                return []

            records = result.get("records", [])
            logger.info(Fore.GREEN + f"✅ Found {len(records)} missing movies")
            return records

        except Exception as e:
            logger.error(Fore.RED + f"❌ Failed to get missing movies: {str(e)}")
            return []

    async def get_queue(self) -> List[Dict]:
        """Get the current download queue from Radarr."""
        try:
            logger.info(Fore.BLUE + "📥 Getting download queue from Radarr")
            result = await self._request(
                "queue?sortKey=title&sortDirection=ascending&pageSize=1000"
            )

            if not result or not isinstance(result, dict):
                logger.warning(Fore.YELLOW + "⚠️ No queue items found in Radarr")
                return []

            records = result.get("records", [])
            logger.info(Fore.GREEN + f"✅ Found {len(records)} queue items in Radarr")
            return records

        except Exception as e:
            logger.error(Fore.RED + f"❌ Failed to get Radarr queue: {str(e)}")
            return []

    async def get_cutoff_unmet(self) -> List[Dict]:
        """Get movies that are below the quality cutoff."""
        try:
            logger.info(Fore.BLUE + "⚠️ Getting cutoff unmet movies from Radarr")
            result = await self._request(
                "wanted/cutoff?sortKey=title&sortDirection=ascending&pageSize=1000"
            )

            if not result or not isinstance(result, dict):
                logger.warning(Fore.YELLOW + "⚠️ No cutoff unmet movies found")
                return []

            records = result.get("records", [])
            logger.info(Fore.GREEN + f"✅ Found {len(records)} cutoff unmet movies")
            return records

        except Exception as e:
            logger.error(Fore.RED + f"❌ Failed to get cutoff unmet movies: {str(e)}")
            return []

    async def search_command(self, movie_id: int) -> bool:
        """Trigger a manual search for a specific movie."""
        try:
            logger.info(Fore.BLUE + f"🔍 Triggering search for movie ID: {movie_id}")
            success, data, error = await self._make_request(
                "command",
                method="POST",
                data={"name": "MoviesSearch", "movieIds": [movie_id]},
            )

            if success:
                logger.info(Fore.GREEN + f"✅ Search triggered for movie ID: {movie_id}")
                return True

            logger.error(Fore.RED + f"❌ Failed to trigger search: {error}")
            return False

        except Exception as e:
            logger.error(Fore.RED + f"❌ Failed to trigger search: {str(e)}")
            return False

    async def get_calendar(self, start: str, end: str) -> List[Dict]:
        """Get upcoming movie releases within a date range"""
        try:
            logger.info(Fore.BLUE + f"🔍 Getting Radarr calendar: {start} to {end}")
            results = await self._request(f"calendar?start={start}&end={end}")

            if not results:
                logger.warning(Fore.YELLOW + "⚠️ No upcoming movies found")
                return []

            logger.info(Fore.GREEN + f"✅ Found {len(results)} upcoming movies")
            return results

        except Exception as e:
            logger.error(Fore.RED + f"❌ Failed to get calendar: {str(e)}")
            return []

    async def get_history(self, page: int = 1, page_size: int = 20,
                          event_type: Optional[str] = None) -> List[Dict]:
        """Get recent history from Radarr."""
        try:
            logger.info(Fore.BLUE + "📜 Getting history from Radarr")
            endpoint = (
                f"history?sortKey=date&sortDirection=descending"
                f"&page={page}&pageSize={page_size}"
            )
            if event_type:
                endpoint += f"&eventType={event_type}"

            result = await self._request(endpoint)

            if not result or not isinstance(result, dict):
                logger.warning(Fore.YELLOW + "⚠️ No history found in Radarr")
                return []

            records = result.get("records", [])
            logger.info(Fore.GREEN + f"✅ Found {len(records)} history items in Radarr")
            return records

        except Exception as e:
            logger.error(Fore.RED + f"❌ Failed to get Radarr history: {str(e)}")
            return []

    async def get_movies(self) -> List[Dict]:
        """Get all movies in the library"""
        try:
            logger.info(Fore.BLUE + "🔍 Getting all movies from Radarr")
            results = await self._request("movie")

            if not results:
                logger.warning(Fore.YELLOW + "⚠️ No movies found in library")
                return []

            logger.info(Fore.GREEN + f"✅ Found {len(results)} movies in library")
            return results

        except Exception as e:
            logger.error(Fore.RED + f"❌ Failed to get movies: {str(e)}")
            return []

    async def get_movie_by_id(self, movie_id: int) -> Optional[Dict]:
        """Get movie details by internal Radarr ID"""
        try:
            logger.info(f"🔍 Looking up movie with ID: {movie_id}")
            result = await self._request(f"movie/{movie_id}")

            if result:
                logger.info(f"✅ Found movie: {result.get('title')}")
                return result

            logger.warning(f"⚠️ No movie found with ID: {movie_id}")
            return None

        except Exception as e:
            logger.error(f"❌ Failed to get movie by ID: {str(e)}")
            return None

    async def delete_movie(self, movie_id: int) -> bool:
        """Delete a movie from Radarr by internal ID"""
        logger.info(f"🗑️ Deleting movie with ID: {movie_id}")
        success, _data, _error = await self._make_request(
            f"movie/{movie_id}?deleteFiles=true", method="DELETE", max_retries=0
        )
        if success:
            logger.info(f"✅ Successfully deleted movie {movie_id}")
        return success

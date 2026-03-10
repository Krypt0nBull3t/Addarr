"""
Filename: bazarr.py
Author: Christian Blank (https://github.com/Cyneric)
Created Date: 2024-11-08
Description: Bazarr API client module.
"""

from typing import List, Dict
from colorama import Fore

from src.api.base import BaseApiClient
from src.config.settings import config
from src.utils.logger import get_logger

logger = get_logger("addarr.bazarr")


class BazarrClient(BaseApiClient):
    """Bazarr API client for subtitle management."""

    # Bazarr API has no version prefix — override to empty string
    API_VERSION = ""

    def __init__(self):
        """Initialize Bazarr API client."""
        bazarr_config = config.get("bazarr", {})
        server_config = bazarr_config.get("server", {})
        auth_config = bazarr_config.get("auth", {})

        addr = server_config.get("addr")
        port = server_config.get("port")

        if not addr or not port:
            logger.error(
                Fore.RED + "❌ Bazarr server address or port not configured"
            )
            raise ValueError(
                "Bazarr server address or port not configured"
            )

        if not auth_config.get("apikey"):
            logger.error(Fore.RED + "❌ Bazarr API key not configured")
            raise ValueError("Bazarr API key not configured")

        super().__init__("bazarr")
        logger.info(
            Fore.GREEN + f"✅ Bazarr API client initialized: {self.base_url}"
        )

    async def search(self, term: str) -> List[Dict]:
        """Search movies by title in Bazarr's tracked library."""
        try:
            logger.info(Fore.BLUE + f"🔍 Searching Bazarr for: {term}")
            result = await self._request("movies")

            if not result or not isinstance(result, dict):
                logger.warning(
                    Fore.YELLOW + "⚠️ No results from Bazarr"
                )
                return []

            movies = result.get("data", [])
            term_lower = term.lower()
            matches = [
                m for m in movies
                if term_lower in m.get("title", "").lower()
            ]

            logger.info(
                Fore.GREEN
                + f"✅ Found {len(matches)} matches for: {term}"
            )
            return matches

        except Exception as e:
            logger.error(Fore.RED + f"❌ Search failed: {str(e)}")
            return []

    async def get_movies(self) -> List[Dict]:
        """Get all movies with subtitle info."""
        try:
            result = await self._request("movies")
            if result and isinstance(result, dict):
                return result.get("data", [])
            return []
        except Exception as e:
            logger.error(
                Fore.RED + f"❌ Failed to get movies: {str(e)}"
            )
            return []

    async def get_wanted_movies(self) -> List[Dict]:
        """Get movies missing subtitles."""
        try:
            logger.info(
                Fore.BLUE + "📭 Getting movies wanted subtitles"
            )
            result = await self._request("movies/wanted")
            if result and isinstance(result, dict):
                data = result.get("data", [])
                logger.info(
                    Fore.GREEN
                    + f"✅ Found {len(data)} movies wanting subtitles"
                )
                return data
            return []
        except Exception as e:
            logger.error(
                Fore.RED
                + f"❌ Failed to get wanted movies: {str(e)}"
            )
            return []

    async def get_wanted_episodes(self) -> List[Dict]:
        """Get episodes missing subtitles."""
        try:
            logger.info(
                Fore.BLUE + "📭 Getting episodes wanted subtitles"
            )
            result = await self._request("episodes/wanted")
            if result and isinstance(result, dict):
                data = result.get("data", [])
                logger.info(
                    Fore.GREEN
                    + f"✅ Found {len(data)} episodes wanting subtitles"
                )
                return data
            return []
        except Exception as e:
            logger.error(
                Fore.RED
                + f"❌ Failed to get wanted episodes: {str(e)}"
            )
            return []

    async def search_movie_subtitles(
        self,
        radarr_id: int,
        language: str,
        forced: bool = False,
        hi: bool = False,
    ) -> bool:
        """Trigger subtitle search for a specific movie."""
        try:
            logger.info(
                Fore.BLUE
                + f"🔍 Searching subtitles for movie {radarr_id}"
                + f" ({language})"
            )
            forced_str = "true" if forced else "false"
            hi_str = "true" if hi else "false"
            success, _data, error = await self._make_request(
                f"movies/subtitles?radarrid={radarr_id}"
                f"&language={language}"
                f"&forced={forced_str}&hi={hi_str}",
                method="PATCH",
            )
            if success:
                logger.info(
                    Fore.GREEN
                    + f"✅ Subtitle search triggered for movie"
                    + f" {radarr_id}"
                )
            else:
                logger.error(
                    Fore.RED
                    + f"❌ Subtitle search failed: {error}"
                )
            return success
        except Exception as e:
            logger.error(
                Fore.RED
                + f"❌ Failed to search subtitles: {str(e)}"
            )
            return False

    async def search_episode_subtitles(
        self,
        sonarr_series_id: int,
        sonarr_episode_id: int,
        language: str,
        forced: bool = False,
        hi: bool = False,
    ) -> bool:
        """Trigger subtitle search for a specific episode."""
        try:
            logger.info(
                Fore.BLUE
                + f"🔍 Searching subtitles for episode"
                + f" {sonarr_episode_id}"
            )
            forced_str = "true" if forced else "false"
            hi_str = "true" if hi else "false"
            success, _data, error = await self._make_request(
                f"episodes/subtitles?seriesid={sonarr_series_id}"
                f"&episodeid={sonarr_episode_id}"
                f"&language={language}"
                f"&forced={forced_str}&hi={hi_str}",
                method="PATCH",
            )
            if success:
                logger.info(
                    Fore.GREEN
                    + f"✅ Subtitle search triggered for episode"
                    + f" {sonarr_episode_id}"
                )
            else:
                logger.error(
                    Fore.RED
                    + f"❌ Episode subtitle search failed: {error}"
                )
            return success
        except Exception as e:
            logger.error(
                Fore.RED
                + f"❌ Failed to search episode subtitles: {str(e)}"
            )
            return False

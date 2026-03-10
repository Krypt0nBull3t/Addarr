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

    def _build_api_url(self, endpoint: str) -> str:
        """Build API URL without version prefix (Bazarr uses /api/)."""
        return f"{self.base_url}/api/{endpoint}"

    def _get_headers(self):
        """Bazarr uses X-API-KEY header format."""
        return {
            'X-API-KEY': self.config["auth"]["apikey"],
            'Content-Type': 'application/json'
        }

    async def _get_list(self, endpoint: str, label: str) -> List[Dict]:
        """Fetch a paginated list endpoint, returning data items."""
        try:
            logger.info(Fore.BLUE + f"📭 Getting {label}")
            result = await self._request(endpoint)
            if result and isinstance(result, dict):
                data = result.get("data", [])
                logger.info(
                    Fore.GREEN + f"✅ Found {len(data)} {label}"
                )
                return data
            return []
        except Exception as e:
            logger.error(
                Fore.RED + f"❌ Failed to get {label}: {str(e)}"
            )
            return []

    async def _trigger_subtitle_search(
        self, endpoint: str, label: str
    ) -> bool:
        """Trigger a subtitle search via PATCH request."""
        try:
            logger.info(
                Fore.BLUE + f"🔍 Searching subtitles for {label}"
            )
            success, _data, error = await self._make_request(
                endpoint, method="PATCH"
            )
            if success:
                logger.info(
                    Fore.GREEN
                    + f"✅ Subtitle search triggered for {label}"
                )
            else:
                logger.error(
                    Fore.RED + f"❌ Subtitle search failed: {error}"
                )
            return success
        except Exception as e:
            logger.error(
                Fore.RED
                + f"❌ Failed to search subtitles: {str(e)}"
            )
            return False

    async def search(self, term: str) -> List[Dict]:
        """Search movies by title in Bazarr's tracked library."""
        logger.info(Fore.BLUE + f"🔍 Searching Bazarr for: {term}")
        movies = await self.get_movies()
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

    async def get_movies(self) -> List[Dict]:
        """Get all movies with subtitle info."""
        return await self._get_list("movies", "movies")

    async def get_wanted_movies(self) -> List[Dict]:
        """Get movies missing subtitles."""
        return await self._get_list(
            "movies/wanted", "movies wanting subtitles"
        )

    async def get_wanted_episodes(self) -> List[Dict]:
        """Get episodes missing subtitles."""
        return await self._get_list(
            "episodes/wanted", "episodes wanting subtitles"
        )

    async def search_movie_subtitles(
        self,
        radarr_id: int,
        language: str,
        forced: bool = False,
        hi: bool = False,
    ) -> bool:
        """Trigger subtitle search for a specific movie."""
        forced_str = str(forced).lower()
        hi_str = str(hi).lower()
        endpoint = (
            f"movies/subtitles?radarrid={radarr_id}"
            f"&language={language}"
            f"&forced={forced_str}&hi={hi_str}"
        )
        return await self._trigger_subtitle_search(
            endpoint, f"movie {radarr_id}"
        )

    async def search_episode_subtitles(
        self,
        sonarr_series_id: int,
        sonarr_episode_id: int,
        language: str,
        forced: bool = False,
        hi: bool = False,
    ) -> bool:
        """Trigger subtitle search for a specific episode."""
        forced_str = str(forced).lower()
        hi_str = str(hi).lower()
        endpoint = (
            f"episodes/subtitles?seriesid={sonarr_series_id}"
            f"&episodeid={sonarr_episode_id}"
            f"&language={language}"
            f"&forced={forced_str}&hi={hi_str}"
        )
        return await self._trigger_subtitle_search(
            endpoint, f"episode {sonarr_episode_id}"
        )

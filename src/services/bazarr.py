"""
Filename: bazarr.py
Author: Christian Blank (https://github.com/Cyneric)
Created Date: 2024-11-08
Description: Bazarr service for Addarr. Handles business logic for subtitle operations.
"""

from typing import Any, Dict, List, Optional
from ..api.bazarr import BazarrClient
from ..config.settings import config
from ..utils.logger import get_logger

logger = get_logger("addarr.services.bazarr")


class BazarrService:
    """Service class for Bazarr subtitle operations."""

    _instance: Optional["BazarrService"] = None
    _client: Optional[BazarrClient] = None
    _config: Dict[str, Any] = {}

    def __new__(cls):
        """Ensure only one instance of BazarrService exists."""
        if cls._instance is None:
            cls._instance = super(BazarrService, cls).__new__(cls)
            cls._initialize()
        return cls._instance

    @classmethod
    def _initialize(cls):
        """Initialize service state on first instantiation."""
        cls._client = None
        cls._config = config.get("bazarr", {})

    @property
    def client(self) -> Optional[BazarrClient]:
        """Get or create Bazarr API client."""
        if not self._client and self._config.get("enable"):
            try:
                self._client = BazarrClient()
            except Exception as e:
                logger.error(
                    f"Failed to initialize Bazarr client: {str(e)}"
                )
                return None
        return self._client

    def is_enabled(self) -> bool:
        """Check if Bazarr is enabled in config."""
        return bool(self._config.get("enable"))

    async def search(self, term: str) -> List[Dict]:
        """Search movies by title in Bazarr."""
        if not self.client:
            return []
        return await self.client.search(term)

    async def get_movies(self) -> List[Dict]:
        """Get all movies with subtitle info."""
        if not self.client:
            return []
        return await self.client.get_movies()

    async def get_wanted_movies(self) -> List[Dict]:
        """Get movies missing subtitles."""
        if not self.client:
            return []
        return await self.client.get_wanted_movies()

    async def get_wanted_episodes(self) -> List[Dict]:
        """Get episodes missing subtitles."""
        if not self.client:
            return []
        return await self.client.get_wanted_episodes()

    async def search_movie_subtitles(
        self,
        radarr_id: int,
        language: str,
        forced: bool = False,
        hi: bool = False,
    ) -> bool:
        """Trigger subtitle search for a specific movie."""
        if not self.client:
            return False
        return await self.client.search_movie_subtitles(
            radarr_id, language, forced=forced, hi=hi
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
        if not self.client:
            return False
        return await self.client.search_episode_subtitles(
            sonarr_series_id, sonarr_episode_id, language,
            forced=forced, hi=hi
        )

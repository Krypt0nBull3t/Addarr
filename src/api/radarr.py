"""
Filename: radarr.py
Author: Christian Blank (https://github.com/Cyneric)
Created Date: 2024-11-08
Description: Radarr API client module.
"""

import json
import aiohttp
from typing import Optional, List, Dict
from colorama import Fore

from src.api.base import BaseApiClient, filter_root_folders
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
        try:
            logger.info(Fore.BLUE + f"🔍 Searching Radarr for: {term}")
            results = await self._request(f"movie/lookup?term={term}")

            if not results:
                logger.warning(Fore.YELLOW + f"⚠️ No results found for: {term}")
                return []

            logger.info(Fore.GREEN + f"✅ Found {len(results)} results for: {term}")
            return results

        except Exception as e:
            logger.error(Fore.RED + f"❌ Search failed: {str(e)}")
            return []

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

            # Verify quality profile exists
            quality_profiles = await self.get_quality_profiles()
            if not any(p["id"] == quality_profile_id for p in quality_profiles):
                logger.error(f"❌ Invalid quality profile ID: {quality_profile_id}")
                return False, "Invalid quality profile selected"

            data = {
                "tmdbId": movie["tmdbId"],
                "title": movie["title"],
                "qualityProfileId": quality_profile_id,
                "rootFolderPath": root_folder,
                "monitored": True,
                "addOptions": {
                    "searchForMovie": True
                }
            }

            try:
                session = await self._get_session()
                url = f"{self.base_url}/api/{self.API_VERSION}/movie"
                async with session.post(url, headers=self._get_headers(), json=data) as response:
                    response_text = await response.text()

                    # Check if response can be parsed as JSON
                    try:
                        response_data = json.loads(response_text)

                        # If we get a movie object back, it was successful
                        if isinstance(response_data, dict) and response_data.get("id"):
                            logger.info(f"✅ Successfully added movie: {movie['title']}")
                            return True, f"Successfully added {movie['title']}"

                        # If we get an error array back
                        if isinstance(response_data, list) and response_data:
                            error_msg = response_data[0].get("errorMessage")
                            if error_msg:
                                if "already" in error_msg.lower():
                                    logger.info(f"ℹ️ Movie already exists: {movie['title']}")
                                    return False, f"{movie['title']} is already in your library"
                                logger.warning(f"⚠️ API Error: {error_msg}")
                                return False, error_msg

                    except json.JSONDecodeError:
                        pass

                    # If we can't parse the response or don't recognize the format
                    if response.status == 201 or response.status == 200:
                        logger.info(f"✅ Successfully added movie: {movie['title']}")
                        return True, f"Successfully added {movie['title']}"
                    else:
                        logger.error(f"❌ Failed to add movie: {response_text}")
                        return False, f"Failed to add {movie['title']}"

            except aiohttp.ClientError as e:
                logger.error(f"❌ Connection error: {str(e)}")
                return False, f"Connection error: {str(e)}"
            except Exception as e:
                logger.error(f"❌ Error adding movie: {str(e)}")
                return False, str(e)

        except Exception as e:
            logger.error(f"❌ Error in add_movie: {str(e)}")
            return False, str(e)

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
        try:
            logger.info(f"🗑️ Deleting movie with ID: {movie_id}")
            url = f"{self.base_url}/api/{self.API_VERSION}/movie/{movie_id}?deleteFiles=true"

            session = await self._get_session()
            async with session.delete(url, headers=self._get_headers()) as response:
                if response.status == 200:
                    logger.info(f"✅ Successfully deleted movie {movie_id}")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(
                        f"❌ Failed to delete movie ({response.status}): {error_text}"
                    )
                    return False

        except aiohttp.ClientError as e:
            logger.error(f"❌ Connection error deleting movie: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"❌ Error deleting movie: {str(e)}")
            return False

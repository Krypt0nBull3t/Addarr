"""
Filename: lidarr.py
Author: Christian Blank (https://github.com/Cyneric)
Created Date: 2024-11-08
Description: Lidarr API client module.
"""

from typing import Any, Optional, List, Dict
from colorama import Fore

from src.api.base import (
    APIError, BaseApiClient, filter_quality_profiles, filter_root_folders
)
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
        logger.info(Fore.BLUE + f"🔍 Searching Lidarr for: {term}")
        success, results, error = await self._make_request(
            "artist/lookup", params={"term": term}
        )
        if not success:
            raise APIError(f"Lidarr search failed: {error}")

        if not results:
            logger.warning(Fore.YELLOW + f"⚠️ No results found for: {term}")
            return []

        logger.info(Fore.GREEN + f"✅ Found {len(results)} results for: {term}")
        return results

    async def search_albums(self, term: str) -> List[Dict]:
        """Search for albums"""
        logger.info(Fore.BLUE + f"🔍 Searching Lidarr albums for: {term}")
        success, results, error = await self._make_request(
            "album/lookup", params={"term": term}
        )
        if not success:
            raise APIError(f"Lidarr album search failed: {error}")

        if not results:
            logger.warning(Fore.YELLOW + f"⚠️ No album results found for: {term}")
            return []

        logger.info(Fore.GREEN + f"✅ Found {len(results)} album results for: {term}")
        return results

    async def get_album_tracks(self, foreign_album_id: str) -> List[Dict]:
        """Get track data from an album's media array.

        Looks up the album by foreignAlbumId and extracts track info
        from the media array. Returns [] if album not found or no
        track data available (best-effort).
        """
        try:
            logger.info(f"🔍 Looking up tracks for album: {foreign_album_id}")
            results = await self._request(
                f"album/lookup?term=lidarr:{foreign_album_id}"
            )

            if not results or not isinstance(results, list) or not results[0]:
                logger.warning(
                    f"⚠️ No album found for track lookup: {foreign_album_id}"
                )
                return []

            album = results[0]
            tracks = []
            for medium in album.get("media", []):
                for track in medium.get("tracks", []):
                    tracks.append(track)

            if not tracks:
                logger.info(
                    f"ℹ️ No track data in album: {foreign_album_id}"
                )

            return tracks

        except Exception as e:
            logger.error(f"❌ Failed to get album tracks: {str(e)}")
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

    async def add_artist(self, artist_id: str, root_folder: Optional[str] = None, quality_profile_id: Optional[int] = None, albums_to_monitor: Optional[List[str]] = None, future_albums: bool = False) -> tuple[bool, str]:
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

            add_options: Dict[str, Any] = {
                "searchForMissingAlbums": lidarr_features.get("search", True)
            }

            if future_albums:
                add_options["monitor"] = "future"
                if albums_to_monitor is not None:
                    add_options["albumsToMonitor"] = albums_to_monitor
            elif albums_to_monitor is not None:
                add_options["monitor"] = "none"
                add_options["albumsToMonitor"] = albums_to_monitor
            else:
                add_options["monitor"] = monitor_option

            data = {
                "foreignArtistId": artist["foreignArtistId"],
                "artistName": artist["artistName"],
                "qualityProfileId": quality_profile_id or 1,  # Default profile if not specified
                "metadataProfileId": config.get("lidarr", {}).get("metadataProfileId", 1),
                "rootFolderPath": root_folder or "/music",  # Default path if not specified
                "albumFolder": album_folder,
                "monitored": True,
                "addOptions": add_options
            }

            success, _result, error = await self._make_request(
                "artist", method="POST", data=data, title=artist["artistName"], max_retries=0
            )
            if success:
                logger.info(f"✅ Successfully added artist: {artist['artistName']}")
                return True, f"Successfully added {artist['artistName']}"
            return False, error or f"Failed to add {artist['artistName']}"

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
            profiles = filter_quality_profiles(profiles, config.get("lidarr", {}))

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

    async def get_queue(self) -> List[Dict]:
        """Get the current download queue from Lidarr."""
        try:
            logger.info(Fore.BLUE + "📥 Getting download queue from Lidarr")
            result = await self._request(
                "queue?sortKey=title&sortDirection=ascending&pageSize=1000"
            )

            if not result or not isinstance(result, dict):
                logger.warning(Fore.YELLOW + "⚠️ No queue items found in Lidarr")
                return []

            records = result.get("records", [])
            logger.info(Fore.GREEN + f"✅ Found {len(records)} queue items in Lidarr")
            return records

        except Exception as e:
            logger.error(Fore.RED + f"❌ Failed to get Lidarr queue: {str(e)}")
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
        logger.info(f"🗑️ Deleting artist with ID: {artist_id}")
        success, _data, _error = await self._make_request(
            f"artist/{artist_id}?deleteFiles=true", method="DELETE", max_retries=0
        )
        if success:
            logger.info(f"✅ Successfully deleted artist {artist_id}")
        return success

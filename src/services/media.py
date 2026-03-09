"""
Filename: media.py
Author: Christian Blank (https://github.com/Cyneric)
Created Date: 2024-11-08
Description: Media service module.

This module handles interactions with media services (Radarr, Sonarr, Lidarr).
"""

import asyncio
import datetime
from typing import List, Dict, Optional

from src.utils.logger import get_logger
from src.config.settings import config
from src.api.radarr import RadarrClient
from src.api.sonarr import SonarrClient
from src.api.lidarr import LidarrClient

logger = get_logger("addarr.services.media")


class MediaService:
    """Service for handling media operations"""

    # Class-level storage for singleton instances
    _instance = None
    _radarr = None
    _sonarr = None
    _lidarr = None

    def __new__(cls):
        """Ensure only one instance of MediaService exists"""
        if cls._instance is None:
            cls._instance = super(MediaService, cls).__new__(cls)
            cls._initialize_clients()
        return cls._instance

    @classmethod
    def _initialize_clients(cls):
        """Initialize API clients if not already initialized"""
        # Initialize Radarr
        if cls._radarr is None:
            try:
                if config.get("radarr", {}).get("enable"):
                    cls._radarr = RadarrClient()
            except Exception as e:
                logger.error(f"Failed to initialize Radarr client: {e}")
                cls._radarr = None

        # Initialize Sonarr
        if cls._sonarr is None:
            try:
                if config.get("sonarr", {}).get("enable"):
                    cls._sonarr = SonarrClient()
            except Exception as e:
                logger.error(f"Failed to initialize Sonarr client: {e}")
                cls._sonarr = None

        # Initialize Lidarr
        if cls._lidarr is None:
            try:
                if config.get("lidarr", {}).get("enable"):
                    cls._lidarr = LidarrClient()
            except Exception as e:
                logger.error(f"Failed to initialize Lidarr client: {e}")
                cls._lidarr = None

    def __init__(self):
        """Initialize the service"""
        self.transmission = None
        self.sabnzbd = None

        # Initialize download clients if enabled
        try:
            if config.get("transmission", {}).get("enable"):
                from src.api.transmission import TransmissionClient
                self.transmission = TransmissionClient()
        except ImportError:
            logger.warning("Transmission module not available")

        try:
            if config.get("sabnzbd", {}).get("enable"):
                from src.api.sabnzbd import SabnzbdClient
                self.sabnzbd = SabnzbdClient()
        except ImportError:
            logger.warning("SABnzbd module not available")

    @property
    def radarr(self):
        return self._radarr

    @property
    def sonarr(self):
        return self._sonarr

    @property
    def lidarr(self):
        return self._lidarr

    async def search_movies(self, query: str) -> List[Dict]:
        """Search for movies using Radarr"""
        if not self.radarr:
            raise ValueError("Radarr is not enabled or configured")

        try:
            results = await self.radarr.search(query)
            return [
                {
                    "id": str(movie["tmdbId"]),
                    "title": f"{movie['title']} ({movie.get('year', 'N/A')})",
                    "overview": movie.get("overview", "No overview available"),
                    "year": movie.get("year"),
                    "poster": (
                        # Try Radarr image first
                        next((img["remoteUrl"] for img in movie.get("images", [])
                             if img.get("coverType", "").lower() == "poster"), None)
                        # Fallback to TMDB
                        or (f"https://image.tmdb.org/t/p/w500/{movie.get('remotePoster')}"
                            if movie.get("remotePoster")
                            else None)
                    ),
                    "ratings": {
                        "imdb": movie.get("ratings", {}).get("imdb", {}).get("value", "N/A"),
                        "rottenTomatoes": movie.get("ratings", {}).get("rottenTomatoes", {}).get("value", "N/A")
                    },
                    "studio": movie.get("studio", "N/A"),  # Added studio info
                    "status": movie.get("status", "unknown"),
                    "runtime": movie.get("runtime", "N/A"),
                    "genres": movie.get("genres", []),  # Full genre list
                    "external_ids": {
                        "imdb": movie.get("imdbId"),
                        "tmdb": movie.get("tmdbId"),
                    },
                    "data": movie
                }
                for movie in results
                if movie.get("tmdbId")
            ]
        except Exception as e:
            logger.error(f"Error searching movies: {e}")
            raise

    async def search_series(self, query: str) -> List[Dict]:
        """Search for TV series using Sonarr"""
        if not self.sonarr:
            raise ValueError("Sonarr is not enabled or configured")

        try:
            results = await self.sonarr.search(query)
            return [
                {
                    "id": str(series["tvdbId"]),
                    "title": f"{series['title']} ({series.get('year', 'N/A')})",
                    "overview": series.get("overview", "No overview available"),
                    "year": series.get("year"),
                    "poster": (
                        # Try Sonarr image first
                        next((img["remoteUrl"] for img in series.get("images", [])
                             if img.get("coverType", "").lower() == "poster"), None)
                        # Fallback to TVDB
                        or (f"https://artworks.thetvdb.com/banners/{series.get('remotePoster')}"
                            if series.get('remotePoster')
                            else None)
                    ),
                    "ratings": {
                        "tmdb": series.get("ratings", {}).get("tmdb", {}).get("value", "N/A"),
                        "votes": series.get("ratings", {}).get("tmdb", {}).get("votes", 0)
                    },
                    "network": series.get("network", "N/A"),
                    "studio": series.get("studio", "N/A"),  # Added studio info
                    "status": series.get("status", "unknown"),
                    "seasons": len(series.get("seasons", [])),
                    "runtime": series.get("runtime", "N/A"),
                    "genres": series.get("genres", []),  # Full genre list
                    "external_ids": {
                        "tvdb": series.get("tvdbId"),
                        "imdb": series.get("imdbId"),
                    },
                    "data": series
                }
                for series in results
                if series.get("tvdbId")
            ]
        except Exception as e:
            logger.error(f"Error searching series: {e}")
            raise

    async def search_music(self, query: str) -> List[Dict]:
        """Search for music using Lidarr (artists, albums, and songs)"""
        if not self.lidarr:
            raise ValueError("Lidarr is not enabled or configured")

        try:
            artist_results, album_results = await asyncio.gather(
                self.lidarr.search(query),
                self.lidarr.search_albums(query),
            )

            # Normalize artist results
            artists = [
                {
                    "id": str(artist["foreignArtistId"]),
                    "title": artist["artistName"],
                    "overview": artist.get("overview", "No overview available"),
                    "year": artist.get("statistics", {}).get("yearStart", "N/A"),
                    "poster": (
                        next((img["remoteUrl"] for img in artist.get("images", [])
                             if img.get("coverType", "").lower() in ["poster", "cover"]), None)
                        or (f"https://coverartarchive.org/release-group/{artist.get('foreignArtistId')}/front"
                            if artist.get("foreignArtistId")
                            else None)
                        or (f"https://ws.audioscrobbler.com/2.0/?method=artist.getinfo"
                            f"&artist={artist['artistName']}&format=json"
                            if artist.get('artistName')
                            else None)
                    ),
                    "rating": artist.get("ratings", {}).get("value", "N/A"),
                    "genres": ", ".join(artist.get("genres", ["Unknown"])),
                    "type": artist.get("artistType", "Unknown"),
                    "status": artist.get("status", "unknown"),
                    "music_type": "artist",
                    "external_ids": {
                        "musicbrainz": artist.get("foreignArtistId"),
                    },
                    "data": artist,
                }
                for artist in artist_results
                if artist.get("foreignArtistId")
            ]

            # Normalize album results
            albums = []
            songs = []
            for album in album_results:
                album_id = album.get("foreignAlbumId")
                if not album_id:
                    continue

                artist_info = album.get("artist", {})
                artist_id = artist_info.get("foreignArtistId", "")

                albums.append({
                    "id": f"album:{album_id}",
                    "title": album["title"],
                    "overview": album.get("overview", "No overview available"),
                    "poster": next(
                        (img["remoteUrl"] for img in album.get("images", [])
                         if img.get("coverType", "").lower() in ["poster", "cover"]),
                        None,
                    ),
                    "release_date": album.get("releaseDate", ""),
                    "artist_name": artist_info.get("artistName", ""),
                    "artist_id": artist_id,
                    "album_id": album_id,
                    "music_type": "album",
                    "external_ids": {
                        "musicbrainz": album.get("foreignAlbumId"),
                    },
                    "data": album,
                })

                # Extract song matches from track data (best-effort)
                query_lower = query.lower()
                for medium in album.get("media", []):
                    for track in medium.get("tracks", []):
                        track_title = track.get("title", "")
                        if track_title and query_lower in track_title.lower():
                            songs.append({
                                "id": f"album:{album_id}",
                                "title": track_title,
                                "album_title": album["title"],
                                "artist_name": artist_info.get("artistName", ""),
                                "artist_id": artist_id,
                                "album_id": album_id,
                                "music_type": "song",
                                "external_ids": {
                                    "musicbrainz": album.get("foreignAlbumId"),
                                },
                                "data": album,
                            })

            # Merge: artists → albums → songs
            return artists + albums + songs

        except Exception as e:
            logger.error(f"Error searching music: {e}")
            raise

    async def add_movie(self, tmdb_id: str) -> tuple[bool, str]:
        """Add a movie to Radarr"""
        if not self.radarr:
            raise ValueError("Radarr is not enabled or configured")

        try:
            # Get root folder and quality profiles
            root_folders = await self.radarr.get_root_folders()
            if not root_folders:
                return False, "No root folders configured in Radarr"

            quality_profiles = await self.radarr.get_quality_profiles()
            if not quality_profiles:
                return False, "No quality profiles configured in Radarr"

            # Get movie details using proper lookup endpoint
            lookup_results = await self.radarr.get_movie(tmdb_id)  # Use get_movie instead of search
            if not lookup_results:
                return False, "Movie not found"

            movie = lookup_results

            # Format quality profiles for selection
            profile_text = "Select quality profile:\n\n"
            for i, profile in enumerate(quality_profiles, 1):
                profile_text += f"{i}. {profile['name']}\n"

            # Store information for later use
            return {
                "type": "quality_selection",
                "profiles": quality_profiles,
                "root_folder": root_folders[0],  # Use first root folder for now
                "movie": movie,
                "message": profile_text
            }

        except Exception as e:
            logger.error(f"❌ Error in MediaService.add_movie: {str(e)}")
            return False, str(e)

    async def add_movie_with_profile(self, tmdb_id: str, profile_id: int, root_folder: str) -> tuple[bool, str]:
        """Add a movie to Radarr with selected quality profile"""
        if not self.radarr:
            raise ValueError("Radarr is not enabled or configured")

        try:
            # Add the movie with selected profile
            success, message = await self.radarr.add_movie(
                int(tmdb_id),
                root_folder,
                profile_id
            )

            if success:
                logger.info("✅ Movie added successfully")
            else:
                logger.info(f"ℹ️ {message}")

            return success, message

        except Exception as e:
            logger.error(f"❌ Error in MediaService.add_movie: {str(e)}")
            return False, str(e)

    async def add_series(self, tvdb_id: str) -> tuple[bool, str]:
        """Add a TV series to Sonarr"""
        if not self.sonarr:
            raise ValueError("Sonarr is not enabled or configured")

        try:
            # Get root folder and quality profiles
            root_folders = await self.sonarr.get_root_folders()
            if not root_folders:
                return False, "No root folders configured in Sonarr"

            quality_profiles = await self.sonarr.get_quality_profiles()
            if not quality_profiles:
                return False, "No quality profiles configured in Sonarr"

            # Get series details and seasons
            lookup_results = await self.sonarr.get_series(tvdb_id)
            if not lookup_results:
                return False, "Series not found"

            seasons = await self.sonarr.get_seasons(tvdb_id)
            if not seasons:
                return False, "No seasons found for series"

            series = lookup_results

            # Format quality profiles for selection
            profile_text = "Select quality profile:\n\n"
            for i, profile in enumerate(quality_profiles, 1):
                profile_text += f"{i}. {profile['name']}\n"

            # Store information for later use
            return {
                "type": "quality_selection",
                "profiles": quality_profiles,
                "root_folder": root_folders[0],  # Use first root folder for now
                "series": series,
                "seasons": seasons,  # Add seasons to context
                "message": profile_text
            }

        except Exception as e:
            logger.error(f"❌ Error in MediaService.add_series: {str(e)}")
            return False, str(e)

    async def add_series_with_profile(self, tvdb_id: str, profile_id: int, root_folder: str, selected_seasons: List[int] = None) -> tuple[bool, str]:
        """Add a series to Sonarr with selected quality profile and seasons"""
        if not self.sonarr:
            raise ValueError("Sonarr is not enabled or configured")

        try:
            # Get all seasons
            seasons = await self.sonarr.get_seasons(tvdb_id)

            # Format season data
            season_data = []
            for season in seasons:
                season_number = season.get("seasonNumber")
                if season_number is not None:
                    season_data.append({
                        "seasonNumber": season_number,
                        "monitored": selected_seasons is None or season_number in selected_seasons
                    })

            # Add the series with selected profile and seasons
            success, message = await self.sonarr.add_series(
                int(tvdb_id),
                root_folder,
                profile_id,
                season_data
            )

            if success:
                logger.info("✅ Series added successfully")
            else:
                logger.info(f"ℹ️ {message}")

            return success, message

        except Exception as e:
            logger.error(f"❌ Error in MediaService.add_series: {str(e)}")
            return False, str(e)

    async def add_music(self, artist_id: str) -> tuple[bool, str]:
        """Add an artist to Lidarr"""
        if not self.lidarr:
            raise ValueError("Lidarr is not enabled or configured")

        try:
            # Get root folder and quality profiles
            root_folders = await self.lidarr.get_root_folders()
            if not root_folders:
                return False, "No root folders configured in Lidarr"

            quality_profiles = await self.lidarr.get_quality_profiles()
            if not quality_profiles:
                return False, "No quality profiles configured in Lidarr"

            # Get artist details
            lookup_results = await self.lidarr.get_artist(artist_id)
            if not lookup_results:
                return False, "Artist not found"

            artist = lookup_results

            # Format quality profiles for selection
            profile_text = "Select quality profile:\n\n"
            for i, profile in enumerate(quality_profiles, 1):
                profile_text += f"{i}. {profile['name']}\n"

            # Store information for later use
            return {
                "type": "quality_selection",
                "profiles": quality_profiles,
                "root_folder": root_folders[0],  # Use first root folder for now
                "artist": artist,
                "message": profile_text
            }

        except Exception as e:
            logger.error(f"❌ Error in MediaService.add_music: {str(e)}")
            return False, str(e)

    async def add_music_with_profile(self, artist_id: str, profile_id: int, root_folder: str, albums_to_monitor: List[str] = None, future_albums: bool = False) -> tuple[bool, str]:
        """Add an artist to Lidarr with selected quality profile"""
        if not self.lidarr:
            raise ValueError("Lidarr is not enabled or configured")

        try:
            # Add the artist with selected profile
            kwargs = {}
            if albums_to_monitor is not None:
                kwargs["albums_to_monitor"] = albums_to_monitor
            if future_albums:
                kwargs["future_albums"] = True

            success, message = await self.lidarr.add_artist(
                artist_id,
                root_folder,
                profile_id,
                **kwargs,
            )

            if success:
                logger.info("✅ Artist added successfully")
            else:
                logger.info(f"ℹ️ {message}")

            return success, message

        except Exception as e:
            logger.error(f"❌ Error in MediaService.add_music: {str(e)}")
            return False, str(e)

    async def get_artist_albums(self, artist_id: str) -> List[Dict]:
        """Get albums for an artist from Lidarr.

        Returns normalized list of {album_id, title, release_date} dicts.
        Returns [] if Lidarr disabled or on error.
        """
        if not self.lidarr:
            return []

        try:
            results = await self.lidarr.search_albums(artist_id)
            return [
                {
                    "album_id": album["foreignAlbumId"],
                    "title": album["title"],
                    "release_date": album.get("releaseDate", ""),
                }
                for album in results
                if album.get("foreignAlbumId")
            ]
        except Exception as e:
            logger.error(f"Error getting artist albums: {e}")
            return []

    async def get_upcoming(self, days: int = 7) -> List[Dict]:
        """Get upcoming releases from Radarr and Sonarr calendars.

        Returns a normalized, date-sorted list of upcoming items.
        Skips disabled services and handles errors gracefully.
        """
        today = datetime.date.today()
        start = today.isoformat()
        end = (today + datetime.timedelta(days=days)).isoformat()

        items = []

        # Fetch from both services concurrently
        tasks = []
        if self.radarr:
            tasks.append(("radarr", self.radarr.get_calendar(start, end)))
        if self.sonarr:
            tasks.append(("sonarr", self.sonarr.get_calendar(start, end)))

        if not tasks:
            return []

        results = await asyncio.gather(
            *(t[1] for t in tasks), return_exceptions=True
        )

        for (service_name, _), result in zip(tasks, results):
            if isinstance(result, Exception):
                logger.error(f"Calendar fetch failed for {service_name}: {result}")
                continue

            if service_name == "radarr":
                for movie in result:
                    items.append(self._normalize_radarr_calendar(movie))
            else:
                for episode in result:
                    items.append(self._normalize_sonarr_calendar(episode))

        items.sort(key=lambda x: x["date"])
        return items

    @staticmethod
    def _normalize_radarr_calendar(movie: Dict) -> Dict:
        """Normalize a Radarr calendar movie into the unified schema."""
        # Pick earliest non-null date
        date_candidates = []
        for field, label in [
            ("inCinemas", "Cinema"),
            ("digitalRelease", "Digital"),
            ("physicalRelease", "Physical"),
        ]:
            val = movie.get(field)
            if val:
                date_candidates.append((val[:10], label))

        if date_candidates:
            date_candidates.sort(key=lambda x: x[0])
            date, date_label = date_candidates[0]
        else:
            date, date_label = "", "Unknown"

        return {
            "type": "movie",
            "title": movie.get("title", ""),
            "series_title": None,
            "date": date,
            "date_label": date_label,
            "year": movie.get("year"),
            "season": None,
            "episode": None,
            "in_library": "id" in movie,
            "media_id": str(movie.get("tmdbId", "")),
            "internal_id": movie.get("id"),
        }

    @staticmethod
    def _normalize_sonarr_calendar(ep: Dict) -> Dict:
        """Normalize a Sonarr calendar episode into the unified schema."""
        series = ep.get("series", {})
        air_date = ep.get("airDateUtc", "")

        return {
            "type": "episode",
            "title": ep.get("title", ""),
            "series_title": series.get("title"),
            "date": air_date[:10] if air_date else "",
            "date_label": "Airing",
            "year": None,
            "season": ep.get("seasonNumber"),
            "episode": ep.get("episodeNumber"),
            "in_library": "id" in ep,
            "media_id": str(series.get("tvdbId", "")),
            "internal_id": series.get("id"),
        }

    async def get_missing_media(self) -> List[Dict]:
        """Get missing/wanted media from Radarr and Sonarr.

        Returns a normalized, title-sorted list of missing items.
        """
        return await self._fetch_wanted_media("get_missing", "missing")

    async def get_cutoff_unmet_media(self) -> List[Dict]:
        """Get cutoff-unmet media from Radarr and Sonarr.

        Returns a normalized, title-sorted list of cutoff-unmet items.
        """
        return await self._fetch_wanted_media("get_cutoff_unmet", "cutoff-unmet")

    async def _fetch_wanted_media(
        self, method: str, label: str
    ) -> List[Dict]:
        """Shared fetcher for missing and cutoff-unmet media.

        Calls ``method`` on each enabled client, normalizes results,
        and returns them sorted by title.
        """
        tasks = []
        if self.radarr:
            tasks.append(("radarr", getattr(self.radarr, method)()))
        if self.sonarr:
            tasks.append(("sonarr", getattr(self.sonarr, method)()))

        if not tasks:
            return []

        results = await asyncio.gather(
            *(t[1] for t in tasks), return_exceptions=True
        )

        items = []
        for (service_name, _), result in zip(tasks, results):
            if isinstance(result, Exception):
                logger.error(
                    f"{label} fetch failed for {service_name}: {result}"
                )
                continue

            if service_name == "radarr":
                for movie in result:
                    items.append(self._normalize_radarr_missing(movie))
            else:
                for episode in result:
                    items.append(self._normalize_sonarr_missing(episode))

        items.sort(key=lambda x: (x.get("title") or "").lower())
        return items

    async def trigger_missing_search(self, service: str, item_id: int) -> bool:
        """Trigger a manual search for a missing item."""
        client = {"radarr": self.radarr, "sonarr": self.sonarr}.get(service)

        if not client:
            logger.warning(f"Service '{service}' not available for search")
            return False

        try:
            return await client.search_command(item_id)
        except Exception as e:
            logger.error(f"Failed to trigger search on {service}: {e}")
            return False

    @staticmethod
    def _normalize_radarr_missing(movie: Dict) -> Dict:
        """Normalize a Radarr missing movie into the unified schema."""
        return {
            "type": "movie",
            "title": movie.get("title", ""),
            "series_title": None,
            "year": movie.get("year"),
            "season": None,
            "episode": None,
            "media_id": str(movie.get("tmdbId", "")),
            "internal_id": movie.get("id"),
            "service": "radarr",
        }

    @staticmethod
    def _normalize_sonarr_missing(ep: Dict) -> Dict:
        """Normalize a Sonarr missing episode into the unified schema."""
        series = ep.get("series", {})
        return {
            "type": "episode",
            "title": ep.get("title", ""),
            "series_title": series.get("title"),
            "year": series.get("year"),
            "season": ep.get("seasonNumber"),
            "episode": ep.get("episodeNumber"),
            "media_id": str(series.get("tvdbId", "")),
            "internal_id": ep.get("id"),
            "service": "sonarr",
        }

    async def get_queue_media(self) -> List[Dict]:
        """Get download queue items from all enabled services.

        Returns a normalized, title-sorted list of queue items.
        """
        normalizers = {
            "radarr": self._normalize_radarr_queue,
            "sonarr": self._normalize_sonarr_queue,
            "lidarr": self._normalize_lidarr_queue,
        }
        tasks = []
        if self.radarr:
            tasks.append(("radarr", self.radarr.get_queue()))
        if self.sonarr:
            tasks.append(("sonarr", self.sonarr.get_queue()))
        if self.lidarr:
            tasks.append(("lidarr", self.lidarr.get_queue()))

        if not tasks:
            return []

        results = await asyncio.gather(
            *(t[1] for t in tasks), return_exceptions=True
        )

        items = []
        for (service_name, _), result in zip(tasks, results):
            if isinstance(result, Exception):
                logger.error(
                    f"queue fetch failed for {service_name}: {result}"
                )
                continue
            normalize = normalizers[service_name]
            for record in result:
                items.append(normalize(record))

        items.sort(key=lambda x: (x.get("title") or "").lower())
        return items

    @staticmethod
    def _normalize_radarr_queue(item: Dict) -> Dict:
        """Normalize a Radarr queue item into the unified schema."""
        movie = item.get("movie", {})
        size = item.get("size", 0)
        sizeleft = item.get("sizeleft", 0)
        progress = round((1 - sizeleft / size) * 100) if size > 0 else 0
        return {
            "type": "movie",
            "title": movie.get("title", item.get("title", "")),
            "year": movie.get("year"),
            "series_title": None,
            "season": None,
            "episode": None,
            "status": item.get("trackedDownloadState", item.get("status", "")),
            "progress": progress,
            "timeleft": item.get("timeleft", ""),
            "protocol": item.get("protocol", ""),
            "download_client": item.get("downloadClient", ""),
            "media_id": str(movie.get("tmdbId", "")),
            "internal_id": item.get("id"),
            "service": "radarr",
        }

    @staticmethod
    def _normalize_sonarr_queue(item: Dict) -> Dict:
        """Normalize a Sonarr queue item into the unified schema."""
        series = item.get("series", {})
        ep = item.get("episode", {})
        size = item.get("size", 0)
        sizeleft = item.get("sizeleft", 0)
        progress = round((1 - sizeleft / size) * 100) if size > 0 else 0
        return {
            "type": "episode",
            "title": ep.get("title", item.get("title", "")),
            "year": series.get("year"),
            "series_title": series.get("title"),
            "season": ep.get("seasonNumber"),
            "episode": ep.get("episodeNumber"),
            "status": item.get("trackedDownloadState", item.get("status", "")),
            "progress": progress,
            "timeleft": item.get("timeleft", ""),
            "protocol": item.get("protocol", ""),
            "download_client": item.get("downloadClient", ""),
            "media_id": str(series.get("tvdbId", "")),
            "internal_id": item.get("id"),
            "service": "sonarr",
        }

    @staticmethod
    def _normalize_lidarr_queue(item: Dict) -> Dict:
        """Normalize a Lidarr queue item into the unified schema."""
        size = item.get("size", 0)
        sizeleft = item.get("sizeleft", 0)
        progress = round((1 - sizeleft / size) * 100) if size > 0 else 0
        return {
            "type": "album",
            "title": item.get("title", ""),
            "year": None,
            "series_title": None,
            "season": None,
            "episode": None,
            "status": item.get("trackedDownloadState", item.get("status", "")),
            "progress": progress,
            "timeleft": item.get("timeleft", ""),
            "protocol": item.get("protocol", ""),
            "download_client": item.get("downloadClient", ""),
            "media_id": "",
            "internal_id": item.get("id"),
            "service": "lidarr",
        }

    async def get_movies(self) -> List[Dict]:
        """Get all movies from Radarr library"""
        if not self.radarr:
            raise ValueError("Radarr is not enabled or configured")

        try:
            results = await self.radarr.get_movies()
            return [
                {"id": str(movie["id"]), "title": movie["title"]}
                for movie in results
            ]
        except Exception as e:
            logger.error(f"Error getting movies: {e}")
            raise

    async def get_movie(self, movie_id) -> Optional[Dict]:
        """Get a single movie from Radarr by internal ID"""
        if not self.radarr:
            raise ValueError("Radarr is not enabled or configured")

        try:
            result = await self.radarr.get_movie_by_id(int(movie_id))
            if not result:
                return None
            return {"id": str(result["id"]), "title": result["title"]}
        except Exception as e:
            logger.error(f"Error getting movie: {e}")
            raise

    async def get_series(self, series_id=None) -> object:
        """Get series from Sonarr. If series_id given, get single; else list all."""
        if not self.sonarr:
            raise ValueError("Sonarr is not enabled or configured")

        try:
            if series_id is not None:
                result = await self.sonarr.get_series_by_id(int(series_id))
                if not result:
                    return None
                return {"id": str(result["id"]), "title": result["title"]}
            else:
                results = await self.sonarr.get_all_series()
                return [
                    {"id": str(s["id"]), "title": s["title"]}
                    for s in results
                ]
        except Exception as e:
            logger.error(f"Error getting series: {e}")
            raise

    async def get_music(self, music_id=None) -> object:
        """Get artists from Lidarr. If music_id given, get single; else list all."""
        if not self.lidarr:
            raise ValueError("Lidarr is not enabled or configured")

        try:
            if music_id is not None:
                result = await self.lidarr.get_artist_by_id(int(music_id))
                if not result:
                    return None
                return {
                    "id": str(result["id"]),
                    "title": result["artistName"],
                }
            else:
                results = await self.lidarr.get_artists()
                return [
                    {"id": str(a["id"]), "title": a["artistName"]}
                    for a in results
                ]
        except Exception as e:
            logger.error(f"Error getting music: {e}")
            raise

    async def delete_movie(self, movie_id) -> bool:
        """Delete a movie from Radarr"""
        if not self.radarr:
            raise ValueError("Radarr is not enabled or configured")

        try:
            return await self.radarr.delete_movie(int(movie_id))
        except Exception as e:
            logger.error(f"Error deleting movie: {e}")
            raise

    async def delete_series(self, series_id) -> bool:
        """Delete a series from Sonarr"""
        if not self.sonarr:
            raise ValueError("Sonarr is not enabled or configured")

        try:
            return await self.sonarr.delete_series(int(series_id))
        except Exception as e:
            logger.error(f"Error deleting series: {e}")
            raise

    async def delete_music(self, music_id) -> bool:
        """Delete an artist from Lidarr"""
        if not self.lidarr:
            raise ValueError("Lidarr is not enabled or configured")

        try:
            return await self.lidarr.delete_artist(int(music_id))
        except Exception as e:
            logger.error(f"Error deleting music: {e}")
            raise

    async def get_radarr_status(self) -> bool:
        """Check if Radarr is available"""
        try:
            return await self.radarr.check_status() if self.radarr else False
        except Exception as e:
            logger.error(f"Error checking Radarr status: {e}")
            return False

    async def get_sonarr_status(self) -> bool:
        """Check if Sonarr is available"""
        try:
            return await self.sonarr.check_status() if self.sonarr else False
        except Exception as e:
            logger.error(f"Error checking Sonarr status: {e}")
            return False

    async def get_lidarr_status(self) -> bool:
        """Check if Lidarr is available"""
        try:
            return await self.lidarr.check_status() if self.lidarr else False
        except Exception as e:
            logger.error(f"Error checking Lidarr status: {e}")
            return False

    async def get_transmission_status(self) -> bool:
        """Check if Transmission is available"""
        try:
            return await self.transmission.check_status() if self.transmission else False
        except Exception as e:
            logger.error(f"Error checking Transmission status: {e}")
            return False

    async def get_history(self, page: int = 1, page_size: int = 20,
                          event_type: str = None) -> List[Dict]:
        """Get recent history from Radarr and Sonarr.

        Returns a normalized, date-sorted (newest first) list of history items.
        """
        tasks = []
        if self.radarr:
            tasks.append(("radarr", self.radarr.get_history(
                page, page_size, event_type
            )))
        if self.sonarr:
            tasks.append(("sonarr", self.sonarr.get_history(
                page, page_size, event_type
            )))

        if not tasks:
            return []

        results = await asyncio.gather(
            *(t[1] for t in tasks), return_exceptions=True
        )

        items = []
        for (service_name, _), result in zip(tasks, results):
            if isinstance(result, Exception):
                logger.error(f"History fetch failed for {service_name}: {result}")
                continue

            if service_name == "radarr":
                for record in result:
                    items.append(self._normalize_radarr_history(record))
            else:
                for record in result:
                    items.append(self._normalize_sonarr_history(record))

        items.sort(key=lambda x: x.get("date", ""), reverse=True)
        return items

    @staticmethod
    def _normalize_radarr_history(record: Dict) -> Dict:
        """Normalize a Radarr history record."""
        movie = record.get("movie", {})
        return {
            "type": "movie",
            "title": movie.get("title", ""),
            "episode_title": None,
            "season": None,
            "episode": None,
            "date": record.get("date", ""),
            "event_type": record.get("eventType", ""),
            "quality": record.get("quality", {}).get("quality", {}).get("name", ""),
            "source_title": record.get("sourceTitle", ""),
            "service": "radarr",
        }

    @staticmethod
    def _normalize_sonarr_history(record: Dict) -> Dict:
        """Normalize a Sonarr history record."""
        series = record.get("series", {})
        ep = record.get("episode", {})
        return {
            "type": "episode",
            "title": series.get("title", ""),
            "episode_title": ep.get("title"),
            "season": ep.get("seasonNumber"),
            "episode": ep.get("episodeNumber"),
            "date": record.get("date", ""),
            "event_type": record.get("eventType", ""),
            "quality": record.get("quality", {}).get("quality", {}).get("name", ""),
            "source_title": record.get("sourceTitle", ""),
            "service": "sonarr",
        }

    async def get_sabnzbd_status(self) -> bool:
        """Check if SABnzbd is available"""
        try:
            return await self.sabnzbd.check_status() if self.sabnzbd else False
        except Exception as e:
            logger.error(f"Error checking SABnzbd status: {e}")
            return False

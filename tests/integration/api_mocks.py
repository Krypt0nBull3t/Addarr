"""
API mock helpers for integration tests.

Friendly wrappers around aioresponses that register URL patterns matching
the real Radarr, Sonarr, and Lidarr API clients.
"""

import re


class BaseMockHelper:
    """Base class for API mock helpers."""

    SERVICE = ""
    PORT = 0
    API_VERSION = "v3"
    SEARCH_ENDPOINT = ""
    QUALITY_ENDPOINT = "qualityProfile"
    ROOT_FOLDER_ENDPOINT = "rootfolder"
    ADD_ENDPOINT = ""

    def __init__(self, aio_mock):
        self._m = aio_mock
        self.base_url = f"http://localhost:{self.PORT}"

    def _url(self, endpoint):
        return f"{self.base_url}/api/{self.API_VERSION}/{endpoint}"

    def _url_pattern(self, endpoint):
        """Build a regex pattern matching the endpoint (with optional query string)."""
        return re.compile(re.escape(self._url(endpoint)) + r"(\?.*)?$")

    def set_defaults(self):
        """Register default responses: empty search, empty profiles, empty root folders."""
        self.search_returns([])
        self.quality_profiles([])
        self.root_folders([])

    def search_returns(self, results):
        """Mock the search endpoint to return given results."""
        self._m.get(self._url_pattern(self.SEARCH_ENDPOINT), payload=results)

    def quality_profiles(self, profiles=None):
        """Mock the quality profiles endpoint."""
        self._m.get(
            self._url(self.QUALITY_ENDPOINT),
            payload=profiles or [],
        )

    def root_folders(self, folders=None):
        """Mock the root folders endpoint."""
        self._m.get(
            self._url(self.ROOT_FOLDER_ENDPOINT),
            payload=folders or [{"path": "/media", "freeSpace": 1000000000000}],
        )

    def add_returns(self, result=None, status=201):
        """Mock the add (POST) endpoint."""
        self._m.post(
            self._url(self.ADD_ENDPOINT),
            payload=result or {"id": 1},
            status=status,
        )


class RadarrMockHelper(BaseMockHelper):
    SERVICE = "radarr"
    PORT = 7878
    SEARCH_ENDPOINT = "movie/lookup"
    QUALITY_ENDPOINT = "qualityProfile"
    ADD_ENDPOINT = "movie"


class SonarrMockHelper(BaseMockHelper):
    SERVICE = "sonarr"
    PORT = 8989
    SEARCH_ENDPOINT = "series/lookup"
    QUALITY_ENDPOINT = "qualityProfile"
    ADD_ENDPOINT = "series"


class LidarrMockHelper(BaseMockHelper):
    SERVICE = "lidarr"
    PORT = 8686
    API_VERSION = "v1"
    SEARCH_ENDPOINT = "artist/lookup"
    QUALITY_ENDPOINT = "qualityprofile"
    ADD_ENDPOINT = "artist"

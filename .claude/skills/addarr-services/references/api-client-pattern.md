# API Client Pattern

## BaseApiClient Inheritance

All media API clients (Radarr, Sonarr, Lidarr) inherit from `BaseApiClient` in `src/api/base.py`.

### Template

```python
from typing import Dict, List, Optional
from colorama import Fore

from src.api.base import APIError, BaseApiClient
from src.config.settings import config
from src.utils.logger import get_logger

logger = get_logger("addarr.<name>")


class <Name>Client(BaseApiClient):
    """<Name> API client"""

    # Override if API version differs (default is "v3")
    # API_VERSION = "v1"

    def __init__(self):
        """Initialize <Name> API client"""
        service_config = config.get("<service_key>", {})
        server_config = service_config.get("server", {})
        auth_config = service_config.get("auth", {})

        addr = server_config.get("addr")
        port = server_config.get("port")

        if not addr or not port:
            logger.error(Fore.RED + "❌ <Name> server address or port not configured")
            raise ValueError("<Name> server address or port not configured")

        if not auth_config.get("apikey"):
            logger.error(Fore.RED + "❌ <Name> API key not configured")
            raise ValueError("<Name> API key not configured")

        super().__init__("<service_key>")
        logger.info(Fore.GREEN + f"✅ <Name> API client initialized: {self.base_url}")

    async def search(self, term: str) -> List[Dict]:
        """Search for <media>"""
        logger.info(Fore.BLUE + f"🔍 Searching <Name> for: {term}")
        success, results, error = await self._make_request(
            "<endpoint>/lookup", params={"term": term}
        )
        if not success:
            raise APIError(f"<Name> search failed: {error}")

        if not results:
            logger.warning(Fore.YELLOW + f"⚠️ No results found for: {term}")
            return []

        logger.info(Fore.GREEN + f"✅ Found {len(results)} results for: {term}")
        return results
```

`search()` raises `APIError` when the request fails and returns `[]` only when there are no results, as `RadarrClient.search` does. Do not turn a failed request into `[]`.

### Init Validation

The `__init__` pattern:
1. Extract config sections (`server`, `auth`)
2. Validate required fields (`addr`, `port`, `apikey`)
3. Raise `ValueError` if validation fails (caught by service `_initialize`)
4. Call `super().__init__(service_key)` which builds URL and sets up session management

### What `super().__init__()` Provides

`BaseApiClient.__init__(self, service_name)` sets up:
- `self.config = config[service_name]` — service config section
- `self.base_url` — built from `_build_base_url()` (protocol://addr:port/path)
- `self.logger` — per-service logger
- `self.request_timeout` — default 30s
- `self._session = None` — lazy-loaded aiohttp session

## Request Methods

### `_make_request()` — Full control

```python
success, data, error = await self._make_request(
    "endpoint/path",
    method="GET",       # GET, POST, DELETE
    data=None,          # JSON body for POST
    title="Item Name",  # For error messages
    timeout=60,         # Override default
    max_retries=3,      # Override default (2); add and delete pass 0
    params={"term": term},  # Query parameters, URL-encoded by aiohttp
)
# Returns: Tuple[bool, Any, Optional[str]]
```

### `_request()` — Convenience wrapper

```python
result = await self._request("endpoint/path")
# Returns: data on success, None on failure
```

Use `_request()` for simple GET calls where you just need the data. Use `_make_request()` when you need the success flag, the error message, `params` or `max_retries`.

## Common Endpoint Patterns

### GET with query params
Pass user input via `params=`, never in the endpoint string:
```python
success, results, error = await self._make_request(
    "movie/lookup", params={"term": term}
)
```

### GET by ID
```python
result = await self._request(f"movie/{movie_id}")
```

### GET list
```python
profiles = await self._request("qualityProfile")
root_folders = await self._request("rootFolder")
```

### POST (add item)
Add and delete requests go through `_make_request()` with `max_retries=0`. The default retries a 5xx response, and a non-idempotent POST must not be sent twice.

```python
async def add_movie(self, tmdb_id: int, root_folder: str, quality_profile_id: int) -> tuple[bool, str]:
    # Lookup first (an int ID, so it may stay in the endpoint string)
    lookup = await self._request(f"movie/lookup?term=tmdb:{tmdb_id}")
    if not lookup:
        return False, "Movie not found"

    movie = lookup[0]
    data = {
        "tmdbId": movie["tmdbId"],
        "title": movie["title"],
        "qualityProfileId": quality_profile_id,
        "rootFolderPath": root_folder,
        "monitored": True,
        "addOptions": {"searchForMovie": True}
    }

    success, _result, error = await self._make_request(
        "movie", method="POST", data=data, title=movie["title"], max_retries=0
    )
    if success:
        return True, f"Successfully added {movie['title']}"
    return False, error or f"Failed to add {movie['title']}"
```

### DELETE
```python
async def delete_movie(self, movie_id: int) -> bool:
    success, _data, _error = await self._make_request(
        f"movie/{movie_id}?deleteFiles=true", method="DELETE", max_retries=0
    )
    return success
```

Before you ship a new *arr request, ask the `arr-api-contract-checker` agent to check it against the Servarr OpenAPI spec.

## API Version

| Service | API_VERSION | Base Endpoint |
|-|-|-|
| Radarr | `v3` | `/api/v3/` |
| Sonarr | `v3` | `/api/v3/` |
| Lidarr | `v1` | `/api/v1/` |
| Bazarr | `""`, plus a `BazarrClient._build_api_url` override | `/api/` |

Override in subclass:
```python
class LidarrClient(BaseApiClient):
    API_VERSION = "v1"
```

## Standalone Clients (No BaseApiClient)

Transmission doesn't inherit from BaseApiClient, and SABnzbd has no API client (`SABnzbdService` makes its own `aiohttp` calls):

- **TransmissionClient**: Uses `aiohttp` with the RPC protocol and session ID negotiation

If your new API uses a non-REST pattern, consider a standalone client instead.

## Return Type Conventions

| Method | Returns |
|-|-|
| `search(term)` | `List[Dict]`; raises `APIError` on request failure; `[]` when no results |
| `get_<item>(id)` | `Optional[Dict]` (None on failure) |
| `get_<items>()` | `List[Dict]` or `List[str]` (empty on failure) |
| `add_<item>(...)` | `tuple[bool, str]` (success, message) |
| `delete_<item>(id)` | `bool` |

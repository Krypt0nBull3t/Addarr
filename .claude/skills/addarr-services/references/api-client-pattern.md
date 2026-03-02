# API Client Pattern

## BaseApiClient Inheritance

All media API clients (Radarr, Sonarr, Lidarr) inherit from `BaseApiClient` in `src/api/base.py`.

### Template

```python
from typing import Dict, List, Optional
from colorama import Fore

from src.api.base import BaseApiClient
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
        """Search for <media type>"""
        try:
            logger.info(Fore.BLUE + f"🔍 Searching for: {term}")
            results = await self._request(f"<endpoint>/lookup?term={term}")

            if not results:
                logger.warning(Fore.YELLOW + f"⚠️ No results for: {term}")
                return []

            logger.info(Fore.GREEN + f"✅ Found {len(results)} results")
            return results
        except Exception as e:
            logger.error(Fore.RED + f"❌ Search failed: {str(e)}")
            return []
```

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
    max_retries=3       # Override default (2)
)
# Returns: Tuple[bool, Any, Optional[str]]
```

### `_request()` — Convenience wrapper

```python
result = await self._request("endpoint/path")
# Returns: data on success, None on failure
```

Use `_request()` for simple GET calls where you just need the data. Use `_make_request()` when you need the success flag or error message.

## Common Endpoint Patterns

### GET with query params
```python
results = await self._request(f"movie/lookup?term={term}")
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
For complex POST requests that need custom response handling, use inline session:

```python
async def add_movie(self, tmdb_id, root_folder, quality_profile_id):
    # Lookup first
    lookup = await self._request(f"movie/lookup?term=tmdb:{tmdb_id}")
    if not lookup:
        return False, "Not found"

    data = {
        "tmdbId": lookup[0]["tmdbId"],
        "title": lookup[0]["title"],
        "qualityProfileId": quality_profile_id,
        "rootFolderPath": root_folder,
        "monitored": True,
        "addOptions": {"searchForMovie": True}
    }

    session = await self._get_session()
    url = f"{self.base_url}/api/{self.API_VERSION}/movie"
    async with session.post(url, headers=self._get_headers(), json=data) as response:
        # ... custom response parsing
```

### DELETE
```python
async def delete_movie(self, movie_id: int) -> bool:
    session = await self._get_session()
    url = f"{self.base_url}/api/{self.API_VERSION}/movie/{movie_id}?deleteFiles=true"
    async with session.delete(url, headers=self._get_headers()) as response:
        return response.status == 200
```

## check_status()

Inherited from BaseApiClient — calls `system/status` endpoint:

```python
# Usually no override needed. BaseApiClient provides:
async def check_status(self) -> bool:
    success, _data, _error = await self._make_request("system/status")
    return success
```

Override only if the service uses a different status endpoint.

## API Version

| Service | API_VERSION | Base Endpoint |
|---------|-------------|---------------|
| Radarr  | `v3`        | `/api/v3/`    |
| Sonarr  | `v3`        | `/api/v3/`    |
| Lidarr  | `v1`        | `/api/v1/`    |

Override in subclass:
```python
class LidarrClient(BaseApiClient):
    API_VERSION = "v1"
```

## Standalone Clients (No BaseApiClient)

SABnzbd and Transmission don't inherit from BaseApiClient:

- **SabnzbdClient**: Uses query-param-based API (`?mode=queue&apikey=...`), creates new session per request
- **TransmissionClient**: Uses sync `requests.post()` with RPC protocol and session ID negotiation

If your new API uses a non-REST pattern, consider a standalone client instead.

## Return Type Conventions

| Method | Returns |
|--------|---------|
| `search(term)` | `List[Dict]` (empty on failure) |
| `get_<item>(id)` | `Optional[Dict]` (None on failure) |
| `get_<items>()` | `List[Dict]` or `List[str]` (empty on failure) |
| `add_<item>(...)` | `tuple[bool, str]` (success, message) |
| `delete_<item>(id)` | `bool` |
| `check_status()` | `bool` |

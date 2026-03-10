# Service Singleton Pattern

## Template

```python
import aiohttp
from typing import Optional

from src.config.settings import config
from src.utils.logger import get_logger

logger = get_logger("addarr.<name>")


class <Name>Service:
    """Service for <description>"""
    _instance: Optional["<Name>Service"] = None
    _enabled: bool = False
    _client: Optional["<Name>Client"] = None

    def __new__(cls):
        """Ensure only one instance exists"""
        if cls._instance is None:
            cls._instance = super(<Name>Service, cls).__new__(cls)
            cls._initialize()
        return cls._instance

    @classmethod
    def _initialize(cls):
        """Initialize service state on first instantiation."""
        cls._enabled = False
        cls._client = None

        service_config = config.get('<service_key>', {})
        if not service_config.get('enable', False):
            return

        try:
            # Initialize client or state
            cls._client = <Name>Client()
            cls._enabled = True
            logger.info("✅ <Name>Service initialized")
        except Exception as e:
            logger.error(f"Failed to initialize <Name>Service: {e}")
            cls._enabled = False

    def is_enabled(self) -> bool:
        """Check if service is enabled and properly configured."""
        return bool(self._enabled)
```

## Key Rules

### Singleton via `__new__`
- `_instance` class variable holds the singleton
- `__new__` checks `_instance is None` before creating
- `_initialize()` is a `@classmethod` called once from `__new__`

### `_initialize` Error Handling
- **Never raise** from `_initialize` — set `_enabled = False` and log instead
- This allows handlers to check `is_enabled()` rather than catching init exceptions
- Pattern from issue #78: `try/except Exception` → `_enabled = False`

### Class vs Instance Variables
- All state in `_initialize` uses **class variables** (`cls._enabled`, `cls._client`)
- These are accessed via `self._enabled` in instance methods (Python resolves to class)
- `__init__` is rarely used (runs every time `<Name>Service()` is called, not just first time)
- **mypy requires class-level type annotations** for attrs set in `_initialize` — without them, mypy reports `attr-defined` errors. Always declare types at class level (see template above).

### Testing Implications
- `reset_singletons` fixture must reset `_instance = None` AND all class vars
- Example: `_instance = None, _enabled = False, _client = None`
- See @addarr-testing fixtures.md for the singleton reset warning

## Async Methods

```python
async def get_status(self) -> Dict[str, Any]:
    """Get service status"""
    if not self.is_enabled():
        return {"error": "Service not enabled"}

    try:
        result = await self._client.get_status()
        return result
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return {"error": str(e)}
```

**Rules:**
- Always check `is_enabled()` first
- Wrap in try/except, return sensible defaults on error
- Delegate I/O to API client, don't make HTTP calls directly

## Service with API Client Aggregation

MediaService pattern — wraps multiple API clients:

```python
class MediaService:
    _instance: Optional["MediaService"] = None
    _radarr: Optional[RadarrClient] = None
    _sonarr: Optional[SonarrClient] = None
    _lidarr: Optional[LidarrClient] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MediaService, cls).__new__(cls)
            cls._initialize_clients()
        return cls._instance

    @classmethod
    def _initialize_clients(cls):
        if cls._radarr is None:
            try:
                if config.get("radarr", {}).get("enable"):
                    cls._radarr = RadarrClient()
            except Exception as e:
                logger.error(f"Failed to initialize Radarr: {e}")
                cls._radarr = None
        # Repeat for sonarr, lidarr...

    @property
    def radarr(self):
        return self._radarr

    async def search_movies(self, query: str) -> List[Dict]:
        if not self._radarr:
            return []
        return await self._radarr.search(query)
```

**Key Points:**
- Each client is independently initialized (one failing doesn't block others)
- Properties expose read-only access
- Search methods delegate directly to client
- Returns empty list if client unavailable

## Pre-Instantiated Singletons

Some services export a module-level instance (used in `__init__.py`):

```python
# In src/services/<name>.py
<name>_service = <Name>Service()

# In src/services/__init__.py
from .<name> import <name>_service, <Name>Service
```

Used for services that need shared state (HealthService, TransmissionService). Most services just export the class.

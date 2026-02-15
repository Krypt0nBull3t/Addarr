# Fixture Reference

## Table of Contents

- [Root Fixtures](#root-fixtures)
- [API Fixtures](#api-fixtures)
- [Service Fixtures](#service-fixtures)
- [Handler Fixtures](#handler-fixtures)
- [Sample Data](#sample-data)
- [Config Fixtures](#config-fixtures)

---

## Root Fixtures

Defined in `tests/conftest.py`. Available to all tests.

### reset_singletons (autouse)

Resets all singleton `_instance` attributes after each test:
- `MediaService._instance`, `._radarr`, `._sonarr`, `._lidarr` = None
- `HealthService._instance` = None
- `TranslationService._instance` = None, `._translations` = {}
- `NotificationService._instance` = None, `._bot` = None
- `AuthHandler._authenticated_users` = set()

### mock_translation (autouse)

Patches `TranslationService._load_translations` so tests don't need real YAML files. Does NOT patch `get_text` — tests that call code which uses `get_text` must either:
- Set `_translations` directly, or
- Patch `TranslationService` in the module under test

### mock_config

Returns a fresh `MockConfig()` instance with independent data copy. Use `_set(key, value)` to override values.

```python
def test_custom_language(mock_config):
    mock_config._set("language", "de-de")
    assert mock_config.get("language") == "de-de"
```

### make_user

Factory fixture returning a callable:

```python
user = make_user()                          # Defaults: id=12345, username="testuser"
user = make_user(user_id=99, username="admin", is_bot=True)
```

Returns a `MagicMock` with `.id`, `.username`, `.first_name`, `.last_name`, `.is_bot`.

### make_message

Factory fixture returning a callable:

```python
msg = make_message()                        # Defaults: text="test", chat_id=12345
msg = make_message(text="/start", user=custom_user, chat_id=999)
```

Returns an `AsyncMock` with:
- `.text`, `.photo` (None), `.from_user`, `.chat` (with `.id`, `.title`, `.type`, `.send_message`)
- `.reply_text`, `.edit_text`, `.edit_caption`, `.delete` — all `AsyncMock`

### make_callback_query

Factory fixture returning a callable:

```python
query = make_callback_query(data="menu_movie")
query = make_callback_query(data="select_0", user=custom_user, message=custom_msg)
```

Returns an `AsyncMock` with `.data`, `.from_user`, `.message`, `.answer`, `.edit_message_text`, `.edit_message_caption`.

### make_update

Factory fixture returning a callable. Builds either a text message or callback query update:

```python
# Text message update
update = make_update(text="/start")

# Callback query update
update = make_update(callback_data="menu_movie")

# With custom user
update = make_update(text="search", user=custom_user)
```

Returns `MagicMock` with `.effective_user`, `.message` or `.callback_query`, `.effective_message`.

### make_context

Factory fixture returning a callable:

```python
ctx = make_context()                        # Empty user_data
ctx = make_context(user_data={"search_type": "movie"})
```

Returns `MagicMock` with `.user_data` dict and `.bot` (`AsyncMock` with `.send_message`).

---

## API Fixtures

Defined in `tests/test_api/conftest.py`. Available to `tests/test_api/` tests.

### aio_mock

Yields an `aioresponses()` context manager. Register expected URLs:

```python
async def test_example(aio_mock, radarr_url):
    aio_mock.get(f"{radarr_url}/api/v3/movie/lookup?term=test", payload=[...])
```

### URL Fixtures

- `radarr_url` — `"http://localhost:7878"`
- `sonarr_url` — `"http://localhost:8989"`
- `lidarr_url` — `"http://localhost:8686"`
- `sabnzbd_url` — `"http://localhost:8090"`

### Client Fixtures

Real client instances, safe because the config mock is active:

- `radarr_client` — `RadarrClient()`
- `sonarr_client` — `SonarrClient()`
- `lidarr_client` — `LidarrClient()`
- `sabnzbd_client` — `SabnzbdClient()`

---

## Service Fixtures

Defined in `tests/test_services/conftest.py`. Available to `tests/test_services/` tests.

### mock_radarr_client

`AsyncMock` pre-configured with:
- `search()` -> `[]`
- `get_movie()` -> `None`
- `add_movie()` -> `(True, "Success")`
- `get_root_folders()` -> `["/movies"]`
- `get_quality_profiles()` -> `[{"id": 1, "name": "HD-1080p"}]`
- `check_status()` -> `True`

### mock_sonarr_client

`AsyncMock` pre-configured with:
- `search()` -> `[]`
- `get_series()` -> `None`
- `add_series()` -> `(True, "Success")`
- `get_root_folders()` -> `["/tv"]`
- `get_quality_profiles()` -> `[{"id": 1, "name": "HD-1080p"}]`
- `get_seasons()` -> `[]`
- `check_status()` -> `True`

### mock_lidarr_client

`AsyncMock` pre-configured with:
- `search()` -> `[]`
- `get_artist()` -> `None`
- `add_artist()` -> `(True, "Success")`
- `get_root_folders()` -> `["/music"]`
- `get_quality_profiles()` -> `[{"id": 1, "name": "Lossless"}]`
- `get_metadata_profiles()` -> `[{"id": 1, "name": "Standard"}]`
- `check_status()` -> `True`

---

## Handler Fixtures

Defined in `tests/test_handlers/conftest.py`. Available to `tests/test_handlers/` tests.

### mock_media_service

`MagicMock` with `AsyncMock` methods: `search_movies`, `search_series`, `search_music`, `add_movie`, `add_movie_with_profile`, `add_series`, `add_series_with_profile`, `add_music`, `add_music_with_profile`, `get_radarr_status`, `get_sonarr_status`, `get_lidarr_status`. Also has `.radarr`, `.sonarr`, `.lidarr` as `MagicMock`.

### mock_translation_service

`MagicMock` where `get_text` returns the key (identity function). `current_language = "en-us"`.

### mock_notification_service

`MagicMock` with `AsyncMock` methods: `notify_admin`, `notify_user`, `notify_action`.

---

## Sample Data

Defined in `tests/fixtures/sample_data.py`. Import constants as needed:

```python
from tests.fixtures.sample_data import RADARR_SEARCH_RESULTS
```

| Constant | Type | Description |
|----------|------|-------------|
| `RADARR_SEARCH_RESULTS` | list[dict] | 2 movie results with tmdbId, title, year, etc. |
| `RADARR_MOVIE_DETAIL` | dict | Single movie with full fields |
| `RADARR_ROOT_FOLDERS` | list[dict] | Root folder paths with free space |
| `RADARR_QUALITY_PROFILES` | list[dict] | Quality profiles with id and name |
| `RADARR_SYSTEM_STATUS` | dict | Version and app name |
| `SONARR_SEARCH_RESULTS` | list[dict] | 2 series results |
| `SONARR_SERIES_DETAIL` | dict | Single series with seasons |
| `LIDARR_SEARCH_RESULTS` | list[dict] | 2 artist results |
| `LIDARR_METADATA_PROFILES` | list[dict] | Metadata profiles |
| `TRANSMISSION_SESSION` | dict | Session response with alt-speed-enabled |
| `SABNZBD_QUEUE` | dict | Queue response with slots and speed |

---

## Config Fixtures

Defined in `tests/fixtures/config_fixtures.py`. Factory functions for config variations:

```python
from tests.fixtures.config_fixtures import make_config, make_radarr_config
```

- `make_config(**overrides)` — Full config with overrides merged
- `make_radarr_config(enable=True, **overrides)` — Radarr-specific
- `make_sonarr_config(enable=True, **overrides)` — Sonarr-specific
- `make_lidarr_config(enable=True, **overrides)` — Lidarr-specific
- `make_transmission_config(enable=False, **overrides)` — Transmission-specific
- `make_sabnzbd_config(enable=False, **overrides)` — SABnzbd-specific

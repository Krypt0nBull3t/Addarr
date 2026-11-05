# Fixture Reference

## Table of Contents

- [Root Fixtures](#root-fixtures)
- [API Fixtures](#api-fixtures)
- [Service Fixtures](#service-fixtures)
- [Handler Fixtures](#handler-fixtures)
- [Integration Fixtures](#integration-fixtures)
- [Sample Data](#sample-data)
- [Config Fixtures](#config-fixtures)

---

## Root Fixtures

Defined in `tests/conftest.py`. Available to all tests.

### reset_singletons (autouse)

Resets all singleton `_instance` attributes after each test:
- `TransmissionService._instance`, `SABnzbdService._instance`, `HealthService._instance` = None
- `BazarrService._instance`, `._client` = None, `._config` = {}
- `MediaService._instance`, `._radarr`, `._sonarr`, `._lidarr` = None
- `TranslationService._instance` = None, `._translations` = {}
- `NotificationService._instance` = None, `._bot` = None
- `PreferencesService._instance` = None, `._preferences` = {}
- `RateLimitService._instance` = None, `._records` = {}
- `WebhookService._instance`, `._runner` = None, `._enabled`, `._running` = False
- `AuthHandler._authenticated_users` = set()

> **When adding new singletons:** Reset ALL relevant class vars, not just `_instance`. Singletons often store state beyond the instance reference (e.g., `_preferences = {}`, `_enabled = False`, `_client = None`). If you only reset `_instance = None`, the new instance may inherit stale class-level state from the previous test. Three separate issues (#67, #78, #81) independently discovered this — always audit what class vars your singleton sets during `__new__`/`_initialize` and reset them all.

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

### cleanup_sessions (autouse)

After each test, closes the session of every `radarr_client`, `sonarr_client`, `lidarr_client` and `bazarr_client` the test used. `TransmissionClient` opens a new `aiohttp.ClientSession` per request, so it needs no cleanup.

### aio_mock

Yields an `aioresponses()` context manager. Register expected URLs:

```python
async def test_example(aio_mock):
    aio_mock.get("http://localhost:7878/api/v3/movie/lookup?term=test", payload=[...])
```

### Client Fixtures

Real client instances, safe because the config mock is active:

- `radarr_client`: `RadarrClient()`
- `sonarr_client`: `SonarrClient()`
- `lidarr_client`: `LidarrClient()`
- `bazarr_client`: `BazarrClient()`
- `transmission_client`: `TransmissionClient()` (RPC URL `http://localhost:9091/transmission/rpc`)

SABnzbd has no API client: `SABnzbdService` (`src/services/sabnzbd.py`) makes its own `aiohttp` calls, so there is no SABnzbd URL or client fixture.

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
- `get_calendar()`, `get_movies()`, `get_missing()`, `get_cutoff_unmet()`, `get_queue()`, `get_history()` -> `[]`
- `get_movie_by_id()` -> `None`; `delete_movie()`, `search_command()` -> `True`

### mock_sonarr_client

`AsyncMock` pre-configured with:
- `search()` -> `[]`
- `get_series()` -> `None`
- `add_series()` -> `(True, "Success")`
- `get_root_folders()` -> `["/tv"]`
- `get_quality_profiles()` -> `[{"id": 1, "name": "HD-1080p"}]`
- `get_seasons()` -> `[]`
- `get_calendar()`, `get_all_series()`, `get_missing()`, `get_cutoff_unmet()`, `get_queue()`, `get_history()` -> `[]`
- `get_series_by_id()` -> `None`; `delete_series()`, `search_command()` -> `True`

### mock_lidarr_client

`AsyncMock` pre-configured with:
- `search()` -> `[]`
- `get_artist()` -> `None`
- `add_artist()` -> `(True, "Success")`
- `get_root_folders()` -> `["/music"]`
- `get_quality_profiles()` -> `[{"id": 1, "name": "Lossless"}]`
- `get_metadata_profiles()` -> `[{"id": 1, "name": "Standard"}]`
- `search_albums()`, `get_artists()`, `get_queue()` -> `[]`
- `get_artist_by_id()` -> `None`; `delete_artist()` -> `True`

---

## Handler Fixtures

Defined in `tests/test_handlers/conftest.py`. Available to `tests/test_handlers/` tests.

### mock_media_service

`MagicMock` with `AsyncMock` methods: `search_movies`, `search_series`, `search_music`, `add_movie`, `add_movie_with_profile`, `add_series`, `add_series_with_profile`, `add_music`, `add_music_with_profile`, and the library/wanted/delete methods. Also has `.radarr`, `.sonarr`, `.lidarr` as `MagicMock`.

### mock_translation_service

`MagicMock` where `get_text` and `get_message` return the key (identity function). `current_language = "en-us"`.

### admin_mode

Sets `security.enableAdmin` on and `admins` to `[1]` on `mock_config`, and patches `src.utils.helpers.config` with it. The default test user 12345 is then no admin. Yields the config.

### Handler factory fixtures

Each one patches the handler's services where the handler module imports them, sets `AuthHandler._authenticated_users = {12345}`, and yields the handler. The mocks are on `_mock_*` attributes (for example `handler._mock_service`, `handler._mock_ts`).

`media_handler`, `delete_handler`, `start_handler`, `library_handler`, `system_handler`, `settings_handler`, `calendar_handler`, `missing_handler`, `queue_handler`, `history_handler`, `preferences_handler`

### unchanged_edit

Returns a function that wires a callback query so `query.message.edit_text` raises `BadRequest("Message is not modified: ...")`, as Telegram does for identical text. The function returns a list that records the order of `answer()` and `edit_text()` calls.

---

## Integration Fixtures

Defined in `tests/integration/conftest.py`. Available to `tests/integration/` tests.

- `harness`: a `BotHarness` around a fully wired `Application`; user 12345 is authenticated
- `downloads_harness`: like `harness`, with `TransmissionService.is_enabled` and `SABnzbdService.is_enabled` patched to `True`
- `bazarr_harness`: a harness with `BazarrService.is_enabled` patched to `True` and `bazarr.enable` set in config
- `aio_mock`: `aioresponses()` context manager

---

## Sample Data

Defined in `tests/fixtures/sample_data.py`. Import constants as needed:

```python
from tests.fixtures.sample_data import RADARR_SEARCH_RESULTS
```

| Constant | Type | Description |
|-|-|-|
| `RADARR_SEARCH_RESULTS` | list[dict] | 2 movie results with tmdbId, title, year, etc. |
| `RADARR_MOVIE_DETAIL` | dict | Single movie with full fields |
| `RADARR_QUALITY_PROFILES` | list[dict] | Quality profiles with id and name |
| `RADARR_DISK_SPACE` | list[dict] | Disk space entries with path, label, free and total space |
| `SONARR_SEARCH_RESULTS` | list[dict] | 2 series results |
| `SONARR_SERIES_DETAIL` | dict | Single series with seasons |
| `LIDARR_SEARCH_RESULTS` | list[dict] | 2 artist results |
| `LIDARR_ALBUM_SEARCH_RESULTS` | list[dict] | 2 album results |
| `LIDARR_ALBUM_WITH_TRACKS` | dict | Single album with media (tracks) |
| `LIDARR_METADATA_PROFILES` | list[dict] | Metadata profiles |
| `RADARR_LIBRARY_MOVIES` / `SONARR_LIBRARY_SERIES` / `LIDARR_LIBRARY_ARTISTS` | list[dict] | 2 library items each |
| `RADARR_LIBRARY_MOVIE_DETAIL` / `SONARR_LIBRARY_SERIES_DETAIL` / `LIDARR_LIBRARY_ARTIST_DETAIL` | dict | Single library item with overview and path |
| `RADARR_WANTED_MISSING` / `RADARR_WANTED_CUTOFF` / `SONARR_WANTED_MISSING` / `SONARR_WANTED_CUTOFF` | dict | Paged wanted response (page, pageSize, totalRecords, records) |
| `RADARR_QUEUE` / `SONARR_QUEUE` / `LIDARR_QUEUE` | dict | Paged queue response |
| `RADARR_HISTORY` / `SONARR_HISTORY` | dict | Paged history response |
| `TRANSMISSION_SESSION` | dict | Session response with alt-speed-enabled |

Bazarr responses are in `tests/fixtures/bazarr_data.py` (`from tests.fixtures.bazarr_data import BAZARR_MOVIES`):

| Constant | Type | Description |
|-|-|-|
| `BAZARR_SYSTEM_STATUS` | dict | `data` with Bazarr, Sonarr and Radarr versions |
| `BAZARR_MOVIES` | dict | `data` list of movies with subtitles, and `total` |
| `BAZARR_MOVIES_WANTED` | dict | `data` list of movies missing subtitles, and `total` |
| `BAZARR_EPISODES_WANTED` | dict | `data` list of episodes missing subtitles, and `total` |

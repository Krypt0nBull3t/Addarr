# Addarr Test Suite Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add comprehensive pytest test suite, an addarr-testing skill, and TDD integration to the Addarr Telegram bot.

**Architecture:** Three deliverables — (1) ~45 test files organized by layer with `sys.modules` config injection to bypass import-time `Config()` instantiation, (2) an addarr-testing skill with hub-and-spoke docs, and (3) TDD workflow integration into the existing `/addarr` skill. Tests use `aioresponses` for async HTTP, `unittest.mock` for Telegram objects, and autouse fixtures for singleton reset.

**Tech Stack:** pytest, pytest-asyncio, pytest-cov, pytest-mock, aioresponses, freezegun

---

## Critical Context for Implementer

### The Config Import Problem

`src/config/settings.py:138` runs `config = Config()` at module level. `Config.__init__` reads `config.yaml` from disk and validates against `config_example.yaml`. Every module in `src/` imports `config` — importing ANY source module triggers this chain.

**Solution:** In `tests/conftest.py`, inject a mock `src.config.settings` module into `sys.modules` BEFORE any `src.*` imports. Python checks `sys.modules` first for both absolute and relative imports, so all `from src.config.settings import config` statements (and `from ..config.settings import config` relative equivalents) get the mock.

### Singleton Pattern

`MediaService`, `HealthService`, `TranslationService`, `NotificationService` all use `__new__` + `_instance` class variable. An `autouse=True` fixture resets `_instance = None` before every test.

### Transmission API Uses `requests`, Not `aiohttp`

`src/api/transmission.py` uses synchronous `requests.post()`. Mock with `unittest.mock.patch('requests.post')`, NOT aioresponses.

### Known Bug: `TransmissionAPI(BaseApiClient)` calls `super().__init__()` without `service_name`

`BaseApiClient.__init__` requires `service_name` arg. `TransmissionAPI` passes none. This crashes at runtime (caught by `try/except` in `TransmissionService.client`). Tests should mock `BaseApiClient.__init__` or test around this.

---

## Task 1: Test Infrastructure — Config & Dependencies

> Already partially done: `requirements-test.txt` and `pytest.ini` exist.

**Files:**
- Verify: `requirements-test.txt` (already created)
- Verify: `pytest.ini` (already created)

**Step 1: Install test dependencies**

Run: `pip install -r requirements-test.txt`
Expected: All packages install successfully

**Step 2: Verify pytest discovers test directory**

Run: `pytest --co -q`
Expected: "no tests ran" (no test files yet, but no errors)

**Step 3: Commit**

```bash
git add requirements-test.txt pytest.ini
git commit -m "chore: add test dependencies and pytest config"
```

---

## Task 2: Root conftest.py — Mock Config & Telegram Factories

This is the most critical file. Everything depends on it.

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

**Step 1: Create `tests/__init__.py`**

Empty file (package marker).

**Step 2: Create `tests/conftest.py`**

The conftest MUST:
1. Inject mock `src.config.settings` into `sys.modules` at module level (BEFORE any src imports)
2. Provide `autouse=True` singleton reset fixture
3. Provide Telegram mock factories: `make_user`, `make_message`, `make_callback_query`, `make_update`, `make_context`
4. Provide `mock_translation` autouse fixture

Key config data to mock (mirrors `config_example.yaml` structure):

```python
MOCK_CONFIG = {
    "telegram": {"token": "test-token", "password": "test-pass"},
    "radarr": {
        "enable": True,
        "server": {"addr": "localhost", "port": 7878, "path": "/", "ssl": False},
        "auth": {"apikey": "test-radarr-key", "username": None, "password": None},
        "features": {"search": True, "minimumAvailability": "announced"},
        "paths": {"excludedRootFolders": [], "narrowRootFolderNames": True},
        "quality": {"excludedProfiles": []},
        "tags": {"default": ["telegram"], "addRequesterIdTag": True},
        "adminRestrictions": False,
    },
    "sonarr": {
        "enable": True,
        "server": {"addr": "localhost", "port": 8989, "path": "/", "ssl": False},
        "auth": {"apikey": "test-sonarr-key", "username": None, "password": None},
        "features": {"search": True, "seasonFolder": True},
        "paths": {"excludedRootFolders": [], "narrowRootFolderNames": True},
        "quality": {"excludedProfiles": []},
        "tags": {"default": ["telegram"], "addRequesterIdTag": True},
        "adminRestrictions": False,
    },
    "lidarr": {
        "enable": True,
        "server": {"addr": "localhost", "port": 8686, "path": "/", "ssl": False},
        "auth": {"apikey": "test-lidarr-key", "username": None, "password": None},
        "features": {"search": True, "albumFolder": True, "monitorOption": "all"},
        "paths": {"excludedRootFolders": [], "narrowRootFolderNames": True},
        "quality": {"excludedProfiles": []},
        "tags": {"default": ["telegram"], "addRequesterIdTag": True},
        "adminRestrictions": False,
        "metadataProfileId": 1,
    },
    "transmission": {
        "enable": False, "onlyAdmin": True, "host": "localhost",
        "port": 9091, "authentication": False, "username": None, "password": None,
    },
    "sabnzbd": {
        "enable": False, "onlyAdmin": True,
        "server": {"addr": "localhost", "port": 8090, "path": "/", "ssl": False},
        "auth": {"apikey": "test-sabnzbd-key"},
    },
    "entrypoints": {
        "auth": "auth", "help": "help", "add": "start",
        "allSeries": "allSeries", "allMovies": "allMovies", "allMusic": "allMusic",
        "transmission": "transmission", "sabnzbd": "sabnzbd",
    },
    "security": {"enableAdmin": False, "enableAllowlist": False},
    "language": "en-us",
    "logging": {"toConsole": False, "debug": False, "adminNotifyId": None},
    "admins": [], "allow_list": [], "chat_id": [],
    "authenticated_users": [12345],
    "enableAllowlist": False, "logToConsole": False, "debugLogging": False,
}
```

MockConfig class must implement `__getitem__` and `get` to match the real `Config` API.

Inject into `sys.modules` BEFORE any `from src...` imports:
```python
sys.modules["src.config.settings"] = _settings_mod
```

The `reset_singletons` fixture must reset these class attributes:
- `MediaService._instance`, `._radarr`, `._sonarr`, `._lidarr`
- `HealthService._instance`
- `TranslationService._instance`, `._translations`
- `NotificationService._instance`, `._bot`
- `AuthHandler._authenticated_users`

Telegram mock factories are pytest fixtures returning callables:
- `make_user(user_id=12345, username="testuser", first_name="Test", last_name="User")`
- `make_message(text="test", user=None, chat_id=12345)` — returns `AsyncMock`
- `make_callback_query(data="test", user=None, message=None)` — returns `AsyncMock`
- `make_update(text=None, callback_data=None, user=None)` — builds Update with either message or callback_query
- `make_context(user_data=None)` — returns mock with `user_data` dict and `bot` AsyncMock

**Step 3: Verify conftest loads without error**

Run: `pytest --co -q`
Expected: "no tests ran" with no import errors

**Step 4: Commit**

```bash
git add tests/__init__.py tests/conftest.py
git commit -m "test: add root conftest with config mock and Telegram factories"
```

---

## Task 3: Test Fixtures — Sample Data & Config

**Files:**
- Create: `tests/fixtures/__init__.py`
- Create: `tests/fixtures/config_fixtures.py`
- Create: `tests/fixtures/sample_data.py`

**Step 1: Create `tests/fixtures/__init__.py`**

Empty file.

**Step 2: Create `tests/fixtures/config_fixtures.py`**

Contains factory functions that return config dict variations:
- `make_config(**overrides)` — returns MOCK_CONFIG with overrides merged
- `make_radarr_config(enable=True, **overrides)` — radarr-specific config
- `make_sonarr_config(enable=True, **overrides)` — sonarr-specific config
- `make_lidarr_config(enable=True, **overrides)` — lidarr-specific config
- `make_transmission_config(enable=False, **overrides)` — transmission-specific config
- `make_sabnzbd_config(enable=False, **overrides)` — sabnzbd-specific config

**Step 3: Create `tests/fixtures/sample_data.py`**

Contains realistic API response data as dicts/lists matching real API payloads:

- `RADARR_SEARCH_RESULTS` — list of 2 movie dicts with tmdbId, title, year, overview, images, ratings, genres, studio, status, runtime
- `RADARR_MOVIE_DETAIL` — single movie dict
- `RADARR_ROOT_FOLDERS` — `[{"path": "/movies", "freeSpace": 1000000}]`
- `RADARR_QUALITY_PROFILES` — `[{"id": 1, "name": "HD-1080p", "upgradeAllowed": True}, ...]`
- `RADARR_SYSTEM_STATUS` — `{"version": "5.0.0", "appName": "Radarr"}`
- `SONARR_SEARCH_RESULTS` — list of 2 series dicts with tvdbId, title, seasons, etc.
- `SONARR_SERIES_DETAIL` — single series dict
- `SONARR_SEASONS` — `[{"seasonNumber": 0, "monitored": False}, {"seasonNumber": 1, "monitored": True}]`
- `LIDARR_SEARCH_RESULTS` — list of 2 artist dicts with foreignArtistId, artistName, etc.
- `LIDARR_METADATA_PROFILES` — `[{"id": 1, "name": "Standard"}]`
- `TRANSMISSION_SESSION` — `{"arguments": {"alt-speed-enabled": False, "version": "4.0.0"}, "result": "success"}`
- `SABNZBD_QUEUE` — `{"queue": {"slots": [], "noofslots": 0, "speed": "0 KB/s", "size": "0 MB"}}`

**Step 4: Verify fixture imports work**

Run: `python -c "from tests.fixtures.sample_data import RADARR_SEARCH_RESULTS; print('OK')"`
Expected: `OK`

**Step 5: Commit**

```bash
git add tests/fixtures/
git commit -m "test: add sample data and config fixture factories"
```

---

## Task 4: Smoke Test — Models

Validates the entire test harness works end-to-end.

**Files:**
- Create: `tests/test_models/__init__.py`
- Create: `tests/test_models/test_media.py`
- Create: `tests/test_models/test_notification.py`

**Step 1: Create tests for `src/models/media.py`**

Test file: `tests/test_models/test_media.py`

Tests (all are simple dataclass instantiation + field verification):
- `test_movie_creation` — Movie with all fields, verify `tmdb_id`, `title`, `year`, defaults
- `test_movie_defaults` — Movie with only required fields, verify defaults (`monitored=True`, `minimum_availability="announced"`)
- `test_series_creation` — Series with `tvdb_id`, `season_count`, `monitored_seasons`
- `test_series_defaults` — verify `season_folder=True`
- `test_artist_creation` — Artist with `artist_id`, `artist_type`
- `test_quality_profile` — QualityProfile with `id` and `name`
- `test_root_folder` — RootFolder with `path` and `free_space`
- `test_tag` — Tag with `id` and `label`
- `test_search_result` — SearchResult with `media_type`, `items`, `total_results`, verify `page=1` default

Source: `src/models/media.py` — all are `@dataclass` classes.

**Step 2: Create tests for `src/models/notification.py`**

Test file: `tests/test_models/test_notification.py`

Tests:
- `test_notification_type_enum` — verify all 5 values: INFO, SUCCESS, WARNING, ERROR, ADMIN
- `test_notification_type_values` — verify string values match names
- `test_notification_creation` — Notification with all fields
- `test_notification_defaults` — verify `notify_admin=True`, `parse_mode=ParseMode.HTML`

Note: `from telegram.constants import ParseMode` is needed. This import is safe (telegram library, not our src).

**Step 3: Run tests**

Run: `pytest tests/test_models/ -v`
Expected: All tests pass. This validates the conftest.py config mock works.

**Step 4: Commit**

```bash
git add tests/test_models/
git commit -m "test: add model tests (media, notification) — validates harness"
```

---

## Task 5: Bot Structure Tests — States & Keyboards

**Files:**
- Create: `tests/test_bot/__init__.py`
- Create: `tests/test_bot/test_states.py`
- Create: `tests/test_bot/test_keyboards.py`

**Step 1: Create tests for `src/bot/states.py`**

Test file: `tests/test_bot/test_states.py`

Tests:
- `test_media_states_are_integers` — SEARCHING, SELECTING, QUALITY_SELECT, SEASON_SELECT are ints
- `test_media_states_unique` — all 4 media state values are distinct
- `test_password_state` — PASSWORD == 0
- `test_end_state` — END == "end"
- `test_string_states_are_strings` — AWAITING_DELETE_CONFIRMATION, AWAITING_STATUS_ACTION, etc. are strings

Source: `src/bot/states.py` — simple class with constants.

**Step 2: Create tests for `src/bot/keyboards.py`**

Test file: `tests/test_bot/test_keyboards.py`

Must mock `TranslationService` since keyboards call `TranslationService().get_text(...)`:
```python
@patch("src.bot.keyboards.TranslationService")
def test_get_main_menu_keyboard(mock_ts_class):
    mock_ts = MagicMock()
    mock_ts.get_text.side_effect = lambda key, **kw: key
    mock_ts_class.return_value = mock_ts
    ...
```

Tests:
- `test_main_menu_keyboard_structure` — verify returns `InlineKeyboardMarkup`, has 4 rows, correct callback_data values (`menu_movie`, `menu_series`, `menu_music`, `menu_status`, `menu_help`, `menu_cancel`)
- `test_system_keyboard_returns_none` — `get_system_keyboard()` returns `None`
- `test_settings_keyboard_structure` — 3 rows, correct callback_data patterns (`settings_*`)
- `test_confirmation_keyboard` — `get_confirmation_keyboard("add")` produces `confirm_add` and `confirm_cancel` buttons
- `test_yes_no_keyboard` — `get_yes_no_keyboard("test")` produces `test_yes` and `test_no` buttons
- `test_yes_no_keyboard_custom_text` — custom yes/no text appears on buttons

Source: `src/bot/keyboards.py` — 5 functions.

**Step 3: Run tests**

Run: `pytest tests/test_bot/ -v`
Expected: All pass

**Step 4: Commit**

```bash
git add tests/test_bot/
git commit -m "test: add bot structure tests (states, keyboards)"
```

---

## Task 6: Utility Tests — Pure Functions

**Files:**
- Create: `tests/test_utils/__init__.py`
- Create: `tests/test_utils/test_chat.py`
- Create: `tests/test_utils/test_helpers.py`
- Create: `tests/test_utils/test_validation.py`
- Create: `tests/test_utils/test_error_handler.py`
- Create: `tests/test_utils/test_backup.py`

**Step 1: Create `tests/test_utils/test_chat.py`**

Source: `src/utils/chat.py` — single function `get_chat_name(chat_id, chat_title=None)`

Tests:
- `test_get_chat_name_with_title` — `get_chat_name(123, "My Group")` -> `"My Group (123)"`
- `test_get_chat_name_without_title` — `get_chat_name(123)` -> `"chat 123"`
- `test_get_chat_name_none_title` — `get_chat_name(123, None)` -> `"chat 123"`

**Step 2: Create `tests/test_utils/test_helpers.py`**

Source: `src/utils/helpers.py` — `format_bytes`, `is_admin`, `is_allowed`, `save_chat_id`, `is_authenticated`, `get_authorized_chats`, `get_chat_name` (different from chat.py)

Tests for `format_bytes`:
- `test_format_bytes_bytes` — 500 -> "500.0 B"
- `test_format_bytes_kb` — 1024 -> "1.0 KB"
- `test_format_bytes_mb` — 1048576 -> "1.0 MB"
- `test_format_bytes_gb` — 1073741824 -> "1.0 GB"
- `test_format_bytes_tb` — very large number -> TB format

Tests for `is_admin` (uses file I/O — mock with `tmp_path`):
- `test_is_admin_true` — admin.txt contains the user_id
- `test_is_admin_false` — admin.txt doesn't contain the user_id
- `test_is_admin_no_file` — admin.txt doesn't exist -> False

Tests for `is_allowed` (reads config + allowlist.txt):
- `test_is_allowed_allowlist_disabled` — config `enableAllowlist=False` -> always True
- `test_is_allowed_in_list` — user in allowlist.txt -> True
- `test_is_allowed_not_in_list` — user not in list -> False

Tests for `save_chat_id`:
- `test_save_chat_id_with_name` — appends "123 - TestUser\n" to file
- `test_save_chat_id_without_name` — appends "123\n" to file

Patch `CHATID_PATH`, `ADMIN_PATH`, `ALLOWLIST_PATH` from `src.definitions` to use `tmp_path`.
Patch `src.utils.helpers.config` for `is_allowed` tests.

**Step 3: Create `tests/test_utils/test_validation.py`**

Source: `src/utils/validation.py` — `RequiredValidator`, `TypeValidator`, `RangeValidator`, `validate_data`, `ValidationError`

Tests:
- `test_required_validator_passes` — non-None value passes
- `test_required_validator_fails_none` — None raises `ValidationError`
- `test_required_validator_fails_empty_string` — "" raises `ValidationError`
- `test_type_validator_passes` — correct type passes
- `test_type_validator_fails` — wrong type raises `ValidationError`
- `test_range_validator_passes` — value in range passes
- `test_range_validator_too_low` — below min raises `ValidationError`
- `test_range_validator_too_high` — above max raises `ValidationError`
- `test_range_validator_non_numeric` — string raises `ValidationError`
- `test_validate_data_all_pass` — dict with valid data passes all validators
- `test_validate_data_fails` — dict with invalid data raises `ValidationError`

**Step 4: Create `tests/test_utils/test_error_handler.py`**

Source: `src/utils/error_handler.py` — exceptions + async handlers

Tests:
- `test_addarr_error` — `AddarrError("msg")` has `user_message` attribute
- `test_addarr_error_custom_user_message` — `AddarrError("internal", "user msg")` separates messages
- `test_config_error_inherits` — `ConfigError` is subclass of `AddarrError`
- `test_validation_error_inherits` — `ValidationError` is subclass of `AddarrError`
- `test_service_not_enabled_error` — `ServiceNotEnabledError` is subclass of `AddarrError`
- `test_handle_telegram_error_bad_request` — passes `BadRequest` error, verifies `reply_text` called
- `test_handle_telegram_error_forbidden` — passes `Forbidden` error, verifies `reply_text` called
- `test_handle_telegram_error_unknown` — passes generic `Exception`, verifies `reply_text` called
- `test_handle_telegram_error_no_message` — update with no effective_message, no crash
- `test_send_error_message_text` — message without photo -> `edit_text` called
- `test_send_error_message_photo` — message with photo -> `edit_caption` called
- `test_send_error_message_fallback` — edit fails -> `reply_text` called

Use AsyncMock for telegram objects.

**Step 5: Create `tests/test_utils/test_backup.py`**

Source: `src/utils/backup.py` — `create_backup`, `restore_backup`, `list_backups`

Tests (use `tmp_path` and patch `CONFIG_PATH`):
- `test_create_backup_success` — creates backup file in backup/ dir, returns path
- `test_create_backup_no_source` — source doesn't exist -> returns None
- `test_restore_backup_success` — restores from backup, returns True
- `test_restore_backup_no_file` — backup doesn't exist -> returns False
- `test_list_backups_empty` — no backups -> empty list
- `test_list_backups_sorted` — multiple backups returned in reverse chronological order

Patch `src.utils.backup.CONFIG_PATH` to point to `tmp_path / "config.yaml"`.

**Step 6: Run all util tests**

Run: `pytest tests/test_utils/ -v`
Expected: All pass

**Step 7: Commit**

```bash
git add tests/test_utils/
git commit -m "test: add utility tests (chat, helpers, validation, error_handler, backup)"
```

---

## Task 7: API Tests — conftest + Radarr

Establishes the async/aioresponses pattern for all API tests.

**Files:**
- Create: `tests/test_api/__init__.py`
- Create: `tests/test_api/conftest.py`
- Create: `tests/test_api/test_radarr.py`

**Step 1: Create `tests/test_api/conftest.py`**

Fixtures:
- `aio_mock` — yields `aioresponses()` context manager (session-scoped or function-scoped)
- `radarr_url` — returns `"http://localhost:7878"` (from config)
- `sonarr_url` — returns `"http://localhost:8989"`
- `lidarr_url` — returns `"http://localhost:8686"`
- `sabnzbd_url` — returns `"http://localhost:8090"`
- `radarr_client` — creates `RadarrClient()` (safe because config mock is active)
- `sonarr_client` — creates `SonarrClient()`
- `lidarr_client` — creates `LidarrClient()`

**Step 2: Create `tests/test_api/test_radarr.py`**

Source: `src/api/radarr.py` — `RadarrClient` with `search`, `get_movie`, `add_movie`, `get_root_folders`, `get_quality_profiles`, `check_status`

Note: `RadarrClient.__init__` reads from mock config: `config.get("radarr", {})` -> gets our mock dict. Builds `api_url = "http://localhost:7878"`. Requires `apikey` to be truthy.

Tests (all async, use `aioresponses`):
- `test_search_success` — mock GET `{url}/api/v3/movie/lookup?term=test` -> returns sample data -> verify list returned
- `test_search_no_results` — mock returns None/empty -> verify empty list
- `test_search_connection_error` — mock raises `aiohttp.ClientError` -> verify empty list
- `test_get_movie_success` — mock GET `{url}/api/v3/movie/lookup/tmdb/123` -> returns movie dict
- `test_get_movie_fallback_search` — direct lookup returns None, search with `tmdb:123` returns list
- `test_get_movie_not_found` — both lookups fail -> returns None
- `test_get_root_folders` — mock GET `{url}/api/v3/rootFolder` -> returns list of paths
- `test_get_root_folders_empty` — returns None -> empty list
- `test_get_quality_profiles` — mock GET `{url}/api/v3/qualityProfile` -> returns profile list
- `test_get_quality_profiles_empty` — returns None -> empty list
- `test_add_movie_success` — mock lookup + mock POST `{url}/api/v3/movie` returning `{"id": 1}` -> `(True, "Successfully added...")`
- `test_add_movie_already_exists` — POST returns error array with "already" -> `(False, "...already in your library")`
- `test_add_movie_not_found` — lookup returns empty -> `(False, "Movie not found")`
- `test_check_status_online` — mock GET `{url}/api/v3/system/status` returns data -> True
- `test_check_status_offline` — mock returns error -> False

Pattern for aioresponses:
```python
async def test_search_success(radarr_client, aio_mock, radarr_url):
    from tests.fixtures.sample_data import RADARR_SEARCH_RESULTS
    aio_mock.get(
        f"{radarr_url}/api/v3/movie/lookup?term=test",
        payload=RADARR_SEARCH_RESULTS
    )
    results = await radarr_client.search("test")
    assert len(results) == 2
```

**Step 3: Run tests**

Run: `pytest tests/test_api/test_radarr.py -v`
Expected: All pass

**Step 4: Commit**

```bash
git add tests/test_api/
git commit -m "test: add API test infrastructure and Radarr client tests"
```

---

## Task 8: Remaining API Tests

**Files:**
- Create: `tests/test_api/test_base.py`
- Create: `tests/test_api/test_sonarr.py`
- Create: `tests/test_api/test_lidarr.py`
- Create: `tests/test_api/test_transmission_api.py`
- Create: `tests/test_api/test_sabnzbd_api.py`

**Step 1: Create `tests/test_api/test_base.py`**

Source: `src/api/base.py` — `BaseApiClient` (abstract), `APIError`

Note: BaseApiClient is abstract (has `@abstractmethod search`). Create a concrete subclass for testing:
```python
class ConcreteClient(BaseApiClient):
    def search(self, term):
        return self._make_request(f"search?term={term}")
```

Instantiation requires `service_name` matching a key in mock config (e.g., "radarr").

Tests:
- `test_api_error_attributes` — APIError has message, status_code, response_text
- `test_build_base_url_http` — ssl=False -> `http://...`
- `test_build_base_url_https` — ssl=True -> `https://...`
- `test_get_headers` — returns dict with X-Api-Key and Content-Type
- `test_parse_error_response_json_array` — parses `[{"errorMessage": "msg"}]`
- `test_parse_error_response_already_exists` — "already" in message + title -> `"Title is already in your library"`
- `test_parse_error_response_plain_text` — non-JSON -> returns raw text
- `test_make_request_success` — mock 200 response -> `(True, data, None)`
- `test_make_request_error` — mock 400 response -> `(False, None, error_msg)`
- `test_make_request_connection_error` — mock raises ClientError -> `(False, None, "Connection error: ...")`

**Step 2: Create `tests/test_api/test_sonarr.py`**

Source: `src/api/sonarr.py` — same pattern as Radarr but with `series/lookup`, `tvdb:` prefix, and `get_seasons`

Tests (similar to Radarr, plus):
- `test_search_success` — `series/lookup?term=test`
- `test_get_series_success` — direct lookup + fallback
- `test_get_seasons` — lookup with `tvdb:` prefix, returns seasons array
- `test_get_seasons_empty` — no seasons found
- `test_add_series_success` — with seasons data
- `test_add_series_already_exists` — error with "already"
- `test_check_status` — system/status endpoint

**Step 3: Create `tests/test_api/test_lidarr.py`**

Source: `src/api/lidarr.py` — uses `/api/v1/` (NOT v3!), `artist/lookup`, `foreignArtistId`

Tests (note the v1 URL path):
- `test_search_success` — `{url}/api/v1/artist/lookup?term=test`
- `test_get_artist_lidarr_prefix` — lookup with `lidarr:` prefix
- `test_get_artist_fallback` — fallback to regular search, match by foreignArtistId
- `test_add_artist_success` — POST to `{url}/api/v1/artist`
- `test_add_artist_already_exists` — "already exists" handling
- `test_get_metadata_profiles` — GET `{url}/api/v1/metadataprofile`
- `test_check_status` — `{url}/api/v1/system/status`

**Step 4: Create `tests/test_api/test_transmission_api.py`**

Source: `src/api/transmission.py` — uses `requests.post` (sync!), NOT aiohttp

Note: `TransmissionAPI.__init__` calls `super().__init__()` without args, which will crash because `BaseApiClient.__init__` requires `service_name`. Must patch `BaseApiClient.__init__`:

```python
@patch.object(BaseApiClient, '__init__', lambda self, *a, **kw: None)
def test_something():
    api = TransmissionAPI(host="localhost", port=9091)
    ...
```

Tests (all sync, use `unittest.mock.patch("requests.post")`):
- `test_init` — verify host, port, base_url set correctly
- `test_get_auth_with_credentials` — returns (username, password) tuple
- `test_get_auth_without_credentials` — returns None
- `test_make_request_success` — mock requests.post returns 200 JSON -> returns parsed data
- `test_make_request_session_id_negotiation` — first call returns 409 with session ID header, second succeeds
- `test_make_request_failure` — raises RequestException
- `test_get_session` — calls `_make_request("session-get", {})`
- `test_set_alt_speed_enabled` — calls `_make_request("session-set", {"alt-speed-enabled": True})`
- `test_test_connection_success` — get_session succeeds -> True
- `test_test_connection_failure` — get_session raises -> False

**Step 5: Create `tests/test_api/test_sabnzbd_api.py`**

Source: `src/api/sabnzbd.py` — `SabnzbdClient` with `check_status` only

Tests:
- `test_init_success` — verify api_url and api_key set
- `test_init_missing_addr` — raises ValueError
- `test_init_missing_apikey` — raises ValueError
- `test_check_status_online` — mock GET with apikey in URL returns 200 -> True
- `test_check_status_offline` — mock returns error -> False

**Step 6: Run all API tests**

Run: `pytest tests/test_api/ -v`
Expected: All pass

**Step 7: Commit**

```bash
git add tests/test_api/
git commit -m "test: add API client tests (base, sonarr, lidarr, transmission, sabnzbd)"
```

---

## Task 9: Service Tests

**Files:**
- Create: `tests/test_services/__init__.py`
- Create: `tests/test_services/conftest.py`
- Create: `tests/test_services/test_media_service.py`
- Create: `tests/test_services/test_health_service.py`
- Create: `tests/test_services/test_translation_service.py`
- Create: `tests/test_services/test_transmission_service.py`
- Create: `tests/test_services/test_sabnzbd_service.py`
- Create: `tests/test_services/test_notification_service.py`
- Create: `tests/test_services/test_scheduler.py`

**Step 1: Create `tests/test_services/conftest.py`**

Fixtures:
- `mock_radarr_client` — `AsyncMock(spec=RadarrClient)` with all methods pre-configured
- `mock_sonarr_client` — `AsyncMock(spec=SonarrClient)`
- `mock_lidarr_client` — `AsyncMock(spec=LidarrClient)`
- `media_service_with_mocks` — creates MediaService, injects mock clients via `_radarr`, `_sonarr`, `_lidarr` class attrs

**Step 2: Create `tests/test_services/test_media_service.py`**

Source: `src/services/media.py` — singleton MediaService with search/add for 3 media types

Tests:
- `test_singleton` — two `MediaService()` calls return same instance
- `test_search_movies_success` — mock radarr.search returns data -> formatted results
- `test_search_movies_radarr_disabled` — `_radarr = None` -> raises ValueError
- `test_search_series_success` — mock sonarr.search returns data
- `test_search_music_success` — mock lidarr.search returns data
- `test_add_movie_quality_selection` — mock root_folders + quality_profiles + get_movie -> returns dict with type="quality_selection"
- `test_add_movie_no_root_folders` — empty root_folders -> `(False, "No root folders...")`
- `test_add_movie_with_profile` — mock radarr.add_movie -> success
- `test_add_series_with_seasons` — add_series_with_profile with season data
- `test_get_radarr_status` — mock check_status returns True
- `test_get_radarr_status_disabled` — radarr is None -> False

**Step 3: Create `tests/test_services/test_health_service.py`**

Source: `src/services/health.py` — singleton HealthService with async monitoring

Tests:
- `test_singleton` — two calls return same instance
- `test_check_service_health_success` — mock aiohttp GET returns 200 with version -> `(True, "Online (v...)")`
- `test_check_service_health_connection_error` — mock raises -> `(False, "Error: Connection failed")`
- `test_check_sabnzbd_health_success` — mock GET returns version -> True
- `test_run_health_checks` — mock config with enabled services, mock check methods -> results dict
- `test_get_status` — returns dict with running, last_check, unhealthy_services
- `test_start_stop` — start sets running=True, stop sets running=False

**Step 4: Create `tests/test_services/test_translation_service.py`**

Source: `src/services/translation.py` — singleton, loads YAML files

Tests (mock `_load_translations` to avoid file I/O):
- `test_singleton` — two calls return same instance
- `test_get_text_found` — set `_translations` manually, verify lookup
- `test_get_text_fallback_language` — missing in current lang, found in en-us
- `test_get_text_not_found` — returns the key itself
- `test_get_text_with_format_params` — `"Hello %(name)s"` with `name="World"` -> `"Hello World"`
- `test_get_message_with_subject` — calls get_text for subject translations
- `test_current_language_property` — returns `_current_language`

**Step 5: Create `tests/test_services/test_transmission_service.py`**

Source: `src/services/transmission.py` — TransmissionService with lazy client init

Tests:
- `test_is_enabled_true` — config has `enable: True` -> True
- `test_is_enabled_false` — config has `enable: False` -> False
- `test_client_lazy_init` — accessing `client` property creates TransmissionAPI when enabled
- `test_client_disabled` — accessing `client` when disabled -> None
- `test_set_alt_speed` — mock client, call set_alt_speed(True) -> True
- `test_set_alt_speed_no_client` — client is None -> False
- `test_get_status_connected` — mock client.get_session -> dict with version
- `test_get_status_not_connected` — client raises -> dict with error
- `test_test_connection` — delegates to client.test_connection

**Step 6: Create `tests/test_services/test_sabnzbd_service.py`**

Source: `src/services/sabnzbd.py` — SABnzbdService with async get_status, add_nzb

Tests:
- `test_init_disabled_raises` — sabnzbd not enabled -> ValueError
- `test_init_no_apikey_raises` — missing apikey -> ValueError
- `test_get_status_success` — mock aiohttp GET -> returns dict with active, queued, speed, size
- `test_get_status_error` — mock returns non-200 -> returns zeros dict
- `test_add_nzb_success` — mock GET addurl mode -> True
- `test_add_nzb_with_params` — name and category params passed
- `test_add_nzb_failure` — returns False

Patch config to enable sabnzbd for these tests.

**Step 7: Create `tests/test_services/test_notification_service.py`**

Source: `src/services/notification.py` — singleton, set_bot, notify_admin, notify_user

Tests:
- `test_singleton` — two calls return same instance
- `test_set_bot` — stores bot reference
- `test_notify_admin` — mock bot, verify send_message called with admin chat_id
- `test_notify_admin_no_bot` — no bot set -> no crash
- `test_notify_admin_no_admin_id` — no adminNotifyId -> no crash
- `test_notify_user` — verify send_message called with user chat_id
- `test_notify_action` — verify formatted message sent

**Step 8: Create `tests/test_services/test_scheduler.py`**

Source: `src/services/scheduler.py` — JobScheduler with add/remove/start/stop

Tests (mock `aiocron.crontab`):
- `test_add_job` — job stored in `self.jobs` dict
- `test_add_job_replaces_existing` — same name replaces old job
- `test_remove_job` — removes from dict, calls stop on old job
- `test_remove_nonexistent` — no crash
- `test_start` — sets running=True, calls start on all jobs
- `test_stop` — sets running=False, calls stop on all jobs

**Step 9: Run all service tests**

Run: `pytest tests/test_services/ -v`
Expected: All pass

**Step 10: Commit**

```bash
git add tests/test_services/
git commit -m "test: add service tests (media, health, translation, transmission, sabnzbd, notification, scheduler)"
```

---

## Task 10: Handler Tests

**Files:**
- Create: `tests/test_handlers/__init__.py`
- Create: `tests/test_handlers/conftest.py`
- Create: `tests/test_handlers/test_auth_handler.py`
- Create: `tests/test_handlers/test_media_handler.py`
- Create: `tests/test_handlers/test_start_handler.py`
- Create: `tests/test_handlers/test_help_handler.py`
- Create: `tests/test_handlers/test_delete_handler.py`
- Create: `tests/test_handlers/test_transmission_handler.py`
- Create: `tests/test_handlers/test_sabnzbd_handler.py`
- Create: `tests/test_handlers/test_status_handler.py`
- Create: `tests/test_handlers/test_system_handler.py`

**Step 1: Create `tests/test_handlers/conftest.py`**

Handler tests need service mocks injected. Fixtures:

- `mock_media_service` — MagicMock with async methods, patched as singleton
- `mock_translation_service` — MagicMock where `get_text` returns the key, patched as singleton
- `mock_notification_service` — MagicMock patched as singleton
- `auth_handler` — creates AuthHandler with mocked deps
- `media_handler` — creates MediaHandler with mocked MediaService + TranslationService
- `start_handler` — creates StartHandler
- `help_handler` — creates HelpHandler

Pattern: Patch `MediaService.__new__` to return mock, then create handler:
```python
@pytest.fixture
def media_handler(mock_media_service, mock_translation_service):
    with patch("src.bot.handlers.media.MediaService", return_value=mock_media_service):
        with patch("src.bot.handlers.media.TranslationService", return_value=mock_translation_service):
            handler = MediaHandler()
            handler.media_service = mock_media_service
            handler.translation = mock_translation_service
            return handler
```

**Step 2: Create `tests/test_handlers/test_auth_handler.py`**

Source: `src/bot/handlers/auth.py` — AuthHandler, `require_auth` decorator

Tests:
- `test_require_auth_authenticated` — user ID in `_authenticated_users` -> handler proceeds
- `test_require_auth_not_authenticated` — user ID not in set -> reply_text with auth message, returns None
- `test_require_auth_no_user` — `update.effective_user` is None -> returns None
- `test_is_authenticated_true` — user ID in class set -> True
- `test_is_authenticated_false` — user ID not in set -> False
- `test_start_auth_already_authenticated` — reply with "already allowed", return END
- `test_start_auth_prompts_password` — reply with "Authorize", return PASSWORD state
- `test_check_password_correct` — correct password -> add to set, return END
- `test_check_password_wrong` — wrong password -> reply "Wrong password", return END
- `test_cancel_auth` — reply with "End", return END
- `test_get_handler_returns_conversation_handler` — verify it returns list with ConversationHandler

**Step 3: Create `tests/test_handlers/test_media_handler.py`**

Source: `src/bot/handlers/media.py` — MediaHandler with full conversation flow

Tests:
- `test_handle_movie_sets_search_type` — sets `context.user_data["search_type"] = "movie"`, returns SEARCHING
- `test_handle_series_sets_search_type` — similar for series
- `test_handle_music_sets_search_type` — similar for music
- `test_handle_search_movies` — mock search_movies returns results -> stores in context, returns SELECTING
- `test_handle_search_no_results` — empty results -> reply "No found", returns END
- `test_handle_search_error` — search raises -> reply error, returns END
- `test_handle_selection_cancel` — callback "select_cancel" -> cancels, returns END
- `test_handle_selection_movie` — selects movie, mock add_movie returns quality_selection -> returns QUALITY_SELECT
- `test_handle_quality_selection_cancel` — "quality_cancel" -> cancels
- `test_handle_quality_selection_movie` — selects profile, mock add_movie_with_profile -> success message
- `test_handle_quality_selection_series` — selects profile -> shows season selection -> returns SEASON_SELECT
- `test_handle_menu_callback_cancel` — "menu_cancel" -> cancels
- `test_handle_menu_callback_movie` — "menu_movie" -> sets search type, returns SEARCHING
- `test_cancel_search` — returns END
- `test_get_handler_returns_handlers` — verify returns list with ConversationHandler

**Step 4: Create remaining handler tests**

`tests/test_handlers/test_start_handler.py`:
- `test_show_menu` — reply with main menu keyboard, returns MENU_STATE (1)
- `test_handle_menu_selection_movie` — sets search type, returns SEARCHING
- `test_handle_menu_selection_cancel` — clears user_data, returns END
- `test_handle_menu_selection_status` — delegates to media_handler.handle_status
- `test_handle_menu_selection_help` — delegates to help_handler.show_help

`tests/test_handlers/test_help_handler.py`:
- `test_show_help_command` — reply with help text containing commands
- `test_show_help_callback` — edit_text with help text
- `test_handle_back` — edit_text with main menu keyboard

`tests/test_handlers/test_delete_handler.py`:
- `test_handle_delete` — reply with media type selection keyboard
- `test_handle_delete_selection_cancel` — edit_text with "End"
- `test_handle_delete_selection_type` — shows item list

`tests/test_handlers/test_transmission_handler.py`:
- `test_transmission_not_enabled` — reply with "not enabled" message
- `test_transmission_status` — show status with turtle mode
- `test_handle_toggle_yes` — toggles alt speed
- `test_handle_toggle_no` — keeps current settings

`tests/test_handlers/test_sabnzbd_handler.py`:
- `test_handle_sabnzbd_not_available` — service is None -> reply not enabled
- `test_handle_sabnzbd_shows_keyboard` — shows speed selection
- `test_handle_speed_selection` — sets speed

`tests/test_handlers/test_status_handler.py`:
- `test_handle_status_command` — shows status message
- `test_handle_status_callback` — edit_text with status

`tests/test_handlers/test_system_handler.py`:
- `test_show_status` — reply with system keyboard
- `test_handle_system_action` — processes callback

**Step 5: Run all handler tests**

Run: `pytest tests/test_handlers/ -v`
Expected: All pass

**Step 6: Commit**

```bash
git add tests/test_handlers/
git commit -m "test: add handler tests (auth, media, start, help, delete, transmission, sabnzbd, status, system)"
```

---

## Task 11: Config & Translation Validation Tests

**Files:**
- Create: `tests/test_config/__init__.py`
- Create: `tests/test_config/test_settings.py`
- Create: `tests/test_utils/test_validate_translations.py`

**Step 1: Create `tests/test_config/test_settings.py`**

Source: `src/config/settings.py` — Config class

Test the Config class itself by mocking file I/O:

Tests:
- `test_config_getitem` — `config["telegram"]` returns dict
- `test_config_get` — `config.get("language")` returns "en-us"
- `test_config_get_default` — `config.get("nonexistent", "default")` returns "default"
- `test_config_load_file_not_found` — mock `os.path.exists` returns False -> ConfigurationError
- `test_validate_values_valid_language` — "en-us" passes
- `test_validate_values_invalid_language` — "xx-xx" -> ConfigurationError
- `test_get_missing_keys_none_missing` — identical dicts -> empty list
- `test_get_missing_keys_with_missing` — missing nested key -> returns dotted key path
- `test_configuration_error` — ConfigurationError is Exception subclass

**Step 2: Create `tests/test_utils/test_validate_translations.py`**

Source: `src/utils/validate_translations.py` — standalone script with pure functions

Tests:
- `test_load_yaml_success` — load a temp YAML file -> returns dict
- `test_load_yaml_error` — invalid path -> returns empty dict
- `test_get_all_keys_flat` — `{"a": 1, "b": 2}` -> `["a", "b"]`
- `test_get_all_keys_nested` — `{"a": {"b": 1}}` -> `["a.b"]`
- `test_get_nested_value` — `get_nested_value({"a": {"b": "c"}}, "a.b")` -> `"c"`
- `test_get_nested_value_missing` — missing key -> None
- `test_get_format_placeholders` — `"Hello %{name}"` -> `{"name"}`
- `test_get_format_placeholders_none` — `"Hello"` -> empty set
- `test_validate_translation_missing_keys` — template has keys translation lacks
- `test_validate_translation_extra_keys` — translation has keys template lacks
- `test_check_emoji_consistency` — detects missing emoji in translation

**Step 3: Run tests**

Run: `pytest tests/test_config/ tests/test_utils/test_validate_translations.py -v`
Expected: All pass

**Step 4: Commit**

```bash
git add tests/test_config/ tests/test_utils/test_validate_translations.py
git commit -m "test: add config and translation validation tests"
```

---

## Task 12: CI Integration & CLAUDE.md Update

**Files:**
- Modify: `.github/workflows/ci.yml`
- Modify: `CLAUDE.md`

**Step 1: Add test job to CI**

Add after the existing `lint` job in `.github/workflows/ci.yml`:

```yaml
  test:
    name: Test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - name: Set up Python 3.11
        uses: actions/setup-python@v6
        with:
          python-version: "3.11"
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt -r requirements-test.txt
      - name: Run tests
        run: pytest --cov=src --cov-report=term-missing --tb=short
```

**Step 2: Update CLAUDE.md Commands section**

Add to the `## Commands` section:

```bash
# Run tests
pytest                                    # All tests
pytest --tb=short -q                      # Quick summary
pytest --cov=src --cov-report=term-missing  # With coverage
pytest -k "test_name"                     # Specific test
pytest tests/test_api/                    # Specific directory
pytest -x                                 # Stop on first failure
```

Add to CLAUDE.md a new `## Testing` section documenting key patterns (singleton reset, config mock, Telegram factories).

**Step 3: Run full test suite**

Run: `pytest --cov=src --cov-report=term-missing --tb=short`
Expected: All tests pass, coverage >= 85%

**Step 4: Run flake8 on tests**

Run: `flake8 tests/`
Expected: Clean (no lint errors)

**Step 5: Commit**

```bash
git add .github/workflows/ci.yml CLAUDE.md
git commit -m "ci: add pytest job to CI pipeline, update CLAUDE.md with test docs"
```

---

## Task 13: Addarr Testing Skill

**Files:**
- Create: `.claude/skills/addarr-testing/SKILL.md`
- Create: `.claude/skills/addarr-testing/references/patterns.md`
- Create: `.claude/skills/addarr-testing/references/fixtures.md`
- Create: `.claude/skills/addarr-testing/references/anti-patterns.md`

**Step 1: Create SKILL.md**

Hub document (~200 lines) with:
- Frontmatter: `name: addarr-testing`, `description: Use when writing tests for Addarr...`
- Quick start commands
- Fixture cheat sheet (table)
- Layer quick reference (2-3 lines each + link to patterns.md)
- Common mistakes quick ref (one-liners + link to anti-patterns.md)
- Cross-references to superpowers:test-driven-development and python-testing-pro

**Step 2: Create references/patterns.md**

~300 lines with TOC. One section per layer with concrete Addarr example:
- API clients: aioresponses + URL matching
- Services: mock client injection into singletons
- Handlers: make_update factory, state transitions, @require_auth
- Config: overriding config per-test
- Keyboards: asserting on InlineKeyboardMarkup
- Translations: identity-function mock

**Step 3: Create references/fixtures.md**

~200 lines with TOC. Every fixture documented:
- Root (singleton reset, mock config, Telegram factories)
- API (aioresponses, base URLs, client instances)
- Services (mock clients)
- Handlers (pre-built handlers)
- Sample data

**Step 4: Create references/anti-patterns.md**

~100 lines. Each pitfall has "why" and "instead":
- Don't import src at test module level
- Don't forget to patch config at every import site
- Don't create real aiohttp.ClientSession
- Don't skip singleton reset
- Don't use requests_mock for Transmission
- Don't test translation text literally

**Step 5: Commit**

```bash
git add .claude/skills/addarr-testing/
git commit -m "feat: add addarr-testing skill with patterns, fixtures, anti-patterns docs"
```

---

## Task 14: TDD Integration into Addarr Workflow

**Files:**
- Modify: `.claude/skills/addarr-workflow/SKILL.md`
- Modify: `.claude/skills/addarr-workflow/references/new-task.md`
- Modify: `.claude/skills/addarr-workflow/references/preflight.md`
- Modify: `.claude/skills/addarr-workflow/references/create-pr.md`

**Step 1: Update SKILL.md**

Add after the `## Flows` section:

```markdown
## Development Approach

TDD is the default. Reference @superpowers:test-driven-development for the red-green-refactor cycle and @addarr-testing for project-specific test patterns.
```

**Step 2: Update new-task.md**

In section `## 4. Plan`, add:
> Include test file locations and what tests to write for each implementation step.

Replace section `## 5. Execute` with TDD cycle:
1. Write failing test (RED) — use @addarr-testing patterns
2. Run test, verify it fails for the right reason
3. Write minimal implementation (GREEN)
4. Run `pytest` — verify pass + no regressions
5. Refactor if needed
6. Repeat

**Step 3: Update preflight.md**

Add as check #1 (before Flake8):

```markdown
### 1. Tests

\`\`\`bash
pytest --tb=short -q
\`\`\`

If failures found: report which tests failed and offer to investigate.
```

Renumber existing checks (Flake8 becomes #2, Translations #3, Docker #4).

**Step 4: Update create-pr.md**

In section `## 1. Preflight`, add:
> All tests must pass. Run `pytest --cov=src --cov-report=term-missing` and verify no regressions.

**Step 5: Commit**

```bash
git add .claude/skills/addarr-workflow/
git commit -m "feat: integrate TDD into addarr-workflow skill"
```

---

## Final Verification

Run these commands to verify everything works:

```bash
# 1. Dependencies
pip install -r requirements-test.txt

# 2. All tests pass
pytest --tb=short -q

# 3. Coverage check
pytest --cov=src --cov-report=term-missing

# 4. Lint check
flake8 tests/

# 5. Full CI simulation
flake8 . && pytest --cov=src --cov-report=term-missing --tb=short
```

Expected final state:
- All tests pass
- Coverage >= 85%
- No flake8 errors in test files
- CI workflow includes pytest job
- addarr-testing skill has 4 files
- addarr-workflow skill updated with TDD references

# Add Missing Integration Tests for All Handler Flows

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add happy-path integration tests for every handler registered in conftest.py's `_register_handlers()`, plus missing handlers (History, Bazarr, Webhooks), and at least one error-path test per conversation flow.

**Architecture:** Each test file follows the existing pattern — use the `harness` fixture to send commands/callbacks, mock service methods on the singleton instances, and assert on `BotResponse` text/method. Three handlers (History, Bazarr, Webhooks) need to be added to conftest's `_register_handlers()` first. Settings tests need `is_admin` patched.

**Tech Stack:** pytest-asyncio, unittest.mock (AsyncMock, patch), BotHarness infrastructure from `tests/integration/conftest.py`

---

## Pre-Work: Update conftest to register missing handlers

The integration test `_register_handlers()` in `tests/integration/conftest.py` is missing three handlers that `main.py` registers: `HistoryHandler`, `BazarrHandler`, and `WebhooksHandler`. These must be added before writing tests for them.

### Conftest Registration Gap Analysis

| Handler | In main.py | In conftest.py | Needs Adding |
|---------|-----------|---------------|-------------|
| HistoryHandler | Yes | No | Yes (always) |
| WebhooksHandler | Yes | No | Yes (always) |
| BazarrHandler | Yes (conditional) | No | Yes (conditional, like transmission/sabnzbd) |

---

## Phase 1: Infrastructure — Register Missing Handlers in Conftest

### Task 1.1: Add HistoryHandler and WebhooksHandler to conftest

**Files:**
- Modify: `tests/integration/conftest.py:19-32` (imports), `tests/integration/conftest.py:313-346` (_register_handlers)

**Changes:**
1. Add imports for `HistoryHandler` and `WebhooksHandler`
2. Add both to the `handler_classes` list in `_register_handlers()` — `HistoryHandler` after `QueueHandler`, `WebhooksHandler` after `SettingsHandler` (matching main.py order)

**Import additions:**
```python
from src.bot.handlers.history import HistoryHandler
from src.bot.handlers.webhooks import WebhooksHandler
```

**Registration order (matching main.py):**
```python
handler_classes = [
    StartHandler,
    AuthHandler,
    MediaHandler,
    SettingsHandler,
    WebhooksHandler,      # NEW
    DeleteHandler,
    LibraryHandler,
    CalendarHandler,
    MissingHandler,
    QueueHandler,
    HistoryHandler,        # NEW
    HelpHandler,
    PreferencesHandler,
    SystemHandler,
]
```

### Task 1.2: Add BazarrHandler (conditional) to conftest

**Files:**
- Modify: `tests/integration/conftest.py` (imports and _register_handlers)

**Changes:**
1. Add import for `BazarrHandler` and `BazarrService`
2. Add conditional registration block (like transmission/sabnzbd)

```python
from src.bot.handlers.bazarr import BazarrHandler
from src.services.bazarr import BazarrService
```

In `_register_handlers()`, after the sabnzbd conditional block:
```python
if config.get("bazarr", {}).get("enable", False):
    handler_classes.append(BazarrHandler)
```

3. Add a `bazarr_harness` fixture that patches `BazarrService.is_enabled` to return True and enables bazarr in config:

```python
@pytest.fixture
async def bazarr_harness():
    """Provide a BotHarness with Bazarr handler enabled."""
    AuthHandler._authenticated_users.add(12345)
    with patch.object(BazarrService, "is_enabled", return_value=True):
        app = _build_application()
        async for h in _make_harness(app):
            yield h
```

**Verification:** Run existing tests to confirm nothing breaks: `pytest tests/integration/ --tb=short -q`

---

## Phase 2: Simple Command Tests (no conversation state)

### Task 2.1: Help handler integration test

**File:** `tests/integration/test_help_flow.py`

**Test: `/help` returns help text**
- Send `/help` command via harness
- Assert response is `sendMessage` with non-empty text

**Test: `menu_back` returns to main menu**
- Tap `menu_back` callback
- Assert response contains text (welcome message)

**Mock needs:** None (help reads config which is already mocked)

### Task 2.2: System/Status handler integration test

**File:** `tests/integration/test_system_flow.py`

**Test: `/status` shows system status**
- Mock `health_service.get_status()` to return `{"running": True, "last_check": None, "unhealthy_services": []}`
- Send `/status`
- Assert response contains "System Status" or similar text

**Test: `system_refresh` re-runs health checks**
- Mock `health_service.run_health_checks()` returning `{"media_services": [], "download_clients": []}`
- Mock `health_service.get_status()` returning status dict
- Send `/status`, then tap `system_refresh`
- Assert response is not None

**Test: `system_details` shows service details**
- Mock `health_service.run_health_checks()` returning service details
- Send `/status`, then tap `system_details`
- Assert response text

**Test: `system_diskspace` shows disk info**
- Mock `health_service.get_disk_space()` returning drive list
- Send `/status`, then tap `system_diskspace`
- Assert response text

**Test: `system_back` returns to main menu**
- Send `/status`, then tap `system_back`
- Assert response text contains "Main Menu"

**Mock target:** `src.services.health.health_service` — it's a module-level singleton, so patch its methods with `patch.object()`

### Task 2.3: Preferences handler integration test

**File:** `tests/integration/test_preferences_flow.py`

**Test: `/preferences` shows current view mode**
- Mock `PreferencesService.get_view_mode` returning `"list"`
- Send `/preferences`
- Assert response contains "Preferences" or "List View"

**Test: `pref_toggle_view` toggles view mode**
- Mock `PreferencesService.get_view_mode` returning `"list"`
- Mock `PreferencesService.toggle_view_mode` returning `"card"`
- Send `/preferences`, then tap `pref_toggle_view`
- Assert response contains "Card View"

**Mock target:** `PreferencesService` methods via `patch.object()`

### Task 2.4: History handler integration test

**File:** `tests/integration/test_history_flow.py`

**Test: `/history` shows history items**
- Mock `MediaService.get_history` returning a list of items
- Send `/history`
- Assert response contains history text

**Test: `/history` with empty results**
- Mock `MediaService.get_history` returning `[]`
- Send `/history`
- Assert response contains "HistoryEmpty" text

**Test: `hist_refresh` re-fetches history**
- Mock `MediaService.get_history` returning items
- Send `/history`, then tap `hist_refresh`
- Assert response is not None

**Test: `hist_back` returns to main menu**
- Send `/history` (with mocked empty results), then tap `hist_back`
- Assert response text contains "Main Menu"

**Mock target:** `MediaService.get_history` via `patch.object()`

**Fixture data to add to `tests/integration/fixtures.py`:**
```python
HISTORY_ITEMS = [
    {
        "id": 1,
        "title": "Fight Club",
        "event_type": "grabbed",
        "date": "2026-03-01",
        "type": "movie",
    },
]
```

---

## Phase 3: Callback-Driven Flow Tests

### Task 3.1: Delete handler integration test

**File:** `tests/integration/test_delete_flow.py`

**Test: `/delete` → type selection → item list → confirm → success**
- Mock `MediaService.get_movies` returning `[{"id": "1", "title": "Fight Club"}]`
- Mock `MediaService.get_movie` returning `{"id": "1", "title": "Fight Club"}`
- Mock `MediaService.delete_movie` returning `True`
- Send `/delete`
- Assert response shows type selection buttons
- Tap `delete_type_movie`
- Assert response shows item list
- Tap `delete_item_1`
- Assert response shows confirmation
- Tap `delete_confirm`
- Assert response contains success text

**Test: `/delete` → cancel**
- Send `/delete`
- Tap `delete_cancel`
- Assert response contains "End" text

**Test: `/delete` → type with empty library**
- Mock `MediaService.get_movies` returning `[]`
- Send `/delete`, tap `delete_type_movie`
- Assert response mentions no items

**Mock target:** `MediaService` methods via `patch.object()`

### Task 3.2: Library handler integration test

**File:** `tests/integration/test_library_flow.py`

**Test: `/allMovies` shows paginated list**
- Mock `MediaService.get_movies` returning 15 items (to test pagination)
- Send `/allMovies`
- Assert response contains movie titles and page info

**Test: `/allSeries` shows series list**
- Mock `MediaService.get_series` returning items
- Send `/allSeries`
- Assert response text

**Test: Pagination via `lib_m_1`**
- Mock `MediaService.get_movies` returning 15 items
- Send `/allMovies`, then tap `lib_m_1`
- Assert response shows page 2

**Test: Empty library**
- Mock `MediaService.get_movies` returning `[]`
- Send `/allMovies`
- Assert response contains "LibraryEmpty" text

**Fixture data:**
```python
LIBRARY_MOVIES = [{"id": str(i), "title": f"Movie {i:02d}"} for i in range(15)]
LIBRARY_SERIES = [{"id": str(i), "title": f"Series {i:02d}"} for i in range(3)]
```

### Task 3.3: Calendar handler integration test

**File:** `tests/integration/test_calendar_flow.py`

**Test: `/upcoming` shows calendar items**
- Mock `MediaService.get_upcoming` returning items
- Send `/upcoming`
- Assert response contains calendar text

**Test: `/upcoming` with no items**
- Mock `MediaService.get_upcoming` returning `[]`
- Send `/upcoming`
- Assert response contains "CalendarEmpty" text

**Test: `cal_period_30` changes period**
- Mock `MediaService.get_upcoming` (called twice)
- Send `/upcoming`, then tap `cal_period_30`
- Assert response text

**Test: `cal_refresh` re-fetches**
- Mock `MediaService.get_upcoming`
- Send `/upcoming`, then tap `cal_refresh`
- Assert response

**Test: `cal_back` returns to main menu**
- Mock `MediaService.get_upcoming` returning `[]`
- Send `/upcoming`, then tap `cal_back`
- Assert "Main Menu"

**Fixture data:**
```python
CALENDAR_ITEMS = [
    {
        "title": "Upcoming Movie",
        "type": "movie",
        "id": "123",
        "date": "2026-03-15",
    },
]
```

### Task 3.4: Missing handler integration test

**File:** `tests/integration/test_missing_flow.py`

**Test: `/missing` shows wanted items**
- Mock `MediaService.get_missing_media` returning items
- Send `/missing`
- Assert response contains wanted count

**Test: `/missing` with no items**
- Mock `MediaService.get_missing_media` returning `[]`
- Send `/missing`
- Assert "MissingEmpty" text

**Test: `missing_refresh` re-fetches**
- Mock `MediaService.get_missing_media`
- Send `/missing`, then tap `missing_refresh`
- Assert response

**Test: `missing_back` returns to main menu**
- Mock `MediaService.get_missing_media` returning `[]`
- Send `/missing`, then tap `missing_back`
- Assert "Main Menu"

**Fixture data:**
```python
MISSING_ITEMS = [
    {
        "title": "Missing Movie",
        "type": "movie",
        "id": 1,
        "service": "radarr",
    },
]
```

### Task 3.5: Queue handler integration test

**File:** `tests/integration/test_queue_flow.py`

**Test: `/queue` shows queue items**
- Mock `MediaService.get_queue_media` returning items
- Send `/queue`
- Assert response contains queue text

**Test: `/queue` with empty queue**
- Mock `MediaService.get_queue_media` returning `[]`
- Send `/queue`
- Assert "QueueEmpty" text

**Test: `queue_refresh` re-fetches**
- Mock `MediaService.get_queue_media`
- Send `/queue`, then tap `queue_refresh`
- Assert response

**Test: `queue_back` returns to main menu**
- Mock `MediaService.get_queue_media` returning `[]`
- Send `/queue`, then tap `queue_back`
- Assert "Main Menu"

**Fixture data:**
```python
QUEUE_ITEMS = [
    {
        "title": "Downloading Movie",
        "type": "movie",
        "id": 1,
        "progress": 45.0,
        "status": "downloading",
    },
]
```

---

## Phase 4: Conversation Flow Tests

### Task 4.1: Settings handler integration test (admin flow)

**File:** `tests/integration/test_settings_flow.py`

**Test: `/settings` as admin shows settings menu**
- Patch `src.bot.handlers.settings.is_admin` returning `True`
- Patch `src.bot.handlers.settings.config.update_nested` and `config.save` as no-ops
- Send `/settings`
- Assert response contains "Settings"
- Assert conversation state is `States.SETTINGS_MENU`

**Test: `/settings` as non-admin gets rejected**
- Patch `src.bot.handlers.settings.is_admin` returning `False`
- Send `/settings`
- Assert response contains "admin" text

**Test: Settings → language → select language → back to settings**
- Patch `is_admin` True
- Send `/settings`, tap `settings_language`, tap `lang_en`
- Assert response contains "Language" confirmation

**Test: Settings → back ends conversation**
- Patch `is_admin` True
- Send `/settings`, tap `settings_back`
- Assert conversation ended

**Mock targets:**
- `src.bot.handlers.settings.is_admin` via `patch()`
- `src.bot.handlers.settings.config.update_nested` and `config.save` as no-ops

### Task 4.2: Bazarr handler integration test

**File:** `tests/integration/test_bazarr_flow.py`

Uses `bazarr_harness` fixture (from Task 1.2).

**Test: `/subtitles` shows menu when enabled**
- Send `/subtitles`
- Assert response contains "BazarrMenu" text

**Test: `/subtitles` when disabled shows error**
- Use regular `harness` (Bazarr not enabled)
- Send `/subtitles`
- Assert response contains "BazarrNotEnabled" text

**Test: Wanted movies flow**
- Mock `BazarrService.get_wanted_movies` returning items
- Send `/subtitles`, then tap `bazarr_wanted_movies`
- Assert response text

**Test: Bazarr cancel**
- Send `/subtitles`, then tap `bazarr_cancel`
- Assert response contains "BazarrCancelled" text

**Fixture data:**
```python
BAZARR_WANTED_MOVIES = [
    {
        "title": "Fight Club",
        "missing_subtitles": [{"name": "English"}],
    },
]
```

---

## Phase 5: Error Path Tests

### Task 5.1: Error paths for media conversation

**File:** `tests/integration/test_error_paths.py`

**Test: Movie search succeeds but add fails**
- Mock `MediaService.search_movies` returning results
- Mock `MediaService.add_movie` raising an exception
- Send `/movie`, type search, select result
- Assert response contains error text (not a crash)

**Test: Series search API failure**
- Mock `MediaService.search_series` raising `Exception("API timeout")`
- Send `/series`, type search
- Assert response contains error text

**Test: Delete confirmation fails**
- Mock all delete steps but `delete_movie` returns `False`
- Walk through full flow
- Assert response contains failure text

---

## Phase 6: Auth Gating Expansion

### Task 6.1: Verify auth gating on all commands

**File:** `tests/integration/test_auth_gating.py` (extend existing)

**Tests:** Parametrize unauthenticated access for all protected commands:
```python
@pytest.mark.parametrize("command", [
    "/help", "/settings", "/delete", "/allMovies", "/allSeries",
    "/allMusic", "/upcoming", "/missing", "/queue", "/preferences",
    "/status", "/history",
])
```

For each: discard auth user, send command, assert response mentions "auth".

**Note:** Some commands (like `/settings`) have admin checks ON TOP of auth. The auth check happens first (via `@require_auth` decorator), so the parametrized test is still valid.

---

## Verification

After all phases:
1. `pytest tests/integration/ --tb=short -v` — all pass
2. `pytest tests/integration/ --cov=src.bot.handlers --cov-report=term-missing` — confirm coverage improvement
3. Count: every handler in conftest's `_register_handlers()` has at least one happy-path test

## Test File Summary

| File | Handler | Tests |
|------|---------|-------|
| test_help_flow.py | HelpHandler | 2 |
| test_system_flow.py | SystemHandler | 5 |
| test_preferences_flow.py | PreferencesHandler | 2 |
| test_history_flow.py | HistoryHandler | 4 |
| test_delete_flow.py | DeleteHandler | 3 |
| test_library_flow.py | LibraryHandler | 4 |
| test_calendar_flow.py | CalendarHandler | 5 |
| test_missing_flow.py | MissingHandler | 4 |
| test_queue_flow.py | QueueHandler | 4 |
| test_settings_flow.py | SettingsHandler | 4 |
| test_bazarr_flow.py | BazarrHandler | 4 |
| test_error_paths.py | Various | 3 |
| test_auth_gating.py | Various (extend) | 1 parametrized (12 cases) |
| **Total** | | **~45 tests** |

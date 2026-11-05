# Issue #106: Download Queue Command (`/queue`)

**Branch:** `feature/106-download-queue-command`
**Plan:** [plan.md](plan.md)

---

### Phase 1: API & Service Layer (2 tasks)

**Goal:** Add `get_queue()` to all three API clients and aggregate in MediaService.

- [x] **1.1** Add `get_queue()` to Radarr, Sonarr, and Lidarr API clients
    - **Context:**
        - **Why:** The *arr APIs expose `GET /queue` with download progress data — we need client methods to fetch it
        - **Architecture:** Identical pattern to `get_missing()` on each client — call `_request()`, extract `records` from paginated response, return `[]` on error
        - **Key refs:** `src/api/radarr.py:196-214` (`get_missing`), `src/api/sonarr.py:202-220`, `src/api/lidarr.py` (has `API_VERSION = "v1"` not v3)
        - **Watch out:** Sonarr sort key is `series.title` not `title`. Lidarr uses v1 API but `_request()` handles that automatically via `self.API_VERSION`
    - **Scope:** 3 `get_queue()` methods, sample data fixtures, API client tests
    - **Touches:** `src/api/radarr.py`, `src/api/sonarr.py`, `src/api/lidarr.py`, `tests/fixtures/sample_data.py`, `tests/test_api/test_radarr.py`, `tests/test_api/test_sonarr.py`, `tests/test_api/test_lidarr.py`
    - **Action items:**
        - [RED] Add `RADARR_QUEUE`, `SONARR_QUEUE`, `LIDARR_QUEUE` sample data to `tests/fixtures/sample_data.py`
        - [RED] Write 4 tests for `RadarrClient.get_queue()` — success, empty, connection error, exception (mirror `TestRadarrGetMissing` at test_radarr.py:762)
        - [RED] Write 4 tests for `SonarrClient.get_queue()` — same pattern (mirror `TestSonarrGetMissing` at test_sonarr.py:744)
        - [RED] Write 4 tests for `LidarrClient.get_queue()` — same pattern (check existing Lidarr test file for BASE URL constant)
        - [GREEN] Implement `RadarrClient.get_queue()` after `get_missing()` at radarr.py:214
        - [GREEN] Implement `SonarrClient.get_queue()` after `get_missing()` at sonarr.py:220
        - [GREEN] Implement `LidarrClient.get_queue()` at end of LidarrClient class
    - **Success:** All 12 new API tests pass, `pytest tests/test_api/ --tb=short -q` green
    - **Completed:** 2026-03-04
    - **Learnings:**
        - Sonarr queue sort key is `series.title` (matches existing `get_missing` pattern)
        - Lidarr v1 API handles identically via `self.API_VERSION` — no special casing needed
    - **Key Changes:**
        - Added `get_queue()` to `RadarrClient`, `SonarrClient`, `LidarrClient`
        - Added `RADARR_QUEUE`, `SONARR_QUEUE`, `LIDARR_QUEUE` fixtures to `sample_data.py`
        - 12 new tests across 3 API test files
    - **Notes:** All 3 methods follow identical pattern to `get_missing()` — paginated response, extract `records`

- [x] **1.2** Add `get_queue_media()` and queue normalizers to MediaService
    - **Context:**
        - **Why:** Need to aggregate queue data from all enabled services into a unified, sorted list
        - **Architecture:** Three static normalizers (`_normalize_radarr_queue`, `_normalize_sonarr_queue`, `_normalize_lidarr_queue`) plus `get_queue_media()` aggregator. Queue schema extends the missing schema with `status`, `progress`, `timeleft`, `protocol`, `download_client` fields
        - **Key refs:** `src/services/media.py:624-661` (`_fetch_wanted_media` pattern), `src/services/media.py:677-706` (normalizer pattern)
        - **Watch out:** Progress calculation: `round((1 - sizeleft / size) * 100)` — guard against `size == 0` (default to 0%). Lidarr queue items don't have nested `movie`/`series` objects like Radarr/Sonarr do. Unlike `_fetch_wanted_media`, queue includes Lidarr (3 services not 2)
    - **Scope:** 3 normalizers, 1 aggregation method, normalizer tests, aggregation tests, mock fixture update
    - **Touches:** `src/services/media.py`, `tests/test_services/test_media_service.py`, `tests/test_handlers/conftest.py`
    - **Action items:**
        - [RED] Write 6 normalizer tests — 2 per service (standard item + missing fields) mirroring `TestNormalizeRadarrMissing` at test_media_service.py:1952
        - [RED] Write 5 aggregation tests — all services, radarr-only, no services, one errors, lidarr included (mirror `TestGetMissingMedia` at test_media_service.py:2020)
        - [GREEN] Implement 3 normalizer static methods after `_normalize_sonarr_missing` at media.py:706
        - [GREEN] Implement `get_queue_media()` after normalizers
        - [GREEN] Add `service.get_queue_media = AsyncMock(return_value=[])` to `mock_media_service` in `tests/test_handlers/conftest.py:39`
    - **Success:** All 11 new service tests pass, `pytest tests/test_services/test_media_service.py --tb=short -q` green
    - **Completed:** 2026-03-04
    - **Learnings:**
        - Progress calculation needs `size == 0` guard (default to 0%) — Lidarr sometimes sends 0-size items
        - Lidarr queue items have flat structure (no nested `movie`/`series` objects), title comes from `title` field directly
        - Queue aggregation includes all 3 services (unlike `_fetch_wanted_media` which only does radarr+sonarr)
    - **Key Changes:**
        - Added `_normalize_radarr_queue`, `_normalize_sonarr_queue`, `_normalize_lidarr_queue` static methods to `MediaService`
        - Added `get_queue_media()` aggregator using `asyncio.gather()` across enabled services
        - Updated `mock_media_service` and mock client fixtures with `get_queue` / `get_queue_media` mocks
        - 11 new tests (6 normalizer + 5 aggregation)
    - **Notes:** Queue schema extends missing schema with: status, progress, timeleft, protocol, download_client

---

### Phase 2: Handler & Keyboards (1 task)

**Goal:** Create the QueueHandler and keyboard builders for the Telegram UI.

- [x] **2.1** Implement QueueHandler and queue keyboard builders
    - **Context:**
        - **Why:** Users need a `/queue` command with filter tabs, pagination, and refresh — the Telegram UI layer
        - **Architecture:** Callback-driven handler (no ConversationHandler/states). `CommandHandler("queue")` + `CallbackQueryHandler(pattern="^queue_")`. Filter/page/refresh cached in `context.user_data`. Keyboard builders in `src/bot/keyboards.py`
        - **Key refs:** `src/bot/handlers/missing.py` (entire file — mirror this), `src/bot/keyboards.py:600-708` (missing keyboards to mirror), `tests/test_handlers/test_missing_handler.py` (test pattern to mirror), `tests/test_handlers/conftest.py:402-435` (`missing_handler` fixture to mirror)
        - **Watch out:** Update `_MEDIA_TYPE_EMOJI` dict to include `"album"` type. Item display differs from missing — show progress/time status line instead of "Search Now" button. Filter tabs are All/Movies/Series/Music (not Cutoff). `_handle_filter` for "all" re-fetches; other filters are local-only
    - **Scope:** New handler file, keyboard functions, handler fixture, handler tests
    - **Touches:** `src/bot/handlers/queue.py` (new), `src/bot/keyboards.py`, `tests/test_handlers/test_queue_handler.py` (new), `tests/test_handlers/conftest.py`
    - **Action items:**
        - [RED] Add `queue_handler` fixture to `tests/test_handlers/conftest.py` (mirror `missing_handler` fixture)
        - [RED] Write ~14 handler tests in `tests/test_handlers/test_queue_handler.py`:
            - show_queue: with results, empty, via callback, no user (4 tests)
            - filter: movie, episode, album, all re-fetch (4 tests)
            - navigation: page change, refresh, back to menu, noop callback (4 tests)
            - edge: no callback query, get_handler structure (2 tests)
        - [GREEN] Add `"album": "\U0001f3b5"` to `_MEDIA_TYPE_EMOJI` in keyboards.py
        - [GREEN] Implement `get_queue_empty_keyboard()` in keyboards.py (mirror `get_missing_empty_keyboard`)
        - [GREEN] Implement `_build_queue_filter_row()` in keyboards.py — tabs: All/Movies/Series/Music
        - [GREEN] Implement `get_queue_items_keyboard()` in keyboards.py — items show status line (progress %, timeleft, protocol) instead of search button
        - [GREEN] Create `src/bot/handlers/queue.py` with QueueHandler class (mirror missing.py structure)
    - **Success:** All ~14 handler tests pass, `pytest tests/test_handlers/test_queue_handler.py --tb=short -q` green
    - **Completed:** 2026-03-04
    - **Learnings:**
        - Callback-driven handler (no ConversationHandler) is simpler — just CommandHandler + CallbackQueryHandler
        - `_build_response` needs `active_filter` parameter passed through for keyboard rendering
        - `_MEDIA_TYPE_EMOJI` extraction to module constant avoids duplication across keyboard functions
    - **Key Changes:**
        - Created `src/bot/handlers/queue.py` with full QueueHandler class
        - Added `get_queue_empty_keyboard()`, `get_queue_items_keyboard()`, `_build_queue_filter_row()` to keyboards.py
        - Added `"album": "\U0001f3b5"` to `_MEDIA_TYPE_EMOJI`
        - Added `queue_handler` fixture to handler conftest
        - 14 handler tests in `test_queue_handler.py`
    - **Notes:** Filter tabs are All/Movies/Series/Music; "all" re-fetches from API, others filter locally

---

### Phase 3: Integration (1 task)

**Goal:** Wire QueueHandler into the bot and add translation keys.

- [x] **3.1** Register QueueHandler, add `/queue` command, and translation keys
    - **Context:**
        - **Why:** Handler exists but isn't registered — needs wiring into bot startup, command menu, and i18n
        - **Architecture:** Import + 3-line registration block in `main.py`, conditional command in `commands.py` (show if ANY *arr service enabled), flat translation keys in all 9 locale files
        - **Key refs:** `src/main.py:18` (MissingHandler import), `src/main.py:142-145` (Missing registration block), `src/bot/commands.py:57-59` (missing command conditional), `translations/addarr.en-us.yml:244-252` (missing keys section)
        - **Watch out:** Handler registration order matters — insert after MissingHandler, before Transmission. Command condition: `radarr OR sonarr OR lidarr` (3-way, not 2-way like missing). Translation validation must pass for all 9 files. Check if `tests/test_bot/test_main.py` has handler count assertions
    - **Scope:** Import + registration, command entry, 9 translation files, possible test update
    - **Touches:** `src/main.py`, `src/bot/commands.py`, `translations/addarr.*.yml` (9 files), possibly `tests/test_bot/test_main.py`
    - **Action items:**
        - [RED] Check `tests/test_bot/test_main.py` for handler count assertions — update if needed
        - [GREEN] Add `from src.bot.handlers.queue import QueueHandler` to main.py imports
        - [GREEN] Add QueueHandler registration block after MissingHandler in `_add_handlers()`
        - [GREEN] Add `/queue` command to `build_authenticated_commands()` in commands.py (3-way OR condition)
        - [GREEN] Add `Queue`, `CommandQueue`, `QueueTitle`, `QueueEmpty` keys to all 9 translation files
        - [GREEN] Run `PYTHONIOENCODING=utf-8 python run.py --validate-i18n` to verify
    - **Success:** Full test suite passes, i18n validation passes, `pytest --tb=short -q` green
    - **Completed:** 2026-03-04
    - **Learnings:**
        - Queue command condition is 3-way OR (radarr OR sonarr OR lidarr), not 2-way like missing/upcoming
        - `test_commands.py` had count assertions for individual services that also needed updating (4 tests, not just `test_all_services_enabled`)
        - `test_main.py` handler counts: each mock handler class returns `[MagicMock()]` so adding QueueHandler adds 1 to each count
    - **Key Changes:**
        - Added `QueueHandler` import and registration block in `src/main.py` (after MissingHandler, before Transmission)
        - Added `/queue` command with 3-way OR condition in `src/bot/commands.py`
        - Added `Queue`, `CommandQueue`, `QueueTitle`, `QueueEmpty` keys to all 9 locale files + template
        - Updated handler count assertions in `tests/test_main.py` (11→12, 12→13, 13→14)
        - Updated command count assertions in `tests/test_bot/test_commands.py` (4 tests)
    - **Notes:** All 1589 tests pass, all 9 translations valid

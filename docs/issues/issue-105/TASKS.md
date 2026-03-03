# Issue #105: Missing/Wanted Media Command (`/missing`)

**Plan:** [plan.md](plan.md)
**Branch:** `feature/105-missing-wanted-command`
**Issue:** https://github.com/Krypt0nBull3t/Addarr/issues/105

---

### Phase 1: API Client Extensions (2 tasks)

**Goal:** Add `get_missing()`, `get_cutoff_unmet()`, and `search_command()` to both RadarrClient and SonarrClient.

- [x] **1.1** Add missing/cutoff/search methods to RadarrClient
    - **Context:**
        - **Why:** Radarr exposes `GET /api/v3/wanted/missing` and `GET /api/v3/wanted/cutoff` for tracking wanted media, plus `POST /api/v3/command` for triggering manual searches. No client methods exist for these yet.
        - **Architecture:** Follow existing method patterns in `RadarrClient` — use `self._request()` for GETs (returns data or None), `self._make_request()` for POSTs (returns `(success, data, error)` tuple). The wanted endpoints return paginated `{"page":N, "pageSize":N, "totalRecords":N, "records":[...]}` — we request `pageSize=1000` and extract `records`.
        - **Key refs:** `src/api/radarr.py:196-211` (`get_calendar` as pattern), `src/api/base.py:47` (`_make_request` signature), `tests/test_api/test_radarr.py:75-114` (test patterns), `tests/fixtures/sample_data.py` (test data constants)
        - **Watch out:** Response is a dict with `records` key (not a bare list like `search()`). Must check `isinstance(result, dict)` before accessing `.get("records")`. The `search_command` POST returns status 201 on success.
    - **Scope:** Three new methods on RadarrClient + sample data constants + tests
    - **Touches:** `src/api/radarr.py`, `tests/test_api/test_radarr.py`, `tests/fixtures/sample_data.py`
    - **Action items:**
        - [RED] Add `RADARR_WANTED_MISSING` and `RADARR_WANTED_CUTOFF` sample data to `tests/fixtures/sample_data.py`
        - [RED] Write tests for `get_missing()`: success (2 records), empty (0 records), connection error, exception
        - [RED] Write tests for `get_cutoff_unmet()`: success, empty, connection error, exception
        - [RED] Write tests for `search_command()`: success (POST 201), failure (POST error), exception
        - [GREEN] Implement `get_missing()` in `RadarrClient`
        - [GREEN] Implement `get_cutoff_unmet()` in `RadarrClient`
        - [GREEN] Implement `search_command()` in `RadarrClient`
    - **Success:** `python -m pytest tests/test_api/test_radarr.py -v` all pass, `python -m flake8 src/api/radarr.py` clean

- [x] **1.2** Add missing/cutoff/search methods to SonarrClient
    - **Context:**
        - **Why:** Sonarr has the same `wanted/missing`, `wanted/cutoff`, and `command` endpoints. Sonarr returns *episodes* (not series), so each record has `seriesId`, `seasonNumber`, `episodeNumber`, `title`, and a nested `series` object.
        - **Architecture:** Identical pattern to RadarrClient methods. The only differences: Sonarr sort key is `series.title` instead of `title`, and the search command is `{"name": "EpisodeSearch", "episodeIds": [id]}` instead of `MoviesSearch`.
        - **Key refs:** `src/api/sonarr.py:202-217` (`get_calendar` as pattern), `tests/test_api/test_sonarr.py` (test patterns), Radarr implementation from task 1.1 as template
        - **Watch out:** Sonarr wanted/missing sort key is `series.title` (dot notation). The `EpisodeSearch` command takes `episodeIds` (plural with `s`), not `episodeId`.
    - **Scope:** Three new methods on SonarrClient + sample data constants + tests
    - **Touches:** `src/api/sonarr.py`, `tests/test_api/test_sonarr.py`, `tests/fixtures/sample_data.py`
    - **Action items:**
        - [RED] Add `SONARR_WANTED_MISSING` and `SONARR_WANTED_CUTOFF` sample data to `tests/fixtures/sample_data.py`
        - [RED] Write tests for `get_missing()`: success, empty, connection error, exception
        - [RED] Write tests for `get_cutoff_unmet()`: success, empty, connection error, exception
        - [RED] Write tests for `search_command()`: success, failure, exception
        - [GREEN] Implement `get_missing()` in `SonarrClient`
        - [GREEN] Implement `get_cutoff_unmet()` in `SonarrClient`
        - [GREEN] Implement `search_command()` in `SonarrClient`
    - **Success:** `python -m pytest tests/test_api/test_sonarr.py -v` all pass, `python -m flake8 src/api/sonarr.py` clean

---

### Phase 2: Service Layer (1 task)

**Goal:** Add aggregation methods to MediaService that merge results from Radarr and Sonarr, normalize them, and dispatch search commands.

- [x] **2.1** Add missing media aggregation and search trigger to MediaService
    - **Context:**
        - **Why:** The handler needs a single call to get all missing media across services, normalized into a unified schema. It also needs a way to trigger a search for a specific item without knowing which service it came from.
        - **Architecture:** Follow the `get_upcoming()` pattern in `MediaService` (lines 515-554): build task list from enabled services, `asyncio.gather` with `return_exceptions=True`, normalize per-service results, sort, return. Add static `_normalize_radarr_missing()` and `_normalize_sonarr_missing()` methods following the existing `_normalize_radarr_calendar()` pattern.
        - **Key refs:** `src/services/media.py:515-608` (`get_upcoming` + normalizers as template), `tests/test_services/conftest.py` (mock client fixtures), `tests/test_services/test_media.py` (existing service tests)
        - **Watch out:** Sonarr returns episodes, not series — the `internal_id` is the episode ID (for search dispatch), but the display title comes from the nested `series` object. Must tag each item with `"service": "radarr"|"sonarr"` so the handler can route search commands correctly. Update `mock_radarr_client` and `mock_sonarr_client` fixtures with `get_missing`, `get_cutoff_unmet`, `search_command` methods.
    - **Scope:** Three service methods (`get_missing_media`, `get_cutoff_unmet_media`, `trigger_missing_search`) + two static normalizers + fixture updates + tests
    - **Touches:** `src/services/media.py`, `tests/test_services/test_media.py`, `tests/test_services/conftest.py`
    - **Action items:**
        - [RED] Update `mock_radarr_client` and `mock_sonarr_client` in `tests/test_services/conftest.py` with `get_missing`, `get_cutoff_unmet`, `search_command` async mocks
        - [RED] Write tests for `get_missing_media()`: both services return data (merged + sorted), radarr-only, sonarr-only, no services enabled, one service errors
        - [RED] Write tests for `_normalize_radarr_missing()`: standard movie, missing fields
        - [RED] Write tests for `_normalize_sonarr_missing()`: episode with full info, missing season/episode
        - [RED] Write tests for `get_cutoff_unmet_media()`: both services, one service only, errors
        - [RED] Write tests for `trigger_missing_search()`: radarr dispatch, sonarr dispatch, unavailable service, exception
        - [GREEN] Implement `_normalize_radarr_missing()` and `_normalize_sonarr_missing()` static methods
        - [GREEN] Implement `get_missing_media()`
        - [GREEN] Implement `get_cutoff_unmet_media()`
        - [GREEN] Implement `trigger_missing_search()`
    - **Success:** `python -m pytest tests/test_services/test_media.py -v` all pass, `python -m flake8 src/services/media.py` clean
    - **Completed:** 2026-03-03
    - **Learnings:**
        - Extracted `_fetch_wanted_media(method, label)` to DRY `get_missing_media` and `get_cutoff_unmet_media` — they differ only in which client method to call
        - Sonarr missing `internal_id` is the episode ID (not series ID) — critical for search dispatch routing
        - `trigger_missing_search` uses dict lookup `{"radarr": self.radarr, "sonarr": self.sonarr}.get(service)` for clean dispatch
    - **Key Changes:**
        - `src/services/media.py`: Added `get_missing_media()`, `get_cutoff_unmet_media()`, `_fetch_wanted_media()`, `trigger_missing_search()`, `_normalize_radarr_missing()`, `_normalize_sonarr_missing()`
        - `tests/test_services/test_media_service.py`: 16 new tests across 5 test classes (normalizers, missing, cutoff, search)
        - `tests/test_services/conftest.py`: Added `get_missing`, `get_cutoff_unmet`, `search_command` to mock clients
    - **Notes:** 100% coverage on `src/services/media.py`

---

### Phase 3: Handler & Keyboards (1 task)

**Goal:** Create MissingHandler with `/missing` command, filter tabs, pagination, "Search Now" action, and the keyboard builders that support it.

- [ ] **3.1** Implement MissingHandler and keyboard builders
    - **Context:**
        - **Why:** Users need a Telegram UI to browse missing/wanted media, filter by type, page through results, and trigger manual searches per item.
        - **Architecture:** Follow CalendarHandler pattern exactly (see `src/bot/handlers/calendar.py`): callback-driven (no ConversationHandler states), cache items in `context.user_data["missing_items"]`, filter state in `context.user_data["missing_filter"]`, stateless pagination via callback data. Keyboard builder follows `get_calendar_items_keyboard()` pattern with filter tabs at top, item+action buttons, pagination, refresh/back at bottom. All callbacks use `missing_` prefix.
        - **Key refs:** `src/bot/handlers/calendar.py` (full reference implementation), `src/bot/keyboards.py:519-595` (`get_calendar_items_keyboard` for pagination pattern), `tests/test_handlers/conftest.py:349-396` (calendar handler fixture as template), `tests/test_handlers/test_calendar_handler.py` (test patterns)
        - **Watch out:** The `@require_auth` decorator is on both `show_missing` and `handle_missing_action` (same as calendar). The `_handle_search` callback parses `missing_search_{service}_{id}` — 4 parts split by `_`, where parts[2] is service and parts[3] is ID. The first `query.answer("Searching...")` is non-blocking feedback; the second `query.answer(result, show_alert=True)` shows a popup.
    - **Scope:** New `MissingHandler` class, two keyboard builders (`get_missing_items_keyboard`, `get_missing_empty_keyboard`), handler test fixture, full test coverage
    - **Touches:** `src/bot/handlers/missing.py` (create), `src/bot/keyboards.py`, `tests/test_handlers/conftest.py`, `tests/test_handlers/test_missing_handler.py` (create)
    - **Action items:**
        - [RED] Add `missing_handler` fixture to `tests/test_handlers/conftest.py` (patch MediaService, TranslationService, keyboard builders)
        - [RED] Write handler tests: show_missing with results, empty, via callback, no user
        - [RED] Write filter tests: filter_movie, filter_series, filter_cutoff, filter_all
        - [RED] Write navigation tests: page change, refresh, back to menu, noop callback
        - [RED] Write search tests: search success, search failure
        - [GREEN] Implement `get_missing_items_keyboard()` and `get_missing_empty_keyboard()` in `keyboards.py`
        - [GREEN] Implement `MissingHandler` class in `src/bot/handlers/missing.py`
    - **Success:** `python -m pytest tests/test_handlers/test_missing_handler.py -v` all pass, `python -m flake8 src/bot/handlers/missing.py src/bot/keyboards.py` clean

---

### Phase 4: Integration & Registration (1 task)

**Goal:** Wire MissingHandler into the bot, register the `/missing` command, add translation keys, and verify everything works end-to-end.

- [ ] **4.1** Register handler, command, translations, and update test fixtures
    - **Context:**
        - **Why:** The handler exists but isn't connected to the bot application, the `/missing` command isn't in Telegram's command menu, and translation keys are missing.
        - **Architecture:** Handler registration follows the pattern in `src/main.py:103-170` — import, instantiate, iterate `get_handler()`, call `add_handler()`. Command registration follows `src/bot/commands.py:57-58` — conditional on Radarr/Sonarr enabled. Translation keys are flat top-level (not nested) per the `TranslationService.get_text()` single-level lookup convention.
        - **Key refs:** `src/main.py:136-139` (CalendarHandler registration — insert after this), `src/bot/commands.py:57-58` (upcoming command conditional — add similar block), `translations/addarr.en-us.yml:226-242` (calendar keys as naming pattern), `tests/test_handlers/conftest.py:13-42` (`mock_media_service` — needs new method mocks)
        - **Watch out:** Handler registration ORDER matters — add MissingHandler after CalendarHandler and before Transmission. The `mock_media_service` fixture in `tests/test_handlers/conftest.py` must include `get_missing_media`, `get_cutoff_unmet_media`, and `trigger_missing_search` or other handler tests that use this fixture may break. All 9 translation files need the same keys (use English as placeholder for non-English).
    - **Scope:** 4 integration points: main.py wiring, commands.py registration, translation files, test fixture updates
    - **Touches:** `src/main.py`, `src/bot/commands.py`, `translations/addarr.*.yml` (all 9 files), `tests/test_handlers/conftest.py`
    - **Action items:**
        - [GREEN] Add `get_missing_media`, `get_cutoff_unmet_media`, `trigger_missing_search` to `mock_media_service` in `tests/test_handlers/conftest.py`
        - [GREEN] Import and register `MissingHandler` in `src/main.py` after CalendarHandler
        - [GREEN] Add `BotCommand("missing", ...)` to `build_authenticated_commands()` in `src/bot/commands.py`
        - [GREEN] Add 11 translation keys to all 9 `translations/addarr.*.yml` files
        - [GREEN] Run full test suite to verify no regressions
        - [GREEN] Run `python -m flake8 .` to verify lint
        - [GREEN] Run `PYTHONIOENCODING=utf-8 python run.py --validate-i18n` to verify translations
    - **Success:** Full test suite passes, flake8 clean, i18n validation passes, architecture tests pass (handler convention auto-discovers `missing.py` and verifies `get_handler()` exists)

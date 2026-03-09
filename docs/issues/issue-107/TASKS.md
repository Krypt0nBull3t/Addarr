# Issue #107: Download History Command (`/history`)

**Goal:** Add a `/history` command showing recent grab/import/fail activity from Radarr and Sonarr with event type filtering and pagination.

**Plan:** See `plan.md` for full design, API schemas, and code templates.

---

### Phase 1: API + Service Layer (2 tasks)

**Goal:** Add `get_history()` to API clients and MediaService with normalization.

- [x] **1.1** Add `get_history()` to RadarrClient and SonarrClient
    - **Context:** See plan.md Phase 1. Key refs: `src/api/radarr.py:196` (`get_missing` as pattern template), `src/api/sonarr.py:202` (same pattern). Both use paginated `?sortKey=date&sortDirection=descending` endpoints returning `{"records": [...]}`.
    - **Watch out:** Event type filter is optional query param `&eventType=grabbed`. Response shape matches missing/queue (paginated dict with `records` key).
    - **Scope:** `get_history(page, page_size, event_type)` on both clients + sample data fixtures
    - **Touches:** `src/api/radarr.py`, `src/api/sonarr.py`, `tests/fixtures/sample_data.py`, `tests/test_api/test_radarr.py`, `tests/test_api/test_sonarr.py`
    - **Action items:**
        - [RED] Add `RADARR_HISTORY` and `SONARR_HISTORY` sample data to `tests/fixtures/sample_data.py`
        - [RED] Write tests for Radarr `get_history` (success, with filter, empty, error, non-dict response)
        - [RED] Write tests for Sonarr `get_history` (mirror Radarr tests)
        - [GREEN] Implement `get_history()` on RadarrClient
        - [GREEN] Implement `get_history()` on SonarrClient
    - **Success:** `pytest tests/test_api/test_radarr.py tests/test_api/test_sonarr.py -v` passes, new methods have 100% coverage
    - **Completed:** 2026-03-09
    - **Learnings:** History endpoint follows exact same pattern as get_missing/get_queue — paginated dict with `records` key. Optional `eventType` query param appended when provided.
    - **Key Changes:** Added `get_history(page, page_size, event_type)` to `RadarrClient` and `SonarrClient`, added `RADARR_HISTORY` and `SONARR_HISTORY` sample data, added 10 tests (5 per client).
    - **Notes:** Both clients have identical method signatures and logic, differing only in log messages.

- [x] **1.2** Add `get_history()` to MediaService with normalizers
    - **Context:** See plan.md Phase 2. Key refs: `src/services/media.py:532` (`get_upcoming` as pattern — gather, normalize, sort). Normalized schema includes `type`, `title`, `episode_title`, `season`, `episode`, `date`, `event_type`, `quality`, `source_title`, `service`.
    - **Watch out:** Sort by date descending (newest first), unlike `get_upcoming` which sorts ascending. Exception from one service should not block the other.
    - **Scope:** `get_history()` method + `_normalize_radarr_history` and `_normalize_sonarr_history` statics
    - **Touches:** `src/services/media.py`, `tests/test_services/test_media_service.py`
    - **Action items:**
        - [RED] Write tests: both services return items (merged + sorted desc), radarr-only, sonarr-only, no services, one exception, event_type passthrough, normalizer unit tests
        - [GREEN] Implement `get_history()` and both normalizer statics
    - **Success:** `pytest tests/test_services/test_media_service.py -v` passes, new methods have 100% coverage
    - **Completed:** 2026-03-09
    - **Learnings:** Follows get_upcoming pattern exactly — gather, normalize, sort. Only difference is descending sort and no date computation.
    - **Key Changes:** Added `get_history()`, `_normalize_radarr_history()`, `_normalize_sonarr_history()` to MediaService. Added `get_history` to mock client fixtures. Added 8 tests.
    - **Notes:** Also added `get_history = AsyncMock(return_value=[])` to both `mock_radarr_client` and `mock_sonarr_client` fixtures in conftest.

---

### Phase 2: UI Layer (3 tasks)

**Goal:** Add translation keys, keyboard functions, and the handler.

- [x] **2.1** Add history translation keys to all locales
    - **Context:** See plan.md Phase 3. Key refs: `translations/addarr.en-us.yml:273` (Queue section — add after it). Flat top-level keys only (no nesting). Must add to all 10 locale files + template.
    - **Watch out:** Use `PYTHONIOENCODING=utf-8` when validating. Keep emoji prefixes consistent across locales.
    - **Scope:** 8 new keys: `History`, `CommandHistory`, `HistoryTitle`, `HistoryEmpty`, `HistoryGrabbed`, `HistoryImported`, `HistoryFailed`, `HistoryAll`
    - **Touches:** All files in `translations/` (10 locales + template)
    - **Action items:**
        - [GREEN] Add English keys to `addarr.en-us.yml`
        - [GREEN] Add translated keys to all other locale files
        - [GREEN] Add keys to `addarr.template.yml`
    - **Success:** `PYTHONIOENCODING=utf-8 python run.py --validate-i18n` passes
    - **Completed:** 2026-03-09
    - **Learnings:** All locale files have a consistent structure — QueueEmpty is always followed by a blank line then handler error section.
    - **Key Changes:** Added 8 keys (History, CommandHistory, HistoryTitle, HistoryEmpty, HistoryGrabbed, HistoryImported, HistoryFailed, HistoryAll) to all 10 locale files + template.
    - **Notes:** Keys placed after Queue section, before handler error messages section.

- [x] **2.2** Add history keyboard functions to `keyboards.py`
    - **Context:** See plan.md Phase 4. Key refs: `src/bot/keyboards.py` (follow `get_calendar_items_keyboard` pattern). Callback data prefix: `hist_`. Filter tabs row + item rows + pagination + action row.
    - **Watch out:** `_HISTORY_EVENT_EMOJI` dict for event type icons. Title truncation at 30 chars. Filter tab bullet prefix for active filter.
    - **Scope:** `get_history_items_keyboard()` and `get_history_empty_keyboard()` + event emoji mapping
    - **Touches:** `src/bot/keyboards.py`, `tests/test_bot/test_keyboards.py`
    - **Action items:**
        - [RED] Write tests: items keyboard with items (pagination present), empty items, active filter highlight, empty keyboard buttons
        - [GREEN] Implement `_HISTORY_EVENT_EMOJI`, `get_history_items_keyboard()`, `get_history_empty_keyboard()`
    - **Success:** `pytest tests/test_bot/test_keyboards.py -v` passes, new functions have 100% coverage
    - **Completed:** 2026-03-09
    - **Learnings:** Need separate tests for title truncation (>30 chars) and Previous button (page > 0) to hit 100% coverage.
    - **Key Changes:** Added `_HISTORY_EVENT_EMOJI`, `get_history_items_keyboard()`, `get_history_empty_keyboard()` to keyboards.py. Added 6 tests.
    - **Notes:** Filter tabs use `\u2022` bullet prefix for active filter. Items use `hist_noop` callback since they're display-only.

- [ ] **2.3** Create HistoryHandler and register in main.py
    - **Context:** See plan.md Phase 5+6. Key refs: `src/bot/handlers/calendar.py` (exact pattern to follow), `src/main.py:149` (registration after QueueHandler). Handler uses `context.user_data` for `hist_items`, `hist_page`, `hist_filter`.
    - **Watch out:** `@require_auth` on both `show_history` and `handle_history_action`. Add `history_handler` fixture to `tests/test_handlers/conftest.py`. Add `("history", "CommandHistory")` to `src/bot/commands.py`. Add `HistoryHandler` to `src/bot/handlers/__init__.py`.
    - **Scope:** Full handler class + registration + fixture + tests
    - **Touches:** `src/bot/handlers/history.py` (create), `src/main.py`, `src/bot/commands.py`, `src/bot/handlers/__init__.py`, `tests/test_handlers/conftest.py`, `tests/test_handlers/test_history_handler.py` (create)
    - **Action items:**
        - [RED] Add `history_handler` fixture to conftest
        - [RED] Write handler tests: show with results, show empty, show via callback, no user, filter grabbed, filter all, page navigation, refresh, back, noop
        - [GREEN] Create `src/bot/handlers/history.py` with HistoryHandler
        - [GREEN] Register handler in `main.py` after QueueHandler
        - [GREEN] Add command to `src/bot/commands.py`
        - [GREEN] Add to `src/bot/handlers/__init__.py`
    - **Success:** `pytest tests/test_handlers/test_history_handler.py -v` passes, full test suite green, `flake8` clean

# Issue #162: Add Missing Integration Tests for All Handler Flows

**Source:** [plan.md](plan.md)
**Branch:** `test/162-add-missing-integration-tests`

---

### Phase 1: Infrastructure — Register Missing Handlers (1 task)

**Goal:** Ensure conftest registers all handlers that main.py does, so integration tests can cover them.

- [x] **1.1** Register HistoryHandler, WebhooksHandler, and BazarrHandler in integration conftest
    - **Context:** See plan.md Phase 1. Key refs: `tests/integration/conftest.py:313-346` (_register_handlers), `src/main.py:120-200` (handler registration order)
    - **Watch out:** Handler registration order matters — match main.py. BazarrHandler is conditional (like transmission/sabnzbd). Need a `bazarr_harness` fixture with `BazarrService.is_enabled` patched.
    - **Scope:** Add imports, update handler list, add bazarr_harness fixture
    - **Touches:** `tests/integration/conftest.py`
    - **Action items:**
        - [GREEN] Add imports for HistoryHandler, WebhooksHandler, BazarrHandler, BazarrService
        - [GREEN] Add WebhooksHandler and HistoryHandler to handler_classes list (matching main.py order)
        - [GREEN] Add conditional BazarrHandler registration block
        - [GREEN] Add `bazarr_harness` fixture
        - [GREEN] Run existing tests to verify nothing breaks
    - **Success:** `pytest tests/integration/ --tb=short -q` — all existing tests still pass
    - **Completed:** 2026-03-10
    - **Learnings:** Imports were already present in conftest but handlers weren't in the list. Handler order also needed fixing — Help/Preferences/System come after Downloads in main.py.
    - **Key Changes:** Updated `_register_handlers()` in `tests/integration/conftest.py` — added WebhooksHandler, HistoryHandler to list, conditional BazarrHandler block, reordered Help/Preferences/System after Downloads, added `bazarr_harness` fixture.
    - **Notes:** `bazarr_harness` uses a wrapping mock on `config.get` to return `{"enable": True}` for the "bazarr" key during handler registration.

---

### Phase 2: Simple Command Tests (4 tasks)

**Goal:** Happy-path integration tests for handlers that respond to a single command without complex conversation state.

- [x] **2.1** Help handler integration test
    - **Context:** See plan.md Task 2.1. Key refs: `src/bot/handlers/help.py` — `/help` command, `menu_back` callback
    - **Watch out:** No service mocks needed — help reads config (already mocked in conftest)
    - **Scope:** `/help` response, `menu_back` callback
    - **Touches:** `tests/integration/test_help_flow.py` (new)
    - **Action items:**
        - [RED] Write test: `/help` returns sendMessage with non-empty text
        - [RED] Write test: `menu_back` callback returns response
        - [GREEN] Run tests — should pass immediately (no implementation needed, just verifying harness works)
    - **Success:** `pytest tests/integration/test_help_flow.py -v` — 2 tests pass
    - **Completed:** 2026-03-10
    - **Learnings:** No mocks needed — harness conftest already mocks config and translations.
    - **Key Changes:** Created `tests/integration/test_help_flow.py` with 2 tests.
    - **Notes:** None.

- [x] **2.2** System/Status handler integration test
    - **Context:** See plan.md Task 2.2. Key refs: `src/bot/handlers/system.py` — `/status` command, `system_refresh`, `system_details`, `system_diskspace`, `system_back` callbacks. Uses module-level `health_service` singleton from `src.services.health`.
    - **Watch out:** Mock `health_service` methods via `patch.object()` on the imported singleton. `get_status()` is sync, `run_health_checks()` and `get_disk_space()` are async.
    - **Scope:** `/status` command + 4 callback actions
    - **Touches:** `tests/integration/test_system_flow.py` (new)
    - **Action items:**
        - [RED] Write test: `/status` shows system status text
        - [RED] Write test: `system_refresh` re-runs checks
        - [RED] Write test: `system_details` shows service details
        - [RED] Write test: `system_diskspace` shows disk info
        - [RED] Write test: `system_back` returns to main menu
        - [GREEN] Run tests — should pass with correct mocks
    - **Success:** `pytest tests/integration/test_system_flow.py -v` — 5 tests pass
    - **Completed:** 2026-03-10
    - **Learnings:** Callback handlers produce multiple API calls (editMessageText + answerCallbackQuery), so need a `_find_response` helper to locate the edit call specifically.
    - **Key Changes:** Created `tests/integration/test_system_flow.py` with 5 tests.
    - **Notes:** `_find_response(harness, method)` pattern is reusable for other callback-driven tests.

- [x] **2.3** Preferences handler integration test
    - **Context:** See plan.md Task 2.3. Key refs: `src/bot/handlers/preferences.py` — `/preferences` command, `pref_toggle_view` callback. Uses `PreferencesService` singleton.
    - **Watch out:** Mock `PreferencesService.get_view_mode` and `toggle_view_mode` via `patch.object()`
    - **Scope:** `/preferences` command + toggle callback
    - **Touches:** `tests/integration/test_preferences_flow.py` (new)
    - **Action items:**
        - [RED] Write test: `/preferences` shows current view mode
        - [RED] Write test: `pref_toggle_view` toggles and shows new mode
        - [GREEN] Run tests
    - **Success:** `pytest tests/integration/test_preferences_flow.py -v` — 2 tests pass
    - **Completed:** 2026-03-10
    - **Learnings:** `patch.object` on PreferencesService class methods works because singleton delegates to class-level methods.
    - **Key Changes:** Created `tests/integration/test_preferences_flow.py` with 2 tests.
    - **Notes:** None.

- [x] **2.4** History handler integration test
    - **Context:** See plan.md Task 2.4. Key refs: `src/bot/handlers/history.py` — `/history` command, `hist_refresh`, `hist_back` callbacks. Uses `MediaService.get_history()`.
    - **Watch out:** Need to add `HISTORY_ITEMS` fixture data to `tests/integration/fixtures.py`
    - **Scope:** `/history` command + empty results + refresh + back
    - **Touches:** `tests/integration/test_history_flow.py` (new), `tests/integration/fixtures.py`
    - **Action items:**
        - [GREEN] Add `HISTORY_ITEMS` to fixtures.py
        - [RED] Write test: `/history` shows items
        - [RED] Write test: `/history` with empty results
        - [RED] Write test: `hist_refresh` re-fetches
        - [RED] Write test: `hist_back` returns to main menu
        - [GREEN] Run tests
    - **Success:** `pytest tests/integration/test_history_flow.py -v` — 4 tests pass
    - **Completed:** 2026-03-10
    - **Learnings:** Same `_find_response` helper pattern needed for callback tests. Refresh test requires sending `/history` first to populate `user_data`.
    - **Key Changes:** Added `HISTORY_ITEMS` to `tests/integration/fixtures.py`, created `tests/integration/test_history_flow.py` with 4 tests.
    - **Notes:** None.

---

### Phase 3: Callback-Driven Flow Tests (5 tasks)

**Goal:** Integration tests for handlers that use multi-step callback button flows (no ConversationHandler).

- [x] **3.1** Delete handler integration test
    - **Context:** See plan.md Task 3.1. Key refs: `src/bot/handlers/delete.py` — `/delete` → `delete_type_{type}` → `delete_item_{id}` → `delete_confirm`. Uses `MediaService.get_movies()`, `get_movie()`, `delete_movie()`.
    - **Watch out:** Handler stores state in `context.user_data["delete_type"]` and `["delete_item"]`. The `handle_delete_selection` method isn't decorated with `@require_auth` — only the entry `/delete` is.
    - **Scope:** Full delete flow + cancel + empty library
    - **Touches:** `tests/integration/test_delete_flow.py` (new)
    - **Action items:**
        - [RED] Write test: happy path — `/delete` → type → item → confirm → success
        - [RED] Write test: `/delete` → cancel
        - [RED] Write test: type selection with empty library
        - [GREEN] Run tests
    - **Success:** `pytest tests/integration/test_delete_flow.py -v` — 3 tests pass
    - **Completed:** 2026-03-10
    - **Learnings:** Full multi-step flow works through harness — each tap_button call carries user_data forward.
    - **Key Changes:** Created `tests/integration/test_delete_flow.py` with 3 tests.
    - **Notes:** None.

- [x] **3.2** Library handler integration test
    - **Context:** See plan.md Task 3.2. Key refs: `src/bot/handlers/library.py` — `/allMovies`, `/allSeries`, `/allMusic` commands, `lib_{type}_{page}` pagination. Uses `MediaService.get_movies()` etc.
    - **Watch out:** Need 15+ items to test pagination (ITEMS_PER_PAGE=10). Items cached in `context.user_data[f"library_{media_type}"]`.
    - **Scope:** All three library commands + pagination + empty
    - **Touches:** `tests/integration/test_library_flow.py` (new), `tests/integration/fixtures.py`
    - **Action items:**
        - [GREEN] Add `LIBRARY_MOVIES` and `LIBRARY_SERIES` to fixtures.py
        - [RED] Write test: `/allMovies` shows paginated list
        - [RED] Write test: `/allSeries` shows list
        - [RED] Write test: pagination via `lib_m_1`
        - [RED] Write test: empty library
        - [GREEN] Run tests
    - **Success:** `pytest tests/integration/test_library_flow.py -v` — 4 tests pass
    - **Completed:** 2026-03-10
    - **Learnings:** LIBRARY_MOVIES uses list comprehension for 15 items; pagination kicks in at ITEMS_PER_PAGE=10.
    - **Key Changes:** Added `LIBRARY_MOVIES`, `LIBRARY_SERIES` to fixtures.py. Created `tests/integration/test_library_flow.py` with 4 tests.
    - **Notes:** None.

- [x] **3.3** Calendar handler integration test
    - **Context:** See plan.md Task 3.3. Key refs: `src/bot/handlers/calendar.py` — `/upcoming` command, `cal_period_{days}`, `cal_refresh`, `cal_back` callbacks. Uses `MediaService.get_upcoming(days)`.
    - **Watch out:** `get_upcoming` is called with `days` parameter. Period change calls it again with new days value.
    - **Scope:** `/upcoming` + period change + refresh + back + empty
    - **Touches:** `tests/integration/test_calendar_flow.py` (new), `tests/integration/fixtures.py`
    - **Action items:**
        - [GREEN] Add `CALENDAR_ITEMS` to fixtures.py
        - [RED] Write test: `/upcoming` shows items
        - [RED] Write test: empty calendar
        - [RED] Write test: `cal_period_30` changes period
        - [RED] Write test: `cal_refresh`
        - [RED] Write test: `cal_back` returns to main menu
        - [GREEN] Run tests
    - **Success:** `pytest tests/integration/test_calendar_flow.py -v` — 5 tests pass
    - **Completed:** 2026-03-10
    - **Learnings:** CALENDAR_ITEMS needs `media_id` key in addition to `id` — `get_calendar_items_keyboard` reads `item['media_id']` for callback data.
    - **Key Changes:** Added `CALENDAR_ITEMS` to fixtures.py. Created `tests/integration/test_calendar_flow.py` with 5 tests.
    - **Notes:** None.

- [x] **3.4** Missing handler integration test
    - **Context:** See plan.md Task 3.4. Key refs: `src/bot/handlers/missing.py` — `/missing` command, `missing_refresh`, `missing_back` callbacks. Uses `MediaService.get_missing_media()`.
    - **Watch out:** Items cached in `context.user_data["missing_items"]`
    - **Scope:** `/missing` + empty + refresh + back
    - **Touches:** `tests/integration/test_missing_flow.py` (new), `tests/integration/fixtures.py`
    - **Action items:**
        - [GREEN] Add `MISSING_ITEMS` to fixtures.py
        - [RED] Write test: `/missing` shows items
        - [RED] Write test: empty missing
        - [RED] Write test: `missing_refresh`
        - [RED] Write test: `missing_back` returns to main menu
        - [GREEN] Run tests
    - **Success:** `pytest tests/integration/test_missing_flow.py -v` — 4 tests pass
    - **Completed:** 2026-03-10
    - **Learnings:** MISSING_ITEMS needs `internal_id` key — `get_missing_items_keyboard` reads `item['internal_id']` for search callback data.
    - **Key Changes:** Added `MISSING_ITEMS` (with `internal_id`) to fixtures.py. Created `tests/integration/test_missing_flow.py` with 4 tests.
    - **Notes:** None.

- [x] **3.5** Queue handler integration test
    - **Context:** See plan.md Task 3.5. Key refs: `src/bot/handlers/queue.py` — `/queue` command, `queue_refresh`, `queue_back` callbacks. Uses `MediaService.get_queue_media()`.
    - **Watch out:** Items cached in `context.user_data["queue_items"]`
    - **Scope:** `/queue` + empty + refresh + back
    - **Touches:** `tests/integration/test_queue_flow.py` (new), `tests/integration/fixtures.py`
    - **Action items:**
        - [GREEN] Add `QUEUE_ITEMS` to fixtures.py
        - [RED] Write test: `/queue` shows items
        - [RED] Write test: empty queue
        - [RED] Write test: `queue_refresh`
        - [RED] Write test: `queue_back` returns to main menu
        - [GREEN] Run tests
    - **Success:** `pytest tests/integration/test_queue_flow.py -v` — 4 tests pass
    - **Completed:** 2026-03-10
    - **Learnings:** Same pattern as missing/history — straightforward with MediaService mock.
    - **Key Changes:** Added `QUEUE_ITEMS` to fixtures.py. Created `tests/integration/test_queue_flow.py` with 4 tests.
    - **Notes:** None.

---

### Phase 4: Conversation Flow Tests (2 tasks)

**Goal:** Integration tests for handlers using ConversationHandler with state machines.

- [x] **4.1** Settings handler integration test (admin flow)
    - **Context:** See plan.md Task 4.1. Key refs: `src/bot/handlers/settings.py` — `/settings` command, `settings_conversation` ConversationHandler. Admin-only via `is_admin()` from `src.definitions`.
    - **Watch out:** Must patch `src.bot.handlers.settings.is_admin` (not `src.definitions.is_admin`). Must also patch `config.update_nested` and `config.save` as no-ops to prevent disk writes.
    - **Scope:** Admin access + non-admin rejection + language flow + back
    - **Touches:** `tests/integration/test_settings_flow.py` (new)
    - **Action items:**
        - [RED] Write test: `/settings` as admin shows menu
        - [RED] Write test: `/settings` as non-admin rejected
        - [RED] Write test: settings → language → select → confirmed
        - [RED] Write test: settings → back ends conversation
        - [GREEN] Run tests
    - **Success:** `pytest tests/integration/test_settings_flow.py -v` — 4 tests pass
    - **Completed:** 2026-03-10
    - **Learnings:** Language flow requires patching `config` at handler import site to intercept `update_nested`/`save`. `MagicMock` for config with explicit `get`/`update_nested`/`save` works cleanly.
    - **Key Changes:** Created `tests/integration/test_settings_flow.py` with 4 tests: admin menu, non-admin rejection, language select flow, back ends conversation.
    - **Notes:** None.

- [x] **4.2** Bazarr handler integration test
    - **Context:** See plan.md Task 4.2. Key refs: `src/bot/handlers/bazarr.py` — `/subtitles` command, `bazarr_wanted_movies`, `bazarr_cancel` callbacks. Uses `BazarrService` singleton. Requires `bazarr_harness` fixture from task 1.1.
    - **Watch out:** Regular `harness` doesn't register BazarrHandler. Use `bazarr_harness` for enabled tests. For "disabled" test, use regular `harness` and send `/subtitles` — BazarrHandler won't be registered, so no response is expected. Alternative: mock `is_enabled()` to return False in bazarr_harness.
    - **Scope:** Menu + disabled check + wanted movies + cancel
    - **Touches:** `tests/integration/test_bazarr_flow.py` (new), `tests/integration/fixtures.py`
    - **Action items:**
        - [GREEN] Add `BAZARR_WANTED_MOVIES` to fixtures.py
        - [RED] Write test: `/subtitles` shows menu when enabled (bazarr_harness)
        - [RED] Write test: `bazarr_wanted_movies` shows list
        - [RED] Write test: `bazarr_cancel` sends cancelled message
        - [GREEN] Run tests
    - **Success:** `pytest tests/integration/test_bazarr_flow.py -v` — 3 tests pass
    - **Completed:** 2026-03-10
    - **Learnings:** `bazarr_harness` had a recursion bug — `original_get = config.get` captured the mock, not the real method. Fixed by capturing `real_get` before the `patch.object` context.
    - **Key Changes:** Fixed `bazarr_harness` fixture in `conftest.py` (capture `real_get` before patching). Added `BAZARR_WANTED_MOVIES` to `fixtures.py`. Created `tests/integration/test_bazarr_flow.py` with 3 tests.
    - **Notes:** None.

---

### Phase 5: Error Path Tests (1 task)

**Goal:** At least one error-path test per conversation flow — API failures mid-conversation.

- [ ] **5.1** Error path integration tests
    - **Context:** See plan.md Task 5.1. Key refs: existing happy-path tests in `test_media_flow.py` as template.
    - **Watch out:** Handlers use try/except and send error text — don't expect exceptions to propagate. Assert on the error response text instead.
    - **Scope:** Movie add failure, series search failure, delete failure
    - **Touches:** `tests/integration/test_error_paths.py` (new)
    - **Action items:**
        - [RED] Write test: movie search OK but add raises exception → error response
        - [RED] Write test: series search raises exception → error response
        - [RED] Write test: delete confirm with `delete_movie` returning False → failure text
        - [GREEN] Run tests
    - **Success:** `pytest tests/integration/test_error_paths.py -v` — 3 tests pass

---

### Phase 6: Auth Gating Expansion (1 task)

**Goal:** Verify all protected commands gate behind auth.

- [ ] **6.1** Parametrized auth gating test for all commands
    - **Context:** See plan.md Task 6.1. Key refs: `tests/integration/test_auth_gating.py` (existing file with 3 tests).
    - **Watch out:** Some commands like `/settings` have admin checks on top of auth, but `@require_auth` fires first. The parametrized test covers the auth decorator. Use `AuthHandler._authenticated_users.discard(12345)` before each command.
    - **Scope:** Extend existing test file with parametrized test covering all 12 commands
    - **Touches:** `tests/integration/test_auth_gating.py`
    - **Action items:**
        - [RED] Write parametrized test covering: `/help`, `/settings`, `/delete`, `/allMovies`, `/allSeries`, `/allMusic`, `/upcoming`, `/missing`, `/queue`, `/preferences`, `/status`, `/history`
        - [GREEN] Run tests
    - **Success:** `pytest tests/integration/test_auth_gating.py -v` — existing 3 + new parametrized (12 cases) all pass

# Issue #81: List View for Search Results

## Summary

Add a paginated inline button list as an alternative to card-by-card navigation for search results. Includes per-user preference persistence, new keyboard layouts, display methods, callback routing, and a `/preferences` command.

---

### Phase 1: PreferencesService + Config (1 task)

**Goal:** Standalone persistence layer for per-user preferences, fully testable in isolation.

- [x] **1.1** Create PreferencesService singleton with config wiring
    - **Context:**
        - **Why:** Need to persist per-user view preference (card vs list) across bot restarts. This is the foundation all other tasks depend on
        - **Architecture:** Singleton pattern (`__new__` + `_initialize`) matching `TranslationService` in `src/services/translation.py:20-33`. JSON file at project root alongside `config.yaml`. Keys are string user IDs, values are dicts of preferences
        - **Key refs:** `src/services/translation.py:20-33` for singleton pattern, `src/definitions.py:17-31` for path constants, `tests/conftest.py:190-226` for singleton reset fixture
        - **Watch out:** JSON keys must be strings (user IDs as strings). File auto-created if missing. Handle corrupt JSON gracefully (log warning, reset to empty dict). Thread safety not needed (single async event loop)
    - **Scope:** Service class, path constant, gitignore entry, singleton reset in test conftest
    - **Touches:** `src/services/preferences.py` (create), `src/definitions.py`, `.gitignore`, `tests/conftest.py`
    - **Action items:**
        - [RED] Write `tests/test_services/test_preferences.py` — tests for:
            - `get_preference` / `set_preference` (generic key-value)
            - `get_view_mode` returns `"card"` by default
            - `toggle_view_mode` switches between `"card"` and `"list"`
            - Missing file auto-creates empty prefs
            - Corrupt JSON file resets gracefully
            - Multi-user isolation (user A's prefs don't affect user B)
        - [GREEN] Create `src/services/preferences.py` — singleton with `get_preference`, `set_preference`, `get_view_mode(user_id)`, `toggle_view_mode(user_id)`, `_load`, `_save`
        - [GREEN] Add `PREFERENCES_PATH = os.path.join(ROOT_DIR, "user_preferences.json")` to `src/definitions.py` after line 31
        - [GREEN] Add `user_preferences.json` to `.gitignore`
        - [GREEN] Add `PreferencesService._instance = None` to `reset_singletons` fixture in `tests/conftest.py`
    - **Success:** `pytest tests/test_services/test_preferences.py -v` passes, `pytest --tb=short -q` all green, `flake8 .` clean
    - **Completed:** 2026-03-02
    - **Learnings:**
        - Singleton pattern slightly simpler than TranslationService — no `_initialize` classmethod needed since `_load` is an instance method called once in `__new__`
        - Singleton reset fixture needs both `_instance = None` and `_preferences = {}` to prevent state leakage between tests
        - Tests use `tmp_path` fixture + patch of `PREFERENCES_PATH` to isolate file I/O
    - **Key Changes:**
        - Created `src/services/preferences.py` — singleton with JSON persistence, generic get/set + view_mode convenience methods
        - Added `PREFERENCES_PATH` to `src/definitions.py`
        - Added `user_preferences.json` to `.gitignore`
        - Added `PreferencesService` singleton reset in `tests/conftest.py`
        - Created `tests/test_services/test_preferences.py` — 17 tests covering all behaviors
    - **Notes:** Service is generic key-value per user, not just view_mode — extensible for future preferences

---

### Phase 2: Keyboards + Display Methods (1 task)

**Goal:** Keyboard builders and rendering methods for list view, testable independently of handler wiring.

- [x] **2.1** Add list view keyboards and MediaHandler display methods
    - **Context:**
        - **Why:** List view needs two new keyboard layouts (paginated list + detail card) and two new display methods on MediaHandler (`_show_list`, `_show_list_detail`). Also need to extract `_build_result_caption()` from `_show_result()` to share caption logic between card and list detail views
        - **Architecture:** Keyboard functions go in `src/bot/keyboards.py` following existing patterns (e.g. `get_main_menu_keyboard` at line 14). Display methods are private helpers on `MediaHandler`. Card view sends photos via `reply_photo`, list view sends text via `reply_text`. When toggling views, must delete old message and send new one (not edit) to avoid photo↔text type mismatch
        - **Key refs:** `src/bot/keyboards.py` for keyboard patterns, `src/bot/handlers/media.py:292-429` for `_show_result` method (caption logic at lines 296-354, keyboard at 357-378, photo sending at 381-413)
        - **Watch out:**
            - Emoji prefix varies by search type: 🎬 movie, 📺 series, 🎵 music
            - Page indicator button uses `listpage_noop` callback data (no-op, just for display)
            - Single-page results (≤page_size) should hide the pagination row entirely
            - `_build_result_caption` must produce identical output to current `_show_result` caption when called with index/total args, so existing card view tests don't break
            - Add "📋 Switch to List View" button to card view keyboard (viewtoggle callback)
    - **Scope:** Two keyboard functions, caption extraction, two display methods, viewtoggle button on card view
    - **Touches:** `src/bot/keyboards.py`, `src/bot/handlers/media.py`, `tests/test_handlers/test_media_handler.py`
    - **Action items:**
        - [RED] Write tests for `get_search_results_list_keyboard`:
            - Renders result titles with emoji prefix per media type
            - Pagination buttons (◀️/▶️) with correct `listpage_{n}` callback data
            - Page indicator shows "Page X/Y" with `listpage_noop` callback
            - Single-page results omit pagination row
            - Bottom row has viewtoggle + cancel buttons
        - [RED] Write tests for `get_list_detail_keyboard`:
            - "Add to Library" button with `select_{id}` callback (reuses existing flow)
            - "Back to List" button with `listback` callback
            - "Cancel" button with `select_cancel` callback
        - [RED] Write tests for `_build_result_caption` — movie with year/ratings, series with TMDB rating, with/without index/total counter
        - [RED] Write tests for `_show_list` — sends text message with list keyboard, stores page in user_data
        - [RED] Write tests for `_show_list_detail` — sends photo + detail caption + list detail keyboard
        - [RED] Write test verifying `_show_result` still works unchanged after caption extraction refactor
        - [GREEN] Implement `get_search_results_list_keyboard(results, page, page_size=5, search_type="movie")` in `keyboards.py`
        - [GREEN] Implement `get_list_detail_keyboard(result_id)` in `keyboards.py`
        - [GREEN] Extract `_build_result_caption(self, result, index=None, total=None)` from `_show_result` in `media.py`
        - [GREEN] Refactor `_show_result` to use `_build_result_caption` + add viewtoggle button to its keyboard
        - [GREEN] Implement `_show_list(self, message, results, page, search_type)` in `media.py`
        - [GREEN] Implement `_show_list_detail(self, message, result)` in `media.py`
    - **Success:** All existing media handler tests pass (card view unchanged), new keyboard + display tests pass, `flake8 .` clean
    - **Completed:** 2026-03-02
    - **Learnings:**
        - Caption extraction was clean — `_build_result_caption` accepts optional `index`/`total` args, so card view passes them and list detail view omits them
        - Existing `_show_result` tests all pass without modification after refactor — the caption output is byte-identical
        - Viewtoggle button added to card view keyboard between "Add" and "Cancel" rows
    - **Key Changes:**
        - Added `get_search_results_list_keyboard()` and `get_list_detail_keyboard()` to `src/bot/keyboards.py`
        - Extracted `_build_result_caption()` from `_show_result()` in `src/bot/handlers/media.py`
        - Added `_show_list()` and `_show_list_detail()` display methods to `MediaHandler`
        - Added viewtoggle button to card view keyboard in `_show_result()`
        - Added imports for new keyboard functions in `media.py`
        - Added 9 keyboard tests and 11 media handler display/caption tests (23 new total)
    - **Notes:** `_show_list` and `_show_list_detail` are not yet wired into the conversation handler — that happens in Phase 3

---

### Phase 3: Handler Integration + Preferences Command (1 task)

**Goal:** Wire callback routing, handle_search branching, PreferencesHandler, and bot registration.

- [x] **3.1** Wire list view callbacks, create PreferencesHandler, register in bot
    - **Context:**
        - **Why:** The SELECTING state in both `media_conversation` and `start_conversation` ConversationHandlers needs to route new callback patterns (`listsel_`, `listback`, `listpage_`, `viewtoggle`) to new handler methods. `handle_search` must branch on user's view preference. Users also need a `/preferences` command to view/toggle their view mode
        - **Architecture:**
            - New `CallbackQueryHandler` entries in SELECTING state for both handlers. Callback prefixes are disjoint so order doesn't matter, but add after existing ones for clarity
            - `handle_search` (media.py:242) branches: after storing results, check `PreferencesService().get_view_mode(user_id)` → call `_show_list()` or `_show_result()` accordingly
            - `PreferencesHandler` follows `HelpHandler` pattern (src/bot/handlers/help.py) — simple `CommandHandler` + `CallbackQueryHandler`, registered after Help in `_add_handlers()` (src/main.py:144-147)
            - StartHandler (src/bot/handlers/start.py:58-71) delegates to `self.media_handler.*` methods for the 4 new callbacks
        - **Key refs:**
            - `src/bot/handlers/media.py:42-110` for MediaHandler's ConversationHandler setup (SELECTING state at lines 63-76)
            - `src/bot/handlers/start.py:58-71` for StartHandler's SELECTING state
            - `src/bot/handlers/media.py:242-290` for `handle_search` method
            - `src/bot/handlers/help.py:20-31` for simple handler pattern
            - `src/main.py:99-156` for handler registration order
        - **Watch out:**
            - `listpage_noop` callback must just `query.answer()` and return `SELECTING` (no-op)
            - `handle_view_toggle` must delete old message and send new one (photo↔text switch)
            - StartHandler creates its own `MediaHandler()` instance at line 35 — its new callback entries delegate to `self.media_handler.handle_list_*`
            - `media_handler` fixture in `tests/test_handlers/conftest.py` needs `PreferencesService` patched
            - `start_handler` fixture needs the 4 new async methods added to `mock_media_handler`
            - PreferencesHandler must use `@require_auth` decorator
    - **Scope:** 4 callback methods on MediaHandler, handle_search branching, ConversationHandler routing updates, PreferencesHandler class, bot registration, test fixture updates
    - **Touches:** `src/bot/handlers/media.py`, `src/bot/handlers/start.py`, `src/bot/handlers/preferences.py` (create), `src/main.py`, `tests/test_handlers/conftest.py`, `tests/test_handlers/test_media_handler.py`, `tests/test_handlers/test_preferences_handler.py` (create)
    - **Action items:**
        - [RED] Write tests for `handle_search` branching — card view by default, list view when user preference is `"list"`
        - [RED] Write tests for `handle_list_select` — tapping a list item shows detail card via `_show_list_detail`
        - [RED] Write tests for `handle_list_back` — returns to paginated list at correct page
        - [RED] Write tests for `handle_list_page` — navigates pages forward/back, `listpage_noop` is no-op
        - [RED] Write tests for `handle_view_toggle` — toggles preference via PreferencesService, deletes old message, re-renders in new mode
        - [RED] Write `tests/test_handlers/test_preferences_handler.py` — `/preferences` shows current view mode with toggle button, toggle callback switches mode, unauthenticated user is rejected
        - [GREEN] Add `handle_list_select`, `handle_list_back`, `handle_list_page`, `handle_view_toggle` to MediaHandler
        - [GREEN] Update `handle_search` to branch on `PreferencesService().get_view_mode(user_id)`
        - [GREEN] Add 4 new `CallbackQueryHandler` entries to MediaHandler's SELECTING state (patterns: `^listsel_`, `^listback$`, `^listpage_`, `^viewtoggle$`)
        - [GREEN] Add 4 new `CallbackQueryHandler` entries to StartHandler's SELECTING state (delegating to `self.media_handler.*`)
        - [GREEN] Create `src/bot/handlers/preferences.py` — `PreferencesHandler` with `show_preferences`, `handle_toggle`, both using `@require_auth`
        - [GREEN] Register `PreferencesHandler` in `src/main.py:_add_handlers()` after Help handler (line 147)
        - [GREEN] Update `media_handler` fixture to patch `PreferencesService` (default mock returns `"card"`)
        - [GREEN] Update `start_handler` fixture to add `handle_list_select`, `handle_list_back`, `handle_list_page`, `handle_view_toggle` as `AsyncMock` on `mock_media_handler`
        - [GREEN] Add `preferences_handler` fixture to `tests/test_handlers/conftest.py`
    - **Success:** All tests pass (existing + new), card view is default, list view works when preference is set, `/preferences` command works, `flake8 .` clean
    - **Completed:** 2026-03-02
    - **Learnings:**
        - `@require_auth` decorator accesses `update.message.reply_text()` which is only safe for command handlers, not callback queries — works here because callback toggle is always from an authenticated user session
        - PreferencesService mock needs to be patched at `src.bot.handlers.media.PreferencesService` (where it's imported), not at the service module level
        - View toggle page calculation `current_index // 5` correctly maps card view position to list page
        - `listpage_noop` pattern needs no special regex — `^listpage_` matches both `listpage_noop` and `listpage_1`, and the handler distinguishes by parsing the suffix
    - **Key Changes:**
        - Added `handle_list_select`, `handle_list_back`, `handle_list_page`, `handle_view_toggle` to `MediaHandler` in `src/bot/handlers/media.py`
        - Updated `handle_search` to branch on `PreferencesService().get_view_mode(user_id)` — card (default) vs list
        - Added 4 `CallbackQueryHandler` entries to SELECTING state in both `MediaHandler` and `StartHandler` ConversationHandlers
        - Created `src/bot/handlers/preferences.py` — `PreferencesHandler` with `show_preferences` + `handle_toggle`, both `@require_auth`
        - Registered `PreferencesHandler` in `src/main.py` after Help handler
        - Updated `media_handler` fixture to patch `PreferencesService` (default mock returns `"card"`)
        - Updated `start_handler` fixture with 4 new `AsyncMock` methods on `mock_media_handler`
        - Added `preferences_handler` fixture to `tests/test_handlers/conftest.py`
        - Added 13 new media handler tests and 8 preferences handler tests (21 new tests total)
    - **Notes:** Full suite: 1163 passed, flake8 clean. All three phases of issue #81 are now complete.

---

## Verification

After all tasks:
```bash
pytest --tb=short -q                        # All tests pass (existing + new)
pytest --cov=src --cov-report=term-missing  # Coverage maintained
flake8 .                                     # No lint errors
```

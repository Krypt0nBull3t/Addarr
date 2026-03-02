# Issue #81: List View for Search Results — Implementation Plan

## Context

The current card-by-card navigation (prev/next with poster images) is slow when users already know which title they want from many results. This adds a paginated inline button list as an alternative view mode, with per-user preference persistence.

## Architecture

- **No new conversation states** — list view operates within the existing `SELECTING` state using new callback prefixes (`listsel_`, `listback`, `listpage_`, `viewtoggle`)
- **Branching point** is `handle_search()` — after getting results, check user's view preference and call either `_show_result()` (card) or `_show_list()` (list)
- **Detail card reuses `select_{id}`** — tapping "Add to Library" from a list detail card triggers the existing `handle_selection` flow, zero duplication
- **Both ConversationHandlers** (`media_conversation` and `start_conversation`) need the new callback routes in their `SELECTING` state

## Phased Tasks

### Phase 1: PreferencesService + Config (2 tasks)

**Goal:** Standalone persistence layer for per-user preferences.

- [ ] **1.1** Create `UserPreferencesService` singleton
    - **Context:**
        - **Why:** Need to persist per-user view preference across bot restarts
        - **Architecture:** Singleton pattern (`__new__` + `_initialize`) matching existing services. JSON file at project root alongside `config.yaml`
        - **Key refs:** `src/services/translation.py` for singleton pattern, `src/definitions.py:17-31` for path constants
        - **Watch out:** JSON keys must be strings (user IDs as strings). File auto-created if missing. Handle corrupt JSON gracefully
    - **Scope:** Service, path constant, gitignore
    - **Touches:** `src/services/preferences.py` (create), `src/definitions.py` (add `PREFERENCES_PATH`), `.gitignore` (add `user_preferences.json`), `tests/conftest.py` (add singleton reset)
    - **Action items:**
        - [RED] Write `tests/test_services/test_preferences.py` — tests for get/set preference, get/toggle view mode, missing file, corrupt JSON, multi-user isolation
        - [GREEN] Create `src/services/preferences.py` — singleton with `get_preference`, `set_preference`, `get_view_mode`, `toggle_view_mode`, `_load`, `_save`
        - [GREEN] Add `PREFERENCES_PATH = os.path.join(ROOT_DIR, "user_preferences.json")` to `src/definitions.py`
        - [GREEN] Add `user_preferences.json` to `.gitignore`
        - [GREEN] Add `PreferencesService._instance = None` to `reset_singletons` fixture in `tests/conftest.py`
    - **Success:** `pytest tests/test_services/test_preferences.py -v` passes, all existing tests still pass

### Phase 2: Keyboards + Display Methods (2 tasks)

**Goal:** Keyboard builders and rendering methods, testable independently.

- [ ] **2.1** Add list view keyboard builders
    - **Context:**
        - **Why:** List view needs two new keyboard layouts — the paginated list and the detail card
        - **Architecture:** Functions in `src/bot/keyboards.py` following existing patterns (`get_main_menu_keyboard`, etc.)
        - **Key refs:** `src/bot/keyboards.py` for existing keyboard builder patterns
        - **Watch out:** Emoji prefix varies by media type (movie/series/music). Page indicator button uses `listpage_noop` callback. Single-page results should hide pagination row
    - **Scope:** Two new functions in keyboards module
    - **Touches:** `src/bot/keyboards.py`
    - **Action items:**
        - [RED] Write tests for `get_search_results_list_keyboard` — pagination, emoji prefixes, single page, viewtoggle/cancel buttons
        - [RED] Write tests for `get_list_detail_keyboard` — select, back, cancel buttons
        - [GREEN] Implement `get_search_results_list_keyboard(results, page, page_size=5, search_type="movie")`
        - [GREEN] Implement `get_list_detail_keyboard(result_id)`
    - **Success:** Keyboard tests pass

- [ ] **2.2** Add list view display methods to MediaHandler
    - **Context:**
        - **Why:** MediaHandler needs `_show_list` and `_show_list_detail` methods to render list view and detail cards
        - **Architecture:** Extract `_build_result_caption()` from `_show_result()` (lines 296-354) to share caption logic. Card view behavior must not change
        - **Key refs:** `src/bot/handlers/media.py:292-429` for `_show_result` method
        - **Watch out:** Card view sends photos, list view sends text. When toggling views, must delete old message and send new one (not edit) to avoid photo/text type mismatch. Add "Switch to List View" button to card view keyboard
    - **Scope:** Extract caption helper, add `_show_list` and `_show_list_detail` methods, add viewtoggle button to card view
    - **Touches:** `src/bot/handlers/media.py`
    - **Action items:**
        - [RED] Write tests for `_build_result_caption` — movie, series, with/without index
        - [RED] Write tests for `_show_list` — sends text message with list keyboard, pagination
        - [RED] Write tests for `_show_list_detail` — shows poster + detail + back/add/cancel buttons
        - [RED] Write test verifying `_show_result` still works unchanged after refactor
        - [GREEN] Extract `_build_result_caption(result, index=None, total=None)` from `_show_result`
        - [GREEN] Refactor `_show_result` to use the extracted helper + add viewtoggle button
        - [GREEN] Implement `_show_list(message, results, page, search_type)`
        - [GREEN] Implement `_show_list_detail(message, result)`
    - **Success:** All existing media handler tests pass (card view unchanged), new display method tests pass

### Phase 3: Handler Integration (2 tasks)

**Goal:** Wire everything together — callback routing, preferences command, handler registration.

- [ ] **3.1** Wire list view callbacks into MediaHandler and StartHandler
    - **Context:**
        - **Why:** The SELECTING state in both ConversationHandlers needs to route new callback patterns to new handler methods
        - **Architecture:** New `CallbackQueryHandler` entries in SELECTING state for `listsel_`, `listback`, `listpage_`, `viewtoggle`. `handle_search` branches on view mode preference
        - **Key refs:** `src/bot/handlers/media.py:42-110` for ConversationHandler setup, `src/bot/handlers/start.py:58-71` for StartHandler's SELECTING state
        - **Watch out:** StartHandler delegates to `self.media_handler.*` methods. Pattern order doesn't matter (prefixes are disjoint) but add new patterns after existing ones for clarity. `listpage_noop` must be handled gracefully (just `query.answer()`)
    - **Scope:** Callback methods, ConversationHandler routing, handle_search branching
    - **Touches:** `src/bot/handlers/media.py`, `src/bot/handlers/start.py`, `tests/test_handlers/conftest.py` (update media_handler fixture to mock PreferencesService)
    - **Action items:**
        - [RED] Write tests for `handle_search` branching — card view by default, list view when preference set
        - [RED] Write tests for `handle_list_select` — shows detail card for tapped result
        - [RED] Write tests for `handle_list_back` — returns to list at correct page
        - [RED] Write tests for `handle_list_page` — navigates pages, ignores noop
        - [RED] Write tests for `handle_view_toggle` — toggles preference and re-renders in new mode
        - [GREEN] Add `handle_list_select`, `handle_list_back`, `handle_list_page`, `handle_view_toggle` to MediaHandler
        - [GREEN] Update `handle_search` to branch on `PreferencesService().get_view_mode(user_id)`
        - [GREEN] Add 4 new CallbackQueryHandler entries to MediaHandler's SELECTING state
        - [GREEN] Add 4 new CallbackQueryHandler entries to StartHandler's SELECTING state (delegating to `self.media_handler.*`)
        - [GREEN] Update `media_handler` fixture in `tests/test_handlers/conftest.py` to mock PreferencesService
    - **Success:** All tests pass, card view default unchanged, list view works when preference is set

- [ ] **3.2** Create PreferencesHandler + register in AddarrBot
    - **Context:**
        - **Why:** Users need `/preferences` command to view and toggle their view mode
        - **Architecture:** Simple handler following HelpHandler pattern — CommandHandler + CallbackQueryHandler. Registered after Help handler in `_add_handlers()`
        - **Key refs:** `src/bot/handlers/help.py` for simple handler pattern, `src/main.py:99-156` for registration order
        - **Watch out:** Must use `@require_auth` decorator. Future preferences can be added to this handler later
    - **Scope:** PreferencesHandler class, handler registration
    - **Touches:** `src/bot/handlers/preferences.py` (create), `src/main.py`, `tests/test_handlers/test_preferences_handler.py` (create), `tests/test_handlers/conftest.py` (add preferences_handler fixture)
    - **Action items:**
        - [RED] Write `tests/test_handlers/test_preferences_handler.py` — show preferences, toggle view, auth required
        - [GREEN] Create `src/bot/handlers/preferences.py` — `show_preferences`, `handle_toggle` with `@require_auth`
        - [GREEN] Register `PreferencesHandler` in `src/main.py:_add_handlers()` after Help handler
        - [GREEN] Add `preferences_handler` fixture to `tests/test_handlers/conftest.py`
    - **Success:** All tests pass, `/preferences` shows current view mode with toggle button

## File Inventory

| File | Action |
|------|--------|
| `src/services/preferences.py` | Create |
| `src/bot/handlers/preferences.py` | Create |
| `src/definitions.py` | Edit (+1 line: PREFERENCES_PATH) |
| `.gitignore` | Edit (+1 line: user_preferences.json) |
| `src/bot/keyboards.py` | Edit (+2 functions) |
| `src/bot/handlers/media.py` | Edit (extract caption helper, add display methods, add callbacks, update routing) |
| `src/bot/handlers/start.py` | Edit (+4 callback routes in SELECTING state) |
| `src/main.py` | Edit (+PreferencesHandler registration) |
| `tests/conftest.py` | Edit (+singleton reset for PreferencesService) |
| `tests/test_services/test_preferences.py` | Create |
| `tests/test_handlers/test_preferences_handler.py` | Create |
| `tests/test_handlers/conftest.py` | Edit (+preferences_handler fixture, update media_handler fixture) |
| `tests/test_handlers/test_media_handler.py` | Edit (+tests for list view methods and callbacks) |

## Verification

After all phases:
```bash
pytest --tb=short -q                        # All tests pass (existing + new)
pytest --cov=src --cov-report=term-missing  # Coverage maintained
flake8 .                                     # No lint errors
```

# Issue #97: Decompose MediaHandler

> **Plan:** [plan.md](plan.md)
> **Branch:** `refactor/97-decompose-media-handler`
> **Constraint:** Pure refactor — no behavior changes. Existing 3034-line test file is the safety net.

---

### Phase 1: Package Conversion (1 task)

**Goal:** Convert `media.py` to a `media/` package with dispatch tables and backward-compatible imports.

- [x] **1.1** Convert media.py to media/ package with dispatch module
    - **Context:**
        - **Why:** Foundation step — all subsequent extractions depend on the package structure existing
        - **Architecture:** Delete `media.py`, create `media/` directory with `__init__.py` (re-exports), `dispatch.py` (constants + config dict), `handler.py` (full MediaHandler, initially unchanged). Architecture test `_get_python_files()` must be updated to recurse into handler subdirectories so `MediaHandler` in `handler.py` is still checked.
        - **Key refs:**
            - `src/bot/handlers/media.py:1-42` — imports and state constants to move
            - `src/bot/handlers/__init__.py:14` — `from .media import MediaHandler`
            - `src/main.py:22` — `from src.bot.handlers.media import MediaHandler`
            - `src/bot/handlers/start.py:21` — `from src.bot.handlers.media import MediaHandler, SEARCHING, SELECTING`
            - `tests/test_handlers/conftest.py:77-98` — `media_handler` fixture with 3 patch paths
            - `tests/test_architecture/test_conventions.py:48-54` — `_get_python_files()` only scans direct children
        - **Watch out:**
            - Patch paths in conftest must change from `src.bot.handlers.media.X` to `src.bot.handlers.media.handler.X` for `MediaService`, `TranslationService`, `PreferencesService`
            - `__init__.py` must re-export state constants (`SEARCHING`, `SELECTING`, etc.) for existing test imports
            - `_get_python_files` uses `os.listdir` (non-recursive) — needs `os.walk` or similar to find `handler.py` inside `media/`
            - Mixin classes (`SeasonPickerMixin`, `AlbumPickerMixin`) won't end in `Handler` so they won't trigger the `get_handler()` check — this is correct behavior
    - **Scope:** File restructuring, import re-wiring, architecture test update
    - **Touches:**
        - Delete: `src/bot/handlers/media.py`
        - Create: `src/bot/handlers/media/__init__.py`, `src/bot/handlers/media/dispatch.py`, `src/bot/handlers/media/handler.py`
        - Modify: `tests/test_handlers/conftest.py` (3 patch paths)
        - Modify: `tests/test_architecture/test_conventions.py` (`_get_python_files`)
    - **Action items:**
        - [RED] Write test in `tests/test_handlers/test_media_package.py` that imports `MediaHandler`, `SEARCHING`, `SELECTING`, `QUALITY_SELECT`, `SEASON_SELECT`, `ALBUM_SELECT` from `src.bot.handlers.media` — verifying backward-compatible re-exports work
        - [RED] Write test that imports `MEDIA_CONFIG` from `src.bot.handlers.media.dispatch` and asserts it has keys `"movie"`, `"series"`, `"music"` with expected config_key/search/add/add_with_profile values
        - [GREEN] Create `src/bot/handlers/media/dispatch.py` with state constants and `MEDIA_CONFIG` dict
        - [GREEN] Create `src/bot/handlers/media/handler.py` — move entire MediaHandler class from old `media.py`, update state constant imports to `from .dispatch import ...`
        - [GREEN] Create `src/bot/handlers/media/__init__.py` with re-exports: `from .handler import MediaHandler` and `from .dispatch import SEARCHING, SELECTING, QUALITY_SELECT, SEASON_SELECT, ALBUM_SELECT`
        - [GREEN] Delete old `src/bot/handlers/media.py`
        - [GREEN] Update `tests/test_handlers/conftest.py` — change 3 patch paths to `src.bot.handlers.media.handler.X`
        - [GREEN] Update `tests/test_architecture/test_conventions.py` — make `_get_python_files` recurse into subdirectories
        - Run full test suite: `python -m pytest --tb=short -q`
        - Run architecture tests: `python -m pytest tests/test_architecture/ -v`
    - **Success:** All 3034 existing media handler tests pass. Architecture test finds MediaHandler in `handler.py`. New package import test and dispatch config test pass.

---

### Phase 2: Extract Formatters (1 task)

**Goal:** Move result display functions out of MediaHandler into standalone functions in `formatters.py`.

- [x] **2.1** Extract formatter and display functions to formatters.py
    - **Context:**
        - **Why:** The display functions (`_build_result_caption`, `_show_result`, `_show_list`, `_show_list_detail`, `_send_response`) are ~200 lines that don't use `self.media_service` or `self.translation` — they operate purely on message objects and result dicts. Extracting them reduces MediaHandler and makes display logic independently testable.
        - **Architecture:** Standalone async functions (not a class). Handler imports them and calls directly: `await show_result(message, ...)` instead of `await self._show_result(message, ...)`. The `_build_result_caption` helper is also standalone since it only reads from the result dict.
        - **Key refs:**
            - `src/bot/handlers/media/handler.py:344-440` — `_build_result_caption` (97 lines, movie/series/album/song branching)
            - `src/bot/handlers/media/handler.py:442-514` — `_show_result` (73 lines, card view with poster)
            - `src/bot/handlers/media/handler.py:516-534` — `_show_list` (19 lines, paginated list)
            - `src/bot/handlers/media/handler.py:536-573` — `_show_list_detail` (38 lines, detail from list)
            - `src/bot/handlers/media/handler.py:1272-1288` — `_send_response` (17 lines, photo vs text edit)
            - Existing tests that `patch.object(media_handler, "_show_result", ...)`: lines 131, 158 in test_media_handler.py
        - **Watch out:**
            - Tests using `patch.object(media_handler, "_show_result", ...)` need to change to `patch("src.bot.handlers.media.handler.show_result", ...)` since it's no longer a method on `self`
            - `_show_result` uses `InlineKeyboardButton`/`InlineKeyboardMarkup` imports — these go into formatters.py
            - `_build_result_caption` uses `logger` — pass logger as parameter or import in formatters.py
            - `send_response` is used by both pickers (phase 3) and handler — extracting first means pickers can import it too
    - **Scope:** Create formatters.py, move 5 functions, update all call sites in handler.py, update test patches
    - **Touches:**
        - Create: `src/bot/handlers/media/formatters.py`
        - Modify: `src/bot/handlers/media/handler.py` (remove methods, add imports, update calls)
        - Modify: `tests/test_handlers/test_media_handler.py` (update patch targets for `_show_result` patches)
    - **Action items:**
        - [RED] Write tests in `tests/test_handlers/test_media_formatters.py`:
            - `test_build_result_caption_movie` — movie result with year, ratings, genres
            - `test_build_result_caption_series` — series result with network, seasons
            - `test_build_result_caption_album` — album result with artist, release date
            - `test_build_result_caption_song` — song result with album, artist
            - `test_build_result_caption_with_index` — counter line appended
            - `test_build_result_caption_long_overview_truncated` — overview > 300 chars truncated to 297 + "..."
            - `test_send_response_with_photo` — calls `edit_caption`
            - `test_send_response_without_photo` — calls `edit_text`
            - `test_send_response_with_reply_markup` — passes markup through
            - `test_send_response_fallback_on_error` — falls back to `reply_text` on exception
        - [GREEN] Create `src/bot/handlers/media/formatters.py` — move functions, rename (drop leading underscore):
            - `build_result_caption(result, index=None, total=None)`
            - `async show_result(message, result, index, total)`
            - `async show_list(message, results, page, search_type)`
            - `async show_list_detail(message, result)`
            - `async send_response(message, text, reply_markup=None)`
        - [GREEN] Update `handler.py` — add `from .formatters import build_result_caption, show_result, show_list, show_list_detail, send_response`, replace all `self._method(...)` calls with direct function calls
        - [GREEN] Update test patches in `test_media_handler.py` — change `patch.object(media_handler, "_show_result", ...)` to `patch("src.bot.handlers.media.handler.show_result", ...)`
        - Run full test suite: `python -m pytest --tb=short -q`
    - **Success:** All existing tests pass. New formatter unit tests pass. `handler.py` is ~200 lines shorter.
    - **Completed:** 2026-03-04
    - **Learnings:**
        - `patch.object(instance, "_method")` patterns come in multiple line formats — single-line and multi-line with different indentation. Must check for both when doing replace_all.
        - When moving functions from handler.py to formatters.py, patch targets for keyboard imports also need updating (e.g., `get_search_results_list_keyboard` patch must target `formatters` module, not `handler`).
        - `build_result_caption` is only called within other formatter functions, not directly from handler.py — no need to import it in handler.py.
    - **Key Changes:**
        - Created `src/bot/handlers/media/formatters.py` with 5 standalone functions (273 lines)
        - Reduced `handler.py` from 1336 to 1091 lines (~245 lines removed)
        - Created `tests/test_handlers/test_media_formatters.py` with 10 new tests
        - Updated all `patch.object` and direct method calls in `test_media_handler.py`
        - Removed unused `get_search_results_list_keyboard`/`get_list_detail_keyboard` imports from handler.py
    - **Notes:** 100% coverage on entire media package. All 1636 tests pass. Flake8 clean.

---

### Phase 3: Extract Picker Mixins (1 task)

**Goal:** Move season and album picker flows into mixin classes, reducing MediaHandler by ~300 lines.

- [ ] **3.1** Extract SeasonPickerMixin and AlbumPickerMixin
    - **Context:**
        - **Why:** Season picker (~120 lines, 2 methods) and album picker (~170 lines, 3 methods) are self-contained selection flows. As mixins, they reduce handler.py while keeping `self.method_name` calls unchanged in the ConversationHandler registration.
        - **Architecture:** Mixin classes that MediaHandler inherits from: `class MediaHandler(SeasonPickerMixin, AlbumPickerMixin)`. Mixins access `self.media_service` and `self.translation` (provided by MediaHandler's `__init__`). They import `send_response` from formatters and state constants from dispatch. Python MRO ensures MediaHandler methods take priority.
        - **Key refs:**
            - `src/bot/handlers/media/handler.py` — `handle_season_selection`, `handle_season_confirm` (season picker)
            - `src/bot/handlers/media/handler.py` — `handle_album_monitor_mode`, `handle_album_selection`, `handle_album_confirm` (album picker)
            - `src/bot/keyboards.py` — `get_album_selection_keyboard`, `get_album_monitor_mode_keyboard` (imported by album picker)
            - ConversationHandler in `get_handler()` — references `self.handle_season_selection`, `self.handle_album_selection`, etc. (unchanged since mixins provide these via inheritance)
        - **Watch out:**
            - Mixin methods use `send_response` from formatters — import at module level in each mixin file
            - `handle_season_selection` has inline keyboard building with `InlineKeyboardButton`/`InlineKeyboardMarkup` — import in season_picker.py
            - `handle_album_selection` calls `self.handle_album_confirm` — both must be in the same mixin
            - `handle_season_selection` calls `self.handle_season_confirm` — both must be in the same mixin
            - No new tests needed — existing handler tests cover all mixin method behavior through MediaHandler
    - **Scope:** Create 2 mixin files, move 5 methods total, update handler inheritance
    - **Touches:**
        - Create: `src/bot/handlers/media/season_picker.py`
        - Create: `src/bot/handlers/media/album_picker.py`
        - Modify: `src/bot/handlers/media/handler.py` (remove methods, add inheritance)
    - **Action items:**
        - [GREEN] Create `src/bot/handlers/media/season_picker.py` with `SeasonPickerMixin`:
            - Move `handle_season_selection(self, update, context)` from handler.py
            - Move `handle_season_confirm(self, update, context)` from handler.py
            - Add imports: `send_response` from formatters, states from dispatch, telegram types, keyboards
        - [GREEN] Create `src/bot/handlers/media/album_picker.py` with `AlbumPickerMixin`:
            - Move `handle_album_monitor_mode(self, update, context)` from handler.py
            - Move `handle_album_selection(self, update, context)` from handler.py
            - Move `handle_album_confirm(self, update, context)` from handler.py
            - Add imports: `send_response` from formatters, states from dispatch, keyboard functions, telegram types
        - [GREEN] Update `handler.py`:
            - Add `from .season_picker import SeasonPickerMixin`
            - Add `from .album_picker import AlbumPickerMixin`
            - Change class declaration: `class MediaHandler(SeasonPickerMixin, AlbumPickerMixin):`
            - Remove the 5 moved methods
        - Run full test suite: `python -m pytest --tb=short -q`
    - **Success:** All existing tests pass. `handler.py` is ~300 lines shorter. ConversationHandler `self.handle_season_selection` calls resolve to mixin methods.

---

### Phase 4: Parameterize Entry Points & Dispatch (1 task)

**Goal:** Collapse 3 duplicate entry points into 1 shared helper, replace if/elif chains with dispatch dict lookups.

- [ ] **4.1** Parameterize entry points and replace dispatch chains
    - **Context:**
        - **Why:** `handle_movie`, `handle_series`, `handle_music` are 30 lines each with only the config key and search_type string differing. The if/elif chains in `handle_search`, `handle_selection`, and `_add_media_with_profile` branch on `search_type` to call the right service method. Dispatch tables make both patterns data-driven.
        - **Architecture:** `MEDIA_CONFIG` dict (already in `dispatch.py` from phase 1) maps search_type to method names. A shared `_start_search(self, update, context, search_type)` handles the common entry logic. The 3 public methods become one-liners delegating to `_start_search`. `getattr(self.media_service, method_name)` replaces if/elif chains.
        - **Key refs:**
            - `src/bot/handlers/media/handler.py` — `handle_movie` (lines ~188-218), `handle_series` (lines ~220-250), `handle_music` (lines ~252-282) — near-identical
            - `src/bot/handlers/media/handler.py` — `handle_search` (lines ~284-342) — if/elif on search_type for search dispatch
            - `src/bot/handlers/media/handler.py` — `handle_selection` (lines ~664-775) — if/elif on search_type for add dispatch
            - `src/bot/handlers/media/handler.py` — `_add_media_with_profile` (lines ~1256-1270) — if/elif for add_with_profile dispatch
            - `src/bot/handlers/media/dispatch.py` — `MEDIA_CONFIG` dict with search/add/add_with_profile method names
        - **Watch out:**
            - `handle_search` invalid type path: `MEDIA_CONFIG.get(search_type)` returning `None` must still trigger the "Invalid search type" response and `ConversationHandler.END`
            - `handle_selection` music-type has special album: prefix stripping logic — this stays inline, dispatch only replaces the `add_movie`/`add_series`/`add_music` call
            - Entry point methods must keep `@require_auth` and `@rate_limit("search")` decorators
            - `log_user_interaction` call in `_start_search` should use `f"/{search_type}"` for the command name
    - **Scope:** Refactor entry points and 3 dispatch chains in handler.py
    - **Touches:**
        - Modify: `src/bot/handlers/media/handler.py`
    - **Action items:**
        - [GREEN] Add `_start_search(self, update, context, search_type)` to MediaHandler:
            - Guard clauses (effective_message, effective_user)
            - Admin restriction check using `MEDIA_CONFIG[search_type]["config_key"]`
            - Log interaction, set search_type in user_data
            - Show Title prompt with cancel button keyboard
            - Return SEARCHING
        - [GREEN] Simplify `handle_movie`, `handle_series`, `handle_music` to one-liner delegates:
            ```python
            @require_auth
            @rate_limit("search")
            async def handle_movie(self, update, context):
                return await self._start_search(update, context, "movie")
            ```
        - [GREEN] Replace if/elif in `handle_search` with dispatch:
            ```python
            media_cfg = MEDIA_CONFIG.get(search_type)
            if not media_cfg:
                await update.message.reply_text("❌ Invalid search type")
                return ConversationHandler.END
            results = await getattr(self.media_service, media_cfg["search"])(query)
            ```
        - [GREEN] Replace if/elif in `handle_selection` add call with dispatch:
            ```python
            add_fn = MEDIA_CONFIG[search_type]["add"]
            result = await getattr(self.media_service, add_fn)(media_id)
            ```
        - [GREEN] Replace if/elif in `_add_media_with_profile` with dispatch:
            ```python
            media_cfg = MEDIA_CONFIG.get(media_type)
            if not media_cfg:
                return False, "Invalid media type"
            return await getattr(self.media_service, media_cfg["add_with_profile"])(
                selected["id"], profile_id, root_folder
            )
            ```
        - Run full test suite: `python -m pytest --tb=short -q`
        - Run flake8: `python -m flake8 src/bot/handlers/media/`
        - Run architecture tests: `python -m pytest tests/test_architecture/ -v`
        - Verify line count: `wc -l src/bot/handlers/media/handler.py` — should be ~750 or less
        - Run coverage: `python -m pytest tests/test_handlers/test_media_handler.py --cov=src.bot.handlers.media --cov-report=term-missing`
    - **Success:** All tests pass. Flake8 clean. `handler.py` is ~750 lines or less. Coverage on media package is equivalent to before refactor.

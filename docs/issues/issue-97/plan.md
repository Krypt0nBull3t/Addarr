# Decompose MediaHandler Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Decompose the 1336-line `src/bot/handlers/media.py` into a `media/` package with dispatch tables, mixin classes, and extracted formatter utilities — reducing the main handler to ~750 lines with no behavior changes.

**Architecture:** Convert `media.py` to a `media/` package. Extract season picker and album picker flows into mixin classes that MediaHandler inherits from. Extract result display functions into a formatters module. Replace if/elif media-type branching with dispatch dictionaries. All existing tests must pass unchanged.

**Tech Stack:** Python 3.11, python-telegram-bot v20+, pytest, async/await

---

## Context

### Current State

`src/bot/handlers/media.py` is 1336 lines containing:
- `MediaHandler` class with 18 methods
- 3 near-identical entry points (`handle_movie`, `handle_series`, `handle_music`) — differ only in config key and search_type string
- if/elif chains in `handle_search`, `handle_selection`, `_add_media_with_profile` that branch on media type
- Season picker flow (~120 lines): `handle_season_selection`, `handle_season_confirm`
- Album picker flow (~170 lines): `handle_album_monitor_mode`, `handle_album_selection`, `handle_album_confirm`
- Result formatters (~200 lines): `_build_result_caption`, `_show_result`, `_show_list`, `_show_list_detail`, `_send_response`
- 5 module-level state constants: `SEARCHING`, `SELECTING`, `QUALITY_SELECT`, `SEASON_SELECT`, `ALBUM_SELECT`

### Target Structure

```
src/bot/handlers/media/
├── __init__.py          # Re-exports MediaHandler + state constants (backward compat)
├── handler.py           # MediaHandler class (~750 lines) — inherits mixins
├── dispatch.py          # MEDIA_CONFIG dict + state constants
├── formatters.py        # build_result_caption, show_result, show_list, etc.
├── season_picker.py     # SeasonPickerMixin class
└── album_picker.py      # AlbumPickerMixin class
```

### Import Compatibility

These existing import paths must continue to work (via `__init__.py` re-exports):

```python
# src/main.py
from src.bot.handlers.media import MediaHandler

# src/bot/handlers/start.py
from src.bot.handlers.media import MediaHandler, SEARCHING, SELECTING

# src/bot/handlers/__init__.py
from .media import MediaHandler

# tests/test_handlers/conftest.py
from src.bot.handlers.media import MediaHandler

# tests/test_handlers/test_media_handler.py
from src.bot.handlers.media import SEARCHING, SELECTING, QUALITY_SELECT, SEASON_SELECT, ALBUM_SELECT
```

### Architecture Test Impact

`tests/test_architecture/test_conventions.py:test_all_handlers_have_get_handler()` uses `_get_python_files(HANDLERS_DIR)` which only scans direct children of `src/bot/handlers/`. When `media.py` becomes `media/`, the function won't recurse into it. We must update `_get_python_files` to also walk into subdirectories so `MediaHandler` in `handler.py` is still checked.

The mixin classes (`SeasonPickerMixin`, `AlbumPickerMixin`) don't end in `Handler` so they won't trigger the `get_handler()` requirement.

### Test File Impact

The test file `tests/test_handlers/test_media_handler.py` (3034 lines) should remain untouched. Test fixture `media_handler` patches `src.bot.handlers.media.MediaService` — since the `__init__.py` imports from `handler.py`, the patch path `src.bot.handlers.media.MediaService` will resolve to the re-exported name. **However**, if `handler.py` imports `MediaService` at module level, the patch must target the module where the name is bound: `src.bot.handlers.media.handler.MediaService`. We need to verify this and may need to update the fixture patch path.

**Strategy to avoid test changes:** The `__init__.py` will do `from .handler import *` which means names like `MediaService` and `TranslationService` (imported in `handler.py`) are exposed at the package level. Test patches targeting `src.bot.handlers.media.MediaService` will still work because Python resolves the import through `__init__.py`.

Wait — that's not quite right. When `handler.py` does `from src.services.media import MediaService`, the name `MediaService` is bound in `handler.py`'s namespace. When `conftest.py` patches `src.bot.handlers.media.MediaService`, it patches the name in the `src.bot.handlers.media` package's `__init__.py`. But `handler.py`'s reference to `MediaService` is in its own module namespace (`src.bot.handlers.media.handler`), not the package's.

**Solution:** Have `handler.py` NOT import services directly. Instead, import them in `__init__.py` and have `handler.py` use late imports, OR — simpler — just update the conftest to patch `src.bot.handlers.media.handler.MediaService`. Since we want zero test changes, the safest approach is:

1. `handler.py` imports services at module level as before
2. `__init__.py` re-exports everything: `from .handler import MediaHandler, MediaService, TranslationService, PreferencesService`
3. The conftest `patch("src.bot.handlers.media.MediaService")` patches the name in `__init__.py`, but `handler.py` has its own binding
4. **This won't work without test changes.**

**Revised strategy:** We accept minimal test fixture updates. The `media_handler` fixture in `tests/test_handlers/conftest.py` needs patch paths changed from `src.bot.handlers.media.X` to `src.bot.handlers.media.handler.X`. This is a targeted, mechanical change (3 lines in one fixture). Similarly, `test_media_handler.py` state constant imports `from src.bot.handlers.media import SEARCHING` work fine because `__init__.py` re-exports them.

Actually, there's a cleaner solution: make `handler.py` import services from the package level:

```python
# handler.py
from src.bot.handlers.media import MediaService  # NO — circular import!
```

That would create a circular import. So the conftest patch path update is the cleanest approach.

### Conftest Patch Updates Required

In `tests/test_handlers/conftest.py`, the `media_handler` fixture changes:
```python
# Before:
patch("src.bot.handlers.media.MediaService")
patch("src.bot.handlers.media.TranslationService")
patch("src.bot.handlers.media.PreferencesService")

# After:
patch("src.bot.handlers.media.handler.MediaService")
patch("src.bot.handlers.media.handler.TranslationService")
patch("src.bot.handlers.media.handler.PreferencesService")
```

The `start_handler` fixture patches `src.bot.handlers.start.MediaHandler` — this still works because `start.py` imports from `src.bot.handlers.media` which re-exports `MediaHandler`.

---

## Phase 1: Foundation — Package Structure + Dispatch Tables

**Goal:** Convert `media.py` to a `media/` package, create `dispatch.py` with state constants and media config, create `__init__.py` with backward-compatible re-exports. Run tests to verify nothing breaks.

### Task 1.1: Create package structure with dispatch module

1. Delete `src/bot/handlers/media.py` and create `src/bot/handlers/media/` directory
2. Create `src/bot/handlers/media/dispatch.py` with:
   - State constants: `SEARCHING`, `SELECTING`, `QUALITY_SELECT`, `SEASON_SELECT`, `ALBUM_SELECT`
   - `MEDIA_CONFIG` dict mapping search_type → config key, service method names
3. Create `src/bot/handlers/media/handler.py` — move entire `MediaHandler` class here, importing states from dispatch
4. Create `src/bot/handlers/media/__init__.py` — re-export `MediaHandler` + state constants
5. Update conftest patch paths
6. Run full test suite — all must pass

**Key files:**
- Delete: `src/bot/handlers/media.py`
- Create: `src/bot/handlers/media/__init__.py`
- Create: `src/bot/handlers/media/dispatch.py`
- Create: `src/bot/handlers/media/handler.py`
- Modify: `tests/test_handlers/conftest.py` (3 patch paths)

### Task 1.2: Update architecture test for package-style handlers

1. Update `_get_python_files()` in `tests/test_architecture/test_conventions.py` to recurse into subdirectories
2. Verify `test_all_handlers_have_get_handler` still finds `MediaHandler` in `media/handler.py`
3. Verify mixin classes (not ending in `Handler`) are not checked
4. Run architecture tests

**Key files:**
- Modify: `tests/test_architecture/test_conventions.py`

---

## Phase 2: Extract Formatters

**Goal:** Move result display functions out of MediaHandler into standalone functions in `formatters.py`. These functions don't use `self.media_service` or `self.translation` — they only work with message objects and result dicts.

### Task 2.1: Extract formatter functions

1. Create `src/bot/handlers/media/formatters.py` with these functions (moved from MediaHandler):
   - `build_result_caption(result, index=None, total=None)` — was `_build_result_caption`
   - `show_result(message, result, index, total)` — was `_show_result`
   - `show_list(message, results, page, search_type)` — was `_show_list`
   - `show_list_detail(message, result)` — was `_show_list_detail`
   - `send_response(message, text, reply_markup=None)` — was `_send_response`
2. Update `handler.py` to import and call these functions instead of `self._method()`
3. The handler methods that call these functions need updating:
   - `handle_search` → calls `show_result(...)` and `show_list(...)`
   - `handle_list_select` → calls `show_list_detail(...)`
   - `handle_list_back` → calls `show_list(...)`
   - `handle_view_toggle` → calls `show_result(...)` and `show_list(...)`
   - `handle_navigation` → calls `show_result(...)`
   - `handle_selection` → calls `send_response(...)`
   - `handle_quality_selection` → calls `send_response(...)`
   - `handle_season_confirm` → calls `send_response(...)`
   - `handle_album_monitor_mode` → calls `send_response(...)`
   - `handle_album_selection` → calls `send_response(...)`
   - `handle_album_confirm` → calls `send_response(...)`
   - `cancel_search` → calls `send_response(...)`
4. Run full test suite

**Key files:**
- Create: `src/bot/handlers/media/formatters.py`
- Modify: `src/bot/handlers/media/handler.py`

**Note:** Tests that `patch.object(media_handler, "_show_result", ...)` will need updating to `patch("src.bot.handlers.media.formatters.show_result", ...)` or `patch("src.bot.handlers.media.handler.show_result", ...)` depending on the import style. Use `from .formatters import show_result` in handler.py so the patch target is `src.bot.handlers.media.handler.show_result`.

---

## Phase 3: Extract Season Picker Mixin

**Goal:** Move season selection logic into `SeasonPickerMixin` in `season_picker.py`.

### Task 3.1: Create SeasonPickerMixin

1. Create `src/bot/handlers/media/season_picker.py` with:
   ```python
   class SeasonPickerMixin:
       async def handle_season_selection(self, update, context): ...
       async def handle_season_confirm(self, update, context): ...
   ```
2. Move `handle_season_selection` and `handle_season_confirm` from handler.py to the mixin
3. The mixin methods access `self.media_service`, `self.translation` — these are provided by MediaHandler's `__init__`
4. The mixin imports: `send_response` from formatters, state constants from dispatch
5. Update `handler.py`: `class MediaHandler(SeasonPickerMixin, ...)`
6. Remove moved methods from handler.py
7. Run full test suite

**Key files:**
- Create: `src/bot/handlers/media/season_picker.py`
- Modify: `src/bot/handlers/media/handler.py`

---

## Phase 4: Extract Album Picker Mixin

**Goal:** Move album selection logic into `AlbumPickerMixin` in `album_picker.py`.

### Task 4.1: Create AlbumPickerMixin

1. Create `src/bot/handlers/media/album_picker.py` with:
   ```python
   class AlbumPickerMixin:
       async def handle_album_monitor_mode(self, update, context): ...
       async def handle_album_selection(self, update, context): ...
       async def handle_album_confirm(self, update, context): ...
   ```
2. Move `handle_album_monitor_mode`, `handle_album_selection`, `handle_album_confirm` from handler.py
3. The mixin imports: `send_response` from formatters, `get_album_selection_keyboard`/`get_album_monitor_mode_keyboard` from keyboards, state constants from dispatch
4. Update `handler.py` inheritance: `class MediaHandler(SeasonPickerMixin, AlbumPickerMixin)`
5. Remove moved methods from handler.py
6. Run full test suite

**Key files:**
- Create: `src/bot/handlers/media/album_picker.py`
- Modify: `src/bot/handlers/media/handler.py`

---

## Phase 5: Parameterize Entry Points + Replace Dispatch Chains

**Goal:** Collapse the 3 duplicate entry points into 1 shared helper, replace if/elif chains with dispatch dict lookups.

### Task 5.1: Parameterize entry points

1. Add `_start_search(self, update, context, search_type)` to MediaHandler in handler.py:
   ```python
   async def _start_search(self, update, context, search_type):
       if not update.effective_message or not update.effective_user:
           return ConversationHandler.END
       cfg_key = MEDIA_CONFIG[search_type]["config_key"]
       if config.get(cfg_key, {}).get("adminRestrictions", False):
           if update.effective_user.id not in config.get("admins", []):
               await update.message.reply_text("Access restricted to admins only.")
               return ConversationHandler.END
       log_user_interaction(logger, update.effective_user, f"/{search_type}")
       context.user_data["search_type"] = search_type
       prompt = self.translation.get_text("Title")
       keyboard = [[InlineKeyboardButton(
           f"❌ {self.translation.get_text('Cancel')}",
           callback_data="menu_cancel"
       )]]
       await update.message.reply_text(prompt, reply_markup=InlineKeyboardMarkup(keyboard))
       return SEARCHING
   ```
2. Simplify `handle_movie`, `handle_series`, `handle_music` to one-liners:
   ```python
   @require_auth
   @rate_limit("search")
   async def handle_movie(self, update, context):
       return await self._start_search(update, context, "movie")
   ```
3. Run full test suite

### Task 5.2: Replace dispatch chains in handle_search and handle_selection

1. In `handle_search`, replace if/elif with:
   ```python
   search_fn = MEDIA_CONFIG.get(search_type, {}).get("search")
   if not search_fn:
       await update.message.reply_text("❌ Invalid search type")
       return ConversationHandler.END
   results = await getattr(self.media_service, search_fn)(query)
   ```
2. In `handle_selection`, replace add_movie/add_series/add_music dispatch:
   ```python
   add_fn = MEDIA_CONFIG[search_type]["add"]
   result = await getattr(self.media_service, add_fn)(media_id)
   ```
3. In `_add_media_with_profile`, replace if/elif with:
   ```python
   add_fn = MEDIA_CONFIG.get(media_type, {}).get("add_with_profile")
   if not add_fn:
       return False, "Invalid media type"
   return await getattr(self.media_service, add_fn)(selected["id"], profile_id, root_folder)
   ```
4. Run full test suite

---

## Phase 6: Verification and Cleanup

### Task 6.1: Final verification

1. Run full test suite: `pytest --tb=short -q`
2. Run flake8: `python -m flake8 src/bot/handlers/media/`
3. Run architecture tests: `pytest tests/test_architecture/ -v`
4. Verify file sizes — handler.py should be ~750 lines or less
5. Run coverage on media handler: `pytest tests/test_handlers/test_media_handler.py --cov=src.bot.handlers.media --cov-report=term-missing`

---

## Risk Mitigation

1. **Import path breakage:** All external imports go through `__init__.py` re-exports. Only conftest patch paths need updating (targeted, mechanical).
2. **Mixin method resolution order:** Python MRO handles this cleanly. `MediaHandler(SeasonPickerMixin, AlbumPickerMixin)` means MediaHandler methods take priority, then SeasonPickerMixin, then AlbumPickerMixin.
3. **Circular imports:** Formatters and dispatch modules don't import from handler.py. Mixins import from formatters and dispatch but not handler. Handler imports from all sub-modules. No cycles.
4. **Architecture test gap:** Updated `_get_python_files` ensures MediaHandler is still checked.

## Line Count Estimate

| Module | Lines | Content |
|--------|-------|---------|
| `__init__.py` | ~15 | Re-exports |
| `dispatch.py` | ~25 | Constants + MEDIA_CONFIG |
| `formatters.py` | ~200 | 5 display functions |
| `season_picker.py` | ~130 | SeasonPickerMixin (2 methods) |
| `album_picker.py` | ~180 | AlbumPickerMixin (3 methods) |
| `handler.py` | ~750 | MediaHandler core (entry, search, selection, quality, nav, list) |
| **Total** | **~1300** | Comparable total but well-organized |

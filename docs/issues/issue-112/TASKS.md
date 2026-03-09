# Issue #112: Add Library Shortcut to Main Menu

## Summary

Add a "Library" button to the main menu that opens a sub-menu for browsing Movies, Series, or Music libraries, routing to the existing `LibraryHandler`.

---

### Phase 1: Translation & Keyboard Infrastructure (2 tasks)

**Goal:** Add translation keys and keyboard functions needed by the handler layer.

- [x] **1.1** Add translation keys and library menu keyboard
    - **Context:** See plan.md Tasks 1-2. Key refs: `translations/addarr.en-us.yml:37-41` (existing library keys), `src/bot/keyboards.py:20-71` (main menu pattern), `tests/test_bot/test_keyboards.py` (keyboard test pattern with `_mock_translation` helper)
    - **Watch out:** Use Unicode escapes (`\U0001f3ac`) not emoji literals in Python source (Windows cp1252 encoding). Translation keys must be flat top-level (not nested).
    - **Scope:** 2 new translation keys (`Library`, `LibraryPrompt`) in all 10 locale files + template, new `get_library_menu_keyboard()` function
    - **Touches:** `translations/addarr.*.yml`, `src/bot/keyboards.py`, `tests/test_bot/test_keyboards.py`
    - **Action items:**
        - [RED] Write tests for `get_library_menu_keyboard()` — returns markup, has `library_movie`/`library_series`/`library_music` callbacks, has `menu_back` button (~3 tests)
        - [GREEN] Add `Library` and `LibraryPrompt` keys to all locale files
        - [GREEN] Implement `get_library_menu_keyboard()` in `keyboards.py`
        - Validate translations: `PYTHONIOENCODING=utf-8 python run.py --validate-i18n`
    - **Success:** Keyboard tests pass, translation validation passes
    - **Completed:** 2026-03-09
    - **Learnings:** Unicode escapes work fine in keyboards.py. All locale files have identical structure after LibraryExpired line.
    - **Key Changes:** Added `Library`/`LibraryPrompt` keys to all 10 locales + template. Created `get_library_menu_keyboard()` in `keyboards.py`.
    - **Notes:** None

- [x] **1.2** Add Library button to main menu keyboard
    - **Context:** See plan.md Task 3. Key refs: `src/bot/keyboards.py:43-53` (insert new row after Delete), `tests/test_bot/test_keyboards.py:44-57` (expected callback list)
    - **Watch out:** Must update the existing `test_main_menu_keyboard_structure` test's expected list to include `menu_library`.
    - **Scope:** One new button row in `get_main_menu_keyboard()`, update existing test
    - **Touches:** `src/bot/keyboards.py`, `tests/test_bot/test_keyboards.py`
    - **Action items:**
        - [RED] Update existing main menu test to expect `menu_library` callback
        - [GREEN] Add Library button row to `get_main_menu_keyboard()` (after Delete, before Settings)
    - **Success:** Main menu keyboard test passes with `menu_library` in callback list
    - **Completed:** 2026-03-09
    - **Learnings:** Straightforward single-row addition. Used Unicode escape for book emoji.
    - **Key Changes:** Added Library button row to `get_main_menu_keyboard()`, updated test expected list.
    - **Notes:** Button placed after Delete, before Settings (row 4 of 7).

### Phase 2: Handler Wiring (2 tasks)

**Goal:** Wire the menu button to show the library sub-menu, and handle sub-menu selections via LibraryHandler.

- [x] **2.1** Handle `menu_library` in StartHandler
    - **Context:** See plan.md Task 4. Key refs: `src/bot/handlers/start.py:186-188` (upcoming pattern to follow — show keyboard, return END), `tests/test_handlers/conftest.py:122-165` (start_handler fixture needs `get_library_menu_keyboard` patch), `tests/test_handlers/test_start_handler.py:123-134` (upcoming test as pattern)
    - **Watch out:** Must return `ConversationHandler.END` so LibraryHandler's globally-registered `CallbackQueryHandler` can pick up `library_*` callbacks. Must patch `get_library_menu_keyboard` in the test fixture.
    - **Scope:** Import + 4-line handler block in `handle_menu_selection()`, fixture update, one new test
    - **Touches:** `src/bot/handlers/start.py`, `tests/test_handlers/conftest.py`, `tests/test_handlers/test_start_handler.py`
    - **Action items:**
        - [RED] Write test: `menu_library` shows library prompt with library keyboard, returns END (~1 test)
        - [GREEN] Update `start_handler` fixture to patch `get_library_menu_keyboard`
        - [GREEN] Add import + handler block in `handle_menu_selection()`
    - **Success:** All start handler tests pass including new library test
    - **Completed:** 2026-03-09
    - **Learnings:** Fixture needed `get_library_menu_keyboard` patch added to the `with` block. Returns END so LibraryHandler picks up sub-menu callbacks.
    - **Key Changes:** Added import + 4-line handler block in `start.py:handle_menu_selection()`. Updated `start_handler` fixture in conftest.
    - **Notes:** None

- [ ] **2.2** Add callback routing in LibraryHandler for sub-menu buttons
    - **Context:** See plan.md Task 5. Key refs: `src/bot/handlers/library.py:67-96` (`_fetch_and_show` pattern — but uses `update.message.reply_text`; callback version needs `query.message.edit_text`), `tests/test_handlers/test_library_handler.py:30-65` (parametrized command test pattern)
    - **Watch out:** Can't reuse `_fetch_and_show()` directly because it uses `update.message.reply_text` (for commands) while callbacks need `query.message.edit_text`. The new method handles the callback-specific flow separately. Register `library_` pattern handler BEFORE `lib_` in `get_handler()`.
    - **Scope:** New `handle_library_selection()` method, register `CallbackQueryHandler` in `get_handler()`
    - **Touches:** `src/bot/handlers/library.py`, `tests/test_handlers/test_library_handler.py`
    - **Action items:**
        - [RED] Write parametrized test for `library_movie`/`library_series`/`library_music` callbacks (~1 parametrized test = 3 cases)
        - [RED] Write edge case tests: no callback_query, unknown type, ValueError (not enabled), empty library (~4 tests)
        - [GREEN] Implement `handle_library_selection()` method
        - [GREEN] Register `CallbackQueryHandler(pattern="^library_")` in `get_handler()`
    - **Success:** All library handler tests pass, full suite passes

### Phase 3: Verification (1 task)

- [ ] **3.1** Full suite, coverage, lint, and translation validation
    - **Scope:** Run all checks, fix any gaps
    - **Action items:**
        - Run full test suite: `python -m pytest --tb=short -q`
        - Run scoped coverage on changed modules
        - Run lint: `python -m flake8 src/bot/keyboards.py src/bot/handlers/start.py src/bot/handlers/library.py`
        - Validate translations: `PYTHONIOENCODING=utf-8 python run.py --validate-i18n`
    - **Success:** All checks green, 100% coverage on new/changed lines

# Issue #98: Use Existing Translation Keys for Error Messages

## Summary

Replace ~29 hardcoded English error/status strings across 8 handler files with `TranslationService.get_text()` calls. Add 25 new flat translation keys to all locale files. Wire up TranslationService in handlers that don't yet use it.

---

### Phase 1: Translation Keys (1 task)

**Goal:** Add all new translation keys to YAML files so handlers can reference them.

- [x] **1.1** Add 25 new flat translation keys to all locale files
    - **Context:** See plan.md "New Translation Keys" table. `get_text()` only supports flat top-level keys — nested keys like `Error.NotFound` don't work. Keys use PascalCase. Must be added to template + all 9 locale files (en-us, de-de, es-es, fr-fr, it-it, nl-be, pl-pl, pt-pt, ru-ru). Non-English locales get English as placeholder (same pattern as existing keys).
    - **Watch out:** Keys must go BEFORE the closing of the locale block (not nested under `Error:` or any other section). The `--validate-i18n` script checks that all locale files have the same keys as template.
    - **Scope:** Add `# Error and status messages` section with all 25 keys to each file
    - **Touches:** `translations/addarr.template.yml`, `translations/addarr.en-us.yml`, 8 other locale files
    - **Action items:**
        - [GREEN] Add keys to `addarr.template.yml`
        - [GREEN] Add keys to `addarr.en-us.yml`
        - [GREEN] Add keys to all 8 other locale files (English placeholder text)
        - [GREEN] Run `PYTHONIOENCODING=utf-8 python run.py --validate-i18n` to verify
    - **Success:** `--validate-i18n` passes, all 10 files have the 25 new keys
    - **Completed:** 2026-03-09
    - **Learnings:** All locale files end with `QueueEmpty` as the last key before the new block. Translation keys use `%(var)s` syntax (Python %-formatting), not `%{var}` — must match what `get_text()` passes via `**kwargs`.
    - **Key Changes:** Added 25 new flat translation keys to all 10 locale files + template under `# Handler error and status messages` section.
    - **Notes:** Non-English locales have English placeholder text — translators will need to provide proper translations later.

---

### Phase 2: Replace Hardcoded Strings in Existing Handlers (2 tasks)

**Goal:** Replace hardcoded error strings with `get_text()` calls in handlers that already have `self.translation`.

- [ ] **2.1** Replace hardcoded strings in media handler package
    - **Context:** See plan.md Phase 2. `MediaHandler` has `self.translation` (TranslationService singleton). Mixin classes (`SeasonPickerMixin`, `AlbumPickerMixin`) inherit `self.translation` from the handler. `formatters.py` has standalone functions — use `TranslationService().get_text()` inline (singleton, error path only).
    - **Watch out:** `handler.py:491` uses f-string with `{str(e)}` — use `get_text("MediaAddError", error=str(e))` with `%{error}` substitution. `handler.py:622` returns a tuple `(False, message)` not a reply_text — use `get_text()` there too.
    - **Scope:** 14 string replacements across 4 files
    - **Touches:** `src/bot/handlers/media/handler.py`, `src/bot/handlers/media/formatters.py`, `src/bot/handlers/media/album_picker.py`, `src/bot/handlers/media/season_picker.py`
    - **Action items:**
        - [RED] Write tests for error paths in media handler (search error, invalid type, no results, selection errors)
        - [RED] Write tests for error paths in album_picker and season_picker (add error, fetch error, selection error)
        - [GREEN] Replace 8 hardcoded strings in `handler.py` with `self.translation.get_text()` calls
        - [GREEN] Replace 1 hardcoded string in `formatters.py` with `TranslationService().get_text()` (add import)
        - [GREEN] Replace 4 hardcoded strings in `album_picker.py` with `self.translation.get_text()` calls
        - [GREEN] Replace 1 hardcoded string in `season_picker.py` with `self.translation.get_text()` call
        - [GREEN] Run `pytest tests/test_handlers/test_media_handler.py tests/test_handlers/test_media_formatters.py -v`
    - **Success:** All media handler tests pass, no hardcoded English error strings remain in the media package

- [ ] **2.2** Replace hardcoded strings in delete and calendar handlers
    - **Context:** See plan.md Phase 2. Both handlers have `self.translation`. `delete.py` has 6 hardcoded strings across 3 branches (type selection, item selection, confirmation). `calendar.py` has 1 hardcoded string (`"Unknown media type"` at line 155).
    - **Watch out:** `delete.py` lines 105, 160, 218 all say `"❌ Invalid media type"` — consolidate to single key `InvalidMediaType`. The `"❌ Media type not found"` (line 148) is different from `InvalidMediaType` — it means `context.user_data` lost the type.
    - **Scope:** 7 string replacements across 2 files
    - **Touches:** `src/bot/handlers/delete.py`, `src/bot/handlers/calendar.py`
    - **Action items:**
        - [RED] Write tests for error paths in delete handler (invalid media type, media list error, item details error, item data not found)
        - [RED] Write test for unknown media type in calendar handler
        - [GREEN] Replace 6 hardcoded strings in `delete.py`
        - [GREEN] Replace 1 hardcoded string in `calendar.py`
        - [GREEN] Run `pytest tests/test_handlers/test_delete_handler.py tests/test_handlers/test_calendar_handler.py -v`
    - **Success:** All delete/calendar tests pass, no hardcoded English error strings remain

---

### Phase 3: Wire Up TranslationService in Remaining Handlers (2 tasks)

**Goal:** Add TranslationService to SystemHandler and TransmissionHandler, replace their hardcoded strings, update test fixtures.

- [ ] **3.1** Add TranslationService to SystemHandler and replace strings
    - **Context:** See plan.md Phase 3. `SystemHandler` currently has no `__init__` and no TranslationService. Need to add `__init__` with `self.translation = TranslationService()`. The `system_handler` fixture in `tests/test_handlers/conftest.py` (line 271-298) does NOT patch TranslationService — must add the patch. 5 hardcoded strings: `"Unknown action"` (line 68), `"Status refreshed"` (line 79), `"❌ Error refreshing status..."` (line 83), `"Refresh failed"` (line 86), `"❌ Error retrieving..."` (line 101), `"Details failed"` (line 104).
    - **Watch out:** The strings on lines 79, 86, 104 are `query.answer()` toast messages (short text shown briefly) — they still need translating. Must add `from src.services.translation import TranslationService` import.
    - **Scope:** Add TranslationService to handler, replace 5 strings, update fixture + tests
    - **Touches:** `src/bot/handlers/system.py`, `tests/test_handlers/conftest.py`, `tests/test_handlers/test_system_handler.py`
    - **Action items:**
        - [RED] Write tests for system handler error paths (refresh error, details error, unknown action)
        - [GREEN] Add `__init__` with TranslationService to `SystemHandler`
        - [GREEN] Replace 5 hardcoded strings with `self.translation.get_text()` calls
        - [GREEN] Update `system_handler` fixture to patch TranslationService
        - [GREEN] Update existing tests that assert on hardcoded English text
        - [GREEN] Run `pytest tests/test_handlers/test_system_handler.py -v`
    - **Success:** All system handler tests pass, TranslationService is used for all user-facing strings

- [ ] **3.2** Add TranslationService to TransmissionHandler and replace strings
    - **Context:** See plan.md Phase 3. `TransmissionHandler.__init__` exists but only sets `self.service`. The `transmission_handler` fixture already patches `TranslationService` at `src.bot.handlers.transmission.TranslationService` (conftest.py line 173) — no fixture change needed. But the handler doesn't import or use it. 3 hardcoded strings: not-enabled message (line 46-48), connection error (line 54-55), toggle failed (line 95). Existing tests assert on `"not enabled"` and `"connect"` in lowercase — these will break when output becomes translation keys.
    - **Watch out:** The `transmission_handler` fixture patches `TranslationService` but the actual handler code `from src.bot.handlers.transmission import TransmissionHandler` doesn't import `TranslationService` — so the patch target `src.bot.handlers.transmission.TranslationService` won't exist yet. Must add the import first. Also: existing tests import `TransmissionHandler` directly inside the test function and bypass the fixture — check both patterns.
    - **Scope:** Add TranslationService usage to handler, replace 3 strings, update tests
    - **Touches:** `src/bot/handlers/transmission.py`, `tests/test_handlers/test_transmission_handler.py`
    - **Action items:**
        - [RED] Write test for transmission toggle failed error path
        - [GREEN] Add `from src.services.translation import TranslationService` to handler
        - [GREEN] Add `self.translation = TranslationService()` in `__init__`
        - [GREEN] Replace 3 hardcoded strings with `self.translation.get_text()` calls
        - [GREEN] Update existing tests that assert on hardcoded English text (`"not enabled"`, `"connect"`)
        - [GREEN] Run `pytest tests/test_handlers/test_transmission_handler.py -v`
    - **Success:** All transmission handler tests pass, TranslationService is used for all user-facing strings

---

### Phase 4: Final Verification (1 task)

**Goal:** Full test suite, lint, and i18n validation pass.

- [ ] **4.1** Run full preflight checks
    - **Context:** All handler changes and translation keys are in place. Run the full CI-equivalent checks.
    - **Scope:** pytest, flake8, validate-i18n
    - **Action items:**
        - [GREEN] Run `pytest --tb=short -q`
        - [GREEN] Run `python -m flake8 .`
        - [GREEN] Run `PYTHONIOENCODING=utf-8 python run.py --validate-i18n`
        - [GREEN] Run `pytest --cov=src.bot.handlers --cov=src.services.translation --cov-report=term-missing` — check coverage on changed modules
        - [GREEN] Fix any failures
    - **Success:** All checks pass, no regressions

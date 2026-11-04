# Issue 196 Tasks: /delete wrong item, hidden file deletion, key cap

Plan: `docs/issues/issue-196/plan.md`. Design: `docs/issues/issue-196/design.md`.
Branch: `fix/196-delete-wrong-media`. PR targets `development`.

### Phase 1: Safe /delete (4 tasks)

**Goal:** /delete acts on the type and item its button was drawn for, says that files are deleted too, and pages large libraries.

**Phase Context:**

- Why NOT keep `user_data`: the stale list is the bug. State read at tap time cannot match the button drawn earlier.
- Why NOT a keep-files option: decided 2026-10-28. The prompt says it. `deleteFiles=true` and `enableAdmin` stay.
- Why the helper lives here: issue #223 (F265) is open. It specifies `_build_pagination_row`. #223 replaces the other 5 copies later.

- [ ] **1.1** ThisDelete names the title and the files (F003, F001)
    - **Context:**
        - **Why:** The confirm text has no title and does not say the files on disk are deleted. The handler passes `title=` but `ThisDelete` has no `%{title}`.
        - **Architecture:** `TranslationService.get_message("ThisDelete", subject=..., title=...)` reads `messages.ThisDelete`. `get_message` adds `title` to the params (`src/services/translation.py:118`).
        - **Key refs:** `translations/addarr.en-us.yml:59`, `translations/addarr.template.yml:63`, line 71 of the other 8 locale files. Existing real-file tests: `tests/test_services/test_translation_service.py`, `tests/test_utils/test_validate_translations.py`.
        - **Watch out:** The autouse translation mock hides this bug, so the new test must read the real YAML files. Keep each value's leading emoji. Keep fr, it, pt and de plain: #224 (F211) rewrites them. The files are `ru-ru`, `pl-pl`, `pt-pt`, `es-es`, `it-it`, `fr-fr`, `de-de`, `nl-be`, `en-us`.
    - **Scope:** New `ThisDelete` text in 9 locale files and the template. No handler change.
    - **Touches:** `translations/addarr.*.yml`, `tests/test_services/test_delete_prompt_translations.py` (new)
    - **Action items:**
        - [RED] Write a test that loads every real `translations/addarr.*.yml` and asserts `%{title}` is in `messages.ThisDelete`, with a guard that 10 files are found
        - [RED] Write a test that the en-us text contains `files on disk`
        - [GREEN] Edit the 10 files with the texts in `plan.md` Task 1
        - [GREEN] Run `PYTHONIOENCODING=utf-8 python run.py --validate-i18n`
    - **Success:** New tests fail before and pass after. `--validate-i18n`, flake8 and the translation tests pass.

- [ ] **1.2** Paged delete item keyboard (F004)
    - **Context:**
        - **Why:** /delete builds one button per item. A library of about 100 items or more makes Telegram reject the keyboard, and the handler shows `MediaListError`.
        - **Architecture:** Keyboard builders live in `src/bot/keyboards.py` and take `translation` as a parameter. `library.py` pages with `ITEMS_PER_PAGE = 10`.
        - **Key refs:** `src/bot/keyboards.py:869` (`_build_dl_pagination_row`, the only existing helper), `src/bot/handlers/delete.py:124-139` (the code this replaces).
        - **Watch out:** `_build_pagination_row(prefix, page, total_pages) -> list` clamps the page and returns `[]` for one page. `get_delete_items_keyboard` must clamp too, so a stale page shows the last page. Callback data stays under 64 bytes. Leave the 5 other pagination copies alone.
    - **Scope:** `_build_pagination_row`, `DELETE_PAGE_SIZE = 10`, `get_delete_items_keyboard(items, media_type, page, translation)`.
    - **Touches:** `src/bot/keyboards.py`, `tests/test_bot/test_keyboards.py`
    - **Action items:**
        - [RED] Write tests for the row: one page gives `[]`, a middle page has Prev and Next, the first page only Next, a page past the end clamps to the last, a negative page clamps to the first
        - [RED] Write tests for the keyboard: 150 movies give 10 item buttons then a nav row then the cancel row, exactly 10 items give no nav row, page 9 of 25 items shows items 21 to 25, a 10-digit series id stays under 64 bytes
        - [GREEN] Implement both functions
    - **Success:** `scripts/test_runner.py bot --coverage` passes, flake8 and mypy clean.

- [ ] **1.3** Handler reads type and id from callback_data (F002, F004)
    - **Context:**
        - **Why:** `delete.py` reads `user_data["delete_type"]` and `user_data["delete_item"]` at tap time. Radarr and Sonarr ids collide, so a tap on an old list deletes a different item.
        - **Architecture:** `DeleteHandler.handle_delete_selection` is one callback handler for `^delete_`, decorated with `@require_auth` and `@require_admin()`. Callbacks after this task: `delete_type_<type>`, `delete_page_<type>_<n>`, `delete_item_<type>_<id>`, `delete_confirm_<type>_<id>`, `delete_cancel`.
        - **Key refs:** `src/bot/handlers/delete.py:83-261`, `src/services/media.py:807-912` (get and delete methods; ids are strings, the service casts with `int()`), `tests/test_handlers/test_delete_handler.py`.
        - **Watch out:** Write nothing to `user_data`. The confirm step refetches the item for the title and shows `NoExist` when it is gone, with no delete call. Check `<id>` and `<n>` with `str.isdigit()`: a bad value shows `ItemDataNotFound` and calls no service. An unknown type shows `InvalidMediaType`. Rewrite the old tests that set `user_data["delete_type"]`.
    - **Scope:** Callback parsing, helper dispatch methods, paging callback, removal of `user_data` use.
    - **Touches:** `src/bot/handlers/delete.py`, `tests/test_handlers/test_delete_handler.py`
    - **Action items:**
        - [RED] Write tests: `delete_item_movie_42` with `user_data["delete_type"] = "series"` calls `get_movie("42")` and never `get_series`; `delete_confirm_movie_42` calls `delete_movie("42")` whatever `user_data` holds
        - [RED] Write tests: confirm for a missing item shows `NoExist` and does not delete; non-digit ids and unknown types are rejected; no `user_data` key is written
        - [RED] Write tests: 150 movies give one page of item buttons plus a nav row and no `MediaListError`; `delete_page_series_2` refetches series, not movies
        - [GREEN] Implement the parsing, `_fetch_items`, `_fetch_item`, `_delete_item` and the paging callback
        - [GREEN] Keep the existing tests for cancel, no items, service errors, confirm failure and exception on the new callback shapes
    - **Success:** `scripts/test_runner.py handlers --coverage` passes with no uncovered new lines, flake8 and mypy clean.

- [ ] **1.4** Integration flow and callback registry
    - **Context:**
        - **Why:** The bug is a cross-message flow (two /delete lists), so only an end-to-end test shows it. The callback registry must list the new shapes.
        - **Architecture:** `BotHarness` in `tests/integration/conftest.py` drives updates through the real handlers.
        - **Key refs:** `tests/integration/` (look for an existing delete flow), `.claude/skills/addarr-handlers/references/callbacks.md:42`.
        - **Watch out:** `tests/test_architecture/test_skills.py` checks that names in skills exist. Run the architecture tests after the doc edit.
    - **Scope:** One integration test for the happy path and one for the stale list, plus the registry line.
    - **Touches:** `tests/integration/` (extend or add), `.claude/skills/addarr-handlers/references/callbacks.md`
    - **Action items:**
        - [RED] Write the happy-path test: /delete, Movies, an item, confirm
        - [RED] Write the stale-list test: open Movies, then Series, tap a movie button, expect `get_movie` and not `get_series`
        - [GREEN] Update the `delete_` registry line to the new callback shapes
    - **Success:** `pytest tests/integration` and `pytest tests/test_architecture` pass.

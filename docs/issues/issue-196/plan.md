# Issue 196 Implementation Plan: /delete wrong item, hidden file deletion, key cap

**Goal:** /delete acts on the exact type and item the tapped button was drawn for, says in the
prompt that the files on disk are deleted too, and pages large libraries.

**Architecture:** Callback data carries the type and the id, so the handler keeps no state in
`user_data`. A new keyboard builder in `src/bot/keyboards.py` pages the item list through a new
shared `_build_pagination_row`. `ThisDelete` gets a `%{title}` placeholder and a files warning
in all locales.

**Tech Stack:** python-telegram-bot v20, pytest with the project fixtures, YAML translations.

**Design:** `docs/issues/issue-196/design.md`

## Global Constraints

- Branch `fix/196-delete-wrong-media`, PR targets `development`.
- `deleteFiles=true` in `src/api/radarr.py:321`, `sonarr.py:332`, `lidarr.py:322` stays. No config change, no keep-files option, `enableAdmin` default unchanged.
- `callback_data` is at most 64 bytes.
- Config access uses `config.get()`, never `config["key"]`. Optional params use `Optional[...]`.
- New user-facing text goes through `TranslationService`. Check with `PYTHONIOENCODING=utf-8 python run.py --validate-i18n`.
- Keep the other 5 pagination copies in `keyboards.py` as they are (#223).
- Every test, gate and `git push` runs through the suite lock.

## Review Focus

- A page number past the end (stale button) shows the last page, not an empty list.
- A library with exactly 10 items shows no nav row. With 11 items it shows one.
- `delete_item_movie_abc` (non-digit id) deletes and fetches nothing.
- `delete_type_<type>` still lists items and `delete_cancel` still ends the flow.
- A library of 150 items never produces `MediaListError`.
- A confirm tap for an item that is already gone shows `NoExist` and calls no delete.

## File Structure

- `translations/addarr.*.yml` (9 files) and `translations/addarr.template.yml`: new `ThisDelete` text.
- `src/bot/keyboards.py`: new `_build_pagination_row`, new `get_delete_items_keyboard`.
- `src/bot/handlers/delete.py`: parse type and id from callbacks, drop `user_data`, add paging.
- `.claude/skills/addarr-handlers/references/callbacks.md`: the `delete_` registry line.
- Tests: `tests/test_services/test_delete_prompt_translations.py` (new), `tests/test_bot/test_keyboards.py`, `tests/test_handlers/test_delete_handler.py`, `tests/integration/` (check for a delete flow).

## Task 1: ThisDelete names the title and the files (F003, F001)

**Files:**
- Test: `tests/test_services/test_delete_prompt_translations.py` (new)
- Modify: `translations/addarr.en-us.yml:59`, `translations/addarr.template.yml:63`, and line 71 of the other 8 locale files.

**Interfaces:** Produces the new `messages.ThisDelete` text. The handler already passes `subject` and `title` to `get_message("ThisDelete", ...)`.

- [ ] **Step 1: Write the failing tests.** Read every real `translations/addarr.*.yml` (not through the autouse mock) with `yaml.safe_load` and `pathlib`.
  - `test_this_delete_has_title_placeholder` parametrized over all files incl. the template: `"%{title}" in data["messages"]["ThisDelete"]`.
  - `test_en_us_this_delete_says_files_are_deleted`: the en-us text contains `files on disk`.
  - A guard that the glob finds 10 files, so the test cannot pass on an empty list.
- [ ] **Step 2: Run them, expect FAIL** (`pytest tests/test_services/test_delete_prompt_translations.py -v`).
- [ ] **Step 3: Edit the 10 files.** `%{subjectWithArticle}` stays. Each value keeps the leading emoji it has now. Only the text after it changes. New text:
  - en-us, template: `Is this %{subjectWithArticle} you want to delete: %{title}? It and its files on disk are deleted too.`
  - ru: `Этот %{subjectWithArticle} вы хотите удалить: %{title}? Файлы на диске тоже будут удалены.`
  - pl: `Czy to jest %{subjectWithArticle} który chcesz usunąć: %{title}? Pliki na dysku też zostaną usunięte.`
  - pt: `É este %{subjectWithArticle} que pretende eliminar: %{title}? Os ficheiros no disco também são eliminados.`
  - es: `¿Es esta %{subjectWithArticle} que quieres eliminar: %{title}? Los archivos del disco también se eliminan.`
  - it: `Vuoi eliminare questo %{subjectWithArticle}: %{title}? Anche i file sul disco vengono eliminati.`
  - fr: `Ce %{subjectWithArticle} est-il à supprimer : %{title} ? Les fichiers sur le disque sont aussi supprimés.`
  - de: `Möchten sie %{subjectWithArticle} wirklich löschen: %{title}? Die Dateien auf dem Datenträger werden auch gelöscht.`
  - nl-be: `Is dit %{subjectWithArticle} die je wilt verwijderen: %{title}? De bestanden op schijf worden ook verwijderd.`
- [ ] **Step 4: Run the new tests and `PYTHONIOENCODING=utf-8 <lock> .venv/bin/python run.py --validate-i18n`, expect PASS.**
- [ ] **Step 5: Commit** `fix: name the title and the files in the delete prompt (#196, task 1)`.

## Task 2: Paged delete item keyboard (F004)

**Files:**
- Test: `tests/test_bot/test_keyboards.py`
- Modify: `src/bot/keyboards.py` (next to the other builders)

**Interfaces:**
- Produces `_build_pagination_row(prefix: str, page: int, total_pages: int) -> list` : the Prev/Next buttons for the page, clamped into `0..total_pages-1`. It returns `[]` when `total_pages <= 1`. Prev has callback `f"{prefix}_{page - 1}"`, Next `f"{prefix}_{page + 1}"`. There is no middle button.
- Produces `DELETE_PAGE_SIZE = 10` and `get_delete_items_keyboard(items: list, media_type: str, page: int, translation) -> InlineKeyboardMarkup`. It clamps the page, adds one button per item of that page (text `item["title"]`, callback `delete_item_{media_type}_{item["id"]}`), then the nav row from the helper with prefix `delete_page_{media_type}`, then the `StopDelete` button with `delete_cancel`, built as in the current handler, emoji prefix included.

- [ ] **Step 1: Write the failing tests** in `test_keyboards.py`:
  - `test_pagination_row_single_page_is_empty`, `test_pagination_row_middle_has_prev_and_next`, `test_pagination_row_first_has_only_next`, `test_pagination_row_past_end_clamps_to_last` (page 99 of 3: one Prev button with `..._1`), `test_pagination_row_negative_page_clamps_to_first`.
  - `test_delete_items_keyboard_150_movies`: 150 items, page 0 gives 10 item buttons, then a nav row with only Next (`delete_page_movie_1`), then the cancel row.
  - `test_delete_items_keyboard_exactly_one_page`: 10 items gives no nav row.
  - `test_delete_items_keyboard_past_end_shows_last_page`: 25 items, page 9 shows items 21 to 25.
  - `test_delete_items_keyboard_callback_data_under_64_bytes`: the series type with a 10-digit id.
- [ ] **Step 2: Run, expect FAIL** (names not defined).
- [ ] **Step 3: Implement both functions.** Page count is `max(1, ceil(len(items) / DELETE_PAGE_SIZE))`.
- [ ] **Step 4: Run `tests/test_bot/test_keyboards.py`, expect PASS.**
- [ ] **Step 5: Commit** `feat: paged delete item keyboard (#196, task 2)`.

## Task 3: Handler reads type and id from callback_data (F002, F004)

**Files:**
- Test: `tests/test_handlers/test_delete_handler.py`
- Modify: `src/bot/handlers/delete.py`

**Interfaces:**
- Consumes `get_delete_items_keyboard` from Task 2.
- Callbacks after this task: `delete_type_<type>`, `delete_page_<type>_<n>`, `delete_item_<type>_<id>`, `delete_confirm_<type>_<id>`, `delete_cancel`.
- Produces `DeleteHandler._fetch_items(media_type)` and `_fetch_item(media_type, item_id)`: dispatch to `media_service.get_movies/get_series/get_music` and `get_movie/get_series/get_music`. An unknown type raises `ValueError`; the caller shows `InvalidMediaType`. `_delete_item(media_type, item_id)` does the same for `delete_movie/delete_series/delete_music`.

- [ ] **Step 1: Write the failing tests** (rewrite the old `user_data`-based ones in the same file):
  - `test_item_callback_ignores_user_data_type`: `user_data["delete_type"] = "series"`, tap `delete_item_movie_42`: `get_movie` awaited with `"42"`, `get_series` not called, the confirm keyboard holds `delete_confirm_movie_42`, the prompt text includes the title.
  - `test_confirm_callback_ignores_user_data`: `user_data` holds another type and item, tap `delete_confirm_movie_42`: `delete_movie` awaited with `"42"`, `delete_series` not called. The success text names the refetched title.
  - `test_confirm_item_gone_shows_no_exist`: `get_movie` returns `None`, `delete_movie` is not called.
  - `test_item_and_confirm_non_digit_id_rejected`: `delete_item_movie_abc` and `delete_confirm_movie_abc` call no service method and show `ItemDataNotFound`.
  - `test_item_callback_unknown_type`: `delete_item_book_1` shows `InvalidMediaType`.
  - `test_type_callback_150_movies_shows_one_page_and_nav_row`: 150 movies, one page of item buttons plus a nav row, `MediaListError` never sent.
  - `test_page_callback_refetches_list_for_its_own_type`: `delete_page_series_2` calls `get_series`, not `get_movies`, and shows the third page.
  - Keep the existing tests for cancel, no query, no items, service exceptions, confirm failure and exception, with the new callback shapes.
  - Confirm no `context.user_data` key is written by any of these flows.
- [ ] **Step 2: Run, expect FAIL.**
- [ ] **Step 3: Implement.** Parse `action` after `delete_`: `type_<t>`, `page_<t>_<n>`, `item_<t>_<id>`, `confirm_<t>_<id>` (split on `_`, `<id>` and `<n>` checked with `str.isdigit()`). Remove all `user_data` use. The item list step uses `get_delete_items_keyboard(items, media_type, page, self.translation)` for both `type_` (page 0) and `page_`. Keep `@require_auth` and `@require_admin()`.
- [ ] **Step 4: Run `tests/test_handlers/test_delete_handler.py`, expect PASS.**
- [ ] **Step 5: Commit** `fix: delete buttons carry the media type and id (#196, task 3)`.

## Task 4: Integration flow and docs

**Files:**
- Test: `tests/integration/` (extend the existing delete flow test when there is one, else add one with the `BotHarness`)
- Modify: `.claude/skills/addarr-handlers/references/callbacks.md:42`

- [ ] **Step 1: Check `tests/integration/` for a /delete flow.** Extend or add the happy path: /delete, Movies, an item, confirm. Add the stale-list case: open Series after Movies, tap the movie button, expect `get_movie` and not `get_series`.
- [ ] **Step 2: Update the `delete_` registry line** to the new callback shapes. Run `<lock> .venv/bin/python -m pytest tests/test_architecture --tb=short -v`.
- [ ] **Step 3: Commit** `test: delete flow end to end, update callback registry (#196, task 4)`.

## Verification (preflight, in the create-pr flow)

`flake8`, `mypy src/`, `PYTHONIOENCODING=utf-8 python run.py --validate-i18n`, unit tests with the 100% coverage gate, integration tests and architecture tests, all under the suite lock. Then run `arr-api-contract-checker` only if `src/api/` changed (it does not).

## Self-review

- F003, F001: Task 1. F002: Task 3 (and the stale-list integration test in Task 4). F004: Tasks 2 and 3.
- Names match across tasks: `get_delete_items_keyboard`, `_build_pagination_row`, `DELETE_PAGE_SIZE`.

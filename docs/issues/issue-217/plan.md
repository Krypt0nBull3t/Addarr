# Issue 217: Fix stuck spinners and dead ends in Telegram navigation

**Goal:** Every tap stops its spinner, every screen has a way back to its parent, filters start at "all" and keep their row when empty, and Cancel works on photo messages.

**Architecture:** Handler and keyboard fixes only. Reuse `edit_text_ignoring_unmodified` (`src/utils/chat.py`) and `formatters.send_response` (`src/bot/handlers/media/formatters.py`). No new service, state, config key or translation key.

**Tech stack:** python-telegram-bot 22.8, pytest with `AsyncMock`. Tests reuse `unchanged_edit` in `tests/test_handlers/conftest.py`: it makes `edit_text` raise `BadRequest("Message is not modified")` and records the order of `answer` and `edit` calls.

**Spec:** `docs/issues/issue-217/design.md` and issue #217. Line numbers are from `cf51f57`.

## Global constraints

- `flake8` (max line 88, `.flake8` ignores E203, E501, W503), `mypy src/`, 100% coverage gate.
- Every handler entry point keeps `@require_auth`. Config access uses `config.get()`.
- Use `Optional[...]`, not `X | None`.
- Each test must fail before its fix and pass after. Run it red first.
- Out of scope: `_handle_page` in queue, missing and history; the other pagination copies (#223).

## Review focus

- Re-tap of the same filter or tab, with unchanged text: no exception, spinner stops (Task 3).
- Filter with zero matching items: filter row stays, so the user can leave (Task 4).
- Cancel on a poster photo message: caption edited, no `BadRequest` (Task 2).
- Back from SAB speed and from quality lands on the parent screen, not the root (Task 6).
- Help, library list and Bazarr wanted lists, empty and non-empty, each show Back (Task 5).

## File structure

| File | Change |
|-|-|
| `src/bot/handlers/media/handler.py` | F111: `query.answer()` first in `handle_menu_callback` |
| `src/bot/handlers/start.py` | F114: cancel uses `send_response` |
| `src/bot/handlers/queue.py`, `missing.py`, `history.py` | F110, F115 |
| `src/bot/handlers/downloads.py`, `system.py`, `settings.py` | F110, F112 |
| `src/bot/handlers/help.py`, `library.py`, `bazarr.py` | F113 |
| `src/bot/keyboards.py` | F112: quality Back callback |
| `tests/test_handlers/test_*_handler.py`, `tests/test_bot/` keyboard tests | One test per acceptance line |

## Task 1: F111, answer the menu callback first

**Files:** modify `src/bot/handlers/media/handler.py:160` (`handle_menu_callback`); test `tests/test_handlers/test_media_handler.py`.

- [ ] Write `test_handle_menu_callback_movie_answers_query`: `make_update(callback_data="menu_movie")`, call `handle_menu_callback`, assert `query.answer.assert_awaited_once()` and the return value is `SEARCHING`.
- [ ] Run it, expect FAIL (`answer` not awaited).
- [ ] Move `await query.answer()` to just after `query = update.callback_query`. Remove the one in the cancel branch.
- [ ] Run `tests/test_handlers/test_media_handler.py`, expect PASS.
- [ ] Commit.

## Task 2: F114, Cancel on a photo message

**Files:** modify `src/bot/handlers/start.py:92`; test `tests/test_handlers/test_start_handler.py`.

- [ ] Write `test_cancel_on_photo_message_edits_caption`: callback `menu_cancel`, `query.message.photo = [MagicMock()]`. Assert `query.message.edit_caption` is awaited and `edit_text` is not awaited.
- [ ] Run it, expect FAIL.
- [ ] In `start.py`, import `send_response` from `src.bot.handlers.media.formatters` and replace `query.message.edit_text(...)` in the cancel branch with `await send_response(query.message, self.translation.get_text("Canceled"))`.
- [ ] Run `test_start_handler.py` and `tests/test_architecture`, expect PASS (handlers may import handlers).
- [ ] Commit.

## Task 3: F110, spinner never hangs on a re-tap

**Files:** modify `queue.py:104`, `missing.py:110`, `history.py:105`, `downloads.py:323`, `settings.py:648`, `system.py:150`, `:170`; tests in `test_queue_handler.py`, `test_missing_handler.py`, `test_history_handler.py`, `test_downloads_handler.py`, `test_settings_handler.py`, `test_system_handler.py`.

For each handler path, one test with `calls = unchanged_edit(update.callback_query)`:

- [ ] `test_filter_unchanged_message` in queue, missing, history: callback `<prefix>_filter_movie` (history: `hist_filter_all`), assert `calls == ["answer", "edit"]` and no exception. Expect FAIL (BadRequest raised, answer never runs).
- [ ] `test_tab_unchanged_message` and `test_refresh_unchanged_message` in downloads (`dl_tab_queue`, `dl_refresh`), and `test_pause_all_twice_unchanged_message` (`dl_pauseall`, service returns True): no exception, `query.answer` awaited.
- [ ] `test_sab_pause_unchanged_message` in settings (`dl_sab_pause`): no exception, `answer` awaited.
- [ ] `test_details_unchanged_message`, `test_diskspace_unchanged_message` in system (`system_details`, `system_diskspace`): `calls == ["answer", "edit"]`.
- [ ] Implement: in queue, missing and history `_handle_filter`, call `await query.answer()` then `edit_text_ignoring_unmodified(query.message, text, reply_markup=keyboard)`. In `downloads._refresh_current_view` and `settings.handle_sabnzbd_pause_resume`, use the helper. In `system._handle_details` and `_handle_diskspace`, build the text, `await query.answer()`, then use the helper (keep `parse_mode="Markdown"` on disk space). Keep each `except` branch as it is.
- [ ] Run the six test files, expect PASS.
- [ ] Commit.

## Task 4: F115, filters reset and keep their row

**Files:** modify `queue.py:48`, `:144-159`; `missing.py:48`, `:100-103`, `:174-189`; `history.py:147-161`; tests in `test_queue_handler.py`, `test_missing_handler.py`, `test_history_handler.py`.

- [ ] `test_show_queue_resets_stored_filter`: `user_data={"queue_filter": "movie"}`, run `show_queue`, assert `user_data["queue_filter"] == "all"`. Same for `show_missing` and `missing_filter`.
- [ ] `test_empty_filtered_view_keeps_filter_row` for queue (`queue_filter_album` on movie-only items), missing (`missing_filter_series`, movie-only items) and history (`hist_filter_grabbed`, `get_history` returns `[]`): assert `_mock_items_kbd` is called and `_mock_empty_kbd` is not.
- [ ] `test_cutoff_then_movie_refetches_missing`: `user_data={"missing_filter": "cutoff", "missing_items": [cutoff_movie]}`, callback `missing_filter_movie`, assert `get_missing_media` awaited once and `missing_items` equals its result. Same for `missing_filter_series`.
- [ ] Run, expect FAIL.
- [ ] Implement: `user_data["queue_filter"] = "all"` and `user_data["missing_filter"] = "all"` in `show_*`. In the three `_build_response` methods, keep the "empty" text when `items` is empty, but pick the items keyboard when `items` or a filter other than all (`active_filter != "all"`, history `event_filter is not None`) is set; pick the empty keyboard otherwise. In `missing._handle_filter`, for `movie` and `series`, call `get_missing_media()` and store it in `missing_items`.
- [ ] Run the three files, expect PASS.
- [ ] Commit.

## Task 5: F113, Back buttons and a `bazarr_menu` button

**Files:** modify `help.py:73`, `library.py:214`, `bazarr.py:176-220`; tests `test_help_handler.py`, `test_library_handler.py`, `test_bazarr_handler.py`.

- [ ] `test_help_callback_has_back_button`: `menu_help` path (`show_help` with a callback update). Assert the `reply_markup` has a button with `callback_data == "menu_back"`.
- [ ] `test_library_list_keyboard_has_back_button`: `_build_page_message` for one page and for several pages. Assert a button `menu_library` in both (single page used to return `None`).
- [ ] `test_wanted_movies_has_back_button`, `test_wanted_episodes_has_back_button`, and the two empty variants: assert `reply_markup` has `callback_data == "bazarr_menu"`.
- [ ] Run, expect FAIL.
- [ ] Implement: `help.show_help` passes a one-button keyboard (`Back`, `menu_back`) in both the callback and the message branch. `library._build_page_message` appends a Back row (`menu_library`) and always returns a markup. `bazarr` adds a private `_back_keyboard()` (`Back`, `bazarr_menu`, label from `TranslationService.get_text("Back")`) and passes it to the four `edit_message_text` calls in `wanted_movies` and `wanted_episodes`.
- [ ] Run the three files, expect PASS.
- [ ] Commit.

## Task 6: F112, Back goes to the parent

**Files:** modify `src/bot/keyboards.py:326` (`get_quality_profile_keyboard`); `settings.py:109-118` (state map), `:602-605` (SAB speed Back), `:710-718` (`handle_back`); tests `test_settings_handler.py`, keyboard test file for `get_quality_profile_keyboard`.

- [ ] `test_quality_keyboard_back_returns_to_service_menu`: `get_quality_profile_keyboard(profiles, "radarr")`, assert the last button is `settings_radarr`.
- [ ] `test_sab_speed_back_callback_is_sab_menu`: `handle_sabnzbd_speed` with `dl_sab_speed`, assert the Back button is `dl_sabnzbd`.
- [ ] `test_quality_state_routes_service_menu_back`: the `SETTINGS_QUALITY` handler list has a handler whose pattern matches `settings_radarr` and calls `handle_service_menu`.
- [ ] `test_back_from_settings_shows_main_menu_before_end`: `handle_back` returns `ConversationHandler.END`, and `edit_text` is awaited with `reply_markup=get_main_menu_keyboard()` and the main menu text.
- [ ] Run, expect FAIL.
- [ ] Implement: quality Back `callback_data=f"settings_{service}"`; SAB speed Back `dl_sabnzbd`; add `CallbackQueryHandler(self.handle_service_menu, pattern="^settings_(radarr|sonarr|lidarr)$")` to `SETTINGS_QUALITY`; `handle_back` edits to `"\U0001f3e0 Main Menu"` with `get_main_menu_keyboard()` and returns `ConversationHandler.END`.
- [ ] Run, expect PASS.
- [ ] Commit.

## Final verification

- [ ] Integration check: add or extend a `tests/integration` BotHarness test for the settings Back path (Task 6) and the Help Back path (Task 5), then run `pytest tests/integration`.
- [ ] Run `flake8`, `mypy src/`, the 100% coverage gate and the architecture tests through the preflight (`/addarr pr`).

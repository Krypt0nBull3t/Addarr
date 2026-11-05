# Issue 217: Fix stuck spinners and dead ends in Telegram navigation

Source: `plan.md` and `design.md` in this folder. Line numbers are from `cf51f57`.
Run each test command through the suite lock, as the `addarr-workflow` skill says.

### Phase 1: Navigation fixes (7 tasks)

**Goal:** Every tap stops its spinner, every screen has a way back, filters start at "all" and keep their row when empty, and Cancel works on photo messages.

**Phase Context:**

- Why NOT change `_handle_page` in queue, missing and history: a page button always changes the page, so a re-tap cannot raise "Message is not modified". Out of scope for #217.
- Why NOT use `_build_pagination_row` (`src/bot/keyboards.py:886`): F115 adds no nav row. The other pagination copies belong to #223.

- [x] **1.1** F111: answer the menu callback first
    - **Context:**
        - **Why:** `handle_menu_callback` calls `query.answer()` only on the cancel path, so the Movie, Series and Music buttons keep their spinner.
        - **Architecture:** `MediaHandler` conversation entry point, already `@require_auth`.
        - **Key refs:** `src/bot/handlers/media/handler.py:159-196`, `tests/test_handlers/test_media_handler.py`
        - **Watch out:** The cancel branch already calls `answer()`. Move the call to the top and remove the duplicate.
    - **Scope:** One handler method.
    - **Touches:** `src/bot/handlers/media/handler.py`, `tests/test_handlers/test_media_handler.py`
    - **Action items:**
        - [RED] Write `test_handle_menu_callback_movie_answers_query`: `menu_movie` awaits `query.answer()` once and returns `SEARCHING`.
        - [GREEN] Call `await query.answer()` right after `query = update.callback_query`.
    - **Success:** Test fails before and passes after. flake8 and mypy clean.
    - **Completed:** 2026-11-05
    - **Learnings:** The cancel branch already answered, so only the Movie, Series and Music path lacked `answer()`. `tests/integration/test_start_flow.py` already taps `menu_movie`.
    - **Key Changes:** `handle_menu_callback` in `src/bot/handlers/media/handler.py` awaits `query.answer()` once at the top. Added `test_handle_menu_callback_movie_answers_query`.
    - **Notes:** The handlers scoped run passes at 100% coverage (669 tests).

- [x] **1.2** F114: Cancel works on a photo message
    - **Context:**
        - **Why:** `start.py` cancel calls `edit_text` on a poster photo message and gets `BadRequest`.
        - **Architecture:** `StartHandler.handle_menu_selection`; reuse `send_response` (edits the caption for a photo, the text otherwise).
        - **Key refs:** `src/bot/handlers/start.py:88-95`, `src/bot/handlers/media/formatters.py:308`, `tests/test_handlers/test_start_handler.py`
        - **Watch out:** The `make_message` fixture sets `message.photo = None`; set a non-empty list for the photo case. A handler may import another handler module (layer test).
    - **Scope:** The cancel branch.
    - **Touches:** `src/bot/handlers/start.py`, `tests/test_handlers/test_start_handler.py`
    - **Action items:**
        - [RED] Write `test_cancel_on_photo_message_edits_caption`: `edit_caption` awaited, `edit_text` not awaited.
        - [GREEN] Replace the `edit_text` call with `await send_response(query.message, text)`.
    - **Success:** Test fails before and passes after. The existing cancel test and `tests/test_architecture` pass.
    - **Completed:** 2026-11-05
    - **Learnings:** `send_response` falls back to `reply_text` if the edit fails, so Cancel now also survives other edit errors. A venv without the `[job-queue]` extra makes every integration test error with "No `JobQueue` set up"; reinstall the pinned requirements.
    - **Key Changes:** `handle_menu_selection` cancel branch in `src/bot/handlers/start.py` calls `send_response`. Added `test_cancel_on_photo_message_edits_caption` and a `MagicMock` import in `tests/test_handlers/test_start_handler.py`.
    - **Notes:** The handlers scoped run (670 tests, 100%), architecture and integration tests pass.

- [x] **1.3** F110: a re-tap never hangs the spinner
    - **Context:**
        - **Why:** These paths call `edit_text` and Telegram raises "Message is not modified" on a re-tap. In queue, missing, history and system, `answer()` runs after the edit, so it never runs.
        - **Architecture:** Use `edit_text_ignoring_unmodified` (`src/utils/chat.py:31`), as `_handle_refresh` in queue already does. `answer()` first.
        - **Key refs:** `queue.py:104`, `missing.py:110`, `history.py:105`, `downloads.py:323`, `settings.py:648`, `system.py:150`, `:170`; fixture `unchanged_edit` in `tests/test_handlers/conftest.py:482`.
        - **Watch out:** In `system.py` details and disk space keep `parse_mode="Markdown"` and the `except` branches. `_do_action` in downloads already answers first, so fixing `_refresh_current_view` covers tabs, refresh and pause all twice.
    - **Scope:** Seven call sites in six handlers.
    - **Touches:** `src/bot/handlers/{queue,missing,history,downloads,settings,system}.py`, the six matching `tests/test_handlers/test_*_handler.py` files
    - **Action items:**
        - [RED] Write `test_filter_unchanged_message` in queue, missing and history; assert `calls == ["answer", "edit"]` and no exception.
        - [RED] Write downloads tests for tab, refresh and pause all twice with `unchanged_edit`; assert no exception and `answer` awaited.
        - [RED] Write the settings test `dl_sab_pause` and the system tests `system_details` and `system_diskspace` with `unchanged_edit`.
        - [GREEN] Swap in the helper at the seven sites; call `answer()` before the edit in the filter handlers and in system details and disk space.
    - **Success:** All new tests fail before and pass after. The six test files pass. flake8 and mypy clean.
    - **Completed:** 2026-11-05
    - **Learnings:** In system details and disk space the old code also hit the `except` branch on a re-tap, which edited again and raised a second `BadRequest`. The helper ends both. The downloads fix sits in `_refresh_current_view`, so tab, page, refresh, client switch and the pause actions all share it.
    - **Key Changes:** `edit_text_ignoring_unmodified` replaces `edit_text` in `_handle_filter` (queue, missing, history), `downloads._refresh_current_view`, `settings.handle_sabnzbd_pause_resume`, `system._handle_details` and `_handle_diskspace`. Those filter and system handlers now call `query.answer()` first. Added nine `*_unchanged_message` tests.
    - **Notes:** Handlers scoped run: 679 tests, 100% coverage. mypy and integration tests pass.

- [ ] **1.4** F115: filters reset and keep their row
    - **Context:**
        - **Why:** `setdefault` keeps an old filter; an empty filtered view uses the `*_empty_keyboard`, which has no filter row; Movies and Series filters in missing never refetch, so after Cutoff they filter the cutoff list.
        - **Architecture:** Handler `_build_response` picks the keyboard. Keep the empty text when `items` is empty. Pick the items keyboard when items exist or a filter other than all is active.
        - **Key refs:** `queue.py:48`, `:144-159`; `missing.py:48`, `:100-103`, `:174-189`; `history.py:147-161`; handler fixtures `_mock_items_kbd` and `_mock_empty_kbd` in `tests/test_handlers/conftest.py`.
        - **Watch out:** History stores the filter as `None` for all (`event_filter is not None` means a filter is active). Missing "series" maps to the stored filter `"episode"`.
    - **Scope:** `show_queue`, `show_missing`, three `_build_response` methods, `missing._handle_filter`.
    - **Touches:** `src/bot/handlers/{queue,missing,history}.py`, the three matching test files
    - **Action items:**
        - [RED] Write `test_show_queue_resets_stored_filter` and `test_show_missing_resets_stored_filter` (stored `movie` becomes `all`).
        - [RED] Write `test_empty_filtered_view_keeps_filter_row` for queue, missing and history (items keyboard called, empty keyboard not).
        - [RED] Write `test_cutoff_then_movie_refetches_missing` and the series variant (`get_missing_media` awaited, `missing_items` replaced).
        - [GREEN] Assign `"all"` on entry; change the keyboard choice; refetch on movie and series.
    - **Success:** New tests fail before and pass after. The three files pass. flake8 and mypy clean.

- [ ] **1.5** F113: Back buttons and a `bazarr_menu` button
    - **Context:**
        - **Why:** Help, the library list and both Bazarr wanted lists have no Back button. No keyboard has a `bazarr_menu` button, although its handler exists.
        - **Architecture:** Help Back is `menu_back` (handled by `HelpHandler.handle_back`). Library list Back is `menu_library` (handled by `StartHandler`). Bazarr Back is `bazarr_menu` (handled by `subtitles_menu`). Label from `TranslationService().get_text("Back")`, no new key.
        - **Key refs:** `help.py:61-83`, `library.py:177-215`, `bazarr.py:175-220`, `src/bot/keyboards.py:81-108` (library menu).
        - **Watch out:** `library._build_page_message` returns `None` markup for one page today; it must always return a markup. `menu_library` must not match `^lib_` or `^library_`. Bazarr empty replies get Back too.
    - **Scope:** Three handlers, one small helper in bazarr.
    - **Touches:** `src/bot/handlers/{help,library,bazarr}.py`, the three matching test files
    - **Action items:**
        - [RED] Write `test_help_callback_has_back_button` (`menu_back`).
        - [RED] Write `test_library_list_keyboard_has_back_button` for one page and many pages (`menu_library`).
        - [RED] Write Bazarr tests for wanted movies and episodes, empty and non-empty (`bazarr_menu`).
        - [GREEN] Add the buttons; update existing tests that expect `None` markup.
    - **Success:** New tests fail before and pass after. The three files pass. flake8 and mypy clean.

- [ ] **1.6** F112: Back goes to the parent screen
    - **Context:**
        - **Why:** Back from SAB speed (`dl_back`) and from quality (`settings_back`) both land on the settings root. Back from Settings ends with the "End" text and no keyboard.
        - **Architecture:** `SettingsHandler` conversation. SAB speed Back becomes `dl_sabnzbd` (state `SETTINGS_DOWNLOADS` already routes it). Quality Back becomes `settings_<service>`; add a `handle_service_menu` handler for `^settings_(radarr|sonarr|lidarr)$` to state `SETTINGS_QUALITY`. `handle_back` edits to the main menu before END.
        - **Key refs:** `settings.py:109-118`, `:602-605`, `:710-718`; `src/bot/keyboards.py:308-329`; `get_main_menu_keyboard` (`keyboards.py:21`).
        - **Watch out:** Main menu text is `"\U0001f3e0 Main Menu"`, as in the queue and system handlers. `handle_service_menu` reads the service from `query.data.replace("settings_", "")`.
    - **Scope:** One keyboard builder, three places in `settings.py`.
    - **Touches:** `src/bot/keyboards.py`, `src/bot/handlers/settings.py`, `tests/test_handlers/test_settings_handler.py`, the keyboard test file
    - **Action items:**
        - [RED] Write `test_quality_keyboard_back_returns_to_service_menu` (`settings_radarr`).
        - [RED] Write `test_sab_speed_back_callback_is_sab_menu` (`dl_sabnzbd`).
        - [RED] Write `test_quality_state_routes_service_menu_back` (state handler list).
        - [RED] Write `test_back_from_settings_shows_main_menu_before_end` (main menu keyboard, returns `END`).
        - [GREEN] Make the four changes.
    - **Success:** New tests fail before and pass after. `test_settings_handler.py` and keyboard tests pass. flake8 and mypy clean.

- [ ] **1.7** Integration flows for the Back paths
    - **Context:**
        - **Why:** CLAUDE.md and the `addarr-workflow` loop ask for an integration test when a user-facing flow changes.
        - **Architecture:** `BotHarness` in `tests/integration/conftest.py`.
        - **Key refs:** `tests/integration/` existing flow tests; harness fixtures and update factories.
        - **Watch out:** Extend an existing settings or help flow test if one exists. Do not duplicate it.
    - **Scope:** Settings Back (parent screen, main menu) and Help Back.
    - **Touches:** `tests/integration/`
    - **Action items:**
        - [RED] Write a flow test: settings, SAB speed, Back lands on the SAB menu; settings, Back shows the main menu keyboard.
        - [RED] Write a flow test: help, Back shows the main menu.
        - [GREEN] Fix anything the flow test finds.
    - **Success:** `pytest tests/integration` passes. Then the preflight (`/addarr pr`) passes: flake8, mypy, translations, unit tests with the 100% coverage gate, integration and architecture tests.

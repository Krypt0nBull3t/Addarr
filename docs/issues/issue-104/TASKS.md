# Issue #104: Calendar / Upcoming Releases (`/upcoming`)

> **Plan:** [docs/issues/issue-104/plan.md](plan.md)
> **Branch:** `feature/104-upcoming-calendar`
> **Issue:** https://github.com/Krypt0nBull3t/Addarr/issues/104

---

### Phase 1: Backend — API Client Calendar Methods (1 task)

**Goal:** Both RadarrClient and SonarrClient can fetch calendar data from their respective APIs.

- [x] **1.1** Add `get_calendar()` to RadarrClient and SonarrClient
    - **Context:**
        - **Why:** Radarr and Sonarr both expose `GET /api/v3/calendar?start=&end=` but we have no client methods for them. This is the data source for everything else.
        - **Architecture:** Each client inherits `BaseApiClient`. New methods use `self._request()` convenience wrapper (returns parsed JSON or None). Follow the pattern of `get_movies()` (radarr.py:196) and `get_all_series()` (sonarr.py:202) — simple `_request()` call, log, return list.
        - **Key refs:** `src/api/base.py:226` (`_request` wrapper), `src/api/radarr.py:196` (`get_movies` pattern), `src/api/sonarr.py:202` (`get_all_series` pattern), `tests/test_api/conftest.py` (API test fixtures with `aioresponses`), `tests/test_api/test_radarr.py` (existing Radarr test patterns)
        - **Watch out:** Endpoint is `calendar?start={start}&end={end}` (query params in path string, same as `movie/lookup?term={term}` pattern at radarr.py:47). Both APIs return arrays directly. Use `_request()` not `_make_request()` — the convenience wrapper handles error → None. Don't forget `from typing import List, Dict` is already imported in both files.
    - **Scope:** Add `get_calendar(start: str, end: str) -> List[Dict]` to both RadarrClient and SonarrClient + full test coverage
    - **Touches:** `src/api/radarr.py`, `src/api/sonarr.py`, `tests/test_api/test_radarr.py`, `tests/test_api/test_sonarr.py`
    - **Action items:**
        - [RED] Write tests for `RadarrClient.get_calendar()` — happy path (returns list of movies), empty result, API error/exception
        - [RED] Write tests for `SonarrClient.get_calendar()` — happy path (returns list of episodes), empty result, API error/exception
        - [GREEN] Implement `RadarrClient.get_calendar()` — `_request(f"calendar?start={start}&end={end}")`, log, return list or `[]`
        - [GREEN] Implement `SonarrClient.get_calendar()` — identical pattern
    - **Success:** `pytest tests/test_api/test_radarr.py tests/test_api/test_sonarr.py --tb=short -q` passes, new methods return calendar data
    - **Completed:** 2026-03-03
    - **Learnings:**
        - Calendar endpoint uses query params in path string (`calendar?start={start}&end={end}`), same pattern as `movie/lookup?term={term}`
        - Both Radarr and Sonarr return arrays directly from the calendar endpoint
        - `_request()` convenience wrapper handles errors → None cleanly; `not results` catches both None and empty list
    - **Key Changes:**
        - Added `get_calendar(start, end)` to `RadarrClient` (`src/api/radarr.py`)
        - Added `get_calendar(start, end)` to `SonarrClient` (`src/api/sonarr.py`)
        - Added `TestRadarrGetCalendar` and `TestSonarrGetCalendar` test classes (6 tests total)
    - **Notes:** 100% coverage on both radarr.py and sonarr.py

---

### Phase 2: Backend — Service Layer (1 task)

**Goal:** `MediaService.get_upcoming()` aggregates calendar data from both services into a normalized, sorted list.

- [x] **2.1** Add `get_upcoming()` to MediaService
    - **Context:**
        - **Why:** The handler needs a single call to get all upcoming releases across services. MediaService already aggregates Radarr/Sonarr for search — calendar follows the same pattern.
        - **Architecture:** MediaService is a singleton (`src/services/media.py`). New method calls `self.radarr.get_calendar()` and `self.sonarr.get_calendar()` concurrently via `asyncio.gather`, then normalizes into a unified schema. Skips disabled services (checks `self.radarr is None`).
        - **Key refs:** `src/services/media.py:100` (`search_movies` for Radarr delegation pattern), `src/services/media.py:180` (`search_music` for `asyncio.gather` pattern), `tests/test_services/test_media_service.py` (service test patterns), `tests/test_services/conftest.py`
        - **Watch out:** Radarr calendar returns movie-level objects (has `inCinemas`, `digitalRelease`, `physicalRelease` — pick earliest non-null as the "date", label accordingly). Sonarr calendar returns episode-level objects (has `airDateUtc` for date, `series` nested object for series-level info like `tvdbId`). Items with `id` field are already in the library (monitored). Use `datetime.date.today()` for start date computation — import `datetime` at top of file (already imported: `asyncio`).
    - **Scope:** `get_upcoming(days=7)` returning normalized list of dicts sorted by date, with `in_library` flag
    - **Touches:** `src/services/media.py`, `tests/test_services/test_media_service.py`
    - **Normalized item schema:**
        ```
        type: "movie" | "episode"
        title: str              # Movie title or episode title
        series_title: str|None  # None for movies, series name for episodes
        date: str               # YYYY-MM-DD
        date_label: str         # "Cinema" / "Digital" / "Physical" / "Airing"
        year: int|None          # Movie year
        season: int|None        # Episode season number
        episode: int|None       # Episode number
        in_library: bool        # True if item has an internal ID (already monitored)
        media_id: str           # tmdbId (movies) or series tvdbId (episodes)
        internal_id: int|None   # Radarr movie ID or Sonarr series ID
        ```
    - **Action items:**
        - [RED] Write test: both services enabled — returns combined, date-sorted list with correct normalization
        - [RED] Write test: only Radarr enabled (sonarr is None) — returns only movies
        - [RED] Write test: only Sonarr enabled (radarr is None) — returns only episodes
        - [RED] Write test: neither enabled — returns `[]`
        - [RED] Write test: Radarr movie date selection — picks earliest of inCinemas/digitalRelease/physicalRelease, labels correctly
        - [RED] Write test: items with `id` field have `in_library=True`, items without have `in_library=False`
        - [RED] Write test: API error on one service — still returns results from the other (use `asyncio.gather(return_exceptions=True)` or try/except)
        - [GREEN] Implement `get_upcoming()` with date computation, concurrent fetch, normalization, sorting
    - **Success:** `pytest tests/test_services/test_media_service.py --tb=short -q` passes, all normalization and edge cases covered
    - **Completed:** 2026-03-03
    - **Learnings:**
        - `asyncio.gather(return_exceptions=True)` returns exceptions as values — check `isinstance(result, Exception)` to handle gracefully
        - Radarr calendar movies have three date fields (inCinemas, digitalRelease, physicalRelease) — pick earliest non-null, sort by string since ISO format sorts correctly
        - Sonarr calendar returns episode-level objects with nested `series` dict containing `tvdbId` and series `id`
        - `"id" in movie` is the reliable way to detect in-library items
    - **Key Changes:**
        - Added `get_upcoming(days)` to `MediaService` (`src/services/media.py`)
        - Added `_normalize_radarr_calendar()` and `_normalize_sonarr_calendar()` static methods
        - Added `get_calendar` to mock fixtures in `tests/test_services/conftest.py`
        - Added `TestGetUpcoming` class with 11 tests covering all edge cases
    - **Notes:** 100% coverage on media.py (373 statements)

---

### Phase 3: UI Infrastructure — Keyboards & i18n (1 task)

**Goal:** Calendar keyboard functions and translation keys are ready for the handler to use.

- [ ] **3.1** Add calendar keyboards and translation keys
    - **Context:**
        - **Why:** CalendarHandler (next task) needs keyboard layouts and translated strings. Building these first means the handler can focus on logic.
        - **Architecture:** Keyboards in `src/bot/keyboards.py` follow the pattern of `get_system_keyboard()` (simple buttons) and `get_search_results_list_keyboard()` (paginated). Translations use flat top-level keys in YAML files (NOT nested — `get_text()` does single-level lookup).
        - **Key refs:** `src/bot/keyboards.py:64` (`get_system_keyboard` — simple layout), `src/bot/keyboards.py:295` (`get_search_results_list_keyboard` — pagination pattern), `tests/test_bot/test_keyboards.py` (keyboard tests), `translations/addarr.en-us.yml` (English translation file)
        - **Watch out:** Callback data prefix is `cal_` for all calendar buttons. All callback_data strings must be under 64 bytes (Telegram limit). Translation keys must be flat top-level (e.g., `CalendarTitle` not `Calendar.Title`). Template file is `translations/addarr.template.yml`. There are 9 locale files plus the template — all need the same keys added.
    - **Scope:** Two keyboard functions + translation keys across all locale files
    - **Touches:** `src/bot/keyboards.py`, `tests/test_bot/test_keyboards.py`, `translations/addarr.*.yml` (9 locales + template)
    - **Keyboard functions:**
        1. `get_calendar_keyboard(days: int)` — Period row (7d/14d/30d, current highlighted with checkmark), Refresh button, Back button
        2. `get_calendar_items_keyboard(items, page, days, page_size=5)` — Item buttons (emoji + title, `cal_add_{type}_{media_id}` for non-library items), pagination row, period/refresh/back row
    - **Callback data conventions:**
        - `cal_period_7`, `cal_period_14`, `cal_period_30`
        - `cal_page_0`, `cal_page_1`, ...
        - `cal_refresh`
        - `cal_back`
        - `cal_add_movie_{tmdbId}`, `cal_add_episode_{tvdbId}`
    - **Translation keys to add:**
        ```
        Upcoming, CommandUpcoming, CalendarTitle, CalendarEmpty,
        CalendarMovie, CalendarEpisode, CalendarCinema, CalendarDigital,
        CalendarPhysical, CalendarAiring, CalendarDays7, CalendarDays14,
        CalendarDays30, CalendarAddSuccess, CalendarAddFailed,
        CalendarAlreadyInLibrary
        ```
    - **Action items:**
        - [RED] Write tests for `get_calendar_keyboard()` — verify period buttons with correct callback_data, current period highlighted, refresh + back buttons present
        - [RED] Write tests for `get_calendar_items_keyboard()` — verify item buttons, add buttons only for non-library items, pagination when items > page_size, no pagination for single page
        - [GREEN] Implement `get_calendar_keyboard()`
        - [GREEN] Implement `get_calendar_items_keyboard()`
        - [GREEN] Add translation keys to all 10 YAML files (9 locales + template)
    - **Success:** `pytest tests/test_bot/test_keyboards.py --tb=short -q` passes, `PYTHONIOENCODING=utf-8 python run.py --validate-i18n` passes

---

### Phase 4: Handler — CalendarHandler + Registration (2 tasks)

**Goal:** Working `/upcoming` command with inline navigation, pagination, and Add to Library.

- [ ] **4.1** Implement CalendarHandler
    - **Context:**
        - **Why:** This is the core feature — the Telegram handler that ties everything together.
        - **Architecture:** Follows `SystemHandler` pattern (`src/bot/handlers/system.py`): `CommandHandler` for `/upcoming` + `CallbackQueryHandler` for `cal_*` callbacks. No conversation states needed. Uses `context.user_data` to cache calendar items (avoids re-fetching on pagination) and store current period.
        - **Key refs:** `src/bot/handlers/system.py` (simple handler pattern — CommandHandler + CallbackQueryHandler), `src/bot/handlers/auth.py:37` (`@require_auth` decorator), `src/services/rate_limit.py` (`@rate_limit("search")` decorator), `tests/test_handlers/conftest.py` (handler fixture pattern with patched services), `tests/test_handlers/test_system_handler.py` (simple handler tests)
        - **Watch out:** `@require_auth` expects `self` as first arg (it's a method decorator, checks `update.effective_user`). For callback queries, `update.message` is None — use `update.callback_query.message` for editing. Quick-add needs first root folder + first quality profile — call `radarr.get_root_folders()` and `radarr.get_quality_profiles()` (accessed via `self.media_service.radarr`). Sonarr episodes "Add" actually adds the series (by tvdbId). `query.answer(text)` shows a toast, `query.message.edit_text()` updates the message.
    - **Scope:** Full CalendarHandler class with show_upcoming, handle_calendar_action, period/page/refresh/back/add handlers
    - **Touches:** `src/bot/handlers/calendar.py` (create), `tests/test_handlers/test_calendar_handler.py` (create), `tests/test_handlers/conftest.py` (add calendar_handler fixture)
    - **Action items:**
        - [RED] Write `calendar_handler` fixture in `tests/test_handlers/conftest.py` — patch MediaService, TranslationService, set auth
        - [RED] Write test: `show_upcoming` with results — sends message with calendar text and keyboard
        - [RED] Write test: `show_upcoming` with empty results — sends "no upcoming releases" message
        - [RED] Write test: `show_upcoming` via callback query (menu_upcoming) — edits message instead of sending new
        - [RED] Write test: period change (`cal_period_14`) — updates user_data, re-fetches, edits message
        - [RED] Write test: pagination (`cal_page_1`) — shows second page from cached items
        - [RED] Write test: refresh (`cal_refresh`) — clears cache, re-fetches
        - [RED] Write test: back (`cal_back`) — returns to main menu
        - [RED] Write test: add movie (`cal_add_movie_12345`) — calls add_movie_with_profile, shows toast
        - [RED] Write test: add movie failure — shows error toast
        - [RED] Write test: add episode (`cal_add_episode_67890`) — calls add_series_with_profile, shows toast
        - [RED] Write test: unauthenticated user — blocked by @require_auth
        - [GREEN] Implement CalendarHandler class with all methods
    - **Success:** `pytest tests/test_handlers/test_calendar_handler.py --tb=short -q` passes, all handler paths covered

- [ ] **4.2** Register CalendarHandler and wire into bot
    - **Context:**
        - **Why:** Handler exists but isn't wired into the bot yet. Need to register it, add the command to Telegram's menu, add it to the main menu keyboard, and route the main menu callback.
        - **Architecture:** Handler registration in `src/main.py:_add_handlers()`. Command registration in `src/bot/commands.py:build_authenticated_commands()`. Main menu keyboard in `src/bot/keyboards.py:get_main_menu_keyboard()`. StartHandler routes `menu_*` callbacks to handlers.
        - **Key refs:** `src/main.py:102` (`_add_handlers` — registration order), `src/bot/commands.py:31` (`build_authenticated_commands`), `src/bot/keyboards.py:14` (`get_main_menu_keyboard`), `src/bot/handlers/start.py` (menu callback routing), `src/bot/handlers/__init__.py` (handler exports), `tests/test_main.py`, `tests/test_bot/test_commands.py`
        - **Watch out:** Handler registration ORDER matters — put CalendarHandler after Media handler, before Transmission. The `/upcoming` command should only appear when Radarr OR Sonarr is enabled. StartHandler needs to handle `menu_upcoming` callback. Architecture tests (`tests/test_architecture/`) will auto-verify the handler has `get_handler()` and doesn't violate layer boundaries — run them to confirm.
    - **Scope:** Import + register handler, export, command registration, main menu button, start handler routing
    - **Touches:** `src/main.py`, `src/bot/handlers/__init__.py`, `src/bot/commands.py`, `src/bot/keyboards.py`, `src/bot/handlers/start.py`, `tests/test_main.py`, `tests/test_bot/test_commands.py`, `tests/test_bot/test_keyboards.py`
    - **Action items:**
        - [RED] Write test: `/upcoming` appears in authenticated commands when Radarr or Sonarr enabled
        - [RED] Write test: `/upcoming` does NOT appear when neither Radarr nor Sonarr enabled
        - [RED] Write test: main menu keyboard includes "Upcoming" button
        - [GREEN] Add CalendarHandler import and registration to `src/main.py:_add_handlers()`
        - [GREEN] Export CalendarHandler from `src/bot/handlers/__init__.py`
        - [GREEN] Add `/upcoming` to `build_authenticated_commands()` (conditional on Radarr/Sonarr)
        - [GREEN] Add "📅 Upcoming" button to `get_main_menu_keyboard()`
        - [GREEN] Handle `menu_upcoming` callback in StartHandler
        - [GREEN] Run architecture tests to verify no violations: `pytest tests/test_architecture/ --tb=short -q`
    - **Success:** `pytest --tb=short -q` all pass, `python -m flake8 .` clean, `PYTHONIOENCODING=utf-8 python run.py --validate-i18n` passes, architecture tests pass

# Calendar / Upcoming Releases (`/upcoming`) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a `/upcoming` command that shows upcoming movie releases (Radarr) and TV episode airings (Sonarr) with optional "Add to Library" buttons for un-monitored items.

**Architecture:** Extend RadarrClient and SonarrClient with `get_calendar()` methods that hit the `/api/v3/calendar` endpoint. Add a `get_upcoming()` method to MediaService that aggregates both services. Create a new CalendarHandler with `/upcoming` command, inline keyboard navigation (lookahead period, pagination, refresh), and "Add to Library" callbacks that reuse the existing add-media flow.

**Tech Stack:** python-telegram-bot v20+, aiohttp, async/await throughout

---

## Context

### Issue
GitHub Issue #104 — Users have to browse external sites to see upcoming releases. Radarr and Sonarr both provide calendar APIs that we can expose through a Telegram command.

### API Endpoints
- **Radarr:** `GET /api/v3/calendar?start=YYYY-MM-DD&end=YYYY-MM-DD`
  - Returns array of movie objects with `title`, `tmdbId`, `inCinemas`, `digitalRelease`, `physicalRelease`, `hasFile`, `monitored`, `id` (internal)
- **Sonarr:** `GET /api/v3/calendar?start=YYYY-MM-DD&end=YYYY-MM-DD`
  - Returns array of episode objects with `title`, `seriesTitle`, `seasonNumber`, `episodeNumber`, `airDateUtc`, `hasFile`, `series.tvdbId`, `series.id`

### Existing Patterns
- API clients inherit `BaseApiClient`, use `_request()` for simple GET calls
- `MediaService` is a singleton aggregating API clients, accessed by handlers
- Handlers expose `get_handler()` returning list of CommandHandler/CallbackQueryHandler
- `@require_auth` decorator guards handler methods
- `@rate_limit("search")` decorator for rate limiting
- Keyboards built in `src/bot/keyboards.py` using `InlineKeyboardButton`/`InlineKeyboardMarkup`
- Translation via `TranslationService().get_text(key, default=...)`
- Commands registered in `src/bot/commands.py` and `src/main.py`

### Files to Reference
- `src/api/base.py` — BaseApiClient with `_request()` convenience wrapper
- `src/api/radarr.py` — RadarrClient (add `get_calendar()`)
- `src/api/sonarr.py` — SonarrClient (add `get_calendar()`)
- `src/services/media.py` — MediaService singleton
- `src/bot/handlers/system.py` — Simple handler pattern (CommandHandler + CallbackQueryHandler)
- `src/bot/keyboards.py` — Keyboard construction patterns
- `src/bot/commands.py` — Command registration
- `src/main.py` — Handler registration in `_add_handlers()`
- `src/bot/handlers/__init__.py` — Handler exports
- `tests/conftest.py` — MockConfig, Telegram factories, singleton reset
- `tests/test_handlers/conftest.py` — Handler fixture pattern with patched services

---

## Design Decisions

1. **No conversation states** — `/upcoming` is read-only display. Uses CommandHandler for the command + CallbackQueryHandler for inline button actions (period change, pagination, refresh, add-to-library).

2. **Lookahead periods** — 7 days (default), 14 days, 30 days. User toggles via inline buttons. Stored in `context.user_data["calendar_days"]`.

3. **Pagination** — 5 items per page. Same pattern as `get_search_results_list_keyboard()` in keyboards.py.

4. **Add to Library** — Items not already in the user's library get a "+" button. Clicking triggers a callback that calls the existing `MediaService.add_movie_with_profile()` or `MediaService.add_series_with_profile()` with the first available quality profile and root folder (quick-add). Full quality/season selection would over-complicate this view.

5. **Combined display** — Movies and episodes shown in a single chronological list, grouped by date. Movies show title + release type (cinema/digital/physical). Episodes show series name + SxxExx + episode title.

6. **Callback data prefix** — `cal_` for all calendar-related callbacks to avoid collisions.

7. **No new config keys** — Lookahead default is hardcoded at 7 days. No config needed.

---

## Phased Approach

### Phase 1: API Client Extensions
Add `get_calendar()` to RadarrClient and SonarrClient.

### Phase 2: Service Layer
Add `get_upcoming()` to MediaService that aggregates calendar data.

### Phase 3: Keyboard & i18n
Add calendar keyboard functions and translation keys.

### Phase 4: Handler
Create CalendarHandler with `/upcoming`, inline navigation, and add-to-library.

### Phase 5: Registration & Integration
Register handler, command, and exports.

---

## Task Breakdown

### Task 1.1: RadarrClient.get_calendar()

**Files:**
- Modify: `src/api/radarr.py` (add method)
- Test: `tests/test_api/test_radarr.py` (add tests)

**What:** Add `get_calendar(start: str, end: str) -> List[Dict]` to RadarrClient. Takes ISO date strings (YYYY-MM-DD), calls `calendar?start={start}&end={end}`, returns raw API response list. Returns `[]` on error.

**Pattern:** Follow `get_movies()` at line 196 — simple `_request()` call, log, return list.

**Test strategy:** Use `aioresponses` to mock the HTTP call. Test happy path (returns list), empty result, and API error. Reference `tests/test_api/conftest.py` for API test fixtures and `tests/test_api/test_radarr.py` for existing patterns.

---

### Task 1.2: SonarrClient.get_calendar()

**Files:**
- Modify: `src/api/sonarr.py` (add method)
- Test: `tests/test_api/test_sonarr.py` (add tests)

**What:** Add `get_calendar(start: str, end: str) -> List[Dict]` to SonarrClient. Same signature and pattern as Task 1.1 but for Sonarr.

**Pattern:** Follow `get_all_series()` at line 202.

**Test strategy:** Same as Task 1.1 but with Sonarr endpoint URL.

---

### Task 2.1: MediaService.get_upcoming()

**Files:**
- Modify: `src/services/media.py` (add method)
- Test: `tests/test_services/test_media_service.py` (add tests)

**What:** Add `get_upcoming(days: int = 7) -> List[Dict]` to MediaService. Computes `start` = today, `end` = today + days. Calls `radarr.get_calendar()` and `sonarr.get_calendar()` concurrently (via `asyncio.gather`). Normalizes results into a unified list:

```python
{
    "type": "movie" | "episode",
    "title": str,           # Movie title or episode title
    "series_title": str,    # None for movies, series name for episodes
    "date": str,            # ISO date (YYYY-MM-DD) of release/airing
    "date_label": str,      # Human-friendly: "Cinema", "Digital", "Physical", "Airing"
    "year": int,            # Movie year or None
    "season": int,          # None for movies
    "episode": int,         # None for movies
    "in_library": bool,     # True if already monitored
    "media_id": str,        # tmdbId for movies, tvdbId for episodes
    "internal_id": int,     # Radarr movie ID or Sonarr series ID (for items in library)
}
```

Sorts by date ascending. Skips services that are not enabled (radarr/sonarr is None).

**Test strategy:** Mock `self.radarr.get_calendar()` and `self.sonarr.get_calendar()` with sample data. Test: both services enabled, only Radarr, only Sonarr, neither enabled (returns []), date sorting, normalization of fields. Reference `tests/test_services/test_media_service.py` for service test patterns.

---

### Task 3.1: Calendar Keyboard Functions

**Files:**
- Modify: `src/bot/keyboards.py` (add functions)
- Test: `tests/test_bot/test_keyboards.py` (add tests)

**What:** Add two keyboard functions:

1. `get_calendar_keyboard(days: int) -> InlineKeyboardMarkup` — Period selection row (7d/14d/30d with current highlighted), Refresh button, Back to main menu button.

2. `get_calendar_items_keyboard(items: list, page: int, days: int, page_size: int = 5) -> InlineKeyboardMarkup` — Paginated item list. Each item shows emoji + title + date. Items not in library get a "+" button (`cal_add_{type}_{media_id}`). Pagination row (Prev/Page N/M/Next). Period + refresh + back row at bottom.

**Callback data conventions:**
- `cal_period_{days}` — Change lookahead period
- `cal_page_{n}` — Navigate to page
- `cal_refresh` — Re-fetch calendar data
- `cal_back` — Return to main menu
- `cal_add_movie_{tmdbId}` — Quick-add movie
- `cal_add_episode_{tvdbId}` — Quick-add series (by tvdbId)

**Test strategy:** Verify button count, callback_data patterns, pagination logic. Reference `tests/test_bot/test_keyboards.py`.

---

### Task 3.2: Translation Keys

**Files:**
- Modify: All 9 `translations/addarr.*.yml` files
- Modify: `translations/addarr.template.yml`

**What:** Add flat top-level keys (NOT nested — `get_text()` does single-level lookup):

```yaml
# Calendar / Upcoming
Upcoming: "Upcoming"
CommandUpcoming: "View upcoming releases"
CalendarTitle: "Upcoming Releases"
CalendarEmpty: "No upcoming releases found for the next %{days} days."
CalendarMovie: "Movie"
CalendarEpisode: "Episode"
CalendarCinema: "Cinema"
CalendarDigital: "Digital"
CalendarPhysical: "Physical"
CalendarAiring: "Airing"
CalendarDays7: "7 days"
CalendarDays14: "14 days"
CalendarDays30: "30 days"
CalendarAddSuccess: "Added to library!"
CalendarAddFailed: "Failed to add. Try the full /movie or /series command."
CalendarAlreadyInLibrary: "Already in your library."
```

English values above. For other languages, use English as placeholder (same as existing pattern — translations can be improved later).

---

### Task 4.1: CalendarHandler

**Files:**
- Create: `src/bot/handlers/calendar.py`
- Test: `tests/test_handlers/test_calendar_handler.py`

**What:** New handler class following the SystemHandler pattern:

```python
class CalendarHandler:
    def __init__(self):
        self.media_service = MediaService()
        self.translation = TranslationService()

    def get_handler(self):
        return [
            CommandHandler("upcoming", self.show_upcoming),
            CallbackQueryHandler(self.handle_calendar_action, pattern="^cal_"),
        ]

    @require_auth
    @rate_limit("search")
    async def show_upcoming(self, update, context):
        # Get lookahead days from user_data (default 7)
        # Call media_service.get_upcoming(days)
        # Build message text + keyboard
        # Send or edit message

    @require_auth
    async def handle_calendar_action(self, update, context):
        # Parse callback_data prefix after "cal_"
        # Route to: _handle_period, _handle_page, _handle_refresh, _handle_back, _handle_add
```

**Key methods:**
- `_build_calendar_text(items, page, page_size, days)` — Format items for display. Group by date. Movies: "🎬 Title (Year) — Cinema/Digital/Physical on Mar 5". Episodes: "📺 Series SxxExx — Episode Title — Mar 5". Max 5 per page.
- `_handle_period(query, context, days)` — Update `context.user_data["calendar_days"]`, re-fetch and display.
- `_handle_page(query, context, page)` — Show page N of cached results from `context.user_data["calendar_items"]`.
- `_handle_refresh(query, context)` — Re-fetch calendar data and update display.
- `_handle_back(query)` — Return to main menu.
- `_handle_add(query, context, media_type, media_id)` — Quick-add: get first root folder + first quality profile, call `add_movie_with_profile` or `add_series_with_profile`. Show success/failure via `query.answer()`.

**Data caching:** Store fetched items in `context.user_data["calendar_items"]` to avoid re-fetching on pagination. Refresh button clears and re-fetches.

**Test strategy:** Follow `tests/test_handlers/conftest.py` pattern — create `calendar_handler` fixture that patches MediaService + TranslationService. Test: show_upcoming with results, empty results, period change, pagination, refresh, add movie success/failure, add episode success/failure, unauthenticated access. Reference `tests/test_handlers/test_system_handler.py` for simple handler tests.

---

### Task 5.1: Registration & Integration

**Files:**
- Modify: `src/main.py` — Import CalendarHandler, add to `_add_handlers()` (after Media, before Transmission)
- Modify: `src/bot/handlers/__init__.py` — Export CalendarHandler
- Modify: `src/bot/commands.py` — Add `/upcoming` command for authenticated users (visible when either Radarr or Sonarr is enabled)
- Modify: `src/bot/keyboards.py` — Add "📅 Upcoming" button to main menu keyboard
- Test: `tests/test_main.py` — Verify CalendarHandler is registered
- Test: `tests/test_bot/test_commands.py` — Verify `/upcoming` appears in authenticated commands

**Command registration in `build_authenticated_commands()`:**
```python
if config.get("radarr", {}).get("enable") or config.get("sonarr", {}).get("enable"):
    commands.append(BotCommand("upcoming", translation.get_text("CommandUpcoming")))
```

**Main menu keyboard** — Add after Delete row, before Settings:
```python
[InlineKeyboardButton(
    f"📅 {translation.get_text('Upcoming')}",
    callback_data="menu_upcoming"
)]
```

**StartHandler** — Will need to handle `menu_upcoming` callback to route to CalendarHandler. Check how `menu_status` routes to SystemHandler in StartHandler.

---

### Task 5.2: Architecture Test Updates

**Files:**
- Verify: `tests/test_architecture/test_conventions.py` — CalendarHandler will be auto-detected by the handler test (ends with "Handler", must have `get_handler()`). No SINGLETON_CLASSES update needed since no new service.

**What:** Run architecture tests to confirm no violations. CalendarHandler must:
- Have `get_handler()` method
- Not use `config["key"]` bracket access (use `config.get()`)
- Not import API clients directly (go through MediaService)

---

## Verification Checklist

1. `pytest --tb=short -q` — All tests pass
2. `python -m flake8 .` — No lint errors
3. `PYTHONIOENCODING=utf-8 python run.py --validate-i18n` — Translation validation passes
4. Architecture tests pass (handler convention, layer boundaries, config access)
5. Coverage: 100% on new/modified code

## Risk Areas

- **Quick-add without quality selection** — Uses first available profile/root folder. Acceptable for calendar quick-add; users wanting control use `/movie` or `/series`.
- **Large calendar responses** — 30-day window could return many items. Pagination handles this (5 per page).
- **Sonarr episodes vs series** — Calendar returns episodes, but "Add to Library" adds the whole series. Need to communicate this clearly in the button text / confirmation.

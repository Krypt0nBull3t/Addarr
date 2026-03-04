# Missing/Wanted Media Command (`/missing`) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a `/missing` command that shows paginated lists of wanted-but-not-downloaded media from Radarr and Sonarr, with filter tabs (All / Movies / Series / Cutoff Unmet) and a "Search Now" action per item.

**Architecture:** Extends the existing three-layer pattern (API clients -> service -> handler). New API methods on RadarrClient and SonarrClient call the `wanted/missing` and `wanted/cutoff` endpoints. MediaService aggregates and normalizes results from both services. A new MissingHandler displays the list with pagination and routing, following the CalendarHandler pattern (callback-driven, no ConversationHandler states needed).

**Tech Stack:** python-telegram-bot v20+, aiohttp, asyncio.gather for concurrent API calls.

---

## Context & References

| What | Where |
|------|-------|
| Radarr API client | `src/api/radarr.py` |
| Sonarr API client | `src/api/sonarr.py` |
| Base API client (`_request`, `_make_request`) | `src/api/base.py` |
| MediaService (aggregation layer) | `src/services/media.py` |
| CalendarHandler (reference implementation) | `src/bot/handlers/calendar.py` |
| Keyboard builders | `src/bot/keyboards.py` |
| Command registration | `src/bot/commands.py` |
| Handler wiring | `src/main.py:103-170` |
| Translation file | `translations/addarr.en-us.yml` |
| API test fixtures | `tests/test_api/conftest.py` |
| Handler test fixtures | `tests/test_handlers/conftest.py` |
| Service test fixtures | `tests/test_services/conftest.py` |
| Sample data constants | `tests/fixtures/sample_data.py` |
| Architecture conventions | `tests/test_architecture/test_conventions.py` |

### API Endpoints (from issue #105)

| Endpoint | Method | Service | Purpose |
|----------|--------|---------|---------|
| `/api/v3/wanted/missing` | GET | Radarr/Sonarr | Items wanted but not downloaded |
| `/api/v3/wanted/cutoff` | GET | Radarr/Sonarr | Items below quality cutoff |
| `/api/v3/command` | POST | Radarr | `{"name": "MoviesSearch", "movieIds": [id]}` |
| `/api/v3/command` | POST | Sonarr | `{"name": "EpisodeSearch", "episodeIds": [id]}` |

### Callback Data Conventions

All callbacks for this feature use the `missing_` prefix:

| Pattern | Purpose |
|---------|---------|
| `missing_noop` | Non-interactive display buttons |
| `missing_page_{N}` | Pagination (0-indexed) |
| `missing_filter_{type}` | Filter tabs: `all`, `movie`, `series`, `cutoff` |
| `missing_search_{service}_{id}` | Trigger manual search (e.g., `missing_search_radarr_123`) |
| `missing_refresh` | Re-fetch from API |
| `missing_back` | Return to main menu |

### Normalized Missing Item Schema

All items from both services are normalized to this dict structure:

```python
{
    "type": "movie" | "series",      # media type
    "title": str,                     # display title
    "year": int | None,               # release year
    "internal_id": int,               # Radarr movie ID or Sonarr series ID
    "service": "radarr" | "sonarr",   # origin service (for search dispatch)
    "monitored": bool,                # is monitored
    "episode_info": str | None,       # e.g. "S01E05 - Pilot" for series
}
```

For cutoff unmet items, same schema but fetched from a different endpoint.

---

## Phase 1: API Client Extensions

### Task 1.1: Add `get_missing()` to RadarrClient

**Files:**
- Modify: `src/api/radarr.py` (after `get_calendar` method, ~line 211)
- Test: `tests/test_api/test_radarr.py`
- Data: `tests/fixtures/sample_data.py`

**What:** Add a method that calls `GET /api/v3/wanted/missing?sortKey=title&sortDirection=ascending` and returns the `records` list. The Radarr wanted/missing endpoint returns a paginated response `{"page": 1, "pageSize": 20, "totalRecords": N, "records": [...]}`. We fetch all pages by requesting a large pageSize (1000) to keep it simple.

**Sample API response** (Radarr wanted/missing):
```json
{
  "page": 1, "pageSize": 20, "totalRecords": 3,
  "records": [
    {"id": 1, "title": "Fight Club", "year": 1999, "tmdbId": 550, "monitored": true},
    {"id": 2, "title": "Pulp Fiction", "year": 1994, "tmdbId": 680, "monitored": true}
  ]
}
```

**Implementation:**
```python
async def get_missing(self) -> List[Dict]:
    """Get movies that are wanted but not yet downloaded."""
    try:
        logger.info(Fore.BLUE + "📭 Getting missing movies from Radarr")
        result = await self._request(
            "wanted/missing?sortKey=title&sortDirection=ascending&pageSize=1000"
        )

        if not result or not isinstance(result, dict):
            logger.warning(Fore.YELLOW + "⚠️ No missing movies found")
            return []

        records = result.get("records", [])
        logger.info(Fore.GREEN + f"✅ Found {len(records)} missing movies")
        return records

    except Exception as e:
        logger.error(Fore.RED + f"❌ Failed to get missing movies: {str(e)}")
        return []
```

**Test sample data** (add to `tests/fixtures/sample_data.py`):
```python
RADARR_WANTED_MISSING = {
    "page": 1,
    "pageSize": 1000,
    "totalRecords": 2,
    "records": [
        {"id": 1, "title": "Fight Club", "year": 1999, "tmdbId": 550, "monitored": True},
        {"id": 2, "title": "Pulp Fiction", "year": 1994, "tmdbId": 680, "monitored": True},
    ],
}
```

**Tests to write:**
1. `test_get_missing_success` — mock `wanted/missing` endpoint returning `RADARR_WANTED_MISSING`, assert returns 2 records
2. `test_get_missing_empty` — mock returning `{"page":1, "pageSize":1000, "totalRecords":0, "records":[]}`, assert returns `[]`
3. `test_get_missing_connection_error` — mock with `aiohttp.ClientError`, assert returns `[]`
4. `test_get_missing_exception` — patch `_make_request` to raise, assert returns `[]`

### Task 1.2: Add `get_cutoff_unmet()` to RadarrClient

**Files:**
- Modify: `src/api/radarr.py` (after `get_missing`)
- Test: `tests/test_api/test_radarr.py`
- Data: `tests/fixtures/sample_data.py`

**What:** Same pattern as `get_missing()` but hits `wanted/cutoff` endpoint.

**Implementation:**
```python
async def get_cutoff_unmet(self) -> List[Dict]:
    """Get movies that are below the quality cutoff."""
    try:
        logger.info(Fore.BLUE + "⚠️ Getting cutoff unmet movies from Radarr")
        result = await self._request(
            "wanted/cutoff?sortKey=title&sortDirection=ascending&pageSize=1000"
        )

        if not result or not isinstance(result, dict):
            logger.warning(Fore.YELLOW + "⚠️ No cutoff unmet movies found")
            return []

        records = result.get("records", [])
        logger.info(Fore.GREEN + f"✅ Found {len(records)} cutoff unmet movies")
        return records

    except Exception as e:
        logger.error(Fore.RED + f"❌ Failed to get cutoff unmet movies: {str(e)}")
        return []
```

**Test sample data:**
```python
RADARR_WANTED_CUTOFF = {
    "page": 1, "pageSize": 1000, "totalRecords": 1,
    "records": [
        {"id": 3, "title": "Inception", "year": 2010, "tmdbId": 27205, "monitored": True},
    ],
}
```

**Tests:** Same 4-case pattern as Task 1.1.

### Task 1.3: Add `search_command()` to RadarrClient

**Files:**
- Modify: `src/api/radarr.py` (after `get_cutoff_unmet`)
- Test: `tests/test_api/test_radarr.py`

**What:** POST to `/api/v3/command` with `{"name": "MoviesSearch", "movieIds": [id]}` to trigger a manual search for a specific movie. Returns `True` on success.

**Implementation:**
```python
async def search_command(self, movie_id: int) -> bool:
    """Trigger a manual search for a specific movie."""
    try:
        logger.info(Fore.BLUE + f"🔍 Triggering search for movie ID: {movie_id}")
        success, data, error = await self._make_request(
            "command",
            method="POST",
            data={"name": "MoviesSearch", "movieIds": [movie_id]},
        )

        if success:
            logger.info(Fore.GREEN + f"✅ Search triggered for movie ID: {movie_id}")
            return True

        logger.error(Fore.RED + f"❌ Failed to trigger search: {error}")
        return False

    except Exception as e:
        logger.error(Fore.RED + f"❌ Failed to trigger search: {str(e)}")
        return False
```

**Tests:**
1. `test_search_command_success` — mock POST to `command` returning `{"id": 1}` with status 201, assert returns `True`
2. `test_search_command_failure` — mock POST returning error, assert returns `False`
3. `test_search_command_exception` — patch `_make_request` raising, assert returns `False`

### Task 1.4: Add `get_missing()` to SonarrClient

**Files:**
- Modify: `src/api/sonarr.py` (after `get_calendar` method, ~line 217)
- Test: `tests/test_api/test_sonarr.py`
- Data: `tests/fixtures/sample_data.py`

**What:** Same pattern as Radarr. Sonarr's `wanted/missing` returns episodes (not series), so each record has `seriesId`, `seasonNumber`, `episodeNumber`, `title`, and a nested `series` object.

**Sample Sonarr response:**
```json
{
  "page": 1, "pageSize": 1000, "totalRecords": 2,
  "records": [
    {
      "id": 101, "seriesId": 42, "seasonNumber": 1, "episodeNumber": 5,
      "title": "Pilot", "monitored": true,
      "series": {"id": 42, "title": "Breaking Bad", "year": 2008, "tvdbId": 81189}
    }
  ]
}
```

**Implementation:**
```python
async def get_missing(self) -> List[Dict]:
    """Get episodes that are wanted but not yet downloaded."""
    try:
        logger.info(Fore.BLUE + "📭 Getting missing episodes from Sonarr")
        result = await self._request(
            "wanted/missing?sortKey=series.title&sortDirection=ascending&pageSize=1000"
        )

        if not result or not isinstance(result, dict):
            logger.warning(Fore.YELLOW + "⚠️ No missing episodes found")
            return []

        records = result.get("records", [])
        logger.info(Fore.GREEN + f"✅ Found {len(records)} missing episodes")
        return records

    except Exception as e:
        logger.error(Fore.RED + f"❌ Failed to get missing episodes: {str(e)}")
        return []
```

**Tests:** Same 4-case pattern as Task 1.1 with Sonarr-specific sample data.

### Task 1.5: Add `get_cutoff_unmet()` to SonarrClient

**Files:**
- Modify: `src/api/sonarr.py`
- Test: `tests/test_api/test_sonarr.py`
- Data: `tests/fixtures/sample_data.py`

**What:** Same as Radarr cutoff but for Sonarr episodes.

**Tests:** Same 4-case pattern.

### Task 1.6: Add `search_command()` to SonarrClient

**Files:**
- Modify: `src/api/sonarr.py`
- Test: `tests/test_api/test_sonarr.py`

**What:** POST to `/api/v3/command` with `{"name": "EpisodeSearch", "episodeIds": [id]}`.

**Implementation:**
```python
async def search_command(self, episode_id: int) -> bool:
    """Trigger a manual search for a specific episode."""
    try:
        logger.info(Fore.BLUE + f"🔍 Triggering search for episode ID: {episode_id}")
        success, data, error = await self._make_request(
            "command",
            method="POST",
            data={"name": "EpisodeSearch", "episodeIds": [episode_id]},
        )

        if success:
            logger.info(Fore.GREEN + f"✅ Search triggered for episode ID: {episode_id}")
            return True

        logger.error(Fore.RED + f"❌ Failed to trigger search: {error}")
        return False

    except Exception as e:
        logger.error(Fore.RED + f"❌ Failed to trigger search: {str(e)}")
        return False
```

**Tests:** Same 3-case pattern as Task 1.3.

---

## Phase 2: Service Layer

### Task 2.1: Add `get_missing_media()` to MediaService

**Files:**
- Modify: `src/services/media.py` (after `get_upcoming` method, ~line 554)
- Test: `tests/test_services/test_media.py`

**What:** Aggregates missing items from Radarr and Sonarr concurrently using `asyncio.gather`. Normalizes each item into the unified schema. Sorts by title.

**Implementation:**
```python
async def get_missing_media(self) -> List[Dict]:
    """Get missing/wanted items from Radarr and Sonarr.

    Returns a normalized, title-sorted list of missing items.
    Skips disabled services and handles errors gracefully.
    """
    items = []

    tasks = []
    if self.radarr:
        tasks.append(("radarr", self.radarr.get_missing()))
    if self.sonarr:
        tasks.append(("sonarr", self.sonarr.get_missing()))

    if not tasks:
        return []

    results = await asyncio.gather(
        *(t[1] for t in tasks), return_exceptions=True
    )

    for (service_name, _), result in zip(tasks, results):
        if isinstance(result, Exception):
            logger.error(f"Missing fetch failed for {service_name}: {result}")
            continue

        if service_name == "radarr":
            for movie in result:
                items.append(self._normalize_radarr_missing(movie))
        else:
            for episode in result:
                items.append(self._normalize_sonarr_missing(episode))

    items.sort(key=lambda x: x["title"])
    return items

@staticmethod
def _normalize_radarr_missing(movie: Dict) -> Dict:
    """Normalize a Radarr missing movie into the unified schema."""
    return {
        "type": "movie",
        "title": movie.get("title", ""),
        "year": movie.get("year"),
        "internal_id": movie.get("id"),
        "service": "radarr",
        "monitored": movie.get("monitored", False),
        "episode_info": None,
    }

@staticmethod
def _normalize_sonarr_missing(episode: Dict) -> Dict:
    """Normalize a Sonarr missing episode into the unified schema."""
    series = episode.get("series", {})
    season = episode.get("seasonNumber")
    ep_num = episode.get("episodeNumber")
    ep_title = episode.get("title", "")
    ep_info = f"S{season:02d}E{ep_num:02d}" if season is not None and ep_num is not None else ""
    if ep_title:
        ep_info = f"{ep_info} - {ep_title}" if ep_info else ep_title

    return {
        "type": "series",
        "title": series.get("title", ""),
        "year": series.get("year"),
        "internal_id": episode.get("id"),
        "service": "sonarr",
        "monitored": episode.get("monitored", False),
        "episode_info": ep_info,
    }
```

**Tests:**
1. `test_get_missing_media_both_services` — mock both clients returning data, assert merged + sorted
2. `test_get_missing_media_radarr_only` — sonarr is None, assert only movie items
3. `test_get_missing_media_sonarr_only` — radarr is None, assert only series items
4. `test_get_missing_media_no_services` — both None, assert `[]`
5. `test_get_missing_media_service_error` — one raises Exception, other succeeds, assert partial results
6. `test_normalize_radarr_missing` — unit test the static normalizer
7. `test_normalize_sonarr_missing` — unit test with episode info formatting

### Task 2.2: Add `get_cutoff_unmet_media()` to MediaService

**Files:**
- Modify: `src/services/media.py`
- Test: `tests/test_services/test_media.py`

**What:** Same aggregation pattern as `get_missing_media()` but calls `get_cutoff_unmet()` on each client. Reuses the same normalizers since the response schema is identical.

**Implementation:**
```python
async def get_cutoff_unmet_media(self) -> List[Dict]:
    """Get items below quality cutoff from Radarr and Sonarr.

    Returns a normalized, title-sorted list of cutoff unmet items.
    Skips disabled services and handles errors gracefully.
    """
    items = []

    tasks = []
    if self.radarr:
        tasks.append(("radarr", self.radarr.get_cutoff_unmet()))
    if self.sonarr:
        tasks.append(("sonarr", self.sonarr.get_cutoff_unmet()))

    if not tasks:
        return []

    results = await asyncio.gather(
        *(t[1] for t in tasks), return_exceptions=True
    )

    for (service_name, _), result in zip(tasks, results):
        if isinstance(result, Exception):
            logger.error(f"Cutoff fetch failed for {service_name}: {result}")
            continue

        if service_name == "radarr":
            for movie in result:
                items.append(self._normalize_radarr_missing(movie))
        else:
            for episode in result:
                items.append(self._normalize_sonarr_missing(episode))

    items.sort(key=lambda x: x["title"])
    return items
```

**Tests:** Same pattern as Task 2.1 but calling `get_cutoff_unmet_media()`.

### Task 2.3: Add `trigger_missing_search()` to MediaService

**Files:**
- Modify: `src/services/media.py`
- Test: `tests/test_services/test_media.py`

**What:** Dispatches a search command to the correct API client based on service name.

**Implementation:**
```python
async def trigger_missing_search(self, service: str, item_id: int) -> bool:
    """Trigger a manual search for a missing item.

    Args:
        service: "radarr" or "sonarr"
        item_id: Internal ID of the item (movie ID or episode ID)

    Returns:
        True if search was triggered successfully.
    """
    try:
        if service == "radarr" and self.radarr:
            return await self.radarr.search_command(item_id)
        elif service == "sonarr" and self.sonarr:
            return await self.sonarr.search_command(item_id)
        logger.warning(f"Cannot trigger search: {service} not available")
        return False
    except Exception as e:
        logger.error(f"Failed to trigger search for {service}/{item_id}: {e}")
        return False
```

**Tests:**
1. `test_trigger_search_radarr` — mock radarr.search_command returning True
2. `test_trigger_search_sonarr` — mock sonarr.search_command returning True
3. `test_trigger_search_service_unavailable` — radarr is None, returns False
4. `test_trigger_search_exception` — search_command raises, returns False

---

## Phase 3: Keyboard Builder

### Task 3.1: Add `get_missing_items_keyboard()` to keyboards.py

**Files:**
- Modify: `src/bot/keyboards.py` (after `get_calendar_items_keyboard`, ~line 595)
- Test: `tests/test_keyboards.py` (or inline in handler tests)

**What:** Build a paginated keyboard for missing items. Each item shows as a display button, with a "Search Now" action button below it. Filter tabs at top, pagination in middle, refresh/back at bottom.

**Implementation:**
```python
def get_missing_items_keyboard(
    items: list, page: int, active_filter: str = "all",
    page_size: int = 5,
) -> InlineKeyboardMarkup:
    """Get paginated missing items keyboard with filter tabs.

    Args:
        items: Full list of normalized missing items.
        page: Current page (0-indexed).
        active_filter: Active filter tab ("all", "movie", "series", "cutoff").
        page_size: Number of items per page.
    """
    translation = TranslationService()
    type_emoji = {"movie": "\U0001f3ac", "series": "\U0001f4fa"}

    total_pages = max(1, -(-len(items) // page_size))
    start = page * page_size
    end = start + page_size
    page_items = items[start:end]

    keyboard = []

    # Filter tabs row
    filters = [
        ("all", translation.get_text("MissingFilterAll", default="All")),
        ("movie", translation.get_text("MissingFilterMovie", default="Movies")),
        ("series", translation.get_text("MissingFilterSeries", default="Series")),
        ("cutoff", translation.get_text("MissingFilterCutoff", default="Cutoff Unmet")),
    ]
    filter_row = []
    for filter_key, label in filters:
        text = f"\u2705 {label}" if filter_key == active_filter else label
        filter_row.append(
            InlineKeyboardButton(text, callback_data=f"missing_filter_{filter_key}")
        )
    keyboard.append(filter_row[:2])
    keyboard.append(filter_row[2:])

    # Item buttons
    for item in page_items:
        emoji = type_emoji.get(item["type"], "\U0001f3ac")
        title = item["title"]
        if item.get("year"):
            title = f"{title} ({item['year']})"
        if item.get("episode_info"):
            title = f"{title} - {item['episode_info']}"
        keyboard.append([
            InlineKeyboardButton(
                f"{emoji} {title}", callback_data="missing_noop"
            )
        ])
        # Search Now button
        keyboard.append([
            InlineKeyboardButton(
                f"\U0001f50d {translation.get_text('MissingSearchNow', default='Search Now')}",
                callback_data=f"missing_search_{item['service']}_{item['internal_id']}"
            )
        ])

    # Pagination row
    if total_pages > 1:
        nav_row = []
        if page > 0:
            nav_row.append(
                InlineKeyboardButton(
                    "\u25c0\ufe0f Prev", callback_data=f"missing_page_{page - 1}"
                )
            )
        nav_row.append(
            InlineKeyboardButton(
                f"{page + 1}/{total_pages}", callback_data="missing_noop"
            )
        )
        if page < total_pages - 1:
            nav_row.append(
                InlineKeyboardButton(
                    "Next \u25b6\ufe0f", callback_data=f"missing_page_{page + 1}"
                )
            )
        keyboard.append(nav_row)

    # Bottom row: refresh + back
    keyboard.append([
        InlineKeyboardButton(
            "\U0001f504 Refresh", callback_data="missing_refresh"
        ),
        InlineKeyboardButton(
            f"\u25c0\ufe0f {translation.get_text('Back')}",
            callback_data="missing_back"
        ),
    ])

    return InlineKeyboardMarkup(keyboard)


def get_missing_empty_keyboard(
    active_filter: str = "all",
) -> InlineKeyboardMarkup:
    """Get keyboard for empty missing list (filters + refresh + back)."""
    translation = TranslationService()

    keyboard = []

    filters = [
        ("all", translation.get_text("MissingFilterAll", default="All")),
        ("movie", translation.get_text("MissingFilterMovie", default="Movies")),
        ("series", translation.get_text("MissingFilterSeries", default="Series")),
        ("cutoff", translation.get_text("MissingFilterCutoff", default="Cutoff Unmet")),
    ]
    filter_row = []
    for filter_key, label in filters:
        text = f"\u2705 {label}" if filter_key == active_filter else label
        filter_row.append(
            InlineKeyboardButton(text, callback_data=f"missing_filter_{filter_key}")
        )
    keyboard.append(filter_row[:2])
    keyboard.append(filter_row[2:])

    keyboard.append([
        InlineKeyboardButton(
            "\U0001f504 Refresh", callback_data="missing_refresh"
        ),
        InlineKeyboardButton(
            f"\u25c0\ufe0f {translation.get_text('Back')}",
            callback_data="missing_back"
        ),
    ])

    return InlineKeyboardMarkup(keyboard)
```

---

## Phase 4: Handler

### Task 4.1: Create MissingHandler

**Files:**
- Create: `src/bot/handlers/missing.py`
- Test: `tests/test_handlers/test_missing_handler.py`

**What:** New handler class following CalendarHandler pattern. Owns `/missing` command and `missing_*` callbacks. Caches fetched items in `context.user_data["missing_items"]` and active filter in `context.user_data["missing_filter"]`.

**Implementation:**
```python
"""
Filename: missing.py
Author: Addarr Contributors
Created Date: 2026-03-03
Description: Missing/wanted media handler module.
"""

from telegram import Update
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes

from src.utils.logger import get_logger, log_user_interaction
from src.bot.handlers.auth import require_auth
from src.bot.keyboards import (
    get_missing_items_keyboard,
    get_missing_empty_keyboard,
    get_main_menu_keyboard,
)
from src.services.media import MediaService
from src.services.translation import TranslationService

logger = get_logger("addarr.missing")


class MissingHandler:
    """Handler for missing/wanted media browsing"""

    def __init__(self):
        self.media_service = MediaService()
        self.translation = TranslationService()

    def get_handler(self):
        """Get missing command handlers"""
        return [
            CommandHandler("missing", self.show_missing),
            CallbackQueryHandler(
                self.handle_missing_action, pattern="^missing_"
            ),
        ]

    @require_auth
    async def show_missing(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Show missing/wanted media with inline keyboard."""
        if not update.effective_user:
            return

        log_user_interaction(logger, update.effective_user, "/missing")

        active_filter = context.user_data.setdefault("missing_filter", "all")

        items = await self._fetch_items(context, active_filter)
        context.user_data["missing_items"] = items

        text, keyboard = self._build_response(items, active_filter)

        if update.callback_query:
            await update.callback_query.message.edit_text(
                text, reply_markup=keyboard
            )
        else:
            await update.message.reply_text(text, reply_markup=keyboard)

    @require_auth
    async def handle_missing_action(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle missing callback button presses."""
        if not update.callback_query:
            return

        query = update.callback_query
        data = query.data

        log_user_interaction(logger, query.from_user, data)

        if data.startswith("missing_filter_"):
            await self._handle_filter(query, context)
        elif data.startswith("missing_page_"):
            await self._handle_page(query, context)
        elif data.startswith("missing_search_"):
            await self._handle_search(query, context)
        elif data == "missing_refresh":
            await self._handle_refresh(query, context)
        elif data == "missing_back":
            await self._handle_back(query)
        else:
            await query.answer()

    async def _fetch_items(self, context, active_filter):
        """Fetch missing items based on active filter."""
        if active_filter == "cutoff":
            return await self.media_service.get_cutoff_unmet_media()
        else:
            items = await self.media_service.get_missing_media()
            if active_filter == "movie":
                items = [i for i in items if i["type"] == "movie"]
            elif active_filter == "series":
                items = [i for i in items if i["type"] == "series"]
            return items

    async def _handle_filter(self, query, context):
        """Change the active filter and re-fetch."""
        active_filter = query.data.split("_")[-1]
        context.user_data["missing_filter"] = active_filter

        items = await self._fetch_items(context, active_filter)
        context.user_data["missing_items"] = items

        text, keyboard = self._build_response(items, active_filter)
        await query.message.edit_text(text, reply_markup=keyboard)
        await query.answer()

    async def _handle_page(self, query, context):
        """Show a different page of cached missing items."""
        page = int(query.data.split("_")[-1])
        items = context.user_data.get("missing_items", [])
        active_filter = context.user_data.get("missing_filter", "all")

        text, keyboard = self._build_response(items, active_filter, page)
        await query.message.edit_text(text, reply_markup=keyboard)
        await query.answer()

    async def _handle_search(self, query, context):
        """Trigger a manual search for a specific item."""
        # Parse: missing_search_radarr_123
        parts = query.data.split("_")
        service = parts[2]
        item_id = int(parts[3])

        await query.answer(
            self.translation.get_text("MissingSearching", default="Searching...")
        )

        success = await self.media_service.trigger_missing_search(service, item_id)

        if success:
            await query.answer(
                self.translation.get_text("MissingSearchSuccess", default="Search triggered!"),
                show_alert=True,
            )
        else:
            await query.answer(
                self.translation.get_text("MissingSearchFailed", default="Search failed."),
                show_alert=True,
            )

    async def _handle_refresh(self, query, context):
        """Clear cache and re-fetch missing items."""
        active_filter = context.user_data.get("missing_filter", "all")

        items = await self._fetch_items(context, active_filter)
        context.user_data["missing_items"] = items

        text, keyboard = self._build_response(items, active_filter)
        await query.message.edit_text(text, reply_markup=keyboard)
        await query.answer()

    async def _handle_back(self, query):
        """Return to the main menu."""
        await query.message.edit_text(
            "\U0001f3e0 Main Menu",
            reply_markup=get_main_menu_keyboard(),
        )
        await query.answer()

    def _build_response(self, items, active_filter, page=0):
        """Build missing text and keyboard from items."""
        title = self.translation.get_text("MissingTitle", default="Missing/Wanted Media")

        if items:
            text = f"\U0001f4ed {title}\n\n{len(items)} items"
            keyboard = get_missing_items_keyboard(items, page, active_filter)
        else:
            empty = self.translation.get_text("MissingEmpty", default="No missing media found.")
            text = f"\U0001f4ed {title}\n\n{empty}"
            keyboard = get_missing_empty_keyboard(active_filter)
        return text, keyboard
```

**Handler test fixture** (add to `tests/test_handlers/conftest.py`):
```python
@pytest.fixture
def missing_handler(mock_media_service, mock_translation_service):
    """Create a MissingHandler with patched services."""
    with (
        patch("src.bot.handlers.missing.MediaService") as mock_ms_class,
        patch("src.bot.handlers.missing.TranslationService") as mock_ts_class,
        patch("src.bot.handlers.missing.get_missing_items_keyboard") as mock_items_kbd,
        patch("src.bot.handlers.missing.get_missing_empty_keyboard") as mock_empty_kbd,
        patch("src.bot.handlers.missing.get_main_menu_keyboard") as mock_menu_kbd,
    ):
        mock_ts_class.return_value = mock_translation_service
        mock_ms_class.return_value = mock_media_service
        mock_media_service.get_missing_media = AsyncMock(return_value=[])
        mock_media_service.get_cutoff_unmet_media = AsyncMock(return_value=[])
        mock_media_service.trigger_missing_search = AsyncMock(return_value=True)
        mock_items_kbd.return_value = MagicMock()
        mock_empty_kbd.return_value = MagicMock()
        mock_menu_kbd.return_value = MagicMock()

        from src.bot.handlers.missing import MissingHandler
        from src.bot.handlers.auth import AuthHandler

        AuthHandler._authenticated_users = {12345}
        handler = MissingHandler()
        handler._mock_service = mock_media_service
        handler._mock_ts = mock_translation_service
        handler._mock_items_kbd = mock_items_kbd
        handler._mock_empty_kbd = mock_empty_kbd
        handler._mock_menu_kbd = mock_menu_kbd
        yield handler
```

**Tests to write:**
1. `test_show_missing_with_results` — items returned, assert reply_text called with title and items keyboard
2. `test_show_missing_empty` — no items, assert empty keyboard used
3. `test_show_missing_via_callback` — callback_query present, assert edit_text used
4. `test_show_missing_no_user` — effective_user is None, returns None
5. `test_filter_movie` — `missing_filter_movie` callback, assert filter applied
6. `test_filter_series` — `missing_filter_series` callback
7. `test_filter_cutoff` — `missing_filter_cutoff` callback, assert `get_cutoff_unmet_media` called
8. `test_filter_all` — `missing_filter_all` callback, assert `get_missing_media` called
9. `test_page_navigation` — `missing_page_1` callback, assert page param passed
10. `test_search_success` — `missing_search_radarr_123` callback, assert `trigger_missing_search` called, success answer
11. `test_search_failure` — trigger returns False, assert failure answer
12. `test_refresh` — `missing_refresh` callback, assert re-fetch
13. `test_back_to_menu` — `missing_back` callback, assert main menu keyboard
14. `test_noop_callback` — `missing_noop` callback, assert only `query.answer()` called

---

## Phase 5: Integration & Registration

### Task 5.1: Register MissingHandler in main.py

**Files:**
- Modify: `src/main.py` (~line 18 for import, ~line 139 after CalendarHandler registration)

**What:** Import and wire MissingHandler following the same pattern as CalendarHandler.

**Changes:**
1. Add import: `from src.bot.handlers.missing import MissingHandler`
2. Add handler registration after CalendarHandler block (~line 139):
```python
# Missing/wanted handler
missing_handler = MissingHandler()
for handler in missing_handler.get_handler():
    self.application.add_handler(handler)
```

### Task 5.2: Register `/missing` command

**Files:**
- Modify: `src/bot/commands.py` (~line 58, after the `upcoming` command block)

**What:** Add `/missing` command to authenticated users' command list, conditional on Radarr or Sonarr being enabled (same condition as `upcoming`).

**Change:**
```python
# After the upcoming block:
if config.get("radarr", {}).get("enable") or config.get("sonarr", {}).get("enable"):
    commands.append(BotCommand("missing", translation.get_text("CommandMissing")))
```

### Task 5.3: Add translation keys

**Files:**
- Modify: All 9 translation files in `translations/`

**What:** Add flat top-level keys for the missing feature. English values:

```yaml
# Missing/Wanted media
CommandMissing: "Browse missing/wanted media"
MissingTitle: "Missing/Wanted Media"
MissingEmpty: "No missing media found."
MissingSearchNow: "Search Now"
MissingSearching: "Searching..."
MissingSearchSuccess: "Search triggered!"
MissingSearchFailed: "Failed to trigger search."
MissingFilterAll: "All"
MissingFilterMovie: "Movies"
MissingFilterSeries: "Series"
MissingFilterCutoff: "Cutoff Unmet"
```

For non-English translations, use the English text as placeholder (the translation maintainers can update later).

### Task 5.4: Update architecture tests

**Files:**
- Verify: `tests/test_architecture/test_conventions.py` — no changes needed since MissingHandler is not a service singleton. But the handler convention test will auto-discover `missing.py` and verify `get_handler()` exists.
- Verify: Architecture layer boundary tests pass (MissingHandler imports services, not API clients directly).

### Task 5.5: Update mock_media_service fixture

**Files:**
- Modify: `tests/test_handlers/conftest.py` — add `get_missing_media`, `get_cutoff_unmet_media`, `trigger_missing_search` to `mock_media_service`
- Modify: `tests/test_services/conftest.py` — add `get_missing`, `get_cutoff_unmet`, `search_command` to `mock_radarr_client` and `mock_sonarr_client`

---

## Verification

After all phases complete:

1. `python -m pytest --tb=short -q` — all tests pass
2. `python -m flake8 .` — no lint errors
3. `PYTHONIOENCODING=utf-8 python run.py --validate-i18n` — translation validation passes
4. `python -m pytest --cov=src.api.radarr --cov=src.api.sonarr --cov=src.services.media --cov=src.bot.handlers.missing --cov=src.bot.keyboards --cov-report=term-missing` — 100% coverage on new code

# Download History Command (`/history`) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a `/history` command that shows recent grab/import/fail activity from Radarr and Sonarr, with event type filtering and pagination.

**Architecture:** Follows the existing three-layer pattern: API clients get raw history, MediaService normalizes and aggregates, HistoryHandler presents via Telegram with inline keyboards. Mirrors the calendar/missing/queue handler pattern closely.

**Tech Stack:** python-telegram-bot v20+, aiohttp, asyncio.gather for parallel fetches.

---

## Phase 1: API Layer — Add `get_history()` to Radarr and Sonarr clients

### Task 1.1: Add `get_history()` to RadarrClient

**Files:**
- Modify: `src/api/radarr.py` (add method after `get_calendar`)
- Test: `tests/test_api/test_radarr.py`
- Modify: `tests/fixtures/sample_data.py` (add `RADARR_HISTORY` sample data)

**Context:**
- Radarr history endpoint: `GET /api/v3/history?page=1&pageSize=20&sortKey=date&sortDirection=descending`
- Optional filter: `&eventType=grabbed` (values: `grabbed`, `downloadFolderImported`, `downloadFailed`, `movieFileDeleted`, `movieFileRenamed`)
- Response is paginated: `{"page": 1, "pageSize": 20, "totalRecords": 100, "records": [...]}`
- Each record has: `id`, `movieId`, `date`, `eventType`, `sourceTitle`, `quality`, `data` (contains indexer info), plus a `movie` object with `title`, `year`, `tmdbId`
- Follow the `get_missing()` pattern: call `_request()`, check for dict response, extract `records`

**Sample data to add to `tests/fixtures/sample_data.py`:**

```python
RADARR_HISTORY = {
    "page": 1,
    "pageSize": 20,
    "totalRecords": 3,
    "records": [
        {
            "id": 1, "movieId": 10,
            "sourceTitle": "Fight.Club.1999.1080p.BluRay",
            "quality": {"quality": {"name": "Bluray-1080p"}},
            "date": "2026-03-09T14:30:00Z",
            "eventType": "grabbed",
            "data": {"indexer": "NZBgeek"},
            "movie": {"title": "Fight Club", "year": 1999, "tmdbId": 550},
        },
        {
            "id": 2, "movieId": 10,
            "sourceTitle": "Fight.Club.1999.1080p.BluRay",
            "quality": {"quality": {"name": "Bluray-1080p"}},
            "date": "2026-03-09T15:00:00Z",
            "eventType": "downloadFolderImported",
            "data": {},
            "movie": {"title": "Fight Club", "year": 1999, "tmdbId": 550},
        },
        {
            "id": 3, "movieId": 20,
            "sourceTitle": "Pulp.Fiction.1994.720p",
            "quality": {"quality": {"name": "Bluray-720p"}},
            "date": "2026-03-08T10:00:00Z",
            "eventType": "downloadFailed",
            "data": {"indexer": "Drunken Slug"},
            "movie": {"title": "Pulp Fiction", "year": 1994, "tmdbId": 680},
        },
    ],
}
```

**Implementation:**

```python
async def get_history(self, page: int = 1, page_size: int = 20,
                      event_type: str = None) -> List[Dict]:
    """Get recent history from Radarr."""
    try:
        logger.info(Fore.BLUE + "📜 Getting history from Radarr")
        endpoint = (
            f"history?sortKey=date&sortDirection=descending"
            f"&page={page}&pageSize={page_size}"
        )
        if event_type:
            endpoint += f"&eventType={event_type}"

        result = await self._request(endpoint)

        if not result or not isinstance(result, dict):
            logger.warning(Fore.YELLOW + "⚠️ No history found in Radarr")
            return []

        records = result.get("records", [])
        logger.info(Fore.GREEN + f"✅ Found {len(records)} history items in Radarr")
        return records

    except Exception as e:
        logger.error(Fore.RED + f"❌ Failed to get Radarr history: {str(e)}")
        return []
```

**Tests:**
1. `test_get_history_success` — mock `history?sortKey=date&sortDirection=descending&page=1&pageSize=20` returning `RADARR_HISTORY`, assert returns 3 records
2. `test_get_history_with_event_type` — pass `event_type="grabbed"`, assert URL includes `&eventType=grabbed`
3. `test_get_history_empty` — mock returning `{"records": []}`, assert returns `[]`
4. `test_get_history_error` — mock exception, assert returns `[]`
5. `test_get_history_non_dict_response` — mock returning `None`, assert returns `[]`

### Task 1.2: Add `get_history()` to SonarrClient

**Files:**
- Modify: `src/api/sonarr.py` (add method after `get_calendar`)
- Test: `tests/test_api/test_sonarr.py`
- Modify: `tests/fixtures/sample_data.py` (add `SONARR_HISTORY` sample data)

**Context:**
- Sonarr history endpoint: identical URL pattern to Radarr (`/api/v3/history?...`)
- Event types: `grabbed`, `downloadFolderImported`, `downloadFailed`, `episodeFileDeleted`, `episodeFileRenamed`
- Each record has: `id`, `seriesId`, `episodeId`, `date`, `eventType`, `sourceTitle`, `quality`, `data`, plus `series` and `episode` objects
- Implementation is identical to Radarr's `get_history()` except for logger name

**Sample data:**

```python
SONARR_HISTORY = {
    "page": 1,
    "pageSize": 20,
    "totalRecords": 2,
    "records": [
        {
            "id": 101, "seriesId": 42, "episodeId": 201,
            "sourceTitle": "Breaking.Bad.S01E01.720p",
            "quality": {"quality": {"name": "HDTV-720p"}},
            "date": "2026-03-09T12:00:00Z",
            "eventType": "grabbed",
            "data": {"indexer": "NZBgeek"},
            "series": {"title": "Breaking Bad", "year": 2008, "tvdbId": 81189},
            "episode": {"title": "Pilot", "seasonNumber": 1, "episodeNumber": 1},
        },
        {
            "id": 102, "seriesId": 42, "episodeId": 201,
            "sourceTitle": "Breaking.Bad.S01E01.720p",
            "quality": {"quality": {"name": "HDTV-720p"}},
            "date": "2026-03-09T12:30:00Z",
            "eventType": "downloadFolderImported",
            "data": {},
            "series": {"title": "Breaking Bad", "year": 2008, "tvdbId": 81189},
            "episode": {"title": "Pilot", "seasonNumber": 1, "episodeNumber": 1},
        },
    ],
}
```

**Implementation:** Same shape as RadarrClient's `get_history()` with "Sonarr" in log messages.

**Tests:** Mirror Task 1.1 tests.

---

## Phase 2: Service Layer — Aggregate history in MediaService

### Task 2.1: Add `get_history()` to MediaService

**Files:**
- Modify: `src/services/media.py` (add method + two normalizer statics)
- Test: `tests/test_services/test_media_service.py`

**Context:**
- Follow the `get_upcoming()` pattern: gather from both services, normalize, merge, sort by date descending
- Normalize into a unified schema that the handler can display without knowing the source service

**Normalized schema:**

```python
{
    "type": "movie" | "episode",        # from service_name
    "title": str,                        # movie title or series title
    "episode_title": str | None,         # episode title (Sonarr only)
    "season": int | None,                # season number (Sonarr only)
    "episode": int | None,               # episode number (Sonarr only)
    "date": str,                         # ISO date string
    "event_type": str,                   # grabbed, imported, failed, etc.
    "quality": str,                      # quality name
    "source_title": str,                 # release name
    "service": "radarr" | "sonarr",      # source service
}
```

**Implementation:**

```python
async def get_history(self, page: int = 1, page_size: int = 20,
                      event_type: str = None) -> List[Dict]:
    """Get recent history from Radarr and Sonarr.

    Returns a normalized, date-sorted (newest first) list of history items.
    """
    tasks = []
    if self.radarr:
        tasks.append(("radarr", self.radarr.get_history(
            page, page_size, event_type
        )))
    if self.sonarr:
        tasks.append(("sonarr", self.sonarr.get_history(
            page, page_size, event_type
        )))

    if not tasks:
        return []

    results = await asyncio.gather(
        *(t[1] for t in tasks), return_exceptions=True
    )

    items = []
    for (service_name, _), result in zip(tasks, results):
        if isinstance(result, Exception):
            logger.error(f"History fetch failed for {service_name}: {result}")
            continue

        if service_name == "radarr":
            for record in result:
                items.append(self._normalize_radarr_history(record))
        else:
            for record in result:
                items.append(self._normalize_sonarr_history(record))

    # Sort by date descending (newest first)
    items.sort(key=lambda x: x.get("date", ""), reverse=True)
    return items

@staticmethod
def _normalize_radarr_history(record: Dict) -> Dict:
    """Normalize a Radarr history record."""
    movie = record.get("movie", {})
    return {
        "type": "movie",
        "title": movie.get("title", ""),
        "episode_title": None,
        "season": None,
        "episode": None,
        "date": record.get("date", ""),
        "event_type": record.get("eventType", ""),
        "quality": record.get("quality", {}).get("quality", {}).get("name", ""),
        "source_title": record.get("sourceTitle", ""),
        "service": "radarr",
    }

@staticmethod
def _normalize_sonarr_history(record: Dict) -> Dict:
    """Normalize a Sonarr history record."""
    series = record.get("series", {})
    ep = record.get("episode", {})
    return {
        "type": "episode",
        "title": series.get("title", ""),
        "episode_title": ep.get("title"),
        "season": ep.get("seasonNumber"),
        "episode": ep.get("episodeNumber"),
        "date": record.get("date", ""),
        "event_type": record.get("eventType", ""),
        "quality": record.get("quality", {}).get("quality", {}).get("name", ""),
        "source_title": record.get("sourceTitle", ""),
        "service": "sonarr",
    }
```

**Tests:**
1. `test_get_history_both_services` — both radarr and sonarr return items, verify merged and sorted by date descending
2. `test_get_history_radarr_only` — sonarr is None, verify only radarr items returned
3. `test_get_history_sonarr_only` — radarr is None, verify only sonarr items returned
4. `test_get_history_no_services` — both None, returns `[]`
5. `test_get_history_exception_handling` — one service raises, other returns data, verify partial result
6. `test_get_history_with_event_type` — verify event_type passed through to clients
7. `test_normalize_radarr_history` — test normalizer with sample record
8. `test_normalize_sonarr_history` — test normalizer with sample record

---

## Phase 3: Translation Keys

### Task 3.1: Add history translation keys to all locales

**Files:**
- Modify: All 10 locale files in `translations/` + template
- No test file (validated by `--validate-i18n`)

**Keys to add (after the Queue section in each file):**

English (`addarr.en-us.yml`):
```yaml
  # History
  History: "📜 History"
  CommandHistory: "Browse recent activity"
  HistoryTitle: "📜 Recent Activity"
  HistoryEmpty: "No recent activity found."
  HistoryGrabbed: "Grabbed"
  HistoryImported: "Imported"
  HistoryFailed: "Failed"
  HistoryAll: "All"
```

For non-English locales, keep the same keys with translated values. The emoji prefixes stay the same. Use reasonable translations for each language.

**Validation:** Run `PYTHONIOENCODING=utf-8 python run.py --validate-i18n` to verify all keys present.

---

## Phase 4: Keyboards

### Task 4.1: Add history keyboard functions to `keyboards.py`

**Files:**
- Modify: `src/bot/keyboards.py`
- Test: `tests/test_bot/test_keyboards.py`

**Context:**
- Follow the `get_calendar_items_keyboard` / `get_missing_items_keyboard` pattern
- Need two keyboards: items display with pagination, and filter selection

**Implementation:**

```python
_HISTORY_EVENT_EMOJI = {
    "grabbed": "\U0001f4e5",          # inbox tray
    "downloadFolderImported": "\u2705",  # check mark
    "downloadFailed": "\u274c",          # cross mark
    "movieFileDeleted": "\U0001f5d1",    # wastebasket
    "episodeFileDeleted": "\U0001f5d1",
    "movieFileRenamed": "\U0001f4dd",    # memo
    "episodeFileRenamed": "\U0001f4dd",
}


def get_history_items_keyboard(
    items: list, page: int = 0, page_size: int = 5,
    event_filter: str = None,
) -> InlineKeyboardMarkup:
    """Paginated history items keyboard with filter tabs."""
    translation = TranslationService()
    total_pages = max(1, -(-len(items) // page_size))
    start = page * page_size
    page_items = items[start:start + page_size]

    keyboard = []

    # Filter tabs row
    filters = [
        ("HistoryAll", None),
        ("HistoryGrabbed", "grabbed"),
        ("HistoryImported", "downloadFolderImported"),
        ("HistoryFailed", "downloadFailed"),
    ]
    filter_row = []
    for label_key, filter_val in filters:
        prefix = "\u2022 " if event_filter == filter_val else ""
        cb = f"hist_filter_{filter_val}" if filter_val else "hist_filter_all"
        filter_row.append(
            InlineKeyboardButton(
                f"{prefix}{translation.get_text(label_key)}",
                callback_data=cb,
            )
        )
    keyboard.append(filter_row)

    # Item rows
    for item in page_items:
        emoji = _HISTORY_EVENT_EMOJI.get(item.get("event_type"), "\u2753")
        type_emoji = _MEDIA_TYPE_EMOJI.get(item.get("type"), "")
        title = item.get("title", "")
        # Truncate long titles
        if len(title) > 30:
            title = title[:27] + "..."
        quality = item.get("quality", "")
        date_str = item.get("date", "")[:10]

        label = f"{emoji} {type_emoji} {title} [{quality}] {date_str}"
        keyboard.append([
            InlineKeyboardButton(label, callback_data="hist_noop")
        ])

    # Pagination row
    if total_pages > 1:
        nav_row = []
        if page > 0:
            nav_row.append(InlineKeyboardButton(
                f"\u25c0\ufe0f {translation.get_text('Previous')}",
                callback_data=f"hist_page_{page - 1}",
            ))
        nav_row.append(InlineKeyboardButton(
            f"{page + 1}/{total_pages}",
            callback_data="hist_noop",
        ))
        if page < total_pages - 1:
            nav_row.append(InlineKeyboardButton(
                f"{translation.get_text('Next')} \u25b6\ufe0f",
                callback_data=f"hist_page_{page + 1}",
            ))
        keyboard.append(nav_row)

    # Action row
    keyboard.append([
        InlineKeyboardButton(
            "\U0001f504 " + translation.get_text("Search"),
            callback_data="hist_refresh",
        ),
        InlineKeyboardButton(
            "\u25c0\ufe0f " + translation.get_text("Back"),
            callback_data="hist_back",
        ),
    ])

    return InlineKeyboardMarkup(keyboard)


def get_history_empty_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for empty history state."""
    translation = TranslationService()
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(
            "\U0001f504 " + translation.get_text("Search"),
            callback_data="hist_refresh",
        ),
        InlineKeyboardButton(
            "\u25c0\ufe0f " + translation.get_text("Back"),
            callback_data="hist_back",
        ),
    ]])
```

**Tests:**
1. `test_get_history_items_keyboard_with_items` — 6 items, verify pagination present
2. `test_get_history_items_keyboard_empty` — 0 items, verify no item rows
3. `test_get_history_items_keyboard_filter_active` — verify bullet prefix on active filter
4. `test_get_history_empty_keyboard` — verify refresh and back buttons

---

## Phase 5: Handler

### Task 5.1: Create HistoryHandler

**Files:**
- Create: `src/bot/handlers/history.py`
- Test: `tests/test_handlers/test_history_handler.py`
- Modify: `tests/test_handlers/conftest.py` (add `history_handler` fixture)

**Context:**
- Follow CalendarHandler pattern exactly: command handler + callback handler + `_build_response` helper
- Use `context.user_data` for caching items, current page, current filter
- `@require_auth` on both public methods

**Implementation:**

```python
"""
Filename: history.py
Author: Addarr Contributors
Created Date: 2026-03-09
Description: History handler for recent Radarr/Sonarr activity.
"""

from telegram import Update
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes

from src.utils.logger import get_logger, log_user_interaction
from src.bot.handlers.auth import require_auth
from src.bot.keyboards import (
    get_history_items_keyboard,
    get_history_empty_keyboard,
    get_main_menu_keyboard,
)
from src.services.media import MediaService
from src.services.translation import TranslationService

logger = get_logger("addarr.history")


class HistoryHandler:
    """Handler for /history command showing recent activity."""

    def __init__(self):
        self.media_service = MediaService()
        self.translation = TranslationService()

    def get_handler(self):
        """Get history command handlers."""
        return [
            CommandHandler("history", self.show_history),
            CallbackQueryHandler(
                self.handle_history_action, pattern="^hist_"
            ),
        ]

    @require_auth
    async def show_history(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Show recent activity with inline keyboard."""
        if not update.effective_user:  # pragma: no cover
            return

        log_user_interaction(logger, update.effective_user, "/history")

        context.user_data["hist_filter"] = None
        context.user_data["hist_page"] = 0

        items = await self.media_service.get_history()
        context.user_data["hist_items"] = items

        text, keyboard = self._build_response(items)

        if update.callback_query:
            await update.callback_query.message.edit_text(
                text, reply_markup=keyboard
            )
        else:
            await update.message.reply_text(text, reply_markup=keyboard)

    @require_auth
    async def handle_history_action(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle history callback button presses."""
        if not update.callback_query:
            return

        query = update.callback_query
        data = query.data

        log_user_interaction(logger, query.from_user, data)

        if data.startswith("hist_filter_"):
            await self._handle_filter(query, context)
        elif data.startswith("hist_page_"):
            await self._handle_page(query, context)
        elif data == "hist_refresh":
            await self._handle_refresh(query, context)
        elif data == "hist_back":
            await self._handle_back(query)
        else:
            await query.answer()

    async def _handle_filter(self, query, context):
        """Change event type filter and re-fetch."""
        raw = query.data.replace("hist_filter_", "")
        event_filter = None if raw == "all" else raw
        context.user_data["hist_filter"] = event_filter
        context.user_data["hist_page"] = 0

        items = await self.media_service.get_history(
            event_type=event_filter
        )
        context.user_data["hist_items"] = items

        text, keyboard = self._build_response(
            items, event_filter=event_filter
        )
        await query.message.edit_text(text, reply_markup=keyboard)
        await query.answer()

    async def _handle_page(self, query, context):
        """Show a different page of cached history items."""
        page = int(query.data.split("_")[-1])
        context.user_data["hist_page"] = page
        items = context.user_data.get("hist_items", [])
        event_filter = context.user_data.get("hist_filter")

        text, keyboard = self._build_response(
            items, page=page, event_filter=event_filter
        )
        await query.message.edit_text(text, reply_markup=keyboard)
        await query.answer()

    async def _handle_refresh(self, query, context):
        """Re-fetch history data."""
        event_filter = context.user_data.get("hist_filter")
        context.user_data["hist_page"] = 0

        items = await self.media_service.get_history(
            event_type=event_filter
        )
        context.user_data["hist_items"] = items

        text, keyboard = self._build_response(
            items, event_filter=event_filter
        )
        await query.message.edit_text(text, reply_markup=keyboard)
        await query.answer()

    async def _handle_back(self, query):
        """Return to the main menu."""
        await query.message.edit_text(
            "\U0001f3e0 Main Menu",
            reply_markup=get_main_menu_keyboard(),
        )
        await query.answer()

    def _build_response(self, items, page=0, event_filter=None):
        """Build history text and keyboard from items."""
        if items:
            title = self.translation.get_text("HistoryTitle")
            text = f"\U0001f4dc {title}\n\n{len(items)} items"
            keyboard = get_history_items_keyboard(
                items, page, event_filter=event_filter
            )
        else:
            text = (
                f"\U0001f4dc {self.translation.get_text('HistoryTitle')}"
                f"\n\n{self.translation.get_text('HistoryEmpty')}"
            )
            keyboard = get_history_empty_keyboard()
        return text, keyboard
```

**Handler fixture (add to `tests/test_handlers/conftest.py`):**

```python
@pytest.fixture
def history_handler(mock_media_service, mock_translation_service):
    """Create a HistoryHandler with patched services."""
    with (
        patch("src.bot.handlers.history.MediaService") as mock_ms_class,
        patch("src.bot.handlers.history.TranslationService") as mock_ts_class,
        patch("src.bot.handlers.history.get_history_items_keyboard") as mock_items_kbd,
        patch("src.bot.handlers.history.get_history_empty_keyboard") as mock_empty_kbd,
        patch("src.bot.handlers.history.get_main_menu_keyboard") as mock_menu_kbd,
    ):
        mock_ts_class.return_value = mock_translation_service
        mock_ms_class.return_value = mock_media_service
        mock_media_service.get_history = AsyncMock(return_value=[])
        mock_items_kbd.return_value = MagicMock()
        mock_empty_kbd.return_value = MagicMock()
        mock_menu_kbd.return_value = MagicMock()

        from src.bot.handlers.history import HistoryHandler
        from src.bot.handlers.auth import AuthHandler

        AuthHandler._authenticated_users = {12345}
        handler = HistoryHandler()
        handler._mock_service = mock_media_service
        handler._mock_ts = mock_translation_service
        handler._mock_items_kbd = mock_items_kbd
        handler._mock_empty_kbd = mock_empty_kbd
        handler._mock_menu_kbd = mock_menu_kbd
        yield handler
```

**Tests:**
1. `test_show_history_with_results` — service returns items, verify reply_text called with title, items cached in user_data
2. `test_show_history_empty` — service returns [], verify empty text shown, empty keyboard used
3. `test_show_history_via_callback` — callback_query present, verify edit_text called instead of reply_text
4. `test_show_history_no_user` — effective_user is None, verify returns immediately
5. `test_handle_filter_grabbed` — callback `hist_filter_grabbed`, verify `get_history(event_type="grabbed")` called
6. `test_handle_filter_all` — callback `hist_filter_all`, verify `get_history(event_type=None)` called
7. `test_handle_page` — callback `hist_page_1`, verify page 1 shown from cached items
8. `test_handle_refresh` — callback `hist_refresh`, verify `get_history()` re-called
9. `test_handle_back` — callback `hist_back`, verify main menu shown
10. `test_handle_noop` — callback `hist_noop`, verify `query.answer()` called

---

## Phase 6: Registration and Integration

### Task 6.1: Register HistoryHandler in main.py and commands

**Files:**
- Modify: `src/main.py` (add import + registration in `_add_handlers`)
- Modify: `src/bot/commands.py` (add `history` command description)
- Modify: `src/bot/handlers/__init__.py` (add to `__all__`)
- Test: `tests/test_main.py` (verify handler registered)
- Test: `tests/test_bot/test_commands.py` (verify command listed)

**Registration location:** After Queue handler, before Transmission handler (follows the logical grouping of media information commands).

```python
# In _add_handlers():
# History handler
history_handler = HistoryHandler()
for handler in history_handler.get_handler():
    self.application.add_handler(handler)
```

**Command registration in `src/bot/commands.py`:**
Add `("history", "CommandHistory")` to the default commands list.

### Task 6.2: Update architecture test conventions

**Files:**
- Verify: `tests/test_architecture/test_conventions.py` — HistoryHandler will be auto-detected by the `test_all_handlers_have_get_handler` test since it checks all `*Handler` classes. No manual changes needed unless a new service singleton is added (none in this plan).

---

## Verification

After all tasks complete:

1. `python -m pytest --tb=short -q` — all tests pass
2. `python -m flake8 .` — no lint errors
3. `PYTHONIOENCODING=utf-8 python run.py --validate-i18n` — all translation keys present
4. `python -m pytest --cov=src.api.radarr --cov=src.api.sonarr --cov=src.services.media --cov=src.bot.handlers.history --cov=src.bot.keyboards --cov-report=term-missing` — 100% coverage on new code

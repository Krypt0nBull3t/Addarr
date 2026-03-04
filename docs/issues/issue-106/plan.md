# Download Queue Command (`/queue`) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a `/queue` command that shows the current download queue from Radarr, Sonarr, and Lidarr, grouped by service with status and progress info.

**Architecture:** Follows the exact pattern established by `/missing` (issue #105). API clients get `get_queue()` methods, MediaService aggregates via a shared fetcher, QueueHandler uses callback-driven pagination with filter tabs. No ConversationHandler states needed.

**Tech Stack:** python-telegram-bot v20+, aiohttp, asyncio.gather for concurrent API calls.

---

## Context

**Issue:** #106 — Download queue across services (`/queue`)
**Branch:** `feature/106-download-queue-command`
**Reference implementation:** `/missing` command (issue #105) — same layered pattern throughout.

### Key Differences from `/missing`

| Aspect | `/missing` | `/queue` |
|--------|-----------|----------|
| Services | Radarr + Sonarr | Radarr + Sonarr + Lidarr |
| API endpoint | `wanted/missing` | `queue` |
| Lidarr API version | N/A | v1 (not v3) |
| Extra data fields | None | `status`, `trackedDownloadStatus`, `trackedDownloadState`, `protocol`, `sizeleft`, `size`, `timeleft` |
| Filter tabs | All / Movies / Series / Cutoff | All / Movies / Series / Music |
| Item display | Title only | Title + status line (status, progress %, time remaining) |
| Search action | Per-item "Search Now" button | None (items are already downloading) |

### API Response Shapes

**Radarr** `GET /api/v3/queue?sortKey=title&sortDirection=ascending&pageSize=1000`:
```json
{
  "page": 1, "pageSize": 1000, "totalRecords": 2,
  "records": [
    {
      "id": 1, "movieId": 10, "title": "Fight Club",
      "status": "downloading", "trackedDownloadStatus": "ok",
      "trackedDownloadState": "downloading",
      "protocol": "usenet", "size": 1500000000, "sizeleft": 750000000,
      "timeleft": "00:15:00", "downloadClient": "SABnzbd",
      "movie": {"id": 10, "title": "Fight Club", "year": 1999, "tmdbId": 550}
    }
  ]
}
```

**Sonarr** `GET /api/v3/queue?sortKey=series.title&sortDirection=ascending&pageSize=1000`:
```json
{
  "page": 1, "pageSize": 1000, "totalRecords": 1,
  "records": [
    {
      "id": 101, "seriesId": 42, "episodeId": 201, "title": "Pilot",
      "status": "downloading", "trackedDownloadStatus": "ok",
      "trackedDownloadState": "downloading",
      "protocol": "torrent", "size": 500000000, "sizeleft": 100000000,
      "timeleft": "00:05:00", "downloadClient": "Transmission",
      "series": {"id": 42, "title": "Breaking Bad", "year": 2008, "tvdbId": 81189},
      "episode": {"id": 201, "seasonNumber": 1, "episodeNumber": 5, "title": "Pilot"}
    }
  ]
}
```

**Lidarr** `GET /api/v1/queue?sortKey=title&sortDirection=ascending&pageSize=1000`:
```json
{
  "page": 1, "pageSize": 1000, "totalRecords": 1,
  "records": [
    {
      "id": 301, "artistId": 5, "albumId": 20, "title": "OK Computer",
      "status": "downloading", "trackedDownloadStatus": "ok",
      "trackedDownloadState": "downloading",
      "protocol": "usenet", "size": 300000000, "sizeleft": 0,
      "timeleft": "00:00:00", "downloadClient": "SABnzbd"
    }
  ]
}
```

---

## Phase 1: API Client Extensions

### Task 1.1: Add `RadarrClient.get_queue()`

**Files:**
- Modify: `src/api/radarr.py` (after `get_missing()` at line 214)
- Modify: `tests/fixtures/sample_data.py` (add `RADARR_QUEUE` fixture)
- Modify: `tests/test_api/test_radarr.py` (add `TestRadarrGetQueue` class)

**Implementation** — identical structure to `get_missing()`:

```python
async def get_queue(self) -> List[Dict]:
    """Get the current download queue from Radarr."""
    try:
        logger.info(Fore.BLUE + "📥 Getting download queue from Radarr")
        result = await self._request(
            "queue?sortKey=title&sortDirection=ascending&pageSize=1000"
        )

        if not result or not isinstance(result, dict):
            logger.warning(Fore.YELLOW + "⚠️ No queue items found in Radarr")
            return []

        records = result.get("records", [])
        logger.info(Fore.GREEN + f"✅ Found {len(records)} queue items in Radarr")
        return records

    except Exception as e:
        logger.error(Fore.RED + f"❌ Failed to get Radarr queue: {str(e)}")
        return []
```

**Sample data** — add to `tests/fixtures/sample_data.py`:

```python
RADARR_QUEUE = {
    "page": 1,
    "pageSize": 1000,
    "totalRecords": 2,
    "records": [
        {
            "id": 1, "movieId": 10, "title": "Fight Club",
            "status": "downloading", "trackedDownloadStatus": "ok",
            "trackedDownloadState": "downloading",
            "protocol": "usenet", "size": 1500000000, "sizeleft": 750000000,
            "timeleft": "00:15:00", "downloadClient": "SABnzbd",
            "movie": {"id": 10, "title": "Fight Club", "year": 1999, "tmdbId": 550},
        },
        {
            "id": 2, "movieId": 11, "title": "Inception",
            "status": "completed", "trackedDownloadStatus": "ok",
            "trackedDownloadState": "importPending",
            "protocol": "torrent", "size": 2000000000, "sizeleft": 0,
            "timeleft": "00:00:00", "downloadClient": "Transmission",
            "movie": {"id": 11, "title": "Inception", "year": 2010, "tmdbId": 27205},
        },
    ],
}
```

**Tests** — 4 tests mirroring `TestRadarrGetMissing`:
- `test_get_queue_success` — mock `GET queue?...`, assert returns 2 records
- `test_get_queue_empty` — empty records, assert `[]`
- `test_get_queue_connection_error` — `aiohttp.ClientError`, retries, returns `[]`
- `test_get_queue_exception` — generic exception, returns `[]`

**Import update** in test file — add `RADARR_QUEUE` to imports from `sample_data`.

### Task 1.2: Add `SonarrClient.get_queue()`

**Files:**
- Modify: `src/api/sonarr.py` (after `get_missing()` at line 220)
- Modify: `tests/fixtures/sample_data.py` (add `SONARR_QUEUE` fixture)
- Modify: `tests/test_api/test_sonarr.py` (add `TestSonarrGetQueue` class)

**Implementation** — same pattern, different sort key:

```python
async def get_queue(self) -> List[Dict]:
    """Get the current download queue from Sonarr."""
    try:
        logger.info(Fore.BLUE + "📥 Getting download queue from Sonarr")
        result = await self._request(
            "queue?sortKey=series.title&sortDirection=ascending&pageSize=1000"
        )

        if not result or not isinstance(result, dict):
            logger.warning(Fore.YELLOW + "⚠️ No queue items found in Sonarr")
            return []

        records = result.get("records", [])
        logger.info(Fore.GREEN + f"✅ Found {len(records)} queue items in Sonarr")
        return records

    except Exception as e:
        logger.error(Fore.RED + f"❌ Failed to get Sonarr queue: {str(e)}")
        return []
```

**Sample data:**

```python
SONARR_QUEUE = {
    "page": 1,
    "pageSize": 1000,
    "totalRecords": 2,
    "records": [
        {
            "id": 101, "seriesId": 42, "episodeId": 201, "title": "Pilot",
            "status": "downloading", "trackedDownloadStatus": "ok",
            "trackedDownloadState": "downloading",
            "protocol": "torrent", "size": 500000000, "sizeleft": 100000000,
            "timeleft": "00:05:00", "downloadClient": "Transmission",
            "series": {"id": 42, "title": "Breaking Bad", "year": 2008, "tvdbId": 81189},
            "episode": {"id": 201, "seasonNumber": 1, "episodeNumber": 5, "title": "Pilot"},
        },
        {
            "id": 102, "seriesId": 42, "episodeId": 202,
            "title": "Crazy Handful of Nothin'",
            "status": "downloading", "trackedDownloadStatus": "ok",
            "trackedDownloadState": "downloading",
            "protocol": "torrent", "size": 450000000, "sizeleft": 225000000,
            "timeleft": "00:10:00", "downloadClient": "Transmission",
            "series": {"id": 42, "title": "Breaking Bad", "year": 2008, "tvdbId": 81189},
            "episode": {"id": 202, "seasonNumber": 1, "episodeNumber": 6,
                        "title": "Crazy Handful of Nothin'"},
        },
    ],
}
```

**Tests** — 4 tests mirroring `TestSonarrGetMissing`.

### Task 1.3: Add `LidarrClient.get_queue()`

**Files:**
- Modify: `src/api/lidarr.py` (after `get_artists()` at line 319, or at end of class)
- Modify: `tests/fixtures/sample_data.py` (add `LIDARR_QUEUE` fixture)
- Modify: `tests/test_api/test_lidarr.py` (add `TestLidarrGetQueue` class)

**Important:** Lidarr uses `API_VERSION = "v1"`, and `BaseApiClient._request()` already uses `self.API_VERSION` for URL construction, so the endpoint path is just `"queue?..."` — same as Radarr/Sonarr.

**Implementation:**

```python
async def get_queue(self) -> List[Dict]:
    """Get the current download queue from Lidarr."""
    try:
        logger.info(Fore.BLUE + "📥 Getting download queue from Lidarr")
        result = await self._request(
            "queue?sortKey=title&sortDirection=ascending&pageSize=1000"
        )

        if not result or not isinstance(result, dict):
            logger.warning(Fore.YELLOW + "⚠️ No queue items found in Lidarr")
            return []

        records = result.get("records", [])
        logger.info(Fore.GREEN + f"✅ Found {len(records)} queue items in Lidarr")
        return records

    except Exception as e:
        logger.error(Fore.RED + f"❌ Failed to get Lidarr queue: {str(e)}")
        return []
```

**Sample data:**

```python
LIDARR_QUEUE = {
    "page": 1,
    "pageSize": 1000,
    "totalRecords": 1,
    "records": [
        {
            "id": 301, "artistId": 5, "albumId": 20, "title": "OK Computer",
            "status": "downloading", "trackedDownloadStatus": "ok",
            "trackedDownloadState": "downloading",
            "protocol": "usenet", "size": 300000000, "sizeleft": 150000000,
            "timeleft": "00:03:00", "downloadClient": "SABnzbd",
        },
    ],
}
```

**Tests** — 4 tests: success, empty, connection error, exception. Note: Lidarr base URL is `http://localhost:8686/api/v1` (check existing test for correct BASE constant).

---

## Phase 2: Service Layer

### Task 2.1: Add `MediaService.get_queue_media()` and normalizers

**Files:**
- Modify: `src/services/media.py` (add after `_normalize_sonarr_missing` at line 706)
- Modify: `tests/test_services/test_media_service.py` (add normalizer + aggregation tests)

**Implementation — normalizers:**

```python
@staticmethod
def _normalize_radarr_queue(item: Dict) -> Dict:
    """Normalize a Radarr queue item into the unified schema."""
    movie = item.get("movie", {})
    size = item.get("size", 0)
    sizeleft = item.get("sizeleft", 0)
    progress = round((1 - sizeleft / size) * 100) if size > 0 else 0
    return {
        "type": "movie",
        "title": movie.get("title", item.get("title", "")),
        "year": movie.get("year"),
        "series_title": None,
        "season": None,
        "episode": None,
        "status": item.get("trackedDownloadState", item.get("status", "")),
        "progress": progress,
        "timeleft": item.get("timeleft", ""),
        "protocol": item.get("protocol", ""),
        "download_client": item.get("downloadClient", ""),
        "media_id": str(movie.get("tmdbId", "")),
        "internal_id": item.get("id"),
        "service": "radarr",
    }

@staticmethod
def _normalize_sonarr_queue(item: Dict) -> Dict:
    """Normalize a Sonarr queue item into the unified schema."""
    series = item.get("series", {})
    ep = item.get("episode", {})
    size = item.get("size", 0)
    sizeleft = item.get("sizeleft", 0)
    progress = round((1 - sizeleft / size) * 100) if size > 0 else 0
    return {
        "type": "episode",
        "title": ep.get("title", item.get("title", "")),
        "year": series.get("year"),
        "series_title": series.get("title"),
        "season": ep.get("seasonNumber"),
        "episode": ep.get("episodeNumber"),
        "status": item.get("trackedDownloadState", item.get("status", "")),
        "progress": progress,
        "timeleft": item.get("timeleft", ""),
        "protocol": item.get("protocol", ""),
        "download_client": item.get("downloadClient", ""),
        "media_id": str(series.get("tvdbId", "")),
        "internal_id": item.get("id"),
        "service": "sonarr",
    }

@staticmethod
def _normalize_lidarr_queue(item: Dict) -> Dict:
    """Normalize a Lidarr queue item into the unified schema."""
    size = item.get("size", 0)
    sizeleft = item.get("sizeleft", 0)
    progress = round((1 - sizeleft / size) * 100) if size > 0 else 0
    return {
        "type": "album",
        "title": item.get("title", ""),
        "year": None,
        "series_title": None,
        "season": None,
        "episode": None,
        "status": item.get("trackedDownloadState", item.get("status", "")),
        "progress": progress,
        "timeleft": item.get("timeleft", ""),
        "protocol": item.get("protocol", ""),
        "download_client": item.get("downloadClient", ""),
        "media_id": "",
        "internal_id": item.get("id"),
        "service": "lidarr",
    }
```

**Implementation — aggregation method:**

```python
async def get_queue_media(self) -> List[Dict]:
    """Get download queue items from all enabled services.

    Returns a normalized, title-sorted list of queue items.
    """
    normalizers = {
        "radarr": self._normalize_radarr_queue,
        "sonarr": self._normalize_sonarr_queue,
        "lidarr": self._normalize_lidarr_queue,
    }
    tasks = []
    if self.radarr:
        tasks.append(("radarr", self.radarr.get_queue()))
    if self.sonarr:
        tasks.append(("sonarr", self.sonarr.get_queue()))
    if self.lidarr:
        tasks.append(("lidarr", self.lidarr.get_queue()))

    if not tasks:
        return []

    results = await asyncio.gather(
        *(t[1] for t in tasks), return_exceptions=True
    )

    items = []
    for (service_name, _), result in zip(tasks, results):
        if isinstance(result, Exception):
            logger.error(
                f"queue fetch failed for {service_name}: {result}"
            )
            continue
        normalize = normalizers[service_name]
        for record in result:
            items.append(normalize(record))

    items.sort(key=lambda x: (x.get("title") or "").lower())
    return items
```

**Tests — normalizers** (6 tests):
- `TestNormalizeRadarrQueue.test_standard_item` — full Radarr queue item normalizes
- `TestNormalizeRadarrQueue.test_missing_fields` — item with missing movie/size defaults safely
- `TestNormalizeSonarrQueue.test_standard_item` — full Sonarr queue item normalizes
- `TestNormalizeSonarrQueue.test_missing_fields` — missing episode/series defaults safely
- `TestNormalizeLidarrQueue.test_standard_item` — full Lidarr queue item normalizes
- `TestNormalizeLidarrQueue.test_missing_fields` — missing size/title defaults safely

**Tests — aggregation** (5 tests mirroring `TestGetMissingMedia`):
- `test_all_services_merged_sorted` — 3 services enabled, returns combined sorted list
- `test_radarr_only` — only Radarr returns items
- `test_no_services_enabled` — all None, returns `[]`
- `test_one_service_errors` — one service throws, others still return
- `test_lidarr_included` — Lidarr items appear with type "album"

**Update `mock_media_service` fixture** — add to `tests/test_handlers/conftest.py`:
```python
service.get_queue_media = AsyncMock(return_value=[])
```

---

## Phase 3: Handler and Keyboards

### Task 3.1: Create `QueueHandler` and keyboard builders

**Files:**
- Create: `src/bot/handlers/queue.py` (new file)
- Modify: `src/bot/keyboards.py` (add `get_queue_items_keyboard`, `get_queue_empty_keyboard`, `_build_queue_filter_row`, update `_MEDIA_TYPE_EMOJI`)

**Handler implementation** — mirrors `src/bot/handlers/missing.py` exactly:

```python
"""
Filename: queue.py
Author: Addarr Contributors
Created Date: 2026-03-04
Description: Download queue handler module.
"""

from telegram import Update
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes

from src.utils.logger import get_logger, log_user_interaction
from src.bot.handlers.auth import require_auth
from src.bot.keyboards import (
    get_queue_items_keyboard,
    get_queue_empty_keyboard,
    get_main_menu_keyboard,
)
from src.services.media import MediaService
from src.services.translation import TranslationService

logger = get_logger("addarr.queue")


class QueueHandler:
    """Handler for download queue browsing."""

    def __init__(self):
        self.media_service = MediaService()
        self.translation = TranslationService()

    def get_handler(self):
        """Get queue command handlers."""
        return [
            CommandHandler("queue", self.show_queue),
            CallbackQueryHandler(
                self.handle_queue_action, pattern="^queue_"
            ),
        ]

    @require_auth
    async def show_queue(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Show download queue with inline keyboard."""
        if not update.effective_user:
            return

        log_user_interaction(logger, update.effective_user, "/queue")

        context.user_data.setdefault("queue_filter", "all")

        items = await self.media_service.get_queue_media()
        context.user_data["queue_items"] = items

        text, keyboard = self._build_response(items)

        if update.callback_query:
            await update.callback_query.message.edit_text(
                text, reply_markup=keyboard
            )
        else:
            await update.message.reply_text(text, reply_markup=keyboard)

    @require_auth
    async def handle_queue_action(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle queue callback button presses."""
        if not update.callback_query:
            return

        query = update.callback_query
        data = query.data

        log_user_interaction(logger, query.from_user, data)

        if data.startswith("queue_filter_"):
            await self._handle_filter(query, context)
        elif data.startswith("queue_page_"):
            await self._handle_page(query, context)
        elif data == "queue_refresh":
            await self._handle_refresh(query, context)
        elif data == "queue_back":
            await self._handle_back(query)
        else:
            await query.answer()

    async def _handle_filter(self, query, context):
        """Apply a filter tab and update the display."""
        filter_type = query.data.split("_")[-1]

        if filter_type in ("all", "movie", "episode", "album"):
            context.user_data["queue_filter"] = filter_type

        if filter_type == "all":
            items = await self.media_service.get_queue_media()
            context.user_data["queue_items"] = items

        items = context.user_data.get("queue_items", [])
        active_filter = context.user_data.get("queue_filter", "all")
        filtered = self._apply_filter(items, active_filter)

        text, keyboard = self._build_response(
            filtered, active_filter=active_filter
        )
        await query.message.edit_text(text, reply_markup=keyboard)
        await query.answer()

    async def _handle_page(self, query, context):
        """Show a different page of cached queue items."""
        page = int(query.data.split("_")[-1])
        items = context.user_data.get("queue_items", [])
        active_filter = context.user_data.get("queue_filter", "all")
        filtered = self._apply_filter(items, active_filter)

        text, keyboard = self._build_response(
            filtered, page, active_filter=active_filter
        )
        await query.message.edit_text(text, reply_markup=keyboard)
        await query.answer()

    async def _handle_refresh(self, query, context):
        """Re-fetch queue data."""
        items = await self.media_service.get_queue_media()
        context.user_data["queue_items"] = items

        active_filter = context.user_data.get("queue_filter", "all")
        filtered = self._apply_filter(items, active_filter)

        text, keyboard = self._build_response(
            filtered, active_filter=active_filter
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

    def _build_response(self, items, page=0, active_filter="all"):
        """Build queue text and keyboard from items."""
        if items:
            title = self.translation.get_text("QueueTitle")
            text = (
                f"\U0001f4e5 {title}\n\n"
                f"{len(items)} queue items"
            )
            keyboard = get_queue_items_keyboard(items, page, active_filter)
        else:
            text = (
                f"\U0001f4e5 {self.translation.get_text('QueueTitle')}"
                f"\n\n{self.translation.get_text('QueueEmpty')}"
            )
            keyboard = get_queue_empty_keyboard()
        return text, keyboard

    @staticmethod
    def _apply_filter(items, active_filter):
        """Filter items by type."""
        if active_filter in ("movie", "episode", "album"):
            return [i for i in items if i["type"] == active_filter]
        return items
```

**Keyboard builders** — add to `src/bot/keyboards.py`:

1. Update `_MEDIA_TYPE_EMOJI` to add `"album": "\U0001f3b5"`
2. Add `get_queue_empty_keyboard()` — identical pattern to `get_missing_empty_keyboard()` but with `queue_` callback prefix
3. Add `get_queue_items_keyboard()` — like `get_missing_items_keyboard()` but:
   - Uses `_build_queue_filter_row()` for filter tabs
   - Item buttons show status line (progress %, time remaining) instead of "Search Now" button
   - Callback prefix is `queue_` throughout
4. Add `_build_queue_filter_row()` — tabs: All / Movies / Series / Music

**Keyboard item display format:**
- Movie: `🎬 Fight Club (1999)`
- Episode: `📺 Breaking Bad - S01E05 Pilot`
- Album: `🎵 OK Computer`
- Status line per item: `50% • 15:00 remaining • usenet` (non-interactive `queue_noop` button)

**Tests** — create `tests/test_handlers/test_queue_handler.py` mirroring `test_missing_handler.py`:
- `test_show_queue_with_results` — items + keyboard
- `test_show_queue_empty_results` — empty state
- `test_show_queue_via_callback` — edit_text path
- `test_show_queue_no_user` — returns None
- `test_filter_movie` — sets filter, rebuilds
- `test_filter_episode` — sets filter to episode
- `test_filter_album` — sets filter to album
- `test_filter_all` — re-fetches data
- `test_page_change` — pagination
- `test_refresh` — re-fetches and updates
- `test_back_to_menu` — returns main menu keyboard
- `test_noop_callback` — unknown action answers query
- `test_handle_no_callback` — returns None
- `test_get_handler_returns_list` — structure check

**Handler fixture** — add to `tests/test_handlers/conftest.py`:

```python
@pytest.fixture
def queue_handler(mock_media_service, mock_translation_service):
    """Create a QueueHandler with patched services."""
    with (
        patch("src.bot.handlers.queue.MediaService") as mock_ms_class,
        patch("src.bot.handlers.queue.TranslationService") as mock_ts_class,
        patch(
            "src.bot.handlers.queue.get_queue_items_keyboard"
        ) as mock_items_kbd,
        patch(
            "src.bot.handlers.queue.get_queue_empty_keyboard"
        ) as mock_empty_kbd,
        patch("src.bot.handlers.queue.get_main_menu_keyboard") as mock_menu_kbd,
    ):
        mock_ts_class.return_value = mock_translation_service
        mock_ms_class.return_value = mock_media_service
        mock_media_service.get_queue_media = AsyncMock(return_value=[])
        mock_items_kbd.return_value = MagicMock()
        mock_empty_kbd.return_value = MagicMock()
        mock_menu_kbd.return_value = MagicMock()

        from src.bot.handlers.queue import QueueHandler
        from src.bot.handlers.auth import AuthHandler

        AuthHandler._authenticated_users = {12345}
        handler = QueueHandler()
        handler._mock_service = mock_media_service
        handler._mock_ts = mock_translation_service
        handler._mock_items_kbd = mock_items_kbd
        handler._mock_empty_kbd = mock_empty_kbd
        handler._mock_menu_kbd = mock_menu_kbd
        yield handler
```

---

## Phase 4: Integration

### Task 4.1: Register handler, command, and translation keys

**Files:**
- Modify: `src/main.py` (add import + registration after MissingHandler)
- Modify: `src/bot/commands.py` (add `/queue` command)
- Modify: All 9 `translations/addarr.*.yml` files (add queue keys)

**main.py** — add import and registration:

```python
# Import (with other handler imports at top):
from src.bot.handlers.queue import QueueHandler

# Registration (after Missing handler block, around line 145):
# Queue handler
queue_handler = QueueHandler()
for handler in queue_handler.get_handler():
    self.application.add_handler(handler)
```

**commands.py** — add after the missing command block (line 59):

```python
if (config.get("radarr", {}).get("enable")
        or config.get("sonarr", {}).get("enable")
        or config.get("lidarr", {}).get("enable")):
    commands.append(BotCommand("queue", translation.get_text("CommandQueue")))
```

**Translation keys** — add to all 9 locale files after the Missing section:

```yaml
  # Queue / Download queue
  Queue: "📥 Queue"
  CommandQueue: "Browse download queue"
  QueueTitle: "📥 Download Queue"
  QueueEmpty: "No items in download queue."
```

Use English as placeholder in non-English files (translators update later).

**Translation file list** (all 9):
- `translations/addarr.en-us.yml`
- `translations/addarr.de-de.yml`
- `translations/addarr.es-es.yml`
- `translations/addarr.fr-fr.yml`
- `translations/addarr.it-it.yml`
- `translations/addarr.nl-nl.yml`
- `translations/addarr.pl-pl.yml`
- `translations/addarr.pt-pt.yml`
- `translations/addarr.tr-tr.yml`

**Existing test updates:**
- `tests/test_bot/test_main.py` — If there's a handler count assertion, increment it by 1

---

## Verification Checklist

After all tasks complete:

1. `pytest --tb=short -q` — all tests pass
2. `python -m flake8 .` — no lint errors
3. `PYTHONIOENCODING=utf-8 python run.py --validate-i18n` — translation validation passes
4. `pytest --cov=src.api.radarr --cov=src.api.sonarr --cov=src.api.lidarr --cov=src.services.media --cov=src.bot.handlers.queue --cov=src.bot.keyboards --cov-report=term-missing` — 100% on new code

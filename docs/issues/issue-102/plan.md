# Transmission Torrent Management — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extend Transmission integration with torrent listing, per-torrent pause/resume, and a unified `/downloads` dashboard that supports both SABnzbd and Transmission.

**Architecture:** Add `get_torrents()`, `pause_torrent()`, `resume_torrent()`, `stop_all()`, `start_all()` to TransmissionClient using Transmission RPC (`torrent-get`, `torrent-stop`, `torrent-start`). Add corresponding service methods that return data in the same shape as SABnzbd. Extract `/downloads` from SabnzbdHandler into a new DownloadsHandler that delegates to whichever client(s) are enabled, with client tabs when both are active.

**Tech Stack:** Python 3.11, aiohttp, python-telegram-bot v20+, pytest, aioresponses

---

## Context

### Current State
- `TransmissionClient` only has `get_session()`, `set_alt_speed_enabled()`, `test_connection()`
- `TransmissionService` only has `get_status()`, `set_alt_speed()`, `test_connection()`, `is_enabled()`
- `TransmissionHandler` only shows turtle mode toggle via `/transmission`
- `/downloads` lives inside `SabnzbdHandler` and only works with SABnzbd
- Keyboards (`get_downloads_queue_keyboard`, `get_downloads_history_keyboard`) use SABnzbd-specific data

### Target State
- TransmissionClient can list/pause/resume individual torrents and pause/resume all
- TransmissionService exposes `get_queue_details()`, `pause_item()`, `resume_item()`, `pause_queue()`, `resume_queue()` matching SABnzbd's interface shape
- `/downloads` shows a unified dashboard with client tabs (SABnzbd / Transmission) when both are enabled
- `/transmission` keeps its turtle mode toggle (unchanged)
- Existing keyboards work for both clients (items already use generic format)

### Transmission RPC Methods Needed
- `torrent-get` with fields: `id`, `name`, `status`, `percentDone`, `rateDownload`, `eta`, `sizeWhenDone`, `totalSize`
- `torrent-stop` with `ids` argument (pause)
- `torrent-start` with `ids` argument (resume)

Transmission torrent status codes:
- 0 = Stopped, 1 = Check wait, 2 = Checking, 3 = Download wait, 4 = Downloading, 5 = Seed wait, 6 = Seeding

### Key Design Decisions

1. **Unified interface shape**: TransmissionService.get_queue_details() returns the same dict shape as SABnzbdService.get_queue_details() — `{paused, speed, size_remaining, items_count, items}` where each item has `{nzo_id, title, status, progress, size, timeleft}`. Using `nzo_id` as the generic item ID field even for Transmission (it's just a dict key).

2. **Client tabs in /downloads**: When both clients are enabled, add a row of client tabs (`🔽 SABnzbd` / `🔽 Transmission`) above the existing Queue/History tabs. `context.user_data["dl_client"]` tracks which client is active.

3. **Callback data namespacing**: Existing `dl_*` callbacks stay for SABnzbd. Add `dl_client_sab` / `dl_client_tx` for client switching. The handler routes pause/resume to the active client.

4. **DownloadsHandler**: New handler class that owns `/downloads` and all `dl_*` callbacks. SabnzbdHandler keeps `/sabnzbd` speed commands only. TransmissionHandler keeps `/transmission` turtle mode only.

5. **No history for Transmission**: Transmission RPC doesn't have a built-in history endpoint like SABnzbd. The History tab is only shown when SABnzbd is the active client (or hidden entirely in Transmission-only mode).

### Files to Create
- `src/bot/handlers/downloads.py` — new DownloadsHandler
- `tests/test_handlers/test_downloads_handler.py` — tests for DownloadsHandler

### Files to Modify
- `src/api/transmission.py` — add torrent RPC methods
- `src/services/transmission.py` — add queue management methods
- `src/bot/handlers/sabnzbd.py` — remove `/downloads` (keep `/sabnzbd` speed only)
- `src/bot/keyboards.py` — add client tab row, make queue keyboard client-aware
- `src/bot/commands.py` — register `/downloads` when either client is enabled
- `src/main.py` — register DownloadsHandler
- `translations/addarr.en-us.yml` (and other locales) — update translation keys
- `tests/test_api/test_transmission_api.py` — add tests for new client methods
- `tests/test_services/test_transmission_service.py` — add tests for new service methods
- `tests/test_handlers/test_sabnzbd_handler.py` — update after /downloads removal

---

## Phase 1: API Client & Service Layer

### Task 1.1: Add torrent listing to TransmissionClient

**Files:**
- Modify: `src/api/transmission.py`
- Test: `tests/test_api/test_transmission_api.py`

Add `get_torrents()` method that calls `torrent-get` RPC with relevant fields and returns the raw response.

**Behaviors:**
1. `get_torrents()` sends `torrent-get` with field list and returns parsed response
2. `get_torrents()` propagates connection errors (consistent with existing methods)

### Task 1.2: Add torrent pause/resume to TransmissionClient

**Files:**
- Modify: `src/api/transmission.py`
- Test: `tests/test_api/test_transmission_api.py`

Add `pause_torrent(torrent_id)`, `resume_torrent(torrent_id)`, `stop_all()`, `start_all()`.

**Behaviors:**
1. `pause_torrent(id)` calls `torrent-stop` with `ids: [id]`
2. `resume_torrent(id)` calls `torrent-start` with `ids: [id]`
3. `stop_all()` calls `torrent-stop` with no ids (stops all)
4. `start_all()` calls `torrent-start` with no ids (starts all)

### Task 1.3: Add queue management to TransmissionService

**Files:**
- Modify: `src/services/transmission.py`
- Test: `tests/test_services/test_transmission_service.py`

Add methods matching SABnzbd's interface: `get_queue_details()`, `pause_item(id)`, `resume_item(id)`, `pause_queue()`, `resume_queue()`.

**Key implementation detail for `get_queue_details()`:**
- Call `client.get_torrents()` and `client.get_session()` (for download speed)
- Map Transmission status codes to display strings: 0→"Stopped", 3→"Queued", 4→"Downloading", 6→"Seeding"
- Convert `percentDone` (0.0–1.0) to integer percentage (0–100)
- Format `rateDownload` bytes/sec to human-readable speed
- Format `eta` seconds to time string
- Use torrent `id` as the `nzo_id` field (for callback data compatibility)
- Return `{paused: bool, speed: str, size_remaining: str, items_count: int, items: list}`

**Behaviors:**
1. `get_queue_details()` returns correctly shaped dict with torrent data
2. `get_queue_details()` returns empty dict on error (same shape as SABnzbd)
3. `pause_item(id)` delegates to `client.pause_torrent(id)` and returns bool
4. `resume_item(id)` delegates to `client.resume_torrent(id)` and returns bool
5. `pause_queue()` delegates to `client.stop_all()` and returns bool
6. `resume_queue()` delegates to `client.start_all()` and returns bool
7. All methods return False when client is None

---

## Phase 2: Keyboard & Translation Updates

### Task 2.1: Add client tab support to keyboards

**Files:**
- Modify: `src/bot/keyboards.py`
- Test: `tests/test_keyboards/test_keyboards.py` (if exists, otherwise inline in handler tests)

Add a `client` parameter to `get_downloads_queue_keyboard()` and `get_downloads_history_keyboard()`. When `client` is provided and not None, add a client tab row showing which client is active. Add `show_history_tab` parameter to hide History tab for Transmission.

**Behaviors:**
1. When `client=None` (single client mode): keyboards unchanged from current behavior
2. When `client="sabnzbd"`: add client tab row with checkmark on SABnzbd
3. When `client="transmission"`: add client tab row with checkmark on Transmission, hide History tab
4. Client tab callbacks: `dl_client_sab`, `dl_client_tx`

### Task 2.2: Add translation keys

**Files:**
- Modify: `translations/addarr.en-us.yml` (and template)

Update existing SABnzbd-specific keys to be generic:
- `DownloadsTitle` → "Downloads" (was "SABnzbd Downloads")
- `DownloadsHistoryTitle` → "Download History" (was "SABnzbd History")
- `CommandDownloads` → "Download queue" (was "SABnzbd download queue")
- `DownloadsNotEnabled` → "No download clients are enabled." (was SABnzbd-specific)

Add new keys:
- `DownloadsClientSabnzbd`: "SABnzbd"
- `DownloadsClientTransmission`: "Transmission"

---

## Phase 3: Downloads Handler

### Task 3.1: Create DownloadsHandler

**Files:**
- Create: `src/bot/handlers/downloads.py`
- Test: `tests/test_handlers/test_downloads_handler.py`

New handler that owns `/downloads` command and all `dl_*` callbacks. Delegates to SABnzbdService or TransmissionService based on `context.user_data["dl_client"]`.

**Constructor:** Takes both services. Determines which clients are available at init time.

**Key methods:**
- `handle_downloads()` — `/downloads` command entry point
- `handle_client_switch()` — `dl_client_sab` / `dl_client_tx` callbacks
- `handle_downloads_tab()` — `dl_tab_queue` / `dl_tab_history`
- `handle_downloads_page()` — `dl_page_N`
- `handle_downloads_pause_item()` — `dl_pause_<id>`
- `handle_downloads_resume_item()` — `dl_resume_<id>`
- `handle_downloads_pauseall()` — `dl_pauseall`
- `handle_downloads_resumeall()` — `dl_resumeall`
- `handle_downloads_refresh()` — `dl_refresh`
- `handle_downloads_noop()` — `dl_noop`
- `_get_active_service()` — returns the service for current dl_client
- `_refresh_current_view()` — shared refresh logic
- `_format_queue_text()` / `_format_history_text()` — text formatters

**Behaviors:**
1. When only SABnzbd enabled: works identically to current SabnzbdHandler /downloads
2. When only Transmission enabled: shows Transmission queue, no history tab
3. When both enabled: defaults to first available, shows client tabs
4. When neither enabled: shows DownloadsNotEnabled message
5. Client switch resets page to 0 and refreshes
6. All pause/resume/refresh delegate to active client's service
7. History tab only available when active client is SABnzbd

### Task 3.2: Remove /downloads from SabnzbdHandler

**Files:**
- Modify: `src/bot/handlers/sabnzbd.py`
- Modify: `tests/test_handlers/test_sabnzbd_handler.py`

Remove all `/downloads` related methods and callbacks from SabnzbdHandler. Keep only `/sabnzbd` speed command and its callback. Update tests accordingly.

### Task 3.3: Wire up DownloadsHandler in main.py and commands.py

**Files:**
- Modify: `src/main.py`
- Modify: `src/bot/commands.py`

Register DownloadsHandler when either Transmission or SABnzbd is enabled. Update `build_authenticated_commands()` to register `/downloads` when either client is enabled.

**Behaviors:**
1. DownloadsHandler registered when transmission OR sabnzbd is enabled
2. `/downloads` command appears in bot menu when either client is enabled
3. Registration order: after individual client handlers, before Help

---

## Phase 4: Integration & Cleanup

### Task 4.1: Update all translation files

**Files:**
- Modify: All `translations/addarr.*.yml` files

Add new keys (`DownloadsClientSabnzbd`, `DownloadsClientTransmission`) and update existing keys to be client-generic in all 9 language files.

### Task 4.2: Final integration testing

Run full test suite, lint, and i18n validation. Fix any issues.

---

## Verification

1. `pytest --tb=short -q` — all tests pass
2. `python -m flake8 .` — no lint errors
3. `PYTHONIOENCODING=utf-8 python run.py --validate-i18n` — translations valid
4. Coverage: 100% on new/modified source files

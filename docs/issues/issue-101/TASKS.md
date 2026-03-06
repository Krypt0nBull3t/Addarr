# Issue #101: SABnzbd Queue Dashboard — Tasks

## Summary

Add a `/downloads` command that displays a SABnzbd queue dashboard with active downloads, history, per-item pause/resume, pagination, and refresh.

---

### Phase 1: API + Service Layer (2 tasks)

**Goal:** Add per-item pause/resume to API client and service, plus a detailed queue method for dashboard display.

- [x] **1.1** Add per-item pause/resume to API client
    - **Context:**
        - **Why:** SABnzbd supports pausing/resuming individual queue items, but `SabnzbdClient` only has whole-queue `pause_queue()`/`resume_queue()`. Per-item control is needed for the dashboard's inline buttons.
        - **Architecture:** Follow existing method pattern in `SabnzbdClient` — each method builds a URL with query params, makes an async GET via `aiohttp.ClientSession`, returns `bool` on success. SABnzbd API uses `mode=queue&name=pause&value=<nzo_id>` and `mode=queue&name=resume&value=<nzo_id>`.
        - **Key refs:** `src/api/sabnzbd.py:98-118` (`pause_queue`/`resume_queue` as template), `tests/test_api/test_sabnzbd_api.py` (existing test patterns with `aio_mock` fixture and URL-based matching)
        - **Watch out:** URL construction uses f-strings with `self.api_url` and `self.api_key` appended as query params (not `aiohttp.params` dict). Follow the same pattern for consistency.
    - **Scope:** Two new methods on `SabnzbdClient`: `pause_item(nzo_id)` and `resume_item(nzo_id)`
    - **Touches:** `src/api/sabnzbd.py`, `tests/test_api/test_sabnzbd_api.py`
    - **Action items:**
        - [RED] Write tests for `pause_item()` — success (HTTP 200), HTTP error (500), connection error
        - [RED] Write tests for `resume_item()` — success, HTTP error, connection error
        - [GREEN] Implement `pause_item(nzo_id: str) -> bool` and `resume_item(nzo_id: str) -> bool`
    - **Success:** `python -m pytest tests/test_api/test_sabnzbd_api.py -v` all pass
    - **Completed:** 2026-03-06
    - **Learnings:** API client follows f-string URL pattern (not params dict). Methods are straightforward — SABnzbd uses `mode=queue&name=pause&value=<nzo_id>` for per-item control.
    - **Key Changes:** Added `pause_item(nzo_id)` and `resume_item(nzo_id)` to `src/api/sabnzbd.py`, 6 new tests in `tests/test_api/test_sabnzbd_api.py`
    - **Notes:** None

- [x] **1.2** Add per-item control and queue details to service layer
    - **Context:**
        - **Why:** `SABnzbdService` needs per-item methods to delegate to the API client, and a `get_queue_details()` method that returns normalized queue data with all fields the handler needs for display (title, progress, ETA, nzo_id, status per slot).
        - **Architecture:** Singleton service pattern — service makes its own `aiohttp` calls to `self.base_url/api` with `params` dict. `get_queue_details()` should parse the raw queue response into a normalized dict: `{'paused': bool, 'speed': str, 'size_remaining': str, 'items_count': int, 'items': [{'nzo_id': str, 'title': str, 'status': str, 'progress': int, 'size': str, 'timeleft': str}]}`.
        - **Key refs:** `src/services/sabnzbd.py:63-100` (`get_status` as template), `src/services/sabnzbd.py:154-196` (`pause_queue`/`resume_queue` as template for per-item), `tests/test_services/test_sabnzbd_service.py` (uses `aioresponses` context manager and `SABNZBD_API_PATTERN` regex for URL matching)
        - **Watch out:** The service uses `params` dicts (not f-string URLs) for `aiohttp` calls, unlike the API client. Per-item pause uses `mode=queue&name=pause&value=<nzo_id>`. Queue slot fields from SABnzbd: `nzo_id`, `filename`, `status`, `percentage`, `size`, `timeleft`.
    - **Scope:** Three new methods: `pause_item(nzo_id)`, `resume_item(nzo_id)`, `get_queue_details()`
    - **Touches:** `src/services/sabnzbd.py`, `tests/test_services/test_sabnzbd_service.py`
    - **Action items:**
        - [RED] Write tests for `pause_item()` — success, HTTP error, connection error
        - [RED] Write tests for `resume_item()` — success, HTTP error, connection error
        - [RED] Write tests for `get_queue_details()` — success with items (verify normalized structure), empty queue, HTTP error, connection error
        - [GREEN] Implement all three methods
    - **Success:** `python -m pytest tests/test_services/test_sabnzbd_service.py -v` all pass
    - **Completed:** 2026-03-06
    - **Learnings:** Service uses params dict pattern (not f-string URLs). `SABNZBD_QUEUE` fixture in test file has `noofslots: 3` with 1 slot — must create separate empty queue fixture for empty-state tests. `percentage` comes as string from SABnzbd API, needs int conversion.
    - **Key Changes:** Added `pause_item()`, `resume_item()`, `get_queue_details()` to `src/services/sabnzbd.py`. 10 new tests in `tests/test_services/test_sabnzbd_service.py`.
    - **Notes:** `get_queue_details()` returns normalized dict ready for handler consumption.

---

### Phase 2: Keyboards + Translations (1 task)

**Goal:** Add keyboard builders for the downloads dashboard and all required translation keys.

- [x] **2.1** Add downloads dashboard keyboards and translation keys
    - **Context:**
        - **Why:** The handler needs keyboard functions for the queue view (with per-item pause/resume buttons, pagination, tab switching) and history view (pagination, tab switching, refresh). Translation keys needed for all user-facing strings.
        - **Architecture:** Follow existing keyboard patterns in `src/bot/keyboards.py`. Each function returns `InlineKeyboardMarkup`. Pagination follows the `get_queue_items_keyboard` pattern (ceil division, nav_row with Prev/Next). Callback data convention: `dl_` prefix for all downloads dashboard buttons.
        - **Key refs:** `src/bot/keyboards.py:727-822` (`get_queue_items_keyboard` — closest pagination pattern), `src/bot/keyboards.py:712-724` (`get_queue_empty_keyboard` — empty state pattern), `translations/addarr.en-us.yml` for existing key format
        - **Watch out:** Callback data has a 64-byte limit in Telegram. `dl_pause_{nzo_id}` must fit — SABnzbd nzo_ids are typically ~20 chars (e.g., `SABnzbd_nzo_abc123`), so total is ~30 bytes, well within limits. Translation keys must be flat top-level (not nested) per `TranslationService.get_text()` limitation.
    - **Scope:** New keyboard functions + translation keys
    - **Touches:** `src/bot/keyboards.py`, `translations/addarr.en-us.yml`, `tests/test_bot/test_keyboards.py` (or new test file)
    - **Action items:**
        - [RED] Write tests for `get_downloads_queue_keyboard(items, page, paused)` — items with pagination, empty queue, per-item pause/resume buttons based on item status, paused queue shows "Resume All" instead of "Pause All"
        - [RED] Write tests for `get_downloads_history_keyboard(items, page)` — items with pagination, empty history
        - [GREEN] Implement both keyboard functions
        - [GREEN] Add translation keys to `translations/addarr.en-us.yml`: `CommandDownloads`, `DownloadsTitle`, `DownloadsEmpty`, `DownloadsHistoryTitle`, `DownloadsHistoryEmpty`, `DownloadsSpeed`, `DownloadsRemaining`, `DownloadsItems`, `DownloadsPaused`, `DownloadsItemPaused`, `DownloadsItemResumed`, `DownloadsPauseError`, `DownloadsResumeError`, `DownloadsNotEnabled`
    - **Success:** Keyboard tests pass, translation keys present in en-us file
    - **Completed:** 2026-03-06
    - **Learnings:** Template file has duplicated command sections — need to add keys to both. Other locales will show warnings for missing new keys, which is expected.
    - **Key Changes:** Added `get_downloads_queue_keyboard()` and `get_downloads_history_keyboard()` to `src/bot/keyboards.py`. 14 new tests. 16 new translation keys in en-us and template files.
    - **Notes:** Translation warnings for other locales are expected — keys need to be added when translators update.

---

### Phase 3: Handler + Command Registration (1 task)

**Goal:** Wire everything together — `/downloads` command, callback handlers for all interactions, command registration.

- [ ] **3.1** Implement downloads handler and register command
    - **Context:**
        - **Why:** This is the user-facing integration: `/downloads` sends the dashboard message, callbacks handle tab switching, pagination, per-item pause/resume, pause/resume all, and refresh.
        - **Architecture:** Extend `SabnzbdHandler` in `src/bot/handlers/sabnzbd.py`. Add `handle_downloads` command method (with `@require_auth`), and callback methods for each action. Register callbacks with `pattern=r"^dl_"` prefix. Store current view state (tab, page) in `context.user_data`. Register `/downloads` command in `src/bot/commands.py` under the `sabnzbd.enable` conditional.
        - **Key refs:** `src/bot/handlers/sabnzbd.py:25-34` (`get_handler` — extend with new handlers), `src/bot/handlers/sabnzbd.py:36-73` (`handle_sabnzbd` — command method pattern), `src/bot/handlers/transmission.py` (similar simple handler pattern), `src/bot/commands.py:69-70` (existing sabnzbd command registration)
        - **Watch out:** Handler pattern regex `^dl_` must not collide with existing `dl_` callbacks from settings handler (`dl_sabnzbd`, `dl_sab_toggle`, etc.). Use more specific patterns: `^dl_tab_`, `^dl_page_`, `^dl_pause_`, `^dl_resume_`, `^dl_refresh$`, `^dl_pauseall$`, `^dl_resumeall$`. The `@require_auth` decorator checks `update.effective_user.id` against `AuthHandler._authenticated_users`. Existing test pattern: patch `SABnzbdService` and `TranslationService` at the import site.
    - **Scope:** New command handler, 6+ callback handlers, command registration, message formatting
    - **Touches:** `src/bot/handlers/sabnzbd.py`, `src/bot/commands.py`, `tests/test_handlers/test_sabnzbd_handler.py`
    - **Action items:**
        - [RED] Write tests for `handle_downloads` command — shows queue view when service enabled, shows error when disabled, no effective_user returns early
        - [RED] Write tests for tab switching callbacks — `dl_tab_queue` shows queue, `dl_tab_history` shows history
        - [RED] Write tests for pagination — `dl_page_0`, `dl_page_1` update the displayed page
        - [RED] Write tests for per-item pause/resume — `dl_pause_<nzo_id>` calls service, updates message; `dl_resume_<nzo_id>` likewise; error handling
        - [RED] Write tests for pause/resume all — `dl_pauseall` and `dl_resumeall` call service queue methods
        - [RED] Write tests for refresh — `dl_refresh` re-fetches and edits message
        - [RED] Write test for command registration — `build_authenticated_commands()` includes `downloads` when sabnzbd enabled
        - [GREEN] Implement `handle_downloads` command method with `@require_auth`
        - [GREEN] Implement callback handlers for each action
        - [GREEN] Implement message formatting (queue view and history view text builders)
        - [GREEN] Add `CommandHandler("downloads", self.handle_downloads)` and callback handlers to `get_handler()`
        - [GREEN] Register `/downloads` in `build_authenticated_commands()` under sabnzbd conditional
    - **Success:** `python -m pytest tests/test_handlers/test_sabnzbd_handler.py -v` all pass, `python -m pytest --tb=short -q` full suite green, `python -m flake8 .` clean

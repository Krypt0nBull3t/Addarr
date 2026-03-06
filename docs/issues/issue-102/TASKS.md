# Issue #102: Transmission Torrent Management

> Unified `/downloads` dashboard with Transmission torrent listing, per-torrent pause/resume, and client tabs when both SABnzbd and Transmission are enabled.

---

### Phase 1: API Client & Service Layer (3 tasks)

**Goal:** Expose Transmission RPC torrent operations through the existing layered architecture.

- [x] **1.1** Add torrent RPC methods to TransmissionClient
    - **Context:** See plan.md Phase 1. Key refs: `src/api/transmission.py:36` (`_make_request` pattern), `tests/test_api/test_transmission_api.py` (aioresponses pattern)
    - **Watch out:** Transmission `percentDone` is 0.0–1.0 float, not 0–100. Torrent status is an int enum (0=Stopped, 3=DlWait, 4=Downloading, 6=Seeding). `torrent-stop`/`torrent-start` with no `ids` arg affects ALL torrents.
    - **Scope:** `get_torrents()`, `pause_torrent(id)`, `resume_torrent(id)`, `stop_all()`, `start_all()`
    - **Touches:** `src/api/transmission.py`, `tests/test_api/test_transmission_api.py`
    - **Action items:**
        - [RED] Write tests for `get_torrents()` success, `get_torrents()` with fields in request payload
        - [RED] Write tests for `pause_torrent(id)` sends `torrent-stop` with `ids: [id]`
        - [RED] Write tests for `resume_torrent(id)` sends `torrent-start` with `ids: [id]`
        - [RED] Write tests for `stop_all()` sends `torrent-stop` with no ids, `start_all()` sends `torrent-start` with no ids
        - [GREEN] Implement all five methods in TransmissionClient
    - **Success:** `pytest tests/test_api/test_transmission_api.py -v` all pass
    - **Completed:** 2026-03-06
    - **Learnings:** `aioresponses` stores request keys as `("POST", yarl.URL(...))` not `("POST", str)` — need `yarl.URL` for request inspection
    - **Key Changes:** Added `get_torrents()`, `pause_torrent()`, `resume_torrent()`, `stop_all()`, `start_all()` to `src/api/transmission.py`; 6 new tests in `tests/test_api/test_transmission_api.py`
    - **Notes:** All methods delegate to `_make_request()` which handles session ID negotiation

- [x] **1.2** Add queue management methods to TransmissionService
    - **Context:** See plan.md Phase 1. Key refs: `src/services/transmission.py:77` (`get_status` pattern), `src/services/sabnzbd.py:246` (`get_queue_details` return shape to match)
    - **Watch out:** Must return same dict shape as SABnzbd: `{paused, speed, size_remaining, items_count, items}` with items having `{nzo_id, title, status, progress, size, timeleft}`. Use torrent `id` (int) as `nzo_id`. Format bytes to human-readable strings. `paused` = True when all torrents are stopped.
    - **Scope:** `get_queue_details()`, `pause_item(id)`, `resume_item(id)`, `pause_queue()`, `resume_queue()`
    - **Touches:** `src/services/transmission.py`, `tests/test_services/test_transmission_service.py`
    - **Action items:**
        - [RED] Write tests for `get_queue_details()` returns correct shape with mapped status/progress/speed
        - [RED] Write tests for `get_queue_details()` returns empty dict on error, returns empty when no torrents
        - [RED] Write tests for `pause_item(id)` / `resume_item(id)` delegate and return bool
        - [RED] Write tests for `pause_queue()` / `resume_queue()` delegate and return bool
        - [RED] Write tests for all methods returning False when client is None
        - [GREEN] Implement all methods with format helpers for speed/size/eta
    - **Success:** `pytest tests/test_services/test_transmission_service.py -v` all pass
    - **Completed:** 2026-03-06
    - **Learnings:** Format helpers (_format_speed, _format_size, _format_eta) as @staticmethod makes them easily testable without needing a full service instance
    - **Key Changes:** Added `get_queue_details()`, `pause_item()`, `resume_item()`, `pause_queue()`, `resume_queue()` + 3 format helpers to `src/services/transmission.py`; 30 new tests
    - **Notes:** Return shape matches SABnzbd exactly — `nzo_id` is torrent int ID, `progress` is 0-100 int

- [x] **1.3** Phase 1 integration check
    - **Scope:** Run full suite, lint, verify no regressions
    - **Action items:**
        - [GREEN] `pytest --tb=short -q`
        - [GREEN] `python -m flake8 .`
    - **Success:** All pass, no new lint errors
    - **Completed:** 2026-03-06
    - **Learnings:** No issues — clean integration
    - **Key Changes:** None (verification only)
    - **Notes:** 1728 tests passing, 0 lint errors

---

### Phase 2: Keyboard & Translation Updates (2 tasks)

**Goal:** Make existing download keyboards client-aware and add translation keys.

- [x] **2.1** Add client tab support to download keyboards
    - **Context:** See plan.md Phase 2. Key refs: `src/bot/keyboards.py:842` (`get_downloads_queue_keyboard`), `src/bot/keyboards.py:945` (`get_downloads_history_keyboard`)
    - **Watch out:** `client=None` means single-client mode (no client tabs) — must be backward compatible. Transmission has no history, so hide History tab when `show_history_tab=False`. Callback data: `dl_client_sab`, `dl_client_tx`.
    - **Scope:** Add `client` and `show_history_tab` params to both keyboard functions, add client tab row
    - **Touches:** `src/bot/keyboards.py`, keyboard tests if they exist
    - **Action items:**
        - [RED] Write tests for keyboard with `client=None` (unchanged behavior)
        - [RED] Write tests for keyboard with `client="sabnzbd"` (client tab row present, SABnzbd checked)
        - [RED] Write tests for keyboard with `client="transmission"` (client tab row, Transmission checked, no History tab)
        - [RED] Write tests for `show_history_tab=False` hides History tab in queue keyboard
        - [GREEN] Add parameters and client tab row logic to both keyboard functions
    - **Success:** All keyboard tests pass, existing behavior preserved
    - **Completed:** 2026-03-06
    - **Learnings:** Default params (client=None, show_history_tab=True) preserve backward compatibility perfectly — all 17 existing tests pass unchanged
    - **Key Changes:** Added `client` and `show_history_tab` params to `get_downloads_queue_keyboard()` and `client` param to `get_downloads_history_keyboard()` in `src/bot/keyboards.py`; 7 new tests
    - **Notes:** Client tab row uses `dl_client_sab`/`dl_client_tx` callback data, checkmark on active client

- [ ] **2.2** Add and update translation keys
    - **Context:** See plan.md Phase 2. Key refs: `translations/addarr.en-us.yml:224-237` (current Downloads keys)
    - **Watch out:** Update `DownloadsTitle` from "SABnzbd Downloads" to "Downloads", `CommandDownloads` from "SABnzbd download queue" to "Download queue", `DownloadsNotEnabled` to generic message. Must update `addarr.template.yml` too.
    - **Scope:** Update generic keys, add `DownloadsClientSabnzbd`, `DownloadsClientTransmission`
    - **Touches:** `translations/addarr.en-us.yml`, `translations/addarr.template.yml`, other locale files
    - **Action items:**
        - [GREEN] Update existing SABnzbd-specific text to generic
        - [GREEN] Add new client label keys
        - [GREEN] Run `PYTHONIOENCODING=utf-8 python run.py --validate-i18n`
    - **Success:** i18n validation passes

---

### Phase 3: Downloads Handler & Wiring (3 tasks)

**Goal:** New unified DownloadsHandler replaces SabnzbdHandler's /downloads, supports both clients.

- [ ] **3.1** Create DownloadsHandler
    - **Context:** See plan.md Phase 3. Key refs: `src/bot/handlers/sabnzbd.py:113-298` (current /downloads implementation to port), `src/bot/keyboards.py:842` (keyboard functions)
    - **Watch out:** Must handle 4 scenarios: SABnzbd-only, Transmission-only, both enabled, neither enabled. `dl_client` in `user_data` tracks active client. History tab only for SABnzbd. Default to first available client. Use `@require_auth` from `src/bot/handlers/auth.py`.
    - **Scope:** Full handler class with all `dl_*` callbacks, text formatters, service delegation
    - **Touches:** `src/bot/handlers/downloads.py` (new), `tests/test_handlers/test_downloads_handler.py` (new)
    - **Action items:**
        - [RED] Write tests for `/downloads` with SABnzbd-only (matches current behavior)
        - [RED] Write tests for `/downloads` with Transmission-only (no history tab)
        - [RED] Write tests for `/downloads` with both clients (client tabs shown, switching works)
        - [RED] Write tests for `/downloads` with neither enabled (error message)
        - [RED] Write tests for client switch callback (`dl_client_sab`, `dl_client_tx`)
        - [RED] Write tests for pause/resume item delegating to active client
        - [RED] Write tests for pause/resume all delegating to active client
        - [RED] Write tests for tab switch, pagination, refresh, noop
        - [GREEN] Implement DownloadsHandler class
    - **Success:** `pytest tests/test_handlers/test_downloads_handler.py -v` all pass

- [ ] **3.2** Remove /downloads from SabnzbdHandler, wire up DownloadsHandler
    - **Context:** See plan.md Phase 3. Key refs: `src/bot/handlers/sabnzbd.py:38-46` (handler list to trim), `src/main.py:153-157` (Transmission registration pattern), `src/bot/commands.py:69-71` (`/downloads` registration)
    - **Watch out:** Keep `/sabnzbd` speed command and its callback in SabnzbdHandler. Remove all `dl_*` callbacks and `/downloads` command. Update `get_handler()` return list. Update existing SabnzbdHandler tests that test /downloads. Register DownloadsHandler in main.py when EITHER client is enabled. Update `commands.py` to register `/downloads` when either client is enabled.
    - **Scope:** Trim SabnzbdHandler, register DownloadsHandler, update commands
    - **Touches:** `src/bot/handlers/sabnzbd.py`, `src/main.py`, `src/bot/commands.py`, `tests/test_handlers/test_sabnzbd_handler.py`
    - **Action items:**
        - [RED] Update SabnzbdHandler tests: remove /downloads tests, keep speed tests
        - [RED] Write test for DownloadsHandler registration in main.py (when either client enabled)
        - [RED] Write test for `/downloads` command in `build_authenticated_commands` when only transmission enabled
        - [GREEN] Remove /downloads methods from SabnzbdHandler
        - [GREEN] Add DownloadsHandler import and registration in main.py
        - [GREEN] Update commands.py to register `/downloads` when either client is enabled
    - **Success:** `pytest --tb=short -q` all pass, no regressions

- [ ] **3.3** Final integration, coverage, and cleanup
    - **Scope:** Full test suite, coverage check on all changed files, lint, i18n
    - **Action items:**
        - [GREEN] Run `pytest --cov=src.api.transmission --cov=src.services.transmission --cov=src.bot.handlers.downloads --cov=src.bot.handlers.sabnzbd --cov=src.bot.keyboards --cov=src.bot.commands --cov-report=term-missing`
        - [GREEN] Add tests for any uncovered lines
        - [GREEN] `python -m flake8 .`
        - [GREEN] `PYTHONIOENCODING=utf-8 python run.py --validate-i18n`
    - **Success:** 100% coverage on new/modified code, all checks pass

# Issue 207: Download client failures look like success: Tasks

Source: `plan.md` and `design.md` in this folder. Issue: #207 (F080 to F086).
Branch: `fix/207-download-failures-look-like-success`.

### Phase 1: Download client failures (9 tasks)

**Goal:** A down client, a wrong key or a stale button shows an error or acts on the right client.

**Phase Context:**

- Why NOT change `get_history`: the issue's Fix lines do not list it. Name it as a follow-up in the PR body.
- Why NOT `ssl` in the wizard: `config_example.yaml` has no Transmission `ssl` key (#225 aligns the config mock with the example).
- Why NOT replace `_build_dl_pagination_row`: that is #223. Only add and share `clamp_page`.
- Tasks 1.6, 1.7 and 1.8 edit the same handler method `_refresh_current_view`. Keep this order.

- [x] **1.1** F086: SABnzbd remaining size reads `sizeleft`
    - **Context:**
        - **Why:** `size_remaining` is read from `size` (the total), so a big download shows remaining equal to total.
        - **Architecture:** One-line fix in the service. No layer change.
        - **Key refs:** `src/services/sabnzbd.py:228` (`get_queue_details`), `tests/test_services/test_sabnzbd_service.py`.
        - **Watch out:** Existing tests may feed the remaining size through `size`. Fix only the tests this change breaks (the fixtures are #216).
    - **Scope:** One line, one test.
    - **Touches:** `src/services/sabnzbd.py`, `tests/test_services/test_sabnzbd_service.py`
    - **Action items:**
        - [RED] Write `test_get_queue_details_size_remaining_uses_sizeleft` (queue `size` "10 GB", `sizeleft` "2.5 GB", expect "2.5 GB").
        - [GREEN] Use `queue.get('sizeleft', '0 MB')`.
    - **Success:** Test fails before, passes after. flake8 and mypy clean.
    - **Completed:** 2026-11-05
    - **Learnings:** The shared `SABNZBD_QUEUE_DETAILED` fixture used `size` for the remaining size, so the old assertion passed for the wrong reason.
    - **Key Changes:** `src/services/sabnzbd.py` reads `sizeleft`. Added `test_get_queue_details_size_remaining_uses_sizeleft`. The fixture now has `size` 9.9 GB and `sizeleft` 1.2 GB.
    - **Notes:** The other SABnzbd fixtures that use `size` as remaining size are #216.

- [x] **1.2** F081 services: `get_queue_details` returns `None` on a failed fetch
    - **Context:**
        - **Why:** An error returns the `empty` dict, so `/downloads` shows "DownloadsEmpty".
        - **Architecture:** Service layer returns `Optional[Dict[str, Any]]`. `None` means the fetch failed. A real empty queue stays a dict with `items_count` 0.
        - **Key refs:** `src/services/sabnzbd.py:186-238`, `src/services/transmission.py:107-160`, `tests/test_services/test_sabnzbd_service.py`, `tests/test_services/test_transmission_service.py`.
        - **Watch out:** A wrong SABnzbd key gives HTTP 200 with `{"status": false, "error": "API Key Incorrect"}` and no `queue` key. Return `None` when `"queue"` is missing. Transmission returns `None` when `self.client` is `None`. Only the handler uses this method (task 1.7 handles `None`).
    - **Scope:** Both services. Remove the `empty` dicts.
    - **Touches:** `src/services/sabnzbd.py`, `src/services/transmission.py`, the two service test files.
    - **Action items:**
        - [RED] SABnzbd tests: `None` on HTTP 500, on a wrong-key reply, on a connection error. One test that a real empty queue still returns a dict.
        - [RED] Transmission tests: `None` when the client is missing, `None` on a request error.
        - [GREEN] Change both methods. Update existing tests that expect the `empty` dict on errors.
    - **Success:** Tests pass. mypy shows no new error outside `downloads.py`.
    - **Completed:** 2026-11-05
    - **Learnings:** A wrong SABnzbd key is HTTP 200 with no `queue` key, so a status check alone does not catch it. mypy shows no error in `downloads.py` (handler-layer errors are suppressed), so task 1.7 must handle `None` on its own.
    - **Key Changes:** `SABnzbdService.get_queue_details` and `TransmissionService.get_queue_details` return `Optional[Dict]` and `None` on failure. Removed the `empty` dicts. Updated the error-path tests and added `test_get_queue_details_none_on_wrong_api_key`.
    - **Notes:** Until task 1.7, `downloads.py` indexes the result and would crash on `None`. Do not ship tasks 1.2 and 1.7 apart.

- [x] **1.3** F083: the wizard SABnzbd check needs the key
    - **Context:**
        - **Why:** `mode=version` needs no key, so a wrong key passes the wizard check.
        - **Architecture:** Setup layer only. No `src.config.settings` import (ADR 0005).
        - **Key refs:** `src/setup/validators.py:44` (params) and `:71` (success check), `tests/test_setup/test_validators.py`.
        - **Watch out:** SABnzbd reads `apikey` from the query string, not from `X-Api-Key`. Pass it as a query parameter. Other services keep the `version` check.
    - **Scope:** `mode=queue`, `apikey` param, success when `queue` is in the reply.
    - **Touches:** `src/setup/validators.py`, `tests/test_setup/test_validators.py`
    - **Action items:**
        - [RED] `test_sabnzbd_check_sends_mode_queue` (mock `mode=queue`, reply `{"queue": {}}`, expect `True`).
        - [RED] `test_sabnzbd_wrong_key_fails` (200 with `{"status": false, "error": "API Key Incorrect"}`, expect `False`).
        - [GREEN] Implement. Update the existing SABnzbd tests that use `version`.
    - **Success:** Tests pass. flake8 and mypy clean.
    - **Completed:** 2026-11-05
    - **Learnings:** `mode=version` answers without a key, so a test that mocks one fixed reply cannot show the bug. The test uses an `aioresponses` callback that behaves like SABnzbd (`CallbackResult`, `url.query`). A wrong-key reply is only red against the old code through that callback.
    - **Key Changes:** `src/setup/validators.py` sends `mode=queue` with `apikey` as a query parameter and accepts a reply with the key `queue`. Added three SABnzbd tests in `tests/test_setup/test_validators.py`.
    - **Notes:** The printed URL does not include the query, so the key is not logged.

- [x] **1.4** F082: the wizard writes `host` and `port` for Transmission
    - **Context:**
        - **Why:** The wizard writes `server.addr` and `server.port`. `TransmissionClient` reads `host` and `port`, so a remote Transmission becomes localhost:9091.
        - **Architecture:** Setup layer only.
        - **Key refs:** `src/setup/service_config.py:129-200` (`get_valid_service_config`, four return sites), `src/api/transmission.py:21-22`, `tests/test_setup/test_service_config.py:112-165`.
        - **Watch out:** Both the success path and the "skip after a failed test" path must return the new shape. SABnzbd and arr shapes stay the same. Do not write `ssl`.
    - **Scope:** A private helper that builds the dict for the four return sites.
    - **Touches:** `src/setup/service_config.py`, `tests/test_setup/test_service_config.py`
    - **Action items:**
        - [RED] `test_transmission_config_has_host_and_port` (success) and `test_transmission_config_skip_has_host_and_port` (retry False). Assert `host`, `port` and no `server` key.
        - [GREEN] Implement the helper. Transmission returns `{"host": addr, "port": port}`.
    - **Success:** Tests pass. The SABnzbd and arr tests still pass unchanged.
    - **Completed:** 2026-11-05
    - **Learnings:** `test_transmission_no_apikey_prompt` asserted the old `auth` shape; it now asserts `host`. The wizard's `_configure_service` merges the result into the default config (`host`, `authentication`, `username`, `password`), so the other Transmission keys stay.
    - **Key Changes:** `get_valid_service_config` returns `{"host", "port"}` for Transmission in the success and the skip case (two early returns, no helper). Added two tests.
    - **Notes:** Plan said a helper for the four return sites. Two early returns are smaller. `ssl` is not written (config_example has no Transmission `ssl`).

- [x] **1.5** F080: handlers show an error when an action returns `False`
    - **Context:**
        - **Why:** `set_speed_limit`, `pause_queue` and `resume_queue` return `False` on failure. The handlers ignore it and show success.
        - **Architecture:** Handler layer. Use existing texts: `Sabnzbd.Error` in the SABnzbd handler, the existing "could not complete action" text in Settings. No new key.
        - **Key refs:** `src/bot/handlers/sabnzbd.py:86-101`, `src/bot/handlers/settings.py:611-649`, the two handler test files.
        - **Watch out:** In Settings, keep the keyboard and `return States.SETTINGS_DOWNLOADS` on the error path. Keep the existing `except` branches.
    - **Scope:** Four call sites.
    - **Touches:** `src/bot/handlers/sabnzbd.py`, `src/bot/handlers/settings.py`, `tests/test_handlers/test_sabnzbd_handler.py`, `tests/test_handlers/test_settings_handler.py`
    - **Action items:**
        - [RED] SABnzbd handler: speed selection with `set_speed_limit` returning `False` shows `Sabnzbd.Error`, not `Sabnzbd.ChangedTo25`.
        - [RED] Settings: speed, pause and resume each with the service returning `False` show the error text, not the success text.
        - [GREEN] Branch on the returned bool.
    - **Success:** Tests pass. flake8 and mypy clean.
    - **Completed:** 2026-11-05
    - **Learnings:** The Settings speed branch also showed success when the service was disabled. `is_enabled() and await set_speed_limit(...)` now shows the error in that case too.
    - **Key Changes:** `src/bot/handlers/sabnzbd.py` returns the `Sabnzbd.Error` text on `False`. `src/bot/handlers/settings.py` has a `SAB_ACTION_ERROR` constant used by the speed, pause, resume and `except` paths. Added 4 tests.
    - **Notes:** The Settings texts are still hardcoded English (not in scope).

- [x] **1.6** F085: shared `clamp_page` and a clamped Refresh
    - **Context:**
        - **Why:** Refresh keeps `dl_page` without clamping. After downloads finish, the page is empty and has no nav row.
        - **Architecture:** `clamp_page(page: int, total_pages: int) -> int` in `src/bot/keyboards.py`, so the logic exists once. `_build_pagination_row` (the #223 helper) uses it. `DL_PAGE_SIZE = 5` replaces the repeated `5`.
        - **Key refs:** `src/bot/keyboards.py:886` (`_build_pagination_row`), `:961` and `:1058` (the two downloads keyboards), `src/bot/handlers/downloads.py:299-323` (`_refresh_current_view`), `:348` (`_format_history_text`).
        - **Watch out:** Do not replace `_build_dl_pagination_row`. `clamp_page` with `total_pages` 0 returns 0. On the History tab, the text and the keyboard must use the same clamped page. Store the clamped page in `user_data["dl_page"]`.
    - **Scope:** Helper, two keyboards, one handler method.
    - **Touches:** `src/bot/keyboards.py`, `src/bot/handlers/downloads.py`, `tests/test_bot/test_keyboards.py`, `tests/test_handlers/test_downloads_handler.py`
    - **Action items:**
        - [RED] `test_clamp_page_bounds` (negative, in range, past the end, `total_pages` 0).
        - [RED] Both downloads keyboards with `page=9` and 6 items show the nav row `2/2`.
        - [RED] Handler: Refresh with `dl_page` 9 and 6 items shows the last page with its nav row and sets `dl_page` to 1. A History tab variant also checks the text.
        - [GREEN] Implement `clamp_page`, use it in the three places above.
    - **Success:** Tests fail before, pass after. Existing keyboard tests still pass.
    - **Completed:** 2026-11-05
    - **Learnings:** Before the fix a stale page showed `10/2` with no Prev button, which is the "no nav row" bug. `test_pagination_updates_page` set page 2 on a 2-item queue, the state the fix clamps, so it now uses 11 items.
    - **Key Changes:** `src/bot/keyboards.py`: `clamp_page`, `DL_PAGE_SIZE`; `_build_pagination_row` and both downloads keyboards clamp. `src/bot/handlers/downloads.py`: `_clamp_dl_page` is used in `_refresh_current_view` and stores the page in `user_data`. Added 6 tests.
    - **Notes:** `_build_dl_pagination_row` is unchanged (#223). Tasks 1.7 and 1.8 edit `_refresh_current_view` again.

- [ ] **1.7** F081 handler: show an error, not "empty"
    - **Context:**
        - **Why:** The handler formats a failed fetch as an empty queue. It must show an error.
        - **Architecture:** `get_downloads_error_keyboard(client: Optional[str] = None)` in `keyboards.py`: the client switcher row (reuse `_build_dl_client_tab_row`) when `client` is not `None`, then a Refresh button (`dl_refresh`). New key `DownloadsFetchError` through the `i18n-key` skill. Without a keyboard, a user with SABnzbd down could not reach Transmission.
        - **Key refs:** `src/bot/handlers/downloads.py:138-149` (`handle_downloads`) and `_refresh_current_view`, `translations/addarr.template.yml` (near `DownloadsPauseError`), `src/bot/keyboards.py:947`.
        - **Watch out:** `_do_action` calls `_refresh_current_view` after a success, so one change covers it. Existing handler tests mock the queue as a dict. Only a `None` queue takes the error path. History tab stays unchanged.
    - **Scope:** Two handler paths, one keyboard, one key in 10 files.
    - **Touches:** `src/bot/handlers/downloads.py`, `src/bot/keyboards.py`, `translations/addarr.template.yml` and the 9 locale files, `tests/test_handlers/test_downloads_handler.py`, `tests/test_bot/test_keyboards.py`
    - **Action items:**
        - [RED] `/downloads` with a `None` queue replies with `DownloadsFetchError`, not `DownloadsEmpty`, with a `dl_refresh` button. A multi-client variant also has `dl_client_tx`.
        - [RED] Refresh with a `None` queue edits the message to the error text.
        - [RED] Keyboard builder tests with and without `client`.
        - [GREEN] Implement. Add the key to the template and all 9 locale files.
    - **Success:** Tests pass. `PYTHONIOENCODING=utf-8 python run.py --validate-i18n` passes. mypy shows no new error.

- [ ] **1.8** F084: download action buttons carry their client
    - **Context:**
        - **Why:** The handler picks the service from `user_data["dl_client"]`. An old Transmission Pause button, tapped after switching to SABnzbd, sends the torrent id to SABnzbd.
        - **Architecture:** In multi-client mode the keyboard builds `dl_pause_<c>_<id>`, `dl_resume_<c>_<id>`, `dl_pauseall_<c>` and `dl_resumeall_<c>`, with `<c>` = `sab` or `tx`. Single-client mode keeps the old format. The handler accepts both and falls back to `user_data` for old buttons.
        - **Key refs:** `src/bot/keyboards.py:961-1055`, `src/bot/handlers/downloads.py:51-64` (patterns), `:83-101` (`_get_active_service`, `_parse_item_id`), `:224-297` (pause/resume handlers, `_do_action`).
        - **Watch out:** A SABnzbd id starts with `SABnzbd_nzo_`, so read only the first token after the prefix as the client. Page, tab and refresh buttons stay on `user_data`. After an action, set `user_data["dl_client"]` to the button's client before the refresh. `callback_data` must stay at most 64 bytes. The admin check in `_do_action` must use the button's client.
    - **Scope:** Keyboard data, handler patterns and parsing, `_do_action` signature (`client` argument).
    - **Touches:** `src/bot/keyboards.py`, `src/bot/handlers/downloads.py`, `tests/test_bot/test_keyboards.py`, `tests/test_handlers/test_downloads_handler.py`
    - **Action items:**
        - [RED] Keyboard: multi-client data `dl_pause_tx_7`, `dl_pauseall_tx`, `dl_pause_sab_SABnzbd_nzo_abc`. Single-client data unchanged. All data at most 64 bytes.
        - [RED] Handler: `dl_pause_tx_7` with `user_data` "sabnzbd" awaits Transmission `pause_item(7)` (int) and not SABnzbd. Same for `dl_pauseall_tx`. A legacy `dl_pause_7` follows `user_data`. A SABnzbd id with underscores works.
        - [GREEN] Implement.
    - **Success:** Tests fail before, pass after. Existing downloads tests still pass.

- [ ] **1.9** Integration check and preflight
    - **Context:**
        - **Why:** The change alters a user-facing flow (`/downloads`).
        - **Architecture:** `BotHarness` in `tests/integration/conftest.py`; `tests/integration/test_downloads_flow.py` exists.
        - **Key refs:** `tests/integration/test_downloads_flow.py`, `tests/integration/fixtures.py:131`.
        - **Watch out:** Run everything through the suite lock. The full coverage gate runs once, here.
    - **Scope:** One integration test for the error view, then the preflight.
    - **Touches:** `tests/integration/test_downloads_flow.py`
    - **Action items:**
        - [RED] Integration test: with the queue fetch failing, `/downloads` shows the error text and a Refresh button.
        - [GREEN] Fix any gap. Run the preflight (flake8, mypy, i18n, unit tests with the 100% gate, integration, architecture).
    - **Success:** The preflight passes. Every task above has its completion metadata.

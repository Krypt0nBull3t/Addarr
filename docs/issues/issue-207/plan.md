# Issue 207: Download client failures look like success: Implementation Plan

**Goal:** Fix F080 to F086 so a down client, a wrong key or a stale button shows an error or acts on the right client.

**Architecture:** Fix each defect at its source (service, validator, wizard, keyboard, handler). Services signal a failed queue fetch with `None`. Handlers turn a `False` or `None` into an error text. Download buttons carry their client in `callback_data`.

**Tech Stack:** Python 3.10+, python-telegram-bot, aiohttp, pytest with `aioresponses`.

**Spec:** `docs/issues/issue-207/design.md` (decisions confirmed there). Issue: #207.

## Global Constraints

- PR targets `development`. Branch `fix/207-download-failures-look-like-success`.
- `config["key"]` is banned in `src/`. Use `config.get()`.
- Use `Optional[...]` from `typing`, never `X | None`.
- `callback_data` is at most 64 bytes.
- Handlers must not import API clients. Services must not import handlers.
- Every test, gate and push runs through the suite lock (`<lock>` in the workflow skill). Interpreter: the worktree `.venv/bin/python`.
- Coverage gate 100% (`src/`).
- Translation key: add it to `translations/addarr.template.yml` and all 9 locale files (skill `i18n-key`). Run `PYTHONIOENCODING=utf-8 python run.py --validate-i18n`.
- Each test must fail before its fix and pass after.
- Not in scope: `get_history` error handling (name it as a follow-up in the PR body), Transmission `ssl` in the wizard, replacing `_build_dl_pagination_row` (#223), the SABnzbd test fixtures that use `size` as remaining size (#216): update only the tests this change breaks.

## Review Focus

- A SABnzbd reply of HTTP 200 with `{"status": false, "error": "API Key Incorrect"}` and no `queue` key: `get_queue_details` returns `None` (Task 2) and the wizard check fails (Task 3).
- Transmission `client` is `None` (bad config): `get_queue_details` returns `None` (Task 2).
- An old message with `dl_pause_<id>`, `dl_pauseall` (no client in the data): still works through the `user_data` fallback (Task 8).
- A SABnzbd id with underscores (`SABnzbd_nzo_abc`): the client split reads only the first token (Task 8).
- `dl_page` past the end on the History tab, and a queue that became empty: page 0, no crash (Task 6).

---

### Task 1: F086 SABnzbd remaining size

**Files:**
- Modify: `src/services/sabnzbd.py:228`
- Test: `tests/test_services/test_sabnzbd_service.py`

**Interfaces:**
- Produces: `get_queue_details()["size_remaining"]` equals the queue's `sizeleft`.

- [ ] **Step 1: Write the failing test** `test_get_queue_details_size_remaining_uses_sizeleft`: mock `mode=queue` with `{"queue": {"size": "10 GB", "sizeleft": "2.5 GB", "slots": [], "noofslots": 0}}`; assert `result["size_remaining"] == "2.5 GB"`.
- [ ] **Step 2: Run** `<lock> .venv/bin/python -m pytest tests/test_services/test_sabnzbd_service.py -k size_remaining -v`. Expect FAIL (`"10 GB"`).
- [ ] **Step 3: Implement** `'size_remaining': queue.get('sizeleft', '0 MB')`. Fix any existing test in this file that fed the remaining size through `size`.
- [ ] **Step 4: Run the whole file.** Expect PASS.
- [ ] **Step 5: Commit** `fix: read sizeleft for SABnzbd remaining size (#207, F086)`.

### Task 2: F081 services return None on a failed queue fetch

**Files:**
- Modify: `src/services/sabnzbd.py:186-238` (`get_queue_details`), `src/services/transmission.py:107-160` (`get_queue_details`)
- Test: `tests/test_services/test_sabnzbd_service.py`, `tests/test_services/test_transmission_service.py`

**Interfaces:**
- Produces: both `get_queue_details(self) -> Optional[Dict[str, Any]]`. `None` means the fetch failed. A real empty queue stays a dict with `items_count` 0.
- Consumed by: Task 7 (handler).

- [ ] **Step 1: Write failing tests.** SABnzbd: `test_get_queue_details_returns_none_on_http_error` (status 500), `..._on_wrong_api_key` (200 with `{"status": false, "error": "API Key Incorrect"}`), `..._on_connection_error` (aioresponses `exception=aiohttp.ClientError`). Transmission: `test_get_queue_details_returns_none_when_client_missing`, `..._on_request_error`. Also keep one test that a real empty queue (`noofslots` 0, `queue` key present) returns a dict.
- [ ] **Step 2: Run** the new tests. Expect FAIL (they get the `empty` dict).
- [ ] **Step 3: Implement.** Change the return type to `Optional[Dict[str, Any]]`. Delete the `empty` dicts. SABnzbd: return `None` for a non-200 status, for an exception, and when `"queue"` is not in `data`. Transmission: return `None` when `not self.client` and in the `except`. Update the existing tests that expect the `empty` dict on errors.
- [ ] **Step 4: Run** both service test files. Expect PASS. Run `<lock> .venv/bin/python -m mypy src/`: expect errors only in `downloads.py` (fixed in Task 7); if the handler layer ignores them, expect none.
- [ ] **Step 5: Commit** `fix: return None when the download queue fetch fails (#207, F081)`.

### Task 3: F083 wizard SABnzbd check needs the key

**Files:**
- Modify: `src/setup/validators.py:44` and `:71`
- Test: `tests/test_setup/test_validators.py`

**Interfaces:** none new.

- [ ] **Step 1: Write failing tests.** `test_sabnzbd_check_sends_mode_queue`: mock `GET http://host:8090/api?mode=queue` (aioresponses with the query string) returning `{"queue": {}}`; assert `validate_service_connection("sabnzbd", "host", 8090, False, "key")` is `True`. `test_sabnzbd_wrong_key_fails`: reply 200 `{"status": false, "error": "API Key Incorrect"}`; assert `False`.
- [ ] **Step 2: Run.** Expect FAIL.
- [ ] **Step 3: Implement.** `params = {"mode": "queue"}` for SABnzbd, and also pass `apikey` as a query parameter (SABnzbd reads `apikey` from the query, not from `X-Api-Key`). The success check looks for `"queue"` for SABnzbd and `"version"` for the other services. Update the existing SABnzbd tests that use `version`.
- [ ] **Step 4: Run** the file. Expect PASS.
- [ ] **Step 5: Commit** `fix: test the SABnzbd API key in the setup wizard (#207, F083)`.

### Task 4: F082 Transmission wizard keys

**Files:**
- Modify: `src/setup/service_config.py:129-200` (`get_valid_service_config`)
- Test: `tests/test_setup/test_service_config.py`

**Interfaces:**
- Produces: for `service == "transmission"`, `get_valid_service_config` returns a dict with top-level `host` (str) and `port` (int), and no `server` or `auth` key. This holds on a successful test and when the user skips validation after a failure.

- [ ] **Step 1: Write failing tests** `test_transmission_config_has_host_and_port` (success path) and `test_transmission_config_skip_has_host_and_port` (failed test, `retry` False): mock the questionary prompts as the existing SABnzbd test does; assert `result["host"] == "tx.example"`, `result["port"] == 9091`, and `"server" not in result`.
- [ ] **Step 2: Run.** Expect FAIL (`KeyError: 'host'`).
- [ ] **Step 3: Implement** a private helper that builds the returned dict from `(service, enable, addr, port, ssl, apikey)` and use it for the four return sites. Transmission returns `{"host": addr, "port": port}`. The existing SABnzbd and arr shapes stay the same.
- [ ] **Step 4: Run** the file. Expect PASS.
- [ ] **Step 5: Commit** `fix: write host and port for Transmission in the wizard (#207, F082)`.

### Task 5: F080 handlers check the returned bool

**Files:**
- Modify: `src/bot/handlers/sabnzbd.py:86-101`, `src/bot/handlers/settings.py:611-649`
- Test: `tests/test_handlers/test_sabnzbd_handler.py`, `tests/test_handlers/test_settings_handler.py`

**Interfaces:** none new. Uses existing text `Sabnzbd.Error` (SABnzbd handler) and the existing Settings error text (the one the `except` branch of `handle_sabnzbd_pause_resume` uses).

- [ ] **Step 1: Write failing tests.** SABnzbd handler: `test_speed_selection_shows_error_when_service_returns_false` (`set_speed_limit` returns `False`; assert the edited text is the `Sabnzbd.Error` text, not `Sabnzbd.ChangedTo25`). Settings: one test each for speed (`dl_sab_speed_25`), pause (`dl_sab_pause`) and resume (`dl_sab_resume`) with the service returning `False`; assert the edited text is the error text and not the success text for that action.
- [ ] **Step 2: Run.** Expect FAIL.
- [ ] **Step 3: Implement.** Branch on the returned bool in the four places. On `False` use the error text. Keep the `except` branches as they are. In Settings the speed and pause/resume paths keep the same keyboard and return `States.SETTINGS_DOWNLOADS`.
- [ ] **Step 4: Run** both files. Expect PASS.
- [ ] **Step 5: Commit** `fix: show an error when a SABnzbd action fails (#207, F080)`.

### Task 6: F085 shared `clamp_page` and Refresh clamp

**Files:**
- Modify: `src/bot/keyboards.py` (new `clamp_page` and `DL_PAGE_SIZE = 5`; `_build_pagination_row` at `:886`; `get_downloads_queue_keyboard` at `:961`; `get_downloads_history_keyboard` at `:1058`), `src/bot/handlers/downloads.py:299-323` (`_refresh_current_view`) and `:348` (`_format_history_text` default `page_size`)
- Test: `tests/test_bot/test_keyboards.py`, `tests/test_handlers/test_downloads_handler.py`

**Interfaces:**
- Produces: `clamp_page(page: int, total_pages: int) -> int`, returns `min(max(page, 0), max(total_pages, 1) - 1)`. `DL_PAGE_SIZE: int = 5`.
- Consumes: none. Task 7 and 8 edit the same handler method.

- [ ] **Step 1: Write failing tests.** Keyboards: `test_clamp_page_bounds` (negative, in range, past the end, `total_pages` 0), `test_downloads_queue_keyboard_clamps_page_past_the_end` (6 items, `page=9`: the nav row exists and shows `2/2`), same for the history keyboard. Handler: `test_refresh_clamps_dl_page_past_last_page` (`user_data["dl_page"] = 9`, queue of 6 items, call `handle_downloads_refresh`; assert the sent keyboard has the nav row with `2/2` and `user_data["dl_page"] == 1`), and a History tab variant that also checks the text lists the last page's items.
- [ ] **Step 2: Run.** Expect FAIL.
- [ ] **Step 3: Implement.** Add `clamp_page` and `DL_PAGE_SIZE`. `_build_pagination_row` calls `clamp_page`. Both downloads keyboards compute `total_pages` and clamp `page` before slicing, so the nav row and the items match. `_refresh_current_view` clamps the page from the fetched item count, stores it in `user_data["dl_page"]`, and passes it to the text and keyboard. `_format_history_text` uses `DL_PAGE_SIZE`. Leave `_build_dl_pagination_row` as it is.
- [ ] **Step 4: Run** both files. Expect PASS.
- [ ] **Step 5: Commit** `fix: clamp the downloads page on refresh (#207, F085)`.

### Task 7: F081 handler shows an error, not "empty"

**Files:**
- Modify: `src/bot/handlers/downloads.py:138-149` (`handle_downloads`) and `_refresh_current_view`; `src/bot/keyboards.py` (new keyboard); `translations/addarr.template.yml` and the 9 locale files
- Test: `tests/test_handlers/test_downloads_handler.py`, `tests/test_bot/test_keyboards.py`

**Interfaces:**
- Consumes: `get_queue_details() -> Optional[dict]` (Task 2).
- Produces: `get_downloads_error_keyboard(client: Optional[str] = None) -> InlineKeyboardMarkup` in `keyboards.py`: the client switcher row when `client` is not `None` (reuse `_build_dl_client_tab_row`), then one Refresh button with `callback_data="dl_refresh"`. Translation key `DownloadsFetchError` (invoke the `i18n-key` skill; wording in the style of `DownloadsPauseError`, for example "Could not reach the download client. Check that it is running and that the API key is right.").

- [ ] **Step 1: Write failing tests.** Handler: `test_downloads_shows_error_when_queue_is_none` (service returns `None`; the reply text is `DownloadsFetchError`, is not `DownloadsEmpty`, and the markup has `dl_refresh`), a multi-client variant that also has `dl_client_tx`, and `test_refresh_shows_error_when_queue_is_none` (the edited text is the error). Keyboards: test the new builder with and without `client`.
- [ ] **Step 2: Run.** Expect FAIL.
- [ ] **Step 3: Implement.** Add the builder and the key. In both handler paths: when the queue is `None`, send or edit the `DownloadsFetchError` text with `get_downloads_error_keyboard(self._client_param(context))`, then return. Update the existing handler tests that mock the queue.
- [ ] **Step 4: Run** the two test files, then `PYTHONIOENCODING=utf-8 <lock> .venv/bin/python run.py --validate-i18n`. Expect PASS. Run mypy: expect no new errors.
- [ ] **Step 5: Commit** `fix: show an error when the download client fails (#207, F081)`.

### Task 8: F084 buttons carry their client

**Files:**
- Modify: `src/bot/keyboards.py:961-1055` (`get_downloads_queue_keyboard`), `src/bot/handlers/downloads.py` (`get_handler` patterns at `:51-64`, `_get_active_service`, `_parse_item_id`, the four pause/resume handlers, `_do_action`)
- Test: `tests/test_handlers/test_downloads_handler.py`, `tests/test_bot/test_keyboards.py`

**Interfaces:**
- Produces: in multi-client mode (`client` is not `None`) the keyboard emits `dl_pause_<c>_<id>`, `dl_resume_<c>_<id>`, `dl_pauseall_<c>` and `dl_resumeall_<c>`, where `<c>` is `sab` or `tx`. Single-client mode keeps `dl_pause_<id>`, `dl_pauseall` and the others. The handler regexes accept both forms. A callback without `<c>` uses `user_data["dl_client"]`.
- `_do_action(query, context, client, method_name, item_id, success_key, error_key)`: `client` is the client name (`"sabnzbd"` or `"transmission"`). The admin check, the service and the id parse use it.

- [ ] **Step 1: Write failing tests.** Keyboards: a Transmission item button in multi-client mode has `callback_data == "dl_pause_tx_7"`; Pause All is `dl_pauseall_tx`; a SABnzbd button is `dl_pause_sab_SABnzbd_nzo_abc`; single-client mode keeps the old data; every `callback_data` is at most 64 bytes. Handler: `test_pause_item_uses_client_in_callback_not_user_data` (`callback_data="dl_pause_tx_7"`, `user_data["dl_client"] = "sabnzbd"`; assert Transmission's `pause_item` is awaited with the int `7` and SABnzbd's is not), the same for `dl_pauseall_tx`, a legacy `dl_pause_7` test that follows `user_data`, and a SABnzbd id with underscores.
- [ ] **Step 2: Run.** Expect FAIL.
- [ ] **Step 3: Implement.** In the handler, a small parser splits the callback after the prefix: if the first `_` token is `sab` or `tx`, it is the client and the rest is the id; otherwise the client comes from `user_data`. Change the `dl_pauseall` and `dl_resumeall` patterns to `^dl_pauseall(_(sab|tx))?$` and the same for resume. After an action, `_refresh_current_view` still uses `user_data`; set `user_data["dl_client"]` to the button's client before the refresh so the redrawn view matches the button.
- [ ] **Step 4: Run** both files. Expect PASS.
- [ ] **Step 5: Commit** `fix: put the client in download button callback data (#207, F084)`.

### Task 9: Integration and preflight

- [ ] **Step 1:** If `tests/integration/` covers `/downloads`, add or extend a test for the error view (Task 7) with the `BotHarness`. Run `<lock> .venv/bin/python -m pytest tests/integration --tb=short -v`.
- [ ] **Step 2:** Run `<lock> .venv/bin/python scripts/test_runner.py handlers --coverage`, then the preflight flow (flake8, mypy, i18n, full coverage gate, integration, architecture). Fix gaps in the lines this change added.
- [ ] **Step 3:** Mark each task complete in `TASKS.md` with the metadata that `CLAUDE.md` requires.

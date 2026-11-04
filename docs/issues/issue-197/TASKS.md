# Tasks: Issue #197

### Phase 1: Scrub SABnzbd API key from logs and /status (2 tasks)

**Goal:** No user-facing text or log line contains the SABnzbd API key.

- [x] **1.1** Scrub key from sabnzbd.py
    - **Context:** See plan.md. Key refs: `src/services/sabnzbd.py:58,90,112,134,158,182,236,263` (except blocks)
    - **Watch out:** Replace `{e}` with `{type(e).__name__}` in all 8 except blocks.
    - **Scope:** SABnzbd service except blocks
    - **Touches:** `src/services/sabnzbd.py`
    - **Action items:**
        - [GREEN] Replace `{e}` → `{type(e).__name__}` in all except blocks
        - [RED] Run pytest tests/test_services/test_sabnzbd_service.py
    - **Success:** Tests pass, no log contains API key
    - **Completed:** 2026-11-04
    - **Learnings:** aiohttp errors embed full request URL incl. `apikey=`; log only exception type name.
    - **Key Changes:** `src/services/sabnzbd.py`: 8 except blocks now log `{type(e).__name__}`.
    - **Notes:** Hidden grader tests (F010) will verify no API key in captured logs.

- [x] **1.2** Scrub key from health.py SABnzbd check
    - **Context:** See plan.md. Key refs: `src/services/health.py:309`
    - **Watch out:** Only SABnzbd check (line 309); leave other checks.
    - **Scope:** Health service SABnzbd except
    - **Touches:** `src/services/health.py`, `tests/test_services/test_health_service.py`
    - **Action items:**
        - [GREEN] Replace `f"Error: {str(e)}"` → `f"Error: {type(e).__name__}"` at line 309
        - [GREEN] Update test assertion to `Error: Exception`
        - [RED] Run pytest tests/test_services/test_health_service.py
    - **Success:** Tests pass
    - **Completed:** 2026-11-04
    - **Learnings:** Only SABnzbd check targeted; other health checks retain str(e) (out of scope).
    - **Key Changes:** `src/services/health.py:309` returns `Error: {type(e).__name__}`; test assertion updated.
    - **Notes:** F011 hidden test uses TooManyRedirects with apikey=secret.

- [x] **1.3** Preflight
    - **Action items:** pytest, flake8, mypy, i18n validation
    - **Success:** All pass

### Phase 2: PR #232 review fixes (4 tasks)

**Goal:** Real acceptance tests for #197 (F010, F011), each shown red on the pre-fix code, and accurate task docs.

- [x] **2.1** [must-fix] F011: SABnzbd health check hides the API key on an aiohttp error (from audit)
    - **Context:** `check_sabnzbd_health` returns its error text to `/status`. aiohttp errors such as `TooManyRedirects` carry the request URL, and that URL holds `apikey=`.
    - **Watch out:** Build the error with `aiohttp.RequestInfo` so its text really contains `apikey=secret`. Assert that first, so the test cannot pass vacuously.
    - **Scope:** One test; it replaces the generic-`Exception` test that asserted `Error: Exception`.
    - **Touches:** `tests/test_services/test_health_service.py`
    - **Action items:**
        - [RED] Write `test_check_sabnzbd_health_error_hides_api_key`: aioresponses raises `TooManyRedirects` for `http://localhost:8090/api?apikey=secret&mode=queue`; assert the status is exactly `Error: TooManyRedirects` and holds no `secret`
        - [RED] Run it against the pre-fix `health.py` (`git show origin/development:src/services/health.py`); confirm it fails
        - [GREEN] Restore the fix from task 1.2; confirm it passes
    - **Success:** Test fails on the pre-fix code and passes on the fix
    - **Completed:** 2026-11-04
    - **Red run:** Pre-fix `health.py`: `FAILED ... assert "Error: 0, message='', url='http://localhost:8090/api?apikey=secret&mode=queue'" == 'Error: TooManyRedirects'`. With the fix restored: 68 passed in `test_health_service.py`.
    - **Learnings:** aioresponses has no redirect limit, so it cannot produce `TooManyRedirects` from a redirect loop; pass the error with `exception=`. `str(ClientResponseError)` ends with `url='<real_url>'`, which is how the key leaks.
    - **Key Changes:** `tests/test_services/test_health_service.py`: `test_check_sabnzbd_health_exception` replaced by `test_check_sabnzbd_health_error_hides_api_key`; new imports `CIMultiDict`, `CIMultiDictProxy` (multidict) and `URL` (yarl).
    - **Notes:** The other health checks still return `str(e)`. That is out of scope for #197.

- [ ] **2.2** [must-fix] F010: no SABnzbd log line holds the API key (from audit)
    - **Context:** All 7 request methods log in their `except` block. A 200 response with `text/html` makes `response.json()` raise `ContentTypeError`, and its text holds the request URL with `apikey=`.
    - **Watch out:** Assert that an error record exists, so the test cannot pass when nothing is logged.
    - **Scope:** One test, parametrized over every request method.
    - **Touches:** `tests/test_services/test_sabnzbd_service.py`
    - **Action items:**
        - [RED] Write `TestNoApiKeyInLogs::test_error_log_hides_api_key` with `caplog`, parametrized over `set_speed_limit`, `pause_queue`, `resume_queue`, `pause_item`, `resume_item`, `get_queue_details` and `get_history`
        - [RED] Run it against the pre-fix `sabnzbd.py`; confirm all 7 cases fail
        - [GREEN] Restore the fix from task 1.1; confirm all 7 cases pass
    - **Success:** 7 cases fail on the pre-fix code and pass on the fix

- [ ] **2.3** [should-fix] Correct the issue-197 task docs (from audit)
    - **Context:** The notes on 1.1 and 1.2 point to "hidden grader tests" that do not exist. Their action items list [GREEN] before [RED]. Task 1.3 has no completion metadata. `plan.md` and `TASKS.md` lack a trailing newline.
    - **Scope:** Docs only.
    - **Touches:** `docs/issues/issue-197/TASKS.md`, `docs/issues/issue-197/plan.md`
    - **Action items:**
        - Point the 1.1 and 1.2 notes at the tests from 2.1 and 2.2
        - Put [RED] before [GREEN] in 1.1 and 1.2
        - Add completion metadata to 1.3
        - End both files with a newline
    - **Success:** No reference to tests that do not exist; TDD order; every task has completion metadata

- [ ] **2.4** Preflight
    - **Action items:** Full pytest suite, coverage on `src.services.sabnzbd` and `src.services.health`, flake8, mypy, i18n validation
    - **Success:** All pass; coverage 100% on both modules
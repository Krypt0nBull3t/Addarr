# Issue #76: Refactor API Clients to Inherit from BaseApiClient

### Phase 1: BaseApiClient Foundation (1 task)

**Goal:** Prepare `BaseApiClient` with the extension points the *arr clients need, and update its tests to match.

- [x] **1.1** Extend BaseApiClient and update base tests
    - **Context:**
        - **Why:** The *arr clients can't inherit from `BaseApiClient` today because it hardcodes `/api/v3/` (Lidarr needs `/api/v1/`), only accepts HTTP 200 as success (POST returns 201), returns 3-tuples (clients expect data-or-None), and `check_status()` calls a nonexistent `self.get()` method.
        - **Architecture:** All changes are additive/backward-compatible. Existing `_make_request()` signature and return type unchanged. New `_request()` is a thin wrapper. `API_VERSION` class attribute follows the existing pattern of `DEFAULT_TIMEOUT`, `DEFAULT_MAX_RETRIES`, etc.
        - **Key refs:** `src/api/base.py:62` (class attrs), `:88-92` (_build_base_url), `:143` (hardcoded v3 URL), `:164` (status==200 check), `:225-233` (broken check_status)
        - **Watch out:** Mock config has `"path": "/"` which produces double-slash URLs (`http://localhost:7878//api/v3/`). The rstrip fix changes this to single-slash, requiring ~14 URL updates in `test_base.py` including the module-level `URL` constant at line 391.
    - **Scope:** base.py changes + all test_base.py updates
    - **Touches:** `src/api/base.py`, `tests/test_api/test_base.py`
    - **Action items:**
        - [RED] Add tests for `_request()` (success returns data, failure returns None)
        - [RED] Add test for `API_VERSION` parameterization (subclass with `API_VERSION = "v1"` constructs correct URL)
        - [RED] Add test for 201 success handling through `_make_request()`
        - [RED] Add test for non-JSON 2xx response (graceful handling, returns `(True, None, None)`)
        - [GREEN] Add `API_VERSION = "v3"` class attribute
        - [GREEN] Fix `_build_base_url()` to rstrip trailing slash from path
        - [GREEN] Parameterize URL: `f"{self.base_url}/api/{self.API_VERSION}/{endpoint}"`
        - [GREEN] Extend success check to `200 <= response.status < 300`
        - [GREEN] Wrap `json.loads()` in try/except `JSONDecodeError` for 2xx responses
        - [GREEN] Add `_request()` convenience method
        - [GREEN] Fix `check_status()` to use `_make_request("system/status")`
        - [GREEN] Fix all double-slash URLs in test_base.py (~14 occurrences + URL constant)
        - [GREEN] Rewrite `TestBaseApiClientCheckStatus` tests for new implementation
    - **Success:** `pytest tests/test_api/test_base.py -v` passes, all new tests green
    - **Completed:** 2026-02-20
    - **Learnings:**
        - The `server.path` config value of `"/"` was the root cause of double-slash URLs; `rstrip("/")` on path in `_build_base_url()` fixes it cleanly
        - Wrapping `json.loads()` in try/except for 2xx responses is essential — POST 201 can return non-JSON bodies like "Created"
        - The old `check_status()` called `self.get()` which never existed on `BaseApiClient` — tests only passed because the `except` caught the `AttributeError`
    - **Key Changes:**
        - `src/api/base.py`: Added `API_VERSION = "v3"`, `_request()`, fixed `_build_base_url()` rstrip, `_make_request()` 2xx range + JSONDecodeError handling, fixed `check_status()`
        - `tests/test_api/test_base.py`: Fixed 14 double-slash URLs, added 14 new tests (API_VERSION, _request, 201, non-JSON 2xx, check_status), total 42→56 tests
    - **Notes:** All existing test assertions preserved — changes are backward-compatible

### Phase 2: Radarr Client Refactor (1 task)

**Goal:** Refactor `RadarrClient` as the first client to inherit from `BaseApiClient`, establishing the pattern for Sonarr and Lidarr.

- [x] **2.1** Refactor RadarrClient and update tests
    - **Context:**
        - **Why:** RadarrClient duplicates ~70 lines of request logic from BaseApiClient (URL building, headers, session creation, error handling). It creates a new `aiohttp.ClientSession` per request instead of reusing one.
        - **Architecture:** Inherit from `BaseApiClient`. GET methods use `_request()` (data-or-None). `add_movie()` and `delete_movie()` keep inline response parsing but use `self._get_session()` for the shared session and `self._get_headers()` for headers. Validation stays in `__init__` before `super().__init__("radarr")` to preserve `ValueError` behavior.
        - **Key refs:** `src/api/radarr.py:20` (standalone class), `:52-74` (_make_request to delete), `:154-227` (add_movie inline POST), `:263-286` (delete_movie inline DELETE). Tests: `tests/test_api/test_radarr.py:19` (BASE URL constant), `:58-67` (TestRadarrMakeRequest)
        - **Watch out:** Tests that mock single 500/ClientError for GET-based methods now trigger base class retry (3 attempts). These need 3 mocked responses + `patch("asyncio.sleep")`. Affected: `test_search_connection_error`, `test_get_root_folders_empty`, `test_get_quality_profiles_empty`, `test_check_status_offline`, `test_get_movies_connection_error`. Tests that `patch.object(client, "_make_request", side_effect=Exception)` still work because `_request()` calls `_make_request()`.
    - **Scope:** radarr.py refactor + test_radarr.py updates + cleanup_session fixture in conftest
    - **Touches:** `src/api/radarr.py`, `tests/test_api/test_radarr.py`, `tests/test_api/conftest.py`
    - **Action items:**
        - [RED] Update `TestRadarrMakeRequest` to test `_request()` instead of old `_make_request()`
        - [RED] Update 5 tests needing retry mocks (3 responses + sleep patch)
        - [GREEN] Add `cleanup_session` autouse fixture to `tests/test_api/conftest.py`
        - [GREEN] Change `RadarrClient` to inherit from `BaseApiClient`
        - [GREEN] Rewrite `__init__()` — validate, then `super().__init__("radarr")`
        - [GREEN] Delete `_make_request()` method
        - [GREEN] Update GET methods to use `self._request()`
        - [GREEN] Update `add_movie()` to use `self._get_session()` and `self._get_headers()`
        - [GREEN] Update `delete_movie()` to use `self._get_session()` and `self._get_headers()`
        - [GREEN] Replace `self.api_url` with `self.base_url`, `self.headers` with `self._get_headers()`
        - [GREEN] Clean up imports (remove direct `aiohttp`, `json`)
    - **Success:** `pytest tests/test_api/test_radarr.py -v` passes, no regressions in full suite
    - **Completed:** 2026-02-20
    - **Learnings:**
        - `request.node.funcargs.get(name)` is the correct way to access fixture values in autouse teardown — `request.getfixturevalue()` fails with "fixture already torn down" during teardown
        - `aiohttp` and `json` imports can't be removed from radarr.py because `add_movie()` and `delete_movie()` still use inline session logic with `aiohttp.ClientError` catch and `json.loads()` parsing
        - Removing `check_status()` from RadarrClient is safe — the inherited base class version is functionally identical (both return True/False based on system/status endpoint)
        - Root folder exclusion tests that create ad-hoc `RadarrClient()` instances need explicit `await client.close()` in `finally` blocks since they bypass the cleanup fixture
    - **Key Changes:**
        - `src/api/radarr.py`: Inherits `BaseApiClient`, deleted `_make_request()` (~23 lines), `__init__` validates then calls `super().__init__("radarr")`, GET methods use `_request()`, `add_movie`/`delete_movie` use shared session, removed `check_status` override
        - `tests/test_api/conftest.py`: Added `cleanup_sessions` autouse fixture using `request.node.funcargs`
        - `tests/test_api/test_radarr.py`: Updated `TestRadarrMakeRequest` to test `_request()`, added retry mocks (3 responses + `AsyncMock` sleep patch) to 5 tests, added `await client.close()` in 4 root folder exclusion tests
    - **Notes:** `aiohttp` and `json` still imported — needed for inline POST/DELETE logic in `add_movie`/`delete_movie`. Pattern established for Sonarr/Lidarr in Phase 3.

### Phase 3: Sonarr + Lidarr Client Refactors (1 task)

**Goal:** Apply the established Radarr pattern to Sonarr and Lidarr, completing the refactor.

- [x] **3.1** Refactor SonarrClient, LidarrClient, and update tests
    - **Context:**
        - **Why:** Same duplication problem as Radarr. Following the pattern established in Phase 2.
        - **Architecture:** Identical pattern to RadarrClient. Sonarr keeps `get_seasons()`. Lidarr adds `API_VERSION = "v1"` and keeps `get_metadata_profiles()`. Lidarr's `delete_artist()` does NOT use `?deleteFiles=true` (unlike Radarr/Sonarr).
        - **Key refs:** `src/api/sonarr.py:20` (standalone), `src/api/lidarr.py:20` (standalone), `src/api/lidarr.py:54` (api/v1/ path). Tests: `tests/test_api/test_sonarr.py:18` (BASE), `tests/test_api/test_lidarr.py:20` (BASE with v1)
        - **Watch out:** Lidarr `API_VERSION = "v1"` is critical — without it all Lidarr URLs break. Lidarr `add_artist()` has dual lookup logic (lidarr: prefix fallback, foreignArtistId matching) that must be preserved. Lidarr test has 2 `_make_request` tests to update (non_200 + generic_exception) vs 1 for Sonarr.
    - **Scope:** sonarr.py + lidarr.py refactors + both test files
    - **Touches:** `src/api/sonarr.py`, `src/api/lidarr.py`, `tests/test_api/test_sonarr.py`, `tests/test_api/test_lidarr.py`
    - **Action items:**
        - [RED] Update `TestSonarrMakeRequest` to test `_request()` (1 test)
        - [RED] Update `TestLidarrMakeRequest` to test `_request()` (2 tests)
        - [RED] Update Sonarr retry-affected tests (~5 tests needing 3 mocks + sleep)
        - [RED] Update Lidarr retry-affected tests (~5-6 tests needing 3 mocks + sleep)
        - [GREEN] Refactor `SonarrClient`: inherit, rewrite init, delete _make_request, update methods
        - [GREEN] Refactor `LidarrClient`: same + `API_VERSION = "v1"`
        - [GREEN] Update `add_series()` / `add_artist()` to use shared session
        - [GREEN] Update `delete_series()` / `delete_artist()` to use shared session
        - [GREEN] Clean up imports in both files
    - **Success:** `pytest tests/test_api/test_sonarr.py tests/test_api/test_lidarr.py -v` passes
    - **Completed:** 2026-02-20
    - **Learnings:**
        - Sonarr and Lidarr followed the Radarr pattern exactly — same 4 categories of test changes (import, retry mocks, _request() tests, client.close())
        - `add_artist()` fallback lookup tests needed careful retry handling: first 500 lookup triggers 3 retries before falling through to second lookup
        - `test_add_artist_both_lookups_fail` needed 6 total mocks (3 per URL) since both 500 responses are independently retried
        - `aiohttp` and `json` imports remain in both files — needed for inline POST/DELETE logic in `add_series`/`add_artist` and `delete_series`/`delete_artist`
    - **Key Changes:**
        - `src/api/sonarr.py`: Inherits `BaseApiClient`, all methods use `_request()`, `add_series`/`delete_series` use shared session via `_get_session()`/`_get_headers()`, removed `check_status` override
        - `src/api/lidarr.py`: Same pattern + `API_VERSION = "v1"`, `delete_artist()` does NOT use `?deleteFiles=true`
        - `tests/test_api/test_sonarr.py`: Added `AsyncMock` import, 1 `_request()` test update, 4 retry mock tests (3 responses + sleep), 3 `await client.close()` additions
        - `tests/test_api/test_lidarr.py`: Added `AsyncMock` import, 2 `_request()` test updates, 6 retry mock tests, 2 add_artist retry tests, 5 `await client.close()` additions
    - **Notes:** All 98 Sonarr+Lidarr tests pass. Full suite 1029 tests pass with zero regressions.

### Phase 4: Full Verification (1 task)

**Goal:** Confirm zero regressions, full coverage maintained, clean lint.

- [x] **4.1** Run full test suite, coverage, and lint
    - **Context:**
        - **Why:** The refactor touches the API layer which is used by services and handlers. Need to verify nothing upstream broke.
        - **Architecture:** N/A — verification only
        - **Key refs:** Full suite is 1,019 tests. Coverage target is 100% on `src/`.
        - **Watch out:** Services layer (`src/services/media.py`) creates *arr client instances — if constructor signatures changed, those would break. Handler tests mock at the service level so should be unaffected.
    - **Scope:** Full suite run, coverage report, flake8
    - **Touches:** No file changes expected
    - **Action items:**
        - [GREEN] Run `pytest --tb=short -q` — all tests pass
        - [GREEN] Run `pytest --cov=src --cov-report=term-missing` — coverage maintained
        - [GREEN] Run `flake8 .` — no lint errors
        - [GREEN] Fix any failures found
    - **Success:** All 1,019+ tests pass, coverage maintained, zero lint errors
    - **Completed:** 2026-02-20
    - **Learnings:**
        - Full suite grew from 1,019 to 1,029 tests (10 new tests added across Phase 1-3)
        - 100% coverage maintained across all `src/` modules — no missing lines
        - Zero flake8 errors — refactored code follows existing style conventions
        - Services layer unaffected — constructor signatures unchanged, `MediaService` creates clients identically
    - **Key Changes:**
        - No file changes needed — all verification passed on first run
    - **Notes:** Issue #76 refactor is complete. All 4 phases done.

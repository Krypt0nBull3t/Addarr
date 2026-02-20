# Plan: Refactor API Clients to Inherit from BaseApiClient

## Context

Issue #76. `RadarrClient`, `SonarrClient`, and `LidarrClient` each re-implement their own `_make_request()` independently instead of inheriting from `BaseApiClient`. This causes ~200 lines of duplicated request/error/retry logic, no connection pooling (new `aiohttp.ClientSession` per request), and a maintenance burden where fixes must be applied in 4 places. `BaseApiClient` already has proper session management, retry logic with exponential backoff, and timeout handling.

## Design Decisions

1. **Return type bridge** — Add a `_request()` convenience method to `BaseApiClient` that wraps `_make_request()` (3-tuple return) and returns data-or-None, matching what client methods currently expect.

2. **API version via class attribute** — `API_VERSION = "v3"` on base, overridden to `"v1"` by `LidarrClient`. Used in URL construction: `f"{self.base_url}/api/{self.API_VERSION}/{endpoint}"`.

3. **add_*/delete_* keep inline response logic** — These methods have nuanced response parsing (JSON dict-with-id detection, error arrays, 201 status fallback) that doesn't map cleanly to `_make_request()`. Keep their inline logic but use the shared session (`self._get_session()`) instead of creating new sessions per call.

4. **GET-based methods route through `_request()`** — `search()`, `get_*()`, `check_status()`, etc. get retry logic, session reuse, and error parsing from the base class.

5. **Accept 2xx success range** — Extend `_make_request()` from `== 200` to `200 <= status < 300`, with graceful handling of non-JSON 2xx responses (needed for POST 201).

6. **Fix double-slash URL** — `_build_base_url()` rstrips trailing slash from path, fixing `//api/v3/` → `/api/v3/`.

## Files Modified

| File | Change |
|------|--------|
| `src/api/base.py` | API_VERSION, URL fix, 2xx handling, `_request()`, fix `check_status()` |
| `src/api/radarr.py` | Inherit BaseApiClient, remove `_make_request()`, use shared session |
| `src/api/sonarr.py` | Same as radarr |
| `src/api/lidarr.py` | Same + `API_VERSION = "v1"` |
| `tests/test_api/conftest.py` | Add cleanup_session fixture |
| `tests/test_api/test_base.py` | Fix URLs, new tests, update check_status |
| `tests/test_api/test_radarr.py` | Update _make_request tests, add retry mocks |
| `tests/test_api/test_sonarr.py` | Same pattern |
| `tests/test_api/test_lidarr.py` | Same pattern |

## Verification

1. `pytest tests/test_api/test_base.py -v` — Base tests pass with URL fixes and new tests
2. `pytest tests/test_api/test_radarr.py -v` — Radarr tests pass
3. `pytest tests/test_api/test_sonarr.py -v` — Sonarr tests pass
4. `pytest tests/test_api/test_lidarr.py -v` — Lidarr tests pass
5. `pytest --tb=short -q` — Full suite, no regressions
6. `pytest --cov=src --cov-report=term-missing` — Coverage maintained
7. `flake8 .` — No lint errors

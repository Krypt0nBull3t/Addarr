# Issue #21: Add Retry Logic and Timeouts to Base API Client

## Context

`BaseApiClient._make_request()` in `src/api/base.py` creates a new `aiohttp.ClientSession` per request, has no timeout, and no retry logic. This causes unnecessary overhead and silent failures on transient errors.

**Key discovery:** Radarr/Sonarr/Lidarr don't inherit from `BaseApiClient` — they have their own duplicate `_make_request()`. This work is scoped to `base.py` only. The concrete clients will benefit when migrated to inherit (separate refactor issue).

**Scope:** `src/api/base.py` + `tests/test_api/test_base.py` only.

## Plan

### Phase 1: Timeout, Session Reuse, and Retry (3 tasks)

**Phase Context:**
- `_make_request()` return contract `Tuple[bool, Any, Optional[str]]` must not change
- Session reuse requires lazy creation + explicit `close()` + test cleanup fixture
- Retry only on transient errors (5xx, connection errors, timeouts) — never 4xx
- `aioresponses` supports multiple response mocks per URL (consumed in order) — needed for retry tests

---

- [ ] **1.1** Add request timeout and session reuse to `_make_request()`
    - **Context:**
        - **Why:** Every call creates a new `aiohttp.ClientSession` (expensive), and no timeout means requests can hang indefinitely.
        - **Architecture:** Add `self._session` (lazy, reused), `_get_session()`, `close()`. Session created with `aiohttp.ClientTimeout(total=30)` default. Per-request `timeout` kwarg overrides.
        - **Key refs:**
            - `src/api/base.py:117` — current `async with aiohttp.ClientSession()` to replace
            - `src/api/transmission.py:53` — reference for `aiohttp.ClientTimeout(total=10)` pattern
            - `tests/test_api/test_base.py:31` — `ConcreteClient` fixture (sync, needs async cleanup)
        - **Watch out:**
            - `aioresponses` patches `ClientSession._request`, not session creation — session reuse works fine with mocks
            - Must add async `cleanup_session` autouse fixture to close session between tests, preventing mock leakage
            - Session default timeout goes on `_get_session()`, per-request override goes on `session.request()` kwargs
    - **Scope:** Modify `BaseApiClient.__init__`, add `_get_session()`, `close()`, update `_make_request()` signature + body. Add ~9 tests.
    - **Touches:** `src/api/base.py`, `tests/test_api/test_base.py`
    - **Action items:**
        - [RED] Write `TestBaseApiClientSession` tests: session created lazily (None initially), reused across requests, `close()` closes and nullifies, close is idempotent, close without session is safe, new session after close
        - [RED] Write `TestBaseApiClientTimeout` tests: default timeout 30s applied, custom instance timeout respected, per-request timeout override works
        - [GREEN] Add `DEFAULT_TIMEOUT = 30`, `self.request_timeout`, `self._session = None` to `__init__`
        - [GREEN] Implement `_get_session()` — lazy creation with `ClientTimeout(total=self.request_timeout)`
        - [GREEN] Implement `close()` — closes session if open, sets to None
        - [GREEN] Update `_make_request()` — use `_get_session()` instead of creating new session, add `timeout` kwarg for per-request override
        - [GREEN] Add async `cleanup_session` autouse fixture to test file
    - **Success:** All existing + new tests pass, `flake8 src/api/base.py` clean

- [ ] **1.2** Add retry logic with exponential backoff for transient errors
    - **Context:**
        - **Why:** Transient 5xx errors and connection failures cause immediate failure. Retry with backoff gives services time to recover.
        - **Architecture:** Retry loop in `_make_request()` with configurable `max_retries` (default 2 = 3 total attempts). Backoff: `1s * 2^attempt` (1s, 2s). Only retry on 5xx status codes (500, 502, 503, 504), `aiohttp.ClientError`, and `asyncio.TimeoutError`. Never retry 4xx or unexpected exceptions.
        - **Key refs:**
            - `src/api/base.py:136` — current `aiohttp.ClientError` catch to expand
            - `src/api/transmission.py:42-64` — reference for retry pattern (409 session ID negotiation)
            - `tests/test_api/test_transmission_api.py:74-88` — reference for multi-mock retry test pattern
        - **Watch out:**
            - `aioresponses` mocks are consumed in order — register N mocks for N attempts
            - Patch `asyncio.sleep` in retry tests to avoid real delays and verify backoff values
            - `test_make_request_connection_error` (existing) will break — needs 3 exception mocks instead of 1
            - Generic `Exception` is NOT retried — only connection/timeout errors
    - **Scope:** Add retry loop to `_make_request()`, add `_is_retryable_status()` helper, add `import asyncio`. Add ~12 tests, update 1 existing test.
    - **Touches:** `src/api/base.py`, `tests/test_api/test_base.py`
    - **Action items:**
        - [RED] Write `TestBaseApiClientRetry` tests: retry on 500 then success, retry on 502 then success, retry on connection error then success, retry on timeout then success, no retry on 400, no retry on 404, all retries exhausted (5xx), all retries exhausted (connection error), respects `max_retries` setting, retry disabled when `max_retries=0`, per-request `max_retries` override, exponential backoff sleep values verified
        - [RED] Update `test_make_request_connection_error` — register 3 exception mocks, patch `asyncio.sleep`
        - [GREEN] Add `DEFAULT_MAX_RETRIES = 2`, `DEFAULT_BACKOFF_BASE = 1.0`, `RETRYABLE_STATUS_CODES = frozenset({500, 502, 503, 504})`
        - [GREEN] Add `_is_retryable_status()` helper
        - [GREEN] Restructure `_make_request()` with retry loop, backoff, and `max_retries` kwarg
    - **Success:** All existing + new tests pass (including updated connection error test), `flake8 src/api/base.py` clean

- [ ] **1.3** Verify full test suite and lint, update existing tests if needed
    - **Context:**
        - **Why:** Changes to `BaseApiClient` could theoretically affect any test that uses `ConcreteClient` or imports from `base.py`. Need full verification.
        - **Architecture:** Run full pytest suite + flake8 + check no regressions in Radarr/Sonarr/Lidarr tests (they have their own `_make_request()` so should be unaffected).
    - **Scope:** Verification only. Fix any breakage found.
    - **Touches:** Potentially any test file if regressions found
    - **Action items:**
        - Run `pytest --tb=short -q` — all 944+ tests must pass
        - Run `flake8 src/api/base.py tests/test_api/test_base.py` — clean
        - Spot-check: `pytest tests/test_api/ -v --tb=short` — all API tests pass
    - **Success:** Full suite green, lint clean

## Verification

```bash
pytest tests/test_api/test_base.py -v           # All base API tests (existing + ~21 new)
pytest --tb=short -q                             # Full suite, no regressions
flake8 src/api/base.py tests/test_api/test_base.py  # Lint clean
```

# Issue #21: Add Retry Logic and Timeouts to Base API Client

### Phase 1: Timeout, Session Reuse, and Retry (2 tasks)

**Goal:** Make `BaseApiClient._make_request()` resilient with session reuse, timeouts, and retry with exponential backoff on transient errors.

**Phase Context:**

- `_make_request()` return contract `Tuple[bool, Any, Optional[str]]` must not change
- Scoped to `src/api/base.py` only — Radarr/Sonarr/Lidarr have their own `_make_request()` and are unaffected
- Why NOT retry 4xx: client errors are deterministic and retrying won't help

---

- [x] **1.1** Add request timeout and session reuse to `_make_request()`
    - **Context:**
        - **Why:** Every call creates a new `aiohttp.ClientSession` (expensive TCP+TLS handshake), and no timeout means requests can hang indefinitely.
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
    - **Completed:** 2026-02-20
    - **Learnings:**
        - `aioresponses` patches at the `ClientSession._request` level, so session reuse works seamlessly with mocks — no special mock setup needed
        - Per-request timeout override is passed as a kwarg to `session.request()`, while the default timeout lives on the session itself via `ClientTimeout(total=...)` at creation
        - The `cleanup_session` autouse fixture needs to close the reusable session between tests to prevent mock state leaking across test boundaries
        - `_get_session()` also checks `self._session.closed` to handle edge cases where the session was externally closed
    - **Key Changes:**
        - `src/api/base.py`: Added `DEFAULT_TIMEOUT = 30`, `request_timeout` param to `__init__`, `_session` attribute, `_get_session()` (lazy session creation), `close()` method, updated `_make_request()` to use reusable session + `timeout` kwarg
        - `tests/test_api/test_base.py`: Added `cleanup_session` autouse fixture, `TestBaseApiClientSession` (8 tests), `TestBaseApiClientTimeout` (5 tests) — 13 new tests total
    - **Notes:** Subclasses (Radarr, Sonarr, Lidarr) have their own `_make_request()` overrides and are unaffected. `ConcreteClient` constructor now accepts optional `request_timeout` kwarg.

- [x] **1.2** Add retry logic with exponential backoff for transient errors
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
    - **Success:** All existing + new tests pass (including updated connection error test), `pytest --tb=short -q` full suite green, `flake8 src/api/base.py tests/test_api/test_base.py` clean
    - **Completed:** 2026-02-20
    - **Learnings:**
        - `aioresponses` mocks are consumed in FIFO order per URL — register N mocks for N attempts (e.g., 1 failure + 1 success for a retry-then-succeed test)
        - `asyncio.sleep` must be patched at the module level (`"asyncio.sleep"`) to avoid real delays and to verify exact backoff values
        - The existing `test_make_request_connection_error` needed updating from 1 mock to 3 (initial + 2 retries) plus `asyncio.sleep` patch — exactly as predicted in the task's "watch out"
        - `asyncio.TimeoutError` requires separate handling from `aiohttp.ClientError` since it doesn't inherit from it, but both are retryable
        - f-string without placeholders triggers flake8 F541 — use plain string for static messages
    - **Key Changes:**
        - `src/api/base.py`: Added `import asyncio`, class constants `DEFAULT_MAX_RETRIES = 2`, `DEFAULT_BACKOFF_BASE = 1.0`, `RETRYABLE_STATUS_CODES`, `_is_retryable_status()` helper, restructured `_make_request()` with retry loop + `max_retries` kwarg + exponential backoff
        - `tests/test_api/test_base.py`: Added `asyncio` and `unittest.mock` imports at top (removed inline imports), `TestBaseApiClientRetry` class (13 tests), updated `test_make_request_connection_error` for 3 mocks + sleep patch
    - **Notes:** All Phase 1 tasks are now complete. Both timeout/session reuse and retry logic are implemented and tested in `BaseApiClient._make_request()`.

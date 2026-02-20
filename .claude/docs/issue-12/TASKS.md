# Issue #12: SABnzbd Speed Limit Selection Does Nothing

### Phase 1: Implement Speed Limit API (1 task)

**Goal:** Wire up the `set_speed_limit()` method so the existing handler's speed buttons actually control SABnzbd.

- [x] **1.1** Implement `set_speed_limit` in API client and service layer
    - **Context:**
        - **Why:** The SABnzbd handler presents 25%/50%/100% speed buttons and calls `set_speed_limit()`, but the method doesn't exist — clicks silently fail with an unhandled AttributeError
        - **Architecture:** Two independent layers both need the method. The service (`SABnzbdService`) does NOT delegate to the API client (`SabnzbdClient`) — each makes its own HTTP calls via `aiohttp`. Follow existing patterns in each layer exactly.
        - **Key refs:**
            - `src/bot/handlers/sabnzbd.py:90` — call site: `await self.sabnzbd_service.set_speed_limit(speed)`
            - `src/api/sabnzbd.py:45` — `check_status()` as pattern for API client method (inline f-string URL)
            - `src/services/sabnzbd.py:75` — `add_nzb()` as pattern for service method (params dict)
            - SABnzbd API: `mode=config&name=speedlimit&value=<percentage>` returns `{"status": true}`
        - **Watch out:**
            - Service URL has double-slash (`http://host:port//api`) due to `path: "/"` in config — existing test regex `SABNZBD_API_PATTERN` already handles this
            - API client tests use exact URL matching; service tests use regex matching — follow each convention
            - No input validation needed — handler constrains speed to 25/50/100 via button callbacks
    - **Scope:** Add `set_speed_limit(percentage: int) -> bool` to both `SabnzbdClient` and `SABnzbdService`, plus tests for each
    - **Touches:** `src/api/sabnzbd.py`, `src/services/sabnzbd.py`, `tests/test_api/test_sabnzbd_api.py`, `tests/test_services/test_sabnzbd_service.py`
    - **Action items:**
        - [RED] Write `TestSabnzbdSetSpeedLimit` in `tests/test_api/test_sabnzbd_api.py` (success, HTTP error, connection error) — follow `TestSabnzbdCheckStatus` pattern with `aio_mock` fixture
        - [RED] Write `TestSetSpeedLimit` in `tests/test_services/test_sabnzbd_service.py` (success, HTTP error, connection error) — follow `TestAddNzb` pattern with `aioresponses()` context manager
        - [GREEN] Implement `SabnzbdClient.set_speed_limit()` after `check_status` — inline f-string URL, return `bool`
        - [GREEN] Implement `SABnzbdService.set_speed_limit()` after `add_nzb` — params dict, `session.get(url, params=params)`, return `bool`
    - **Success:** `pytest tests/test_api/test_sabnzbd_api.py tests/test_services/test_sabnzbd_service.py tests/test_handlers/test_sabnzbd_handler.py -v` all pass, `flake8` clean
    - **Completed:** 2026-02-20
    - **Learnings:**
        - API client pattern uses inline f-string URLs with query params baked in; service pattern uses `params` dict with `session.get()` — two distinct conventions in the same codebase
        - Service's `set_speed_limit` placed before `add_nzb` to group config operations together
        - SABnzbd API uses `mode=config&name=speedlimit&value=<pct>` and returns `{"status": true}` on success
    - **Key Changes:**
        - Added `SabnzbdClient.set_speed_limit(percentage: int) -> bool` in `src/api/sabnzbd.py:57`
        - Added `SABnzbdService.set_speed_limit(percentage: int) -> bool` in `src/services/sabnzbd.py:36`
        - Added `TestSabnzbdSetSpeedLimit` (3 tests) in `tests/test_api/test_sabnzbd_api.py`
        - Added `TestSetSpeedLimit` (3 tests) in `tests/test_services/test_sabnzbd_service.py`
    - **Notes:** All 30 SABnzbd tests pass (API + service + handler). The handler tests already mock `set_speed_limit` so they passed before this change — now the real method exists behind those mocks.

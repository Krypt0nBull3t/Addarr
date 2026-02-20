# Issue #22: Add Transmission Health Checks to HealthService

### Phase 1: Implement Transmission Health Check (1 task)

**Goal:** Include Transmission in the periodic health check loop so it appears in `download_clients` results alongside SABnzbd.

- [x] **1.1** Add `check_transmission_health` to HealthService and wire into `run_health_checks`
    - **Context:**
        - **Why:** `HealthService.run_health_checks()` monitors Radarr, Sonarr, Lidarr, and SABnzbd but skips Transmission entirely — operators have no visibility into Transmission connectivity
        - **Architecture:** Delegates to `TransmissionClient` instead of making direct HTTP calls (unlike SABnzbd/media checks). Transmission uses an RPC protocol with 409 session ID negotiation that the client already handles — reimplementing it in the health service would be duplication. The method takes no parameters because `TransmissionClient.__init__` reads config internally (flat structure: `host`, `port`, `ssl`, `username`, `password`).
        - **Key refs:**
            - `src/services/health.py:190` — `check_sabnzbd_health()` as pattern for download client health check (return `Tuple[bool, str]`)
            - `src/services/health.py:223` — `run_health_checks()` where Transmission block goes (before SABnzbd block at line 256)
            - `src/api/transmission.py:66` — `get_session()` returns `{"arguments": {"version": "4.0.0", ...}, "result": "success"}`
            - `tests/test_services/test_health_service.py:270` — `TestCheckSabnzbdHealth` as pattern for test class structure
        - **Watch out:**
            - Mock via `patch("src.services.health.TransmissionClient")` — NOT `aioresponses`, since we delegate to the client rather than making direct HTTP
            - Existing `test_run_health_checks_sabnzbd_enabled` patches `config.get` with a `side_effect` that doesn't handle `"transmission"` — it falls through to `default={}`, so `{}.get("enable")` is falsy. No breakage.
            - Exception hierarchy must match other health checks: `ClientConnectorError` → `TimeoutError` → generic `Exception`
    - **Scope:** Add `check_transmission_health() -> Tuple[bool, str]` method, add Transmission block in `run_health_checks()`, plus 8 tests (5 unit + 3 integration)
    - **Touches:** `src/services/health.py`, `tests/test_services/test_health_service.py`
    - **Action items:**
        - [RED] Write `TestCheckTransmissionHealth` in `tests/test_services/test_health_service.py` (5 tests: success, missing version, connection error, timeout, generic exception) — patch `src.services.health.TransmissionClient`, configure `get_session()` return/side_effect
        - [RED] Write 3 integration tests in `TestRunHealthChecks` (transmission enabled, transmission disabled, both download clients enabled) — patch `config.get` side_effect and `patch.object` on health check methods
        - [GREEN] Add `from src.api.transmission import TransmissionClient` to `src/services/health.py`
        - [GREEN] Implement `check_transmission_health()` after `check_sabnzbd_health` — create `TransmissionClient()`, call `get_session()`, extract version from `arguments.version`
        - [GREEN] Add Transmission block in `run_health_checks()` before SABnzbd — check `config.get("transmission", {}).get("enable")`, call method, append to `download_clients`
    - **Success:** `pytest tests/test_services/test_health_service.py -v` all pass (8 new + existing), `pytest --tb=short -q` full suite green, `flake8` clean
    - **Completed:** 2026-02-20
    - **Learnings:**
        - Transmission health check delegates to `TransmissionClient` rather than direct HTTP — different pattern from SABnzbd/media because RPC 409 negotiation is too complex to duplicate
        - Mocking approach differs accordingly: `patch("src.services.health.TransmissionClient")` instead of `aioresponses` — mock the class, configure `get_session()` return value on the instance
        - Existing integration test `test_run_health_checks_sabnzbd_enabled` was unaffected because its config `side_effect` falls through to `default={}` for unhandled keys
    - **Key Changes:**
        - Added `check_transmission_health() -> Tuple[bool, str]` in `src/services/health.py:224`
        - Added Transmission block in `run_health_checks()` in `src/services/health.py:270` (before SABnzbd)
        - Added `TestCheckTransmissionHealth` (5 tests) in `tests/test_services/test_health_service.py`
        - Added 3 integration tests to `TestRunHealthChecks` (enabled, disabled, both clients)
    - **Notes:** All 1022 tests pass. Health service now checks all 5 services: Radarr, Sonarr, Lidarr, Transmission, SABnzbd.

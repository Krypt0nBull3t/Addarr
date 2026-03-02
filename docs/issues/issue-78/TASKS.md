# Issue #78: Standardize Singleton Pattern Across All Services

### Phase 1: Convert Simple Services to Singleton Pattern (2 tasks)

**Goal:** Convert `JobScheduler` and `TransmissionService` to the standard `__new__()` + `_initialize()` singleton pattern, matching `MediaService`/`HealthService`/etc.

**Phase Context:**

- Why NOT a shared base class: Each service has different init logic (config keys, client setup). The pattern is simple enough (~8 lines) that a mixin would add indirection for no gain.
- The `conftest.py` `reset_singletons` fixture must be updated for each new singleton to prevent test state leakage.

- [x] **1.1** Convert JobScheduler to singleton pattern
    - **Context:**
        - **Why:** `JobScheduler` uses plain `__init__` with a module-level `scheduler = JobScheduler()` instance. Multiple calls to `JobScheduler()` create separate objects, inconsistent with other services and risks duplicate job registrations.
        - **Architecture:** Follow `MediaService` pattern exactly: `_instance = None` class var, `__new__()` checks `_instance`, `_initialize()` classmethod sets up `cls.jobs` and `cls.running`. Keep `scheduler = JobScheduler()` module-level instance for backward compat.
        - **Key refs:** `src/services/scheduler.py:19-24` (current `__init__`), `src/services/media.py:30-35` (reference singleton pattern), `tests/conftest.py:190-217` (reset fixture)
        - **Watch out:** Existing tests create `JobScheduler()` directly (not via module-level `scheduler`). After singleton conversion they'll all get the same instance — the `reset_singletons` fixture must reset `_instance = None` to isolate tests.
    - **Scope:** Singleton conversion of JobScheduler + test + conftest reset
    - **Touches:** `src/services/scheduler.py`, `tests/test_services/test_scheduler.py`, `tests/conftest.py`
    - **Action items:**
        - [RED] Add `TestJobSchedulerSingleton.test_singleton` asserting `JobScheduler() is JobScheduler()`
        - [RED] Verify test fails: `pytest tests/test_services/test_scheduler.py::TestJobSchedulerSingleton -v`
        - [GREEN] Convert `JobScheduler`: add `_instance = None`, `__new__()`, `_initialize()` classmethod (sets `cls.jobs = {}`, `cls.running = False`), remove `__init__`
        - [GREEN] Add `JobScheduler._instance = None` to `reset_singletons` in `tests/conftest.py`
        - [GREEN] Verify: `pytest tests/test_services/test_scheduler.py -v` then `pytest --tb=short -q`
    - **Success:** All tests pass, `JobScheduler() is JobScheduler()` holds, conftest resets singleton between tests
    - **Completed:** 2026-03-02
    - **Learnings:**
        - The `__new__()` + `_initialize()` pattern drops in cleanly — existing tests pass because `reset_singletons` fixture gives each test a fresh instance
        - Type annotation `cls.jobs: Dict[str, aiocron.Cron]` works on class vars set in `_initialize()` just like in `__init__`
    - **Key Changes:**
        - `src/services/scheduler.py`: Replaced `__init__` with `_instance`, `__new__()`, `_initialize()` classmethod
        - `tests/test_services/test_scheduler.py`: Added `TestJobSchedulerSingleton` class
        - `tests/conftest.py`: Added `JobScheduler._instance = None` to `reset_singletons`
    - **Notes:** Module-level `scheduler = JobScheduler()` still works — first call creates the singleton, subsequent calls return it

- [x] **1.2** Convert TransmissionService to singleton pattern
    - **Context:**
        - **Why:** `TransmissionService` uses plain `__init__` with module-level `transmission_service = TransmissionService()`. Same inconsistency as JobScheduler — multiple instantiations create separate objects with separate `_client` and `_config`.
        - **Architecture:** Same `__new__()` + `_initialize()` pattern. `_initialize()` sets `cls._client = None` and `cls._config = config.get("transmission", {})`. Keep `transmission_service` module-level instance.
        - **Key refs:** `src/services/transmission.py:19-22` (current `__init__`), `tests/test_services/test_transmission_service.py` (12 existing tests), `tests/conftest.py:190-217`
        - **Watch out:** Tests set `service._client = mock_client` directly on instances. Since all `TransmissionService()` calls return the same instance after conversion, the `reset_singletons` fixture resetting `_instance = None` is critical to prevent client mock leakage between tests.
    - **Scope:** Singleton conversion of TransmissionService + test + conftest reset
    - **Touches:** `src/services/transmission.py`, `tests/test_services/test_transmission_service.py`, `tests/conftest.py`
    - **Action items:**
        - [RED] Add `TestTransmissionServiceSingleton.test_singleton` asserting `TransmissionService() is TransmissionService()`
        - [RED] Verify test fails: `pytest tests/test_services/test_transmission_service.py::TestTransmissionServiceSingleton -v`
        - [GREEN] Convert `TransmissionService`: add `_instance = None`, `__new__()`, `_initialize()` classmethod (sets `cls._client = None`, `cls._config = config.get(...)`), remove `__init__`
        - [GREEN] Add `TransmissionService._instance = None` to `reset_singletons` in `tests/conftest.py`
        - [GREEN] Verify: `pytest tests/test_services/test_transmission_service.py -v` then `pytest --tb=short -q`
    - **Success:** All tests pass, `TransmissionService() is TransmissionService()` holds, conftest resets singleton
    - **Completed:** 2026-03-02
    - **Learnings:**
        - Existing tests that set `service._client = mock_client` still work because `reset_singletons` clears `_instance = None`, so each test gets a fresh singleton
        - The `_config` class var gets set from `config.get()` during `_initialize()` — mock config injection handles this transparently
    - **Key Changes:**
        - `src/services/transmission.py`: Replaced `__init__` with `_instance`, `__new__()`, `_initialize()` classmethod
        - `tests/test_services/test_transmission_service.py`: Added `TestTransmissionServiceSingleton` class
        - `tests/conftest.py`: Added `TransmissionService._instance = None` to `reset_singletons`
    - **Notes:** `is_enabled()` already existed on TransmissionService — no behavioral change needed

### Phase 2: SABnzbdService — Singleton + Behavioral Change (1 task)

**Goal:** Convert `SABnzbdService` to singleton pattern AND replace `ValueError` on disabled with `is_enabled()` check, matching TransmissionService's approach. Update both handlers and all affected tests.

**Phase Context:**

- Why `is_enabled()` instead of ValueError: The current pattern forces every consumer to wrap `SABnzbdService()` in try/except. TransmissionService already uses `is_enabled()` cleanly. Standardizing eliminates error-handling boilerplate and makes the singleton pattern viable (a singleton that raises on construction is problematic for re-instantiation).

- [x] **2.1** Convert SABnzbdService to singleton with `is_enabled()` and update all consumers
    - **Context:**
        - **Why:** `SABnzbdService.__init__` raises `ValueError` when disabled, forcing try/except in `SabnzbdHandler.__init__` (`sabnzbd.py:21-27`) and `SettingsHandler.__init__` (`settings.py:49-52`). This is incompatible with singleton pattern (can't re-instantiate after first call) and inconsistent with TransmissionService.
        - **Architecture:** `_initialize()` reads config, sets `cls._enabled`, `cls.base_url`, `cls.api_key`. If disabled or config errors: set `_enabled = False` + log (no raise). Add `is_enabled()` returning `bool(self._enabled)`. Handlers change from `if not self.sabnzbd_service:` to `if not self.sabnzbd_service.is_enabled():`.
        - **Key refs:**
            - Service: `src/services/sabnzbd.py:21-34` (current `__init__` with ValueError)
            - SABnzbd handler: `src/bot/handlers/sabnzbd.py:21-27` (try/except init), `:31` and `:48` (None checks)
            - Settings handler: `src/bot/handlers/settings.py:49-52` (try/except init), `:579`, `:596`, `:599` (truth checks)
            - Service tests: `tests/test_services/test_sabnzbd_service.py:59-83` (3 init tests with ValueError)
            - Handler tests: `tests/test_handlers/test_sabnzbd_handler.py:25` (ValueError side_effect), `:202` (same)
            - Settings tests: `tests/test_handlers/test_settings_handler.py:643-656` (ValueError mock), `:686` (service=None)
        - **Watch out:**
            - The `sabnzbd_service` fixture (`test_sabnzbd_service.py:46-50`) creates via `SABnzbdService()` — needs `enabled_sabnzbd_config` to work, which it already has as dependency.
            - Settings handler `handle_sabnzbd_pause_resume` uses `and self.sabnzbd_service` as truthiness — with singleton pattern the instance always exists, so must change to `.is_enabled()`.
            - `aiohttp` import in sabnzbd.py is used inside methods, keep it.
    - **Scope:** Service singleton conversion + handler updates + all test rewrites
    - **Touches:** `src/services/sabnzbd.py`, `src/bot/handlers/sabnzbd.py`, `src/bot/handlers/settings.py`, `tests/test_services/test_sabnzbd_service.py`, `tests/test_handlers/test_sabnzbd_handler.py`, `tests/test_handlers/test_settings_handler.py`, `tests/conftest.py`
    - **Action items:**
        - [RED] Add `TestSABnzbdServiceSingleton.test_singleton` (uses `enabled_sabnzbd_config` fixture)
        - [RED] Rewrite `test_init_disabled_raises` → `test_init_disabled_not_enabled`: assert `service.is_enabled() is False` (no ValueError)
        - [RED] Rewrite `test_init_no_api_key`: assert `service.is_enabled() is False` (no ValueError)
        - [RED] Verify all 3 new/changed tests fail
        - [GREEN] Convert `SABnzbdService`: `_instance = None`, `__new__()`, `_initialize()` (sets `_enabled`, `base_url`, `api_key`; logs errors instead of raising), add `is_enabled()` method, remove `__init__`
        - [GREEN] Update `test_init_success`: add `assert service.is_enabled() is True`
        - [GREEN] Verify: `pytest tests/test_services/test_sabnzbd_service.py -v`
        - [GREEN] Update `src/bot/handlers/sabnzbd.py`: remove try/except in `__init__`, change None checks to `.is_enabled()` checks
        - [GREEN] Update `src/bot/handlers/settings.py`: remove try/except in `__init__`, change truthiness checks to `.is_enabled()` at lines 579, 596, 599
        - [GREEN] Update `test_sabnzbd_handler.py`: `test_handle_sabnzbd_not_available` — mock `is_enabled()` returning `False` instead of `side_effect=ValueError`; `test_get_handler_returns_empty_when_unavailable` — same approach
        - [GREEN] Update `test_settings_handler.py`: `test_sabnzbd_service_none_when_valueerror` — assert `handler.sabnzbd_service is not None` and `.is_enabled() is False`; `test_handle_sabnzbd_pause_when_service_none` — set mock with `is_enabled()` returning `False` instead of `= None`
        - [GREEN] Add `SABnzbdService._instance = None` to `reset_singletons` in `tests/conftest.py`
        - [GREEN] Verify: `pytest --tb=short -q`
    - **Success:** All tests pass, SABnzbdService is singleton, `is_enabled()` replaces ValueError, no handler try/except for SABnzbd init
    - **Completed:** 2026-03-02
    - **Learnings:**
        - Singleton `reset_singletons` must be added BEFORE running tests — the singleton persists across tests otherwise, causing enabled state leakage
        - `_initialize()` handles all error cases (disabled, missing API key) by setting `_enabled = False` + logging instead of raising
        - Handler tests that used `side_effect=ValueError` now use `is_enabled.return_value = False` on the mock — cleaner pattern
    - **Key Changes:**
        - `src/services/sabnzbd.py`: Full singleton conversion, added `is_enabled()`, removed ValueError raises
        - `src/bot/handlers/sabnzbd.py`: Removed try/except init, changed None checks to `.is_enabled()` calls
        - `src/bot/handlers/settings.py`: Removed try/except init, changed truthiness checks to `.is_enabled()` at 3 locations
        - `tests/test_services/test_sabnzbd_service.py`: Added singleton test, rewrote 3 init tests (ValueError → is_enabled assertions)
        - `tests/test_handlers/test_sabnzbd_handler.py`: Updated 2 tests (ValueError side_effect → is_enabled mock)
        - `tests/test_handlers/test_settings_handler.py`: Rewrote 2 tests, added MagicMock import
        - `tests/conftest.py`: Added `SABnzbdService._instance = None` to reset fixture
    - **Notes:** The `self.config` attribute was removed from SABnzbdService — config is read once in `_initialize()` and stored as class attrs

### Phase 3: Exports and Final Verification (1 task)

**Goal:** Update `src/services/__init__.py` exports and run full verification.

- [x] **3.1** Update service exports and run final verification
    - **Context:**
        - **Why:** `src/services/__init__.py` currently exports `scheduler` (instance) but not `JobScheduler` (class). Same gap for `TransmissionService` and `SABnzbdService`. Adding class exports improves discoverability and makes the singleton classes importable from the package.
        - **Architecture:** Add class imports alongside existing instance imports. Add to `__all__`.
        - **Key refs:** `src/services/__init__.py:1-20` (current exports)
        - **Watch out:** Don't break existing imports — keep all current exports, only add new ones.
    - **Scope:** Update exports, lint, full coverage run
    - **Touches:** `src/services/__init__.py`
    - **Action items:**
        - [GREEN] Add `JobScheduler`, `TransmissionService`, `SABnzbdService` exports to `src/services/__init__.py`
        - [GREEN] Run `flake8 .` — clean
        - [GREEN] Run `pytest --cov=src --cov-report=term-missing` — all pass, no regressions
        - [GREEN] Review: confirm no functional behavior changes beyond SABnzbd's `ValueError` → `is_enabled()`
    - **Success:** Lint clean, all tests pass with coverage, exports updated
    - **Completed:** 2026-03-02
    - **Learnings:**
        - The generic `except Exception` branch in SABnzbdService._initialize() needed a dedicated test (corrupt config dict) to reach 100% coverage
        - Adding `SABnzbdService` import to `__init__.py` triggered the singleton at import time with disabled config — works fine since `is_enabled()` returns False
    - **Key Changes:**
        - `src/services/__init__.py`: Added `JobScheduler`, `TransmissionService`, `transmission_service`, `SABnzbdService` exports
        - `tests/test_services/test_sabnzbd_service.py`: Added `test_init_config_error` for coverage of exception branch
    - **Notes:** All 1033 tests pass, 100% coverage, flake8 clean

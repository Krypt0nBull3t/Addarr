# Standardize Singleton Pattern Across All Services (#78)

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Convert `JobScheduler`, `TransmissionService`, and `SABnzbdService` to the standard `__new__()` + `_initialize()` singleton pattern used by `MediaService`, `HealthService`, `NotificationService`, and `TranslationService`. No functional behavior changes except SABnzbdService switches from raising `ValueError` on disabled to an `is_enabled()` check (matching TransmissionService's approach).

**Architecture:** Three-layer architecture with singleton services. The `__new__()` + `_initialize()` pattern ensures only one instance exists per class. `_initialize()` is a classmethod that runs once on first instantiation to set up instance state. The `conftest.py` `reset_singletons` fixture resets `_instance = None` between tests.

**Tech Stack:** Python 3.11, python-telegram-bot v20+, aiohttp, pytest

---

### Task 1: JobScheduler — Singleton Conversion (simplest)

**Files:**
- Modify: `src/services/scheduler.py`
- Modify: `tests/test_services/test_scheduler.py`
- Modify: `tests/conftest.py`

**Step 1: RED — Add singleton test**

Add `TestJobSchedulerSingleton` class to `tests/test_services/test_scheduler.py`:

```python
class TestJobSchedulerSingleton:
    def test_singleton(self):
        a = JobScheduler()
        b = JobScheduler()
        assert a is b
```

**Step 2: Verify RED**

Run: `pytest tests/test_services/test_scheduler.py::TestJobSchedulerSingleton -v`
Expected: FAIL (no singleton behavior yet)

**Step 3: GREEN — Convert JobScheduler**

In `src/services/scheduler.py`, convert the class:
- Add `_instance = None` class variable
- Add `__new__()` that checks `_instance`, calls `_initialize()` on first creation
- Add `_initialize()` classmethod that sets `cls.jobs = {}` and `cls.running = False`
- Remove `__init__`
- Keep `scheduler = JobScheduler()` module-level instance

**Step 4: Verify GREEN**

Run: `pytest tests/test_services/test_scheduler.py -v`
Expected: All tests PASS

**Step 5: Update conftest**

Add `JobScheduler._instance = None` to the `reset_singletons` fixture in `tests/conftest.py`.

**Step 6: Verify full suite**

Run: `pytest --tb=short -q`
Expected: All tests PASS

---

### Task 2: TransmissionService — Singleton Conversion

**Files:**
- Modify: `src/services/transmission.py`
- Modify: `tests/test_services/test_transmission_service.py`
- Modify: `tests/conftest.py`

**Step 1: RED — Add singleton test**

Add `TestTransmissionServiceSingleton` class to `tests/test_services/test_transmission_service.py`:

```python
class TestTransmissionServiceSingleton:
    def test_singleton(self):
        a = TransmissionService()
        b = TransmissionService()
        assert a is b
```

**Step 2: Verify RED**

Run: `pytest tests/test_services/test_transmission_service.py::TestTransmissionServiceSingleton -v`
Expected: FAIL

**Step 3: GREEN — Convert TransmissionService**

In `src/services/transmission.py`, convert the class:
- Add `_instance = None` class variable
- Add `__new__()` that checks `_instance`, calls `_initialize()` on first creation
- Add `_initialize()` classmethod that sets `cls._client = None` and `cls._config = config.get(...)`
- Remove `__init__`
- Keep `transmission_service = TransmissionService()` module-level instance

**Step 4: Verify GREEN**

Run: `pytest tests/test_services/test_transmission_service.py -v`
Expected: All tests PASS

**Step 5: Update conftest**

Add `TransmissionService._instance = None` to the `reset_singletons` fixture in `tests/conftest.py`.

**Step 6: Verify full suite**

Run: `pytest --tb=short -q`
Expected: All tests PASS

---

### Task 3: SABnzbdService — Singleton Conversion + Behavioral Change

This is the most complex task. SABnzbdService currently raises `ValueError` if disabled. We change it to use `is_enabled()` like TransmissionService.

**Files:**
- Modify: `src/services/sabnzbd.py`
- Modify: `src/bot/handlers/sabnzbd.py`
- Modify: `src/bot/handlers/settings.py`
- Modify: `tests/test_services/test_sabnzbd_service.py`
- Modify: `tests/test_handlers/test_sabnzbd_handler.py`
- Modify: `tests/test_handlers/test_settings_handler.py`
- Modify: `tests/conftest.py`

**Step 1: RED — Add singleton test**

Add `TestSABnzbdServiceSingleton` class to `tests/test_services/test_sabnzbd_service.py`:

```python
class TestSABnzbdServiceSingleton:
    def test_singleton(self, enabled_sabnzbd_config):
        a = SABnzbdService()
        b = SABnzbdService()
        assert a is b
```

**Step 2: RED — Rewrite init disabled test**

Rewrite `test_init_disabled_raises` → `test_init_disabled_not_enabled`:
- Assert `service.is_enabled() is False` instead of `pytest.raises(ValueError)`

**Step 3: Verify RED**

Run: `pytest tests/test_services/test_sabnzbd_service.py::TestSABnzbdServiceSingleton -v`
Expected: FAIL

**Step 4: GREEN — Convert SABnzbdService**

In `src/services/sabnzbd.py`, convert the class:
- Add `_instance = None` class variable
- Add `__new__()` that checks `_instance`, calls `_initialize()` on first creation
- Add `_initialize()` classmethod:
  - Set `cls._enabled = config.get('sabnzbd', {}).get('enable', False)`
  - Set `cls.base_url = None`, `cls.api_key = None`
  - If enabled: build `base_url` and `api_key` from config (wrapped in try/except for config errors → set `_enabled = False` + log)
  - If `api_key` missing: log error + set `_enabled = False` (instead of raising)
- Add `is_enabled()` method returning `bool(self._enabled)`
- Remove `__init__` and `self.config` attribute
- Remove `import aiohttp` from module-level if only used inside methods

**Step 5: Update remaining service tests**

- `test_init_success`: Add assertion `assert service.is_enabled() is True`
- `test_init_no_api_key`: Assert `service.is_enabled() is False` instead of `pytest.raises(ValueError)`

**Step 6: Verify GREEN**

Run: `pytest tests/test_services/test_sabnzbd_service.py -v`
Expected: All tests PASS

**Step 7: Update sabnzbd handler**

In `src/bot/handlers/sabnzbd.py`:
- `__init__`: Remove try/except, just `self.sabnzbd_service = SABnzbdService()`
- `get_handler()`: Change `if not self.sabnzbd_service:` → `if not self.sabnzbd_service.is_enabled():`
- `handle_sabnzbd()`: Change `if not self.sabnzbd_service:` → `if not self.sabnzbd_service.is_enabled():`

**Step 8: Update settings handler**

In `src/bot/handlers/settings.py`:
- `__init__` (around lines 49-52): Remove try/except, just `self.sabnzbd_service = SABnzbdService()`
- `handle_sabnzbd_speed`: Change `if self.sabnzbd_service:` → `if self.sabnzbd_service.is_enabled():`
- `handle_sabnzbd_pause_resume`: Change `self.sabnzbd_service` truth checks → `self.sabnzbd_service.is_enabled()`

**Step 9: Update handler tests**

In `tests/test_handlers/test_sabnzbd_handler.py`:
- `test_handle_sabnzbd_not_available`: Change `side_effect=ValueError(...)` → mock with `is_enabled()` returning `False`
- `test_get_handler_returns_empty_when_unavailable`: Same approach

In `tests/test_handlers/test_settings_handler.py`:
- `TestSabnzbdInitError::test_sabnzbd_service_none_when_valueerror`: Rewrite — mock returns instance with `is_enabled() = False`, assert `handler.sabnzbd_service is not None` and `handler.sabnzbd_service.is_enabled() is False`
- `test_handle_sabnzbd_pause_when_service_none`: Change `settings_handler.sabnzbd_service = None` to setting a mock with `is_enabled()` returning `False`

**Step 10: Update conftest**

Add `SABnzbdService._instance = None` to the `reset_singletons` fixture in `tests/conftest.py`.

**Step 11: Verify full suite**

Run: `pytest --tb=short -q`
Expected: All tests PASS

---

### Task 4: Update `src/services/__init__.py` Exports

**Files:**
- Modify: `src/services/__init__.py`

**Step 1: Update exports**

Add class exports alongside existing module-level instances:

```python
from .scheduler import scheduler, JobScheduler
from .transmission import transmission_service, TransmissionService
from .sabnzbd import SABnzbdService
```

Add all to `__all__`.

**Step 2: Verify**

Run: `pytest --tb=short -q`
Expected: All tests PASS

---

### Task 5: Final Verification

**Step 1: Lint**

Run: `flake8 .`
Expected: Clean

**Step 2: Full coverage run**

Run: `pytest --cov=src --cov-report=term-missing`
Expected: All tests PASS, no regressions

**Step 3: Review**

Confirm no functional behavior changes beyond SABnzbd's `ValueError` → `is_enabled()`.

---

## Files Summary

| File | Change |
|------|--------|
| `src/services/scheduler.py` | Add singleton pattern, keep module-level instance |
| `src/services/transmission.py` | Add singleton pattern, keep module-level instance |
| `src/services/sabnzbd.py` | Add singleton pattern + `is_enabled()`, remove ValueError |
| `src/services/__init__.py` | Add new class exports |
| `src/bot/handlers/sabnzbd.py` | Remove try/except, use `is_enabled()` |
| `src/bot/handlers/settings.py` | Remove try/except, use `is_enabled()` |
| `tests/conftest.py` | Add 3 singleton resets |
| `tests/test_services/test_scheduler.py` | Add singleton test |
| `tests/test_services/test_transmission_service.py` | Add singleton test |
| `tests/test_services/test_sabnzbd_service.py` | Add singleton test, rewrite 3 init tests |
| `tests/test_handlers/test_sabnzbd_handler.py` | Update 2 tests (ValueError → is_enabled mock) |
| `tests/test_handlers/test_settings_handler.py` | Rewrite 2 tests (ValueError → is_enabled check) |

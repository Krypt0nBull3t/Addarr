# Issue #123: Health Degradation Alerts

## Summary

Extend `HealthService` to proactively notify admins via Telegram when services go down or recover, with debounce to prevent flap noise.

---

### Phase 1: Config + Alert State (1 task)

**Goal:** Add config section and alert state tracking to HealthService.

- [x] **1.1** Add health_alerts config and alert state attributes
    - **Context:** See plan.md Phase 1-2. Key refs: `config_example.yaml:176` (logging section), `src/services/health.py:83-89` (`_initialize`)
    - **Watch out:** Use `config.get()` not bracket access (enforced by architecture tests)
    - **Scope:** New `health_alerts` config section, new state dicts in HealthService._initialize
    - **Touches:** `config_example.yaml`, `src/services/health.py`
    - **Action items:**
        - [RED] Write test: alert state attributes initialized empty after singleton reset
        - [GREEN] Add `health_alerts` section to `config_example.yaml` (enable, flap_threshold)
        - [GREEN] Add `_failure_counts`, `_down_since`, `_alerted_services` to `_initialize()`
    - **Success:** New test passes, config_example.yaml validates
    - **Completed:** 2026-03-10
    - **Learnings:** Straightforward addition — just new class attrs and dict/set initialization in `_initialize()`. Config section placed after `logging` since it depends on `adminNotifyId`.
    - **Key Changes:** Added `_failure_counts`, `_down_since`, `_alerted_services` to `HealthService._initialize()`. Added `health_alerts` section to `config_example.yaml`.
    - **Notes:** Type annotations added to class body (`Dict[str, int]`, `Dict[str, datetime]`, `Set[str]`) for mypy.

### Phase 2: Alert Logic (1 task)

**Goal:** Implement debounced alert dispatch through NotificationService.

- [x] **2.1** Implement `_check_alerts` method and wire into monitor loop
    - **Context:** See plan.md Phase 2. Key refs: `src/services/health.py:118-163` (`_monitor_loop`), `src/services/notification.py:45-56` (`notify_admin`)
    - **Watch out:** Service names in `current_unhealthy` are formatted as `"Radarr: Error: HTTP 500"` — extract just the name (before `:`) for tracking keys. Recovery messages need human-readable duration (e.g., "15 minutes", not "900 seconds").
    - **Scope:** `_check_alerts()` method, integration into `_monitor_loop`, `_format_duration` helper
    - **Touches:** `src/services/health.py`
    - **Action items:**
        - [RED] Write test: single failure does not trigger alert (below threshold)
        - [RED] Write test: consecutive failures at threshold triggers degradation alert
        - [RED] Write test: no duplicate alert after threshold already triggered
        - [RED] Write test: recovery after alert sends recovery message with duration
        - [RED] Write test: recovery before threshold sends no alerts at all
        - [RED] Write test: alerts disabled in config — no notifications even past threshold
        - [RED] Write test: monitor loop integration — unhealthy results trigger alert flow
        - [GREEN] Implement `_format_duration(seconds)` static helper
        - [GREEN] Implement `_check_alerts(current_unhealthy)` method
        - [GREEN] Wire `_check_alerts` into `_monitor_loop` (guarded by config enable)
    - **Success:** All alert tests pass, `pytest --cov=src.services.health --cov-report=term-missing` shows 100% on new lines
    - **Completed:** 2026-03-10
    - **Learnings:**
        - Service names in `_unhealthy_services` use format `"Name: Status"` — extract name via `split(":")[0].strip()` for tracking keys
        - Removed defensive "unknown" duration fallback — `_down_since` is always set before `_alerted_services`, so the branch was unreachable and killed coverage
        - Added `_format_one_minute` test to cover the `== 1` branch in `_format_duration`
    - **Key Changes:**
        - Added `_format_duration()` static method for human-readable durations
        - Added `_check_alerts()` async method with debounce + recovery logic
        - Wired into `_monitor_loop()` guarded by `config.get("health_alerts", {}).get("enable")`
        - Imported `NotificationService` in health.py
        - 15 new tests across 4 test classes (TestCheckAlerts, TestAlertsDisabled, TestFormatDuration, TestAlertStateInitialization)
    - **Notes:** 100% coverage on health.py (273 statements). 1987 total tests passing.

---

## Verification Checklist

- [x] `pytest tests/test_services/test_health_service.py -v` — all pass (62 tests)
- [x] `pytest --tb=short -q` — full suite green (1987 passed)
- [ ] `python -m flake8 .` — clean
- [ ] `mypy src/` — no new errors
- [x] `pytest --cov=src.services.health --cov-report=term-missing` — 100%

# Health Degradation Alerts Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Proactively notify admins via Telegram when services go down or recover, with debounce to avoid flap noise.

**Architecture:** Extend `HealthService._monitor_loop()` to track consecutive failure counts and down-since timestamps per service, then dispatch alerts through the existing `NotificationService.notify_admin()`. Add a `health_alerts` config section for enable/disable, flap threshold, and per-service toggles.

**Tech Stack:** Python async, python-telegram-bot, existing HealthService/NotificationService singletons

---

## Context

### Current State
- `HealthService` (`src/services/health.py`) runs a `_monitor_loop()` every 15 minutes
- It already detects new failures and recoveries by comparing `_unhealthy_services` sets
- But it only **logs** changes — no Telegram notifications are sent
- `NotificationService` (`src/services/notification.py`) has `notify_admin(message)` ready to use
- Config has `logging.adminNotifyId` for the admin chat ID

### Key Files
- **Modify:** `src/services/health.py` (alert state tracking + dispatch)
- **Modify:** `config_example.yaml` (new `health_alerts` section)
- **Test:** `tests/test_services/test_health_service.py` (new alert tests)

### Design Decisions
1. **No new classes** — alert logic lives in `HealthService` since it already owns the monitoring loop
2. **Debounce by consecutive failure count** — configurable threshold (default 2), per-service tracking
3. **Down-duration in recovery messages** — track when each service first failed
4. **Per-service alert names use the service name string** (e.g., "Radarr") as the tracking key, matching existing `_unhealthy_services` entries
5. **Config uses `config.get()` pattern** — consistent with codebase, no bracket access
6. **Alerts respect per-service toggles** — `health_alerts.services.<name>: true/false`
7. **Import NotificationService in health.py** — services can import other services (only handlers are restricted from importing API clients)

---

## Phase 1: Config

### Task 1.1: Add health_alerts config section

Add to `config_example.yaml` after the `logging` section:

```yaml
# Health Alert Configuration (Optional)
# Sends Telegram notifications when services go down or recover
health_alerts:
  enable: false                # Master toggle for health alerts
  flap_threshold: 2            # Consecutive failures before alerting (prevents flap noise)
```

No per-service toggles for now — YAGNI. The master toggle + flap threshold covers the issue requirements. Per-service can be added later if needed.

**Files:** `config_example.yaml`

---

## Phase 2: Alert State Tracking

### Task 2.1: Add alert state attributes to HealthService

Add to `HealthService._initialize()`:
- `_failure_counts: Dict[str, int]` — consecutive failure count per service name
- `_down_since: Dict[str, datetime]` — when each service first became unhealthy
- `_alerted_services: set[str]` — services we've already sent a "down" alert for (prevents re-alerting)

**Files:** `src/services/health.py`

### Task 2.2: Add _check_alerts method

New method `async _check_alerts(current_unhealthy: set[str])` that:

1. For each service in `current_unhealthy`:
   - Increment `_failure_counts[service_name]`
   - If count == 1, record `_down_since[service_name] = datetime.now()`
   - If count >= threshold AND service not in `_alerted_services`:
     - Send degradation alert via `NotificationService.notify_admin()`
     - Add to `_alerted_services`

2. For each service that was in `_alerted_services` but is no longer unhealthy:
   - Calculate downtime from `_down_since`
   - Send recovery alert via `NotificationService.notify_admin()`
   - Remove from `_alerted_services`, `_failure_counts`, `_down_since`

3. For services no longer unhealthy that were NOT alerted (recovered before threshold):
   - Just clean up `_failure_counts` and `_down_since`

**Alert message formats:**
- Down: `"⚠️ {service_name} is unreachable\nStatus: {status}\nFailing since: {time}"`
- Recovery: `"✅ {service_name} is back online\nWas down for: {duration}"`

**Files:** `src/services/health.py`

### Task 2.3: Wire _check_alerts into _monitor_loop

Call `await self._check_alerts(current_unhealthy)` after updating `self._unhealthy_services` in the monitor loop. Only call if `health_alerts.enable` is True in config.

**Files:** `src/services/health.py`

---

## Phase 3: Testing

### Task 3.1: Test alert state initialization

Verify `_failure_counts`, `_down_since`, `_alerted_services` are initialized empty in `_initialize()`.

### Task 3.2: Test debounce — single failure does not alert

Mock `NotificationService.notify_admin`. Run `_check_alerts` with one service unhealthy once. Assert `notify_admin` was NOT called (threshold=2 by default).

### Task 3.3: Test debounce — threshold reached triggers alert

Run `_check_alerts` twice with same service unhealthy. Assert `notify_admin` called once with degradation message containing service name.

### Task 3.4: Test recovery alert after threshold

1. Push service past threshold (alert sent)
2. Call `_check_alerts` with service healthy
3. Assert recovery alert sent with downtime duration
4. Assert state cleaned up (`_failure_counts`, `_down_since`, `_alerted_services`)

### Task 3.5: Test recovery before threshold — no alert

1. One failure, then recovery
2. Assert no alerts sent at all (neither down nor recovery)
3. Assert state cleaned up

### Task 3.6: Test alerts disabled in config

Set `health_alerts.enable: false`. Verify `_check_alerts` is not called from `_monitor_loop` even when services go unhealthy.

### Task 3.7: Test _monitor_loop integration with alerts

Full integration: mock `run_health_checks` to return unhealthy results for enough cycles, verify `notify_admin` gets called with expected messages.

**Files:** `tests/test_services/test_health_service.py`

---

## Verification

1. `pytest tests/test_services/test_health_service.py -v` — all alert tests pass
2. `pytest --tb=short -q` — full suite green
3. `python -m flake8 .` — no lint issues
4. `mypy src/` — no type errors
5. `pytest --cov=src.services.health --cov-report=term-missing` — 100% on new code

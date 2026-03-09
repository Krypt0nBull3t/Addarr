# Issue #108: Disk Space Monitoring in `/status` Command

## Summary

Add disk space information to the `/status` command via a "Disk Space" button. Shows per-drive usage with visual progress bars and low-space warnings (10% threshold). Queries the first enabled *arr service's `/diskspace` endpoint.

**Plan:** `docs/issues/issue-108/plan.md`

---

### Phase 1: Disk Space Monitoring (4 tasks)

**Goal:** Users can tap "Disk Space" in `/status` to see drive usage with visual bars and warnings.

- [x] **1.1** Add `get_disk_space()` to BaseApiClient
    - **Context:** See plan.md Task 1. Key refs: `src/api/base.py:242-249` (`check_status` as pattern template). Endpoint is `diskspace` — works for all *arr clients since `_request` prepends `/api/{API_VERSION}/`.
    - **Watch out:** Use `self.logger` (not module-level `logger`) since BaseApiClient sets its own logger per service name.
    - **Scope:** One method on BaseApiClient, sample data fixture, tests via RadarrClient
    - **Touches:** `src/api/base.py`, `tests/test_api/test_radarr.py`, `tests/fixtures/sample_data.py`
    - **Action items:**
        - [RED] Add `RADARR_DISK_SPACE` sample data to `tests/fixtures/sample_data.py`
        - [RED] Write tests: success (2 drives returned), empty response, exception
        - [GREEN] Implement `get_disk_space()` on `BaseApiClient`
    - **Success:** `pytest tests/test_api/test_radarr.py -v -k disk_space` — 3 tests pass
    - **Completed:** 2026-03-09
    - **Learnings:** `get_disk_space` follows the same pattern as `check_status` — simple endpoint, try/except, return empty list on failure. The `diskspace` endpoint returns a flat list of drive objects.
    - **Key Changes:** Added `get_disk_space()` to `src/api/base.py`, `RADARR_DISK_SPACE` fixture to `tests/fixtures/sample_data.py`, 3 tests in `tests/test_api/test_radarr.py`
    - **Notes:** Method is on BaseApiClient so all *arr clients (Radarr, Sonarr, Lidarr) inherit it automatically.

- [ ] **1.2** Add `get_disk_space()` to HealthService
    - **Context:** See plan.md Task 2. Key refs: `src/services/health.py:238-300` (`run_health_checks` iterates services similarly). HealthService currently builds URLs manually for health checks — for disk space, we create actual API client instances via a new `_get_api_client()` helper with lazy imports.
    - **Watch out:** Returns flat list (not dict-of-lists) since we only query one service. Falls through to next enabled service on error.
    - **Scope:** `_get_api_client()` helper + `get_disk_space()` method, tests
    - **Touches:** `src/services/health.py`, `tests/test_services/test_health_service.py`
    - **Action items:**
        - [RED] Write tests: returns drives from first enabled service, skips disabled services, no enabled services returns `[]`, client error falls through to next service, `_get_api_client` returns None for unknown key
        - [GREEN] Implement `_get_api_client()` and `get_disk_space()` on HealthService
    - **Success:** `pytest tests/test_services/test_health_service.py -v -k disk_space` — 5 tests pass

- [ ] **1.3** Add keyboard button, handler callback, and formatter
    - **Context:** See plan.md Task 3. Key refs: `src/bot/keyboards.py:74-93` (`get_system_keyboard`), `src/bot/handlers/system.py:65-68` (action dispatch), `src/bot/handlers/system.py:96-114` (`_handle_details` as pattern). Formatter and helpers are module-level functions (not methods) for easy unit testing.
    - **Watch out:** `_build_disk_space_text` takes `(drives, translation)` not `self` — keeps it testable as a standalone function. `_format_bytes` divides by 1024 (binary units).
    - **Scope:** Keyboard button, dispatch branch, handler method, 3 module-level functions, tests
    - **Touches:** `src/bot/keyboards.py`, `src/bot/handlers/system.py`, `tests/test_handlers/test_system_handler.py`
    - **Action items:**
        - [RED] Write tests: diskspace callback shows drives with percentage, empty drives shows "no data" message, error shows error message, low space (<10% free) shows warning emoji
        - [RED] Write unit tests for `_format_usage_bar` (0%, 50%, 100%) and `_format_bytes` (0 B, GB range, TB range)
        - [GREEN] Add `LOW_SPACE_THRESHOLD` constant, `_format_usage_bar()`, `_format_bytes()`, `_build_disk_space_text()` to `system.py`
        - [GREEN] Add `_handle_diskspace()` method and dispatch branch in `handle_system_action()`
        - [GREEN] Add "Disk Space" button to `get_system_keyboard()` in `keyboards.py`
    - **Success:** `pytest tests/test_handlers/test_system_handler.py -v -k "diskspace or format_usage or format_bytes"` — 6+ tests pass

- [ ] **1.4** Add translation keys
    - **Context:** See plan.md Task 4. Key refs: `translations/addarr.en-us.yml:295-299` (existing status keys section). Handler uses `default=` fallbacks so this is for i18n completeness.
    - **Watch out:** Must add to both `en-us.yml` AND `template.yml` or `--validate-i18n` will flag mismatches. Use flat top-level keys (TranslationService does single-level lookup only).
    - **Scope:** 3 translation keys in 2 files
    - **Touches:** `translations/addarr.en-us.yml`, `translations/addarr.template.yml`
    - **Action items:**
        - [GREEN] Add `DiskSpaceError`, `DiskSpaceFailed`, `DiskSpaceNone` keys to `en-us.yml`
        - [GREEN] Add same keys to `template.yml`
    - **Success:** `PYTHONIOENCODING=utf-8 python run.py --validate-i18n` passes

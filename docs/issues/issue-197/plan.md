# Plan: Issue #197 — SABnzbd API key leaks into logs and /status

**Goal:** No user-facing text and no log line contains the SABnzbd API key; errors show only exception type.

**Architecture:** Scrub at display/log sites only. Replace `{e}`/`{str(e)}` with `{type(e).__name__}` in SABnzbd service except blocks and SABnzbd health check.

**Tech Stack:** Python, aiohttp, pytest.

## File Structure
- Modify: `src/services/sabnzbd.py` (8 except blocks)
- Modify: `src/services/health.py` (SABnzbd check, line 309)
- Modify: `tests/test_services/test_health_service.py` (assertion)

## Tasks

### Task 1: Scrub key from sabnzbd.py
- Files: src/services/sabnzbd.py
- [ ] Replace `{e}` → `{type(e).__name__}` in all except blocks.
- [ ] Run pytest tests/test_services/test_sabnzbd_service.py.

### Task 2: Scrub key from health.py SABnzbd check
- Files: src/services/health.py
- [ ] Line 309: `f"Error: {str(e)}"` → `f"Error: {type(e).__name__}"`.
- [ ] Update test_health_service assertion.
- [ ] Run pytest tests/test_services/test_health_service.py.

### Task 3: Preflight
- [ ] pytest, flake8, mypy, i18n validation.

## Review Focus
- aiohttp error text containing full URL with apikey= — now excluded.
- Other health checks still use str(e) (out of scope, issue targets SABnzbd only).
# Tasks: Issue #197

### Phase 1: Scrub SABnzbd API key from logs and /status (2 tasks)

**Goal:** No user-facing text or log line contains the SABnzbd API key.

- [x] **1.1** Scrub key from sabnzbd.py
    - **Context:** See plan.md. Key refs: `src/services/sabnzbd.py:58,90,112,134,158,182,236,263` (except blocks)
    - **Watch out:** Replace `{e}` with `{type(e).__name__}` in all 8 except blocks.
    - **Scope:** SABnzbd service except blocks
    - **Touches:** `src/services/sabnzbd.py`
    - **Action items:**
        - [GREEN] Replace `{e}` → `{type(e).__name__}` in all except blocks
        - [RED] Run pytest tests/test_services/test_sabnzbd_service.py
    - **Success:** Tests pass, no log contains API key
    - **Completed:** 2026-11-04
    - **Learnings:** aiohttp errors embed full request URL incl. `apikey=`; log only exception type name.
    - **Key Changes:** `src/services/sabnzbd.py`: 8 except blocks now log `{type(e).__name__}`.
    - **Notes:** Hidden grader tests (F010) will verify no API key in captured logs.

- [x] **1.2** Scrub key from health.py SABnzbd check
    - **Context:** See plan.md. Key refs: `src/services/health.py:309`
    - **Watch out:** Only SABnzbd check (line 309); leave other checks.
    - **Scope:** Health service SABnzbd except
    - **Touches:** `src/services/health.py`, `tests/test_services/test_health_service.py`
    - **Action items:**
        - [GREEN] Replace `f"Error: {str(e)}"` → `f"Error: {type(e).__name__}"` at line 309
        - [GREEN] Update test assertion to `Error: Exception`
        - [RED] Run pytest tests/test_services/test_health_service.py
    - **Success:** Tests pass
    - **Completed:** 2026-11-04
    - **Learnings:** Only SABnzbd check targeted; other health checks retain str(e) (out of scope).
    - **Key Changes:** `src/services/health.py:309` returns `Error: {type(e).__name__}`; test assertion updated.
    - **Notes:** F011 hidden test uses TooManyRedirects with apikey=secret.

- [x] **1.3** Preflight
    - **Action items:** pytest, flake8, mypy, i18n validation
    - **Success:** All pass
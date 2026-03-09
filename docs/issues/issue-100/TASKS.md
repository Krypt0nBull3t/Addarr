# TASKS — Issue #100: Remove built-in packages from requirements.txt

## Phase 1: Remove unnecessary dependencies

- [x] **1.1** Remove `asyncio>=3.4.3` and `dataclasses>=0.6` from `requirements.txt`
    - Remove the `asyncio>=3.4.3` line from the "Async support" section
    - Remove the `dataclasses>=0.6` line and the "Data handling" section header (move `typing-extensions` under a better heading)
    - Run full test suite to verify no breakage
    - Run flake8 and i18n validation
    - **Completed:** 2026-03-09
    - **Learnings:** `typing-extensions` is required by `transmission-rpc` so must stay despite being stdlib-adjacent
    - **Key Changes:** Removed `asyncio>=3.4.3` and `dataclasses>=0.6` from `requirements.txt`, reorganized section headers
    - **Notes:** No runtime impact — both packages are no-op shims on Python 3.11+

# Issue #77: Fix Deprecated CallbackContext and Mixed Imports in Transmission Handler

### Phase 1: Align Transmission Handler with Project Conventions (1 task)

**Goal:** Replace deprecated `CallbackContext` with `ContextTypes.DEFAULT_TYPE` and convert relative imports to absolute, matching all 8 other handlers.

- [x] **1.1** Fix imports and method signatures in transmission handler
    - **Context:**
        - **Why:** `transmission.py` is the only handler using deprecated `CallbackContext` (python-telegram-bot v20+) and mixing relative/absolute imports. This creates inconsistency and will break when `CallbackContext` is removed upstream.
        - **Architecture:** Pure cleanup — no behavior changes. All other handlers use `ContextTypes.DEFAULT_TYPE` and absolute `from src.xxx` imports. Follow existing pattern exactly.
        - **Key refs:** `src/bot/handlers/transmission.py:9` (CallbackContext import), `:14-16` (mixed imports), `:39` and `:81` (method signatures). Reference handler: `src/bot/handlers/sabnzbd.py` (same download-client pattern).
        - **Watch out:** Tests use `make_context` fixture — no `CallbackContext` references in tests, so no test changes needed. Verify with `grep -r "CallbackContext" tests/` before and after.
    - **Scope:** Import block + 2 method signatures in transmission.py
    - **Touches:** `src/bot/handlers/transmission.py`
    - **Action items:**
        - [GREEN] Run `pytest tests/test_handlers/test_transmission_handler.py -v` to establish baseline (all 7 tests pass)
        - [GREEN] Replace `CallbackContext` import with `ContextTypes` on line 9
        - [GREEN] Convert 2 relative imports to absolute on lines 14-15
        - [GREEN] Update `transmission_command` signature: `CallbackContext` → `ContextTypes.DEFAULT_TYPE` on line 39
        - [GREEN] Update `handle_callback` signature: `CallbackContext` → `ContextTypes.DEFAULT_TYPE` on line 81
        - [GREEN] Run `pytest tests/test_handlers/test_transmission_handler.py -v` — all 7 tests pass
        - [GREEN] Run `pytest --tb=short -q` — no regressions
        - [GREEN] Run `flake8 src/bot/handlers/transmission.py` — clean
    - **Success:** All tests pass, lint clean, no `CallbackContext` or relative imports remain in file
    - **Completed:** 2026-03-02
    - **Learnings:**
        - `replace_all` on the Edit tool cleanly handles updating both method signatures in one pass since `context: CallbackContext` was unique enough as a search pattern
        - Tests needed zero changes — `make_context` fixture fully abstracts the context type, confirming good test design
    - **Key Changes:**
        - `src/bot/handlers/transmission.py`: Replaced `CallbackContext` import with `ContextTypes`, converted 2 relative imports (`...services`, `...utils`) to absolute (`src.services`, `src.utils`), updated 2 method signatures to `ContextTypes.DEFAULT_TYPE`
    - **Notes:** All 1029 tests pass, 0 regressions. Transmission handler now matches all 8 other handlers.

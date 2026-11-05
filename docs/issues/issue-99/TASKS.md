# Issue #99: Clean Up Test Suite Warnings

### Phase 1: Fix and Filter Test Warnings (1 task)

**Goal:** Eliminate all test suite warnings so `pytest` runs clean with `filterwarnings = error`.

- [x] **1.1** Fix real warnings and add filterwarnings config
    - **Context:** See plan.md. 13 unique warnings across 4 categories. Three are fixable code issues, the rest are known-safe third-party warnings to filter.
    - **Watch out:** `filterwarnings = error` must be the first entry (turns unfiltered warnings into errors). ResourceWarning is broadly ignored because pytest-asyncio unclosed event loops are unavoidable.
    - **Scope:** Fix unclosed files in test_config_handler.py, fix unawaited coroutine in test_main.py, add filterwarnings to pytest.ini
    - **Touches:** `tests/test_utils/test_config_handler.py`, `tests/test_main.py`, `pytest.ini`
    - **Action items:**
        - [GREEN] Fix `test_config_handler.py:86` — replace `open().read()` with `Path.read_text()`
        - [GREEN] Fix `test_config_handler.py:144-145` — same pattern, two lines
        - [GREEN] Fix `test_main.py:598-602` — close unawaited coroutine from mocked `asyncio.run`
        - [GREEN] Add `filterwarnings` block to `pytest.ini` with `error` + ignore entries for PTBUserWarning, aioresponses DeprecationWarning, AsyncMock RuntimeWarning, SetupWizard/get_valid_service_config RuntimeWarning
        - [GREEN] Run `python -m pytest --tb=short -q` — all pass, zero warnings
        - [GREEN] Run `python -m flake8 .` — lint clean
    - **Success:** `pytest` passes with `filterwarnings = error` active, zero warning output
    - **Completed:** 2026-03-09
    - **Learnings:**
        - `PytestUnraisableExceptionWarning` is a separate warning class from `RuntimeWarning` — pytest wraps GC'd coroutines in it. Need to filter it independently.
        - When `asyncio.run` is mocked with `side_effect`, `call_args` is still recorded — can still call `.close()` on the coroutine arg to prevent GC warnings.
        - All three `TestRunBot` tests create unawaited `main()` coroutines (not just the one without side_effect).
    - **Key Changes:**
        - `tests/test_utils/test_config_handler.py` — replaced 3 bare `open().read()` with `Path.read_text()`
        - `tests/test_main.py` — added `.close()` on unawaited coroutines in all 3 `TestRunBot` tests
        - `pytest.ini` — added `filterwarnings` with `error` + 7 ignore rules for known-safe warnings
    - **Notes:** `filterwarnings = error` catches new warnings immediately as test failures — any new library or code change that produces warnings will surface as a fail rather than being silently ignored.

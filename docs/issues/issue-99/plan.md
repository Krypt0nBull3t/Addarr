# Clean Up Test Suite Warnings — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Eliminate all test suite warnings so `pytest -W error` passes cleanly.

**Architecture:** Three-pronged approach: (1) fix real code issues (unclosed files, unawaited coroutines), (2) add `filterwarnings` in `pytest.ini` for known-safe third-party warnings, (3) verify zero warnings remain.

**Tech Stack:** pytest, AsyncMock, aioresponses, python-telegram-bot v20+

---

## Warning Inventory (13 unique, ~1368 total with duplicates)

| # | Type | Source | Fix Strategy |
|---|------|--------|-------------|
| 1 | ResourceWarning: unclosed file | `tests/test_utils/test_config_handler.py:86` | Fix: use `with` statement |
| 2 | ResourceWarning: unclosed file | `tests/test_utils/test_config_handler.py:144` | Fix: use `with` statement |
| 3 | ResourceWarning: unclosed file | `tests/test_utils/test_config_handler.py:145` | Fix: use `with` statement |
| 4 | ResourceWarning: unclosed event loop | `asyncio/base_events.py` | Filter: pytest-asyncio internal |
| 5 | RuntimeWarning: coroutine 'main' never awaited | `tests/test_main.py:598-602` | Fix: close the coroutine |
| 6 | RuntimeWarning: coroutine 'AsyncMockMixin._execute_mock_call' never awaited | `unittest/mock.py:805` | Filter: known Python AsyncMock issue |
| 7 | RuntimeWarning: coroutine 'AsyncMockMixin._execute_mock_call' never awaited | `unittest/mock.py:528` | Filter: same issue, different callsite |
| 8 | RuntimeWarning: coroutine 'SetupWizard._async_setup' never awaited | `tests/test_setup/test_wizard.py` | Filter: gc collecting mock-created coroutine |
| 9 | RuntimeWarning: coroutine 'get_valid_service_config' never awaited | gc cleanup | Filter: gc collecting mock-created coroutine |
| 10 | DeprecationWarning: asyncio.iscoroutinefunction | `aioresponses/core.py:192` | Filter: upstream aioresponses issue |
| 11 | PTBUserWarning: per_message=False | `src/bot/handlers/start.py:47` | Filter: intentional design choice |
| 12 | PTBUserWarning: per_message=False | `src/bot/handlers/media/handler.py:59` | Filter: intentional design choice |
| 13 | PTBUserWarning: per_message=False | `src/bot/handlers/settings.py:54` | Filter: intentional design choice |

## Task 1: Fix unclosed files in test_config_handler.py

**Files:**
- Modify: `tests/test_utils/test_config_handler.py:86,144-145`

**What:** Replace bare `open().read()` calls with `with` statements or `Path.read_text()`.

Lines to fix:
```python
# Line 86 — currently:
content = open(handler.config_path, encoding="utf-8").read()
# Fix:
content = Path(handler.config_path).read_text(encoding="utf-8")

# Lines 144-145 — currently:
original = open(handler.config_path, encoding="utf-8").read()
backup = open(result, encoding="utf-8").read()
# Fix:
original = Path(handler.config_path).read_text(encoding="utf-8")
backup = Path(result).read_text(encoding="utf-8")
```

Add `from pathlib import Path` to imports if not already present.

## Task 2: Fix unawaited coroutine in test_main.py

**Files:**
- Modify: `tests/test_main.py:598-602`

**What:** When `asyncio.run` is mocked, `run_bot()` calls `asyncio.run(main())` — the mock records the call but the `main()` coroutine object is never awaited and triggers a RuntimeWarning on gc. Fix by closing the coroutine after the test.

```python
@patch("src.main.asyncio.run")
def test_calls_asyncio_run(self, mock_run):
    """run_bot() calls asyncio.run(main())."""
    run_bot()
    mock_run.assert_called_once()
    # Close the unawaited coroutine to suppress RuntimeWarning
    mock_run.call_args[0][0].close()
```

## Task 3: Add filterwarnings to pytest.ini

**Files:**
- Modify: `pytest.ini`

**What:** Add `filterwarnings` entries for known-safe third-party warnings that we cannot fix.

```ini
[pytest]
testpaths = tests
asyncio_mode = auto
filterwarnings =
    error
    ignore::ResourceWarning
    ignore:If 'per_message=False':telegram.warnings.PTBUserWarning
    ignore:'asyncio.iscoroutinefunction' is deprecated:DeprecationWarning:aioresponses
    ignore:coroutine 'AsyncMockMixin._execute_mock_call' was never awaited:RuntimeWarning
    ignore:coroutine 'SetupWizard._async_setup' was never awaited:RuntimeWarning
    ignore:coroutine 'get_valid_service_config' was never awaited:RuntimeWarning
markers =
    slow: marks tests as slow
    integration: marks tests that hit real services
```

**Key design decisions:**

- Start with `error` to turn all warnings into errors (catches new warnings immediately)
- Then `ignore` specific known-safe patterns
- `ResourceWarning` is broadly ignored because unclosed event loops from pytest-asyncio are unavoidable and the file-based ones are fixed in Task 1
- PTB `per_message=False` is intentional — we use `per_message=False` by design
- `aioresponses` deprecation is an upstream issue (uses `asyncio.iscoroutinefunction` internally)
- AsyncMock internal coroutine warnings are a known CPython issue with no workaround

**Note on ResourceWarning:** We could be more targeted (only ignore unclosed event loops) but ResourceWarning from asyncio internals is notoriously inconsistent across platforms. Broad ignore is standard practice — the real file-handle leaks are fixed in Task 1.

## Task 4: Verify zero warnings

**Commands:**
```bash
python -m pytest --tb=short -q
```

The `filterwarnings = error` line means any un-filtered warning will fail the test. If tests pass, we're clean.

## Verification

After all tasks, run:
```bash
python -m pytest --tb=short -q    # All pass, no warnings
python -m flake8 .                 # Lint clean
```

---
title: "Make the coverage gate measure auth and config code"
labels: [tech-debt, priority:high]
slice: 10
findings: [F220, F221, F222]
---
## Problem

The 100% coverage gate does not measure some of the most important code.

- **F220** The `.coveragerc` exclude pattern `pass` also matches "password". 103 lines are excluded, including all of `check_password`.
- **F221** `src/config/settings.py` is omitted from coverage. `tests/test_config/test_settings.py` tests copies of `save` and the validators that are written in the test, not the real module.
- **F222** `pytest.ini` ignores "coroutine ... was never awaited". This hides missing `await`s.

## Expected behavior

Coverage measures every line of `check_password` and of `src/config/settings.py`. The tests run the real settings module. A missing `await` fails the test run.

## Fix

- [ ] **F220** Change the exclude pattern `pass` to `^\s*pass\s*$` (`.coveragerc:13`)
- [ ] **F221** Load the real module via importlib with file reads patched; remove the omit (`.coveragerc:6`, `tests/test_config/test_settings.py:124-375`, `tests/conftest.py:160-205`)
- [ ] **F222** Remove the "was never awaited" ignore; fix the tests that then fail (`pytest.ini:11`)

## Acceptance criteria

- **F220** `pytest --cov=src --cov-report=term-missing` counts the `check_password` lines as statements, not as excluded, and they are covered.
- **F221** `.coveragerc` no longer omits `src/config/settings.py`. `tests/test_config/test_settings.py` calls the real `save()` and validators, not copies. A bug planted in the real `save()` makes a test fail.
- **F222** `pytest.ini` no longer ignores `coroutine 'AsyncMockMixin._execute_mock_call' was never awaited`. A planted missing `await` makes the run fail.
- `pytest` passes with `fail_under = 100`. `flake8` and `mypy src/` pass.

## Notes

- Source: audit 2026-10-28, docs/issues/audit-2026-10-28/FINDINGS.md (F-ids F220, F221, F222).
- Priority: max P 35, sum P 76 (high).
- Order: do slices 1-8 first. Slice 3 (F025) calls the validators that the test copies mirror. Slice 14 (F030, F031) changes the real `Config.save()`; its tests need F221.
- Not agent-ready: F221 has effort 3.

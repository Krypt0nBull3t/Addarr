# Preflight Flow: Step Details

Sequence is defined in SKILL.md. This file holds the commands.

The commands are the ones the CI jobs `lint`, `type-check`, `validate-translations`, `unit-test`, `integration-test` and `architecture-test` run in `.github/workflows/ci.yml`. `tests/test_architecture/test_skills.py` fails when they drift apart. Locally the unit-test command leaves out `--cov-report=html:coverage-html` (a CI upload artifact). Preflight does not run the 3.10-3.14 compatibility matrix, pip-audit or the Docker build; CI does.

**Interpreter (`<py>`):** `.venv/bin/python` in the main checkout. A git worktree builds its own `.venv` and never uses the main checkout's (the worktree guard blocks it): create it with Python 3.11, the CI version (`python3.11 -m venv .venv`), then `.venv/bin/python -m pip install flake8 -r requirements.txt -r requirements-test.txt` (flake8 is not in the requirements files; CI installs it the same way). A cloud session without a venv uses `python`.

**Lock (`<lock>`):** see SKILL.md "The Suite Lock". Empty when the lock script does not exist.

**After merging `development`:** when `requirements.txt` or `requirements-test.txt` changed, re-run `.venv/bin/python -m pip install -r requirements.txt -r requirements-test.txt`. A stale venv misses a new extra: without `python-telegram-bot[job-queue]` every integration test errors with `No JobQueue set up`.

Run the steps in order. Stop on the first failure. After any code fix, re-run from step 1 (a type fix can break a test). At most 3 fix rounds; then report the failing output and `ASK`.

## Step 1: Lint

```bash
<lock> <py> -m flake8 .
```

**On failure:** fix by hand (no formatter is installed). `.flake8` ignores E203, E501 and W503, so line length is not reported.

## Step 2: Type Check

```bash
<lock> <py> -m mypy src/
```

**On failure:** fix the type errors. Common fixes: `Optional[]` for parameters with a `None` default, class-level annotations on singletons, `isinstance(result, BaseException)` for `asyncio.gather` results.

## Step 3: Translation Validation

```bash
PYTHONIOENCODING=utf-8 <lock> <py> run.py --validate-i18n
```

**On failure:** report which translation files have problems and which keys are missing or malformed. Fix them with `@i18n-key`.

## Step 4: Unit Tests With the Coverage Gate

```bash
<lock> <py> -m pytest tests/ --ignore=tests/integration --ignore=tests/test_architecture --cov=src --cov-report=term-missing --cov-fail-under=100 --tb=short
```

**On failure:** `INVOKE` @superpowers:systematic-debugging for a failing test; find the root cause before fixing. For a coverage gap, add tests for the lines `term-missing` lists.

## Step 5: Integration Tests

```bash
<lock> <py> -m pytest tests/integration --tb=short -v
```

## Step 6: Architecture Tests

```bash
<lock> <py> -m pytest tests/test_architecture --tb=short -v
```

## Step 7: Report Results

```
Preflight passed:
  - Lint, type check, translations: clean
  - Unit: X passed, coverage 100%
  - Integration: X passed
  - Architecture: X passed
```

If a check failed and could not be fixed, report which one and its errors. Do not continue to PR creation until every check passes.

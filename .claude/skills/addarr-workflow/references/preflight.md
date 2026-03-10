# Preflight Flow — Step Details

Sequence is defined in SKILL.md. This file provides implementation details per step.

Run sequentially. Stop on first failure. Fix automatically where possible, then re-run.

## Step 1: Tests

```bash
pytest --tb=short -q
```

**On failure:** `INVOKE` @superpowers:systematic-debugging — investigate root cause, fix, re-run. Do not proceed until all tests pass.

## Step 2: Flake8 Lint

```bash
flake8 .
```

**On failure:** Auto-fix formatting issues (line length, whitespace). Report logic-level lint issues that need manual review. Re-run after fixes.

## Step 3: Type Check

```bash
mypy src/
```

**On failure:** Fix type errors. Common fixes: add `Optional[]` for params with `None` default, add class-level annotations on singletons, use `isinstance(result, BaseException)` for asyncio.gather results. Re-run after fixes.

## Step 4: Translation Validation

```bash
PYTHONIOENCODING=utf-8 python run.py --validate-i18n
```

**On failure:** Report which translation files have problems and what keys are missing/malformed. Fix if possible, otherwise report.

## Step 5: Report Results

```
Preflight passed:
  - Tests: X passed
  - Flake8: clean
  - Type check: clean
  - Translations: valid
```

If any check failed and could not be fixed, report clearly which one and what the errors are. Do NOT proceed to PR creation until all required checks pass.

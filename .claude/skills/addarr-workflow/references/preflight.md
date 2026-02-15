# Preflight Checks

Run the same checks locally that CI runs on PRs. This catches issues before pushing.

## Checks

Run these sequentially, stopping on first failure:

### 1. Tests

```bash
pytest --tb=short -q
```

If failures found: report which tests failed and offer to investigate.

### 2. Flake8 Lint

```bash
flake8 .
```

If issues found: report them and offer to auto-fix (autopep8 for formatting, manual for logic).

### 3. Translation Validation

```bash
python run.py --validate-i18n
```

If issues found: report which translation files have problems and what keys are missing/malformed.

### 4. Docker Build Test

```bash
docker build -t addarr-test .
```

This is optional — skip if Docker is not available. Ask the user if they want to include it.

## Reporting

After all checks pass:
```
Preflight passed:
  - Tests: X passed
  - Flake8: clean
  - Translations: valid
  - Docker build: success (or skipped)
```

If any check fails, report clearly which one and what the errors are. Do NOT proceed to PR creation until all required checks pass.

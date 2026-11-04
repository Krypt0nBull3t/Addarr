## Summary

Fixes #

## Changes

-

## Checks

- [ ] Base branch is `development` (only release PRs from `development` target `main`)
- [ ] `pytest` passes and changed `src/` code has 100% coverage (CI: `--cov-fail-under=100`)
- [ ] `flake8 .` and `mypy src/` pass
- [ ] `python run.py --validate-i18n` passes; new keys are in the template and all 9 locale files
- [ ] A changed user-facing flow has an integration test in `tests/integration/`

## Notes

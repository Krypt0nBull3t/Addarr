---
name: release-readiness
description: Use when preparing a development-to-main merge or evaluating whether a release is safe to ship. Runs comprehensive quality, test, documentation, and safety checks beyond the standard preflight.
---

# Release Readiness

Gate for `development` -> `main` merges. Default stance: **NOT READY** unless all checks pass.

## Phase 1: Code Quality

Run `git fetch origin` first. The diffs below compare the remote branches, not stale local ones.

* [ ] **Bug review**: Run `addarr-find-bugs` on `git diff origin/main...origin/development` (this range overrides its Phase 1)
* [ ] **No debug artifacts**: No `TODO`, `FIXME`, `HACK` comments in changed files
* [ ] **No print statements**: No `print()` in `src/` (use `get_logger` from `src/utils/logger.py`)
* [ ] **No bare excepts**: No `except:` without specific exception types in `src/`

## Phase 2: Test Confidence

* [ ] **Preflight passes**: Run `/addarr check` (the addarr-workflow preflight, which runs the ci.yml lint, type, i18n, unit-with-100%-coverage, integration and architecture commands). Report a failure; do not fix it here.
* [ ] **Integration coverage**: `tests/integration/` has a flow test for every handler flow the release adds or changes

## Phase 3: Documentation & Metadata

* [ ] **Completion metadata**: All TASKS.md files for included issues have `**Completed:**`, `**Learnings:**`, `**Key Changes:**`, `**Notes:**` fields
* [ ] **Config template**: Any new config keys are present in `config_example.yaml`
* [ ] **Translation coverage**: New translation keys present in all locale files: `PYTHONIOENCODING=utf-8 python run.py --validate-i18n`
* [ ] **CLAUDE.md current**: Any new conventions, services, or patterns reflected in project CLAUDE.md

## Phase 4: Release Safety

* [ ] **CI green on development**: ci.yml runs on pull requests only, so check the last PR merged into `development`: `gh pr list --repo Krypt0nBull3t/Addarr --base development --state merged --limit 1 --json number,mergedAt`, then `gh pr checks <number> --repo Krypt0nBull3t/Addarr`. Its checks cover the 3.10-3.14 matrix and pip-audit, which no local check runs (pip-audit is `continue-on-error`, so read its result, not only the overall status).
* [ ] **Docker build**: `docker build -t addarr-test .` succeeds (the CI tag; `-t addarr` would overwrite the user's image)
* [ ] **No blocking issues**: `gh issue list --repo Krypt0nBull3t/Addarr --state open --label priority:critical`, and the same with `--label security`, list no open issues
* [ ] **Clean diff**: `git diff origin/main...origin/development --stat` shows only expected files changed

## Output

For each check: PASS or FAIL with specific details.

**Final verdict:** READY or NOT READY.

If NOT READY, list all failing checks with concrete next steps to resolve each.

Do not make changes — just report findings.

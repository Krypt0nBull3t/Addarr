---
name: release-readiness
description: Use when preparing a development-to-main merge or evaluating whether a release is safe to ship. Runs comprehensive quality, test, documentation, and safety checks beyond the standard preflight.
---

# Release Readiness

Gate for `development` -> `main` merges. Default stance: **NOT READY** unless all checks pass.

## Phase 1: Code Quality

* [ ] **Bug review** — Run `find-bugs` on full diff: `git diff main...development`
* [ ] **Simplification** — Run `simplify` on full diff
* [ ] **No debug artifacts** — No `TODO`, `FIXME`, `HACK` comments in changed files
* [ ] **No print statements** — No `print()` in `src/` (use `get_logger` from `src/utils/logger.py`)
* [ ] **No bare excepts** — No `except:` without specific exception types in `src/`

## Phase 2: Test Confidence

* [ ] **Full suite passes** — `pytest --tb=short -q`
* [ ] **Coverage threshold** — `pytest --cov=src --cov-report=term-missing` on changed modules
* [ ] **Architecture tests pass** — Both `tests/test_architecture/test_layer_boundaries.py` and `tests/test_architecture/test_conventions.py`
* [ ] **Integration tests** — `pytest tests/integration/ --tb=short -v` covers all modified handler flows

## Phase 3: Documentation & Metadata

* [ ] **Completion metadata** — All TASKS.md files for included issues have `**Completed:**`, `**Learnings:**`, `**Key Changes:**`, `**Notes:**` fields
* [ ] **Config template** — Any new config keys are present in `config_example.yaml`
* [ ] **Translation coverage** — New translation keys present in all locale files: `PYTHONIOENCODING=utf-8 python run.py --validate-i18n`
* [ ] **CLAUDE.md current** — Any new conventions, services, or patterns reflected in project CLAUDE.md

## Phase 4: Release Safety

* [ ] **Preflight passes** — Full preflight: pytest, flake8, mypy, i18n validation
* [ ] **Docker build** — `docker build -t addarr .` succeeds
* [ ] **No blocking issues** — Check for open issues tagged as blockers: `gh issue list --repo Krypt0nBull3t/Addarr --label blocker`
* [ ] **Clean diff** — `git diff main...development --stat` shows only expected files changed

## Output

For each check: PASS or FAIL with specific details.

**Final verdict:** READY or NOT READY.

If NOT READY, list all failing checks with concrete next steps to resolve each.

Do not make changes — just report findings.

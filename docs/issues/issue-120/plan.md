# Issue #120: Python Version Matrix Testing in CI

## Context

CI currently hardcodes Python 3.11 across all 7 jobs. Issue #100 (remove built-in deps) is resolved, so no `asyncio`/`dataclasses` conflicts remain in requirements.txt. The goal is to verify forward and backward compatibility across Python versions.

## Target Structure

Modify `.github/workflows/ci.yml` only. No source code changes expected unless compatibility issues surface.

## Design Decisions

### Which jobs get the matrix?

**Test jobs only**: unit-test, integration-test, architecture-test. These validate runtime behavior which can differ across Python versions.

**Single-version jobs stay on 3.11**: lint (flake8 output is version-independent), type-check (mypy targets source syntax, not runtime), validate-translations (string validation), security (pip-audit), docker-build (uses its own Python from the image).

### Version range

- **3.10** — oldest supported (drops 3.9 which is EOL)
- **3.11** — current baseline, matches Dockerfile
- **3.12** — stable
- **3.13** — stable
- **3.14** — latest stable (released Oct 2025)

### Matrix implementation

Use a top-level `strategy.matrix` on each test job. GitHub Actions doesn't support workflow-level matrix definitions, but we can keep it maintainable by using the same version list in all three test jobs.

### Artifact naming

Coverage report artifact name must include Python version to prevent collisions: `coverage-report-3.11`, `coverage-report-3.12`, etc.

### Coverage enforcement

`--cov-fail-under=100` runs on all matrix versions. If a version-specific code path exists, it must be covered.

## Approach

### Phase 1: Add matrix to test jobs

1. Add `strategy.matrix.python-version` to unit-test, integration-test, architecture-test jobs
2. Replace hardcoded `python-version: "3.11"` with `${{ matrix.python-version }}`
3. Update job names to include version: `Unit Tests (3.11)`
4. Fix coverage artifact name collision

### Phase 2: Validate

1. Run preflight checks locally (pytest, flake8, mypy, validate-i18n)
2. Push and verify CI matrix expands correctly

## Verification

- [ ] CI workflow is valid YAML
- [ ] Matrix expands to 5 versions for each test job (15 total test runs)
- [ ] Coverage artifacts don't collide
- [ ] Non-test jobs remain on 3.11
- [ ] All local checks pass

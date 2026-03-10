# Issue #120: Python Version Matrix Testing in CI

## Phase 1: Add Matrix Strategy

- [x] **1.1** Add matrix strategy to unit-test job
    - **File:** `.github/workflows/ci.yml` (unit-test job)
    - **Changes:**
        - Add `strategy.matrix.python-version: ["3.10", "3.11", "3.12", "3.13", "3.14"]`
        - Replace `python-version: "3.11"` with `python-version: ${{ matrix.python-version }}`
        - Update job display name to include version: `name: Unit Tests (${{ matrix.python-version }})`
        - Fix artifact name: `coverage-report` → `coverage-report-${{ matrix.python-version }}`
    - **Completed:** 2026-03-10
    - **Key Changes:** `.github/workflows/ci.yml` unit-test job — matrix strategy + dynamic artifact name
    - **Notes:** Artifact name must be unique per matrix run or upload-artifact will fail

- [x] **1.2** Add matrix strategy to integration-test job
    - **File:** `.github/workflows/ci.yml` (integration-test job)
    - **Changes:**
        - Add `strategy.matrix.python-version: ["3.10", "3.11", "3.12", "3.13", "3.14"]`
        - Replace `python-version: "3.11"` with `python-version: ${{ matrix.python-version }}`
        - Update job display name: `name: Integration Tests (${{ matrix.python-version }})`
    - **Completed:** 2026-03-10
    - **Key Changes:** `.github/workflows/ci.yml` integration-test job — matrix strategy

- [x] **1.3** Add matrix strategy to architecture-test job
    - **File:** `.github/workflows/ci.yml` (architecture-test job)
    - **Changes:**
        - Add `strategy.matrix.python-version: ["3.10", "3.11", "3.12", "3.13", "3.14"]`
        - Replace `python-version: "3.11"` with `python-version: ${{ matrix.python-version }}`
        - Update job display name: `name: Architecture Tests (${{ matrix.python-version }})`
    - **Completed:** 2026-03-10
    - **Key Changes:** `.github/workflows/ci.yml` architecture-test job — matrix strategy

- [x] **1.4** Update docker-build needs to reference matrix jobs correctly
    - **Context:** `needs: [unit-test, integration-test, architecture-test]` — GitHub Actions automatically waits for all matrix combinations, no changes needed
    - **Completed:** 2026-03-10
    - **Learnings:** GitHub Actions `needs` on a matrix job waits for all matrix combinations by default
    - **Key Changes:** No changes needed — verified existing `needs` works with matrix jobs

## Phase 2: Validation

- [x] **2.1** Run local preflight checks
    - Run: `pytest --tb=short -q`, `flake8 .`, `mypy src/`, `python run.py --validate-i18n`
    - All must pass
    - **Completed:** 2026-03-10
    - **Learnings:** CI-only changes don't affect local checks — all 1869 tests pass
    - **Key Changes:** No additional changes needed — all checks green

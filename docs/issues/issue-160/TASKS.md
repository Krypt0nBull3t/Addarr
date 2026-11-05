# Issue #160: Optimize CI Matrix — Tasks

## Phase 1: CI Workflow Restructure

- [x] **1.1** Pin primary test jobs to Python 3.11 only
    - Remove `strategy.matrix` from `unit-test`, `integration-test`, `architecture-test`
    - Pin `python-version: "3.11"` directly in each job
    - Update job `name` fields to remove `(${{ matrix.python-version }})` suffix
    - Update coverage artifact name to remove version suffix
    - **Test**: Validate YAML syntax with a dry-run or linter
    - **Completed:** 2026-03-10
    - **Learnings:** Straightforward removal of strategy blocks and matrix references
    - **Key Changes:** Removed matrix strategy from 3 jobs, pinned to 3.11, simplified artifact name
    - **Notes:** N/A

- [x] **1.2** Add compatibility job
    - New `compatibility` job with `strategy.matrix.python-version: ["3.10", "3.14"]`
    - Runs all tests in one `pytest` invocation: `pytest tests/ --tb=short -v`
    - No coverage, no artifact upload — just pass/fail
    - Job name: `Compatibility (${{ matrix.python-version }})`
    - **Test**: Validate YAML syntax
    - **Completed:** 2026-03-10
    - **Learnings:** Single pytest invocation runs unit + integration + architecture together cleanly
    - **Key Changes:** Added `compatibility` job between architecture-test and security
    - **Notes:** N/A

- [x] **1.3** Update docker-build dependencies
    - Change `needs` to `[unit-test, integration-test, architecture-test, compatibility]`
    - **Test**: Validate YAML syntax, confirm dependency graph is correct
    - **Completed:** 2026-03-10
    - **Learnings:** N/A
    - **Key Changes:** Added `compatibility` to docker-build needs array
    - **Notes:** N/A

## Verification

- [x] **2.1** Final validation
    - Confirm total job count is 10 (lint, type-check, translations, security, unit-test, integration-test, architecture-test, 2× compatibility, docker-build)
    - Verify YAML is valid
    - Review the complete diff for correctness
    - **Completed:** 2026-03-10
    - **Learnings:** N/A
    - **Key Changes:** YAML validated with Python yaml.safe_load
    - **Notes:** Job count: 10 (4 standalone + 3 primary tests + 2 compat + 1 docker-build)

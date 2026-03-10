# Issue #160: Optimize CI Matrix

## Context

The CI pipeline runs 20 jobs (15 from a 5×3 Python version matrix + 5 standalone). This is close to GitHub's concurrent job limit and slow due to repeated setup overhead across every job.

## Current State

- **unit-test**: 5 jobs (3.10–3.14), each with coverage + artifact upload
- **integration-test**: 5 jobs (3.10–3.14)
- **architecture-test**: 5 jobs (3.10–3.14)
- **Standalone**: lint, type-check, validate-translations, security (all on 3.11)
- **docker-build**: gates on all 3 test matrices passing

## Target State

- **Primary tests on 3.11 only**: unit-test (with coverage), integration-test, architecture-test
- **Compatibility matrix on boundary versions**: 3.10 + 3.14, running all tests in a single job per version
- **Standalone jobs**: unchanged
- **docker-build**: gates on primary tests + compatibility

**Result**: 20 jobs → 10 jobs. ~50% reduction.

## Design Decisions

1. **3.11 as primary**: Matches all standalone jobs, is the project's target runtime and Docker image version.
2. **Boundary versions only for compat**: 3.10 (oldest supported) and 3.14 (newest) catch version-specific issues. Middle versions (3.12, 3.13) rarely surface unique problems.
3. **Combined compat job**: Runs unit + integration + architecture tests together. No coverage or artifact upload — just pass/fail compatibility check.
4. **Coverage only on primary**: Upload coverage artifact only from 3.11 unit-test job. Avoids 5× redundant artifacts.

## Single File Change

Only `.github/workflows/ci.yml` is modified. No source code changes.

## Changes

### 1. Remove matrix from unit-test, integration-test, architecture-test

Pin each to `python-version: "3.11"`. Remove `matrix` strategy. Update job names to remove version suffix.

### 2. Add compatibility job

New `compatibility` job with matrix `[3.10, 3.14]`. Runs all tests in one pytest invocation (no coverage, no artifacts). Depends on nothing (runs in parallel with primary tests).

### 3. Update docker-build dependencies

Change `needs` to include `compatibility` alongside the 3 primary test jobs.

### 4. Update coverage artifact name

Remove version suffix from artifact name since there's only one now.

## Verification

- [ ] CI passes on the PR itself (meta-verification)
- [ ] Job count is ~10
- [ ] Coverage artifact uploads from unit-test (3.11)
- [ ] Compatibility runs on 3.10 and 3.14
- [ ] docker-build gates on all test jobs

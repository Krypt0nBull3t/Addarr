---
title: "Turn on CodeQL and Dependabot alerts; fix auto-approve and release"
labels: [ops, security, github_actions, priority:high]
slice: 13
findings: [F160, F161, F162, F163, F164, F165]
---
## Problem

- **F160** The CodeQL workflow is `disabled_inactivity` (main has no commits since 2026-03-02). The last run was on 2026-08-25. PRs get no scan.
- **F161** Dependabot security alerts are disabled. Version updates still run.
- **F162** auto-approve calls `createReview` without `commit_id`. A commit pushed during the wait gets the approval.
- **F163** There is no version bump (`__version__ = "0.8"`), and changelog.yaml was deleted. development changes defaults without release notes: chatMode `private_only` refuses groups, and `onlyAdmin` is now enforced.
- **F164** .gitignore has no `.env` pattern. There is no PR template, no issue templates and no CODEOWNERS (harness-audit 24/39).
- **F165** The CI compatibility matrix runs 3.10, 3.12, 3.13 and 3.14. The issue-160 plan decided on 3.10 and 3.14 only.

## Expected behavior

CodeQL scans every PR. Dependabot security alerts are on. An approval applies only to the commit that CI checked. Release 0.9.0 has a version, a tag and GitHub Release notes that name the changed defaults. There is no changelog file. The repo ignores `.env` and has a PR template, issue templates and CODEOWNERS. The issue-160 docs record why the CI matrix runs four versions.

## Fix

- [ ] **F160** Re-enable the workflow in repo settings; release to main more often (`.github/workflows/codeql-analysis.yml`)
- [ ] **F161** Enable Dependabot security alerts (repo settings)
- [ ] **F162** Pass `commit_id: context.payload.workflow_run.head_sha` to `createReview` (`.github/workflows/auto-approve.yml:431`)
- [ ] **F163** Bump `__version__` to `0.9.0` and tag it `v0.9.0`. Write the release notes in the GitHub Release. They name the behavior changes: chatMode `private_only` refuses groups, and `onlyAdmin` is now enforced. Add no changelog file (`src/__init__.py:12`; `src/bot/handlers/auth.py:41`; `src/utils/helpers.py:84`)
- [ ] **F164** Add a `.env` pattern, a PR template, issue templates and CODEOWNERS (`.gitignore`, `.github/`)
- [ ] **F165** Keep the 4-version matrix. Add one line to `docs/issues/issue-160/plan.md` that records why it changed from 3.10 and 3.14 (`.github/workflows/ci.yml:133` stays as is)

## Acceptance criteria

- **F160** `gh api repos/Krypt0nBull3t/Addarr/actions/workflows` shows `.github/workflows/codeql-analysis.yml` as `active` (now `disabled_inactivity`). The next PR gets a CodeQL check.
- **F161** `gh api repos/Krypt0nBull3t/Addarr/vulnerability-alerts -i` returns `204` (now `404`).
- **F162** The `createReview` call passes `commit_id` from `workflow_run.head_sha`. When a commit lands during the wait, the approval stays on the checked commit, not on the new head.
- **F163** `src/__init__.py` has `__version__ = "0.9.0"`. The tag `v0.9.0` exists. Its GitHub Release notes name the `private_only` chatMode default and the enforced `onlyAdmin`. The repo has no changelog file.
- **F164** `.gitignore` ignores `.env`. `.github/` has a PR template, issue templates and CODEOWNERS.
- **F165** The `ci.yml` matrix still runs 3.10, 3.12, 3.13 and 3.14. `docs/issues/issue-160/plan.md` has one line that says why.
- `pytest`, `flake8` and `mypy src/` pass.

## Notes

- Source: audit 2026-10-28, docs/issues/audit-2026-10-28/FINDINGS.md (F-ids F160, F161, F162, F163, F164, F165).
- Priority: max P 30, sum P 124 (high).
- Order: do slices 1-8 first. CodeQL turns itself off again while main gets no commits, so F160 depends on the F163 release cadence.
- F160 and F161 are repo settings: only the owner can change them.
- Decided 2026-10-28: F163 bump to 0.9.0, tag it, release notes in the GitHub Release (with the chatMode `private_only` and `onlyAdmin` changes). No changelog file.
- Decided 2026-10-28: F165 keep the 4-version CI matrix; add one line to docs/issues/issue-160 that records why it changed.

---
title: "Correct stale Key Changes and metadata in docs/issues"
labels: [documentation, priority:low, agent-ready]
slice: 32
findings: [F300]
---

## Problem

**F300** Completed task notes in `docs/issues/` name code that was later removed or moved:

- `SabnzbdClient`: issue-12, issue-20, issue-101
- `JobScheduler`: issue-78, issue-118
- `_format_speed`/`_format_size`: issue-102
- `RateLimitExceededError`: issue-116
- `HANDLER_PATCHES`: issue-80
- `_format_bytes` in `system.py`: issue-108
- `tests/test_services/test_media.py`: issue-105

issue-123 has unchecked boxes. The feature/test-suite tasks lack `Completed` metadata.

## Expected behavior

Task notes point to code that exists, or say what replaced it. Done tasks carry the completion metadata that CLAUDE.md requires.

## Fix

- [ ] **F300** Add "Superseded by 0846b97" notes next to removed code and fix moved paths. Resolve the unchecked boxes in issue-123. Add `Completed` metadata to the feature/test-suite tasks (`docs/issues/issue-20/TASKS.md:41-43`, `:76`; `issue-12/TASKS.md:34`; `issue-101/TASKS.md:28`; `issue-78/TASKS.md:32-34`, `:140`; `issue-118/TASKS.md:63`; `issue-102/TASKS.md:42-43`; `issue-116/TASKS.md:27-65`; `issue-80/TASKS.md:139`; `issue-108/TASKS.md:52`, `:58`; `issue-105/TASKS.md:59-74`; `issue-123/TASKS.md:68-69`; `docs/issues/feature/test-suite/tasks.md`)

## Acceptance criteria

- [ ] Each symbol and path named at the listed lines either exists in `src/` or `tests/`, or has a "Superseded by 0846b97" note (or the corrected path) beside it.
- [ ] `docs/issues/issue-123/TASKS.md` has no unchecked box without a note.
- [ ] Every task in `docs/issues/feature/test-suite/tasks.md` has a `Completed` line.
- [ ] No source change. `pytest`, `flake8` and `mypy src/` pass.

## Notes

- Source: audit 2026-10-28, docs/issues/audit-2026-10-28/FINDINGS.md (F-ids F300).
- Priority: max P 10, sum P 10, `priority:low`.
- 0846b97 is "refactor: remove dead code, unused dependencies and stale files".
- Related open issues: none.

# Issue 227: Correct stale Key Changes and metadata in docs/issues

**Issue:** https://github.com/Krypt0nBull3t/Addarr/issues/227 (audit finding F300)
**Branch:** `refactor/227-correct-stale-key-changes-and-metadata`

## Context

Completed task notes in `docs/issues/` name code that was later removed or moved. Commit
`0846b97` ("refactor: remove dead code, unused dependencies and stale files") removed
some of it. Other code moved in other commits, and some names were wrong from the start.
Done tasks must carry completion metadata (CLAUDE.md § Planning & Task Conventions), and
`docs/issues/feature/test-suite/tasks.md` has none.

Docs only. No change in `src/`, `tests/` or config. Scope is fixed by the orchestrator's answer at step 3c:
edit only the files and lines the issue lists. Other `plan.md` files that name the same
symbols stay as they are. Other lines in the same TASKS.md files that also name the symbols
(for example `issue-20/TASKS.md:112`) stay as they are, and the PR body lists them.

## Findings (verified against git history and the tree at `80943da`)

| Symbol or path in the notes | State now | Evidence | Fix |
|-|-|-|-|
| `SabnzbdClient`, `src/api/sabnzbd.py`, its API tests | Removed | `0846b97` deleted `src/api/sabnzbd.py` and `tests/test_api/test_sabnzbd_api.py` | "Superseded by 0846b97" |
| `JobScheduler`, `src/services/scheduler.py`, `test_scheduler.py` | Removed | `0846b97` | "Superseded by 0846b97" |
| `RateLimitExceededError` in `src/utils/error_handler.py` | Removed | `0846b97` (82 lines of `error_handler.py`) | "Superseded by 0846b97" |
| `_format_speed`, `_format_size` in `TransmissionService` | Removed, replaced by `src.utils.helpers.format_bytes` | `e67a981` (2026-03-06). `_format_eta` still exists. | Moved note citing `e67a981`. Not 0846b97. |
| `_format_bytes` in `src/bot/handlers/system.py` | Replaced by `src.utils.helpers.format_bytes` | `1498e48` (2026-03-09) | Moved note citing `1498e48`. Not 0846b97. |
| `HANDLER_PATCHES` dict in `tests/test_main.py` | Never existed under that name. The helper is `_make_handler_patches()`. | `git log -S` finds no `HANDLER_PATCHES` in `src` or `tests`. `_make_handler_patches` was added in `727333f`. | Corrected name |
| `tests/test_services/test_media.py` | Never existed. The file is `tests/test_services/test_media_service.py`. | Added in `f925e8b` (2026-02-15) | Corrected path |
| issue-123 unchecked boxes `flake8 .` and `mypy src/` | Both pass on `80943da` | Run under the suite lock: flake8 exit 0, mypy "no issues found in 72 source files" | Tick both, with a note on what was re-checked |
| `feature/test-suite/tasks.md` Tasks 1-14 | All done, no `Completed` line | Implementation commits, all dated 2026-02-15 (see below) | Add a `Completed` line per task |

## Note wording

Use these exact forms so the notes read the same everywhere.

- Removed: append ` (Superseded by 0846b97: <thing> removed.)` to the line.
- Moved or replaced by another commit: append ` (Replaced in <sha>: now <new name>.)`.
- Wrong name or path from the start: change the name in place, then append ` (Corrected: was <old>.)`.

Notes are plain text. No Learnings are invented. A task gets only the fields git history proves.

## Edits

Line numbers are from `80943da`. Re-grep before each edit, because earlier edits do not shift lines when notes are appended inline.

| File | Lines | Edit |
|-|-|-|
| `issue-12/TASKS.md` | 34 | Removed note: `SabnzbdClient.set_speed_limit` in `src/api/sabnzbd.py` |
| `issue-20/TASKS.md` | 41, 42, 43, 76 | Removed note on each: `SabnzbdClient`, `src/api/sabnzbd.py`, `tests/test_api/test_sabnzbd_api.py` |
| `issue-101/TASKS.md` | 28 | Removed note: `pause_item`/`resume_item` in `src/api/sabnzbd.py` |
| `issue-78/TASKS.md` | 32, 33, 34, 140 | Removed note: `scheduler.py`, `test_scheduler.py`, `JobScheduler._instance` in conftest, the `JobScheduler` export |
| `issue-118/TASKS.md` | 63 | Removed note after `JobScheduler` in the list of six singletons |
| `issue-102/TASKS.md` | 42, 43 | Replaced note (`e67a981`): `_format_speed` and `_format_size` are gone, `_format_eta` remains |
| `issue-116/TASKS.md` | 27, 31, 41, 51, 65 | Removed note after each `RateLimitExceededError` |
| `issue-80/TASKS.md` | 139 | Corrected name: `_make_handler_patches()` in `tests/test_main.py` |
| `issue-108/TASKS.md` | 52, 58 | Replaced note (`1498e48`): `_format_bytes` is `src.utils.helpers.format_bytes` |
| `issue-105/TASKS.md` | 59, 62, 74 | Corrected path: `tests/test_services/test_media_service.py` |
| `issue-123/TASKS.md` | 68, 69 | Tick both boxes. Append ` (re-checked 2026-11-04 on 80943da: passes)`. |
| `feature/test-suite/tasks.md` | end of each Task 1-14 section | Add `**Completed:** 2026-02-15 (<sha>)` |

### Completed lines for `feature/test-suite/tasks.md`

Dates come from the implementing commits (all 2026-02-15).

| Task | Commit |
|-|-|
| 1 Test infrastructure | `4753d12` |
| 2 Root conftest | `41d8e0d` |
| 3 Fixtures | `e84c2e5` |
| 4 Smoke test, models | `605580d` |
| 5 Bot structure tests | `fa19957` |
| 6 Utility tests | `6afcb51` |
| 7 API tests, Radarr | `7bb1b78` (shared with 8) |
| 8 Remaining API tests | `7bb1b78` (shared with 7) |
| 9 Service tests | `f925e8b` |
| 10 Handler tests | `ae74f02` |
| 11 Config and translation tests | `0e3db27` (config), `6afcb51` (translation validation) |
| 12 CI integration | `5890147` |
| 13 Testing skill | `e8ded38` |
| 14 TDD in workflow | `421e82b` |

## Verification

1. A throwaway script in the scratchpad (not committed) reads the edited lines and checks that
   each `src/` or `tests/` path, and each symbol, at those lines either exists or has a
   note on the same line. Run it before and after: before it lists the misses, after it is empty.
2. `grep -c "\[ \]" docs/issues/issue-123/TASKS.md` is 0.
3. Every `## Task N` section in `docs/issues/feature/test-suite/tasks.md` has a `**Completed:**` line.
4. `git diff --stat` shows only files under `docs/issues/`.
5. `<lock> .venv/bin/python -m flake8 .` and `<lock> .venv/bin/python -m mypy src/` pass.
6. `<lock> .venv/bin/python -m pytest tests/test_architecture --tb=short -v` passes. It
   holds the docs-drift checks.
7. The full preflight (including the 100% coverage gate) runs at the create-pr step.

## Risks

- A listed line number can be off because the audit used older numbering. Mitigation: grep
  the symbol in each file and edit the line that names it. Report any line in the issue's list
  that no longer names the symbol.
- Notes make long lines longer. Markdown only, no lint on it.

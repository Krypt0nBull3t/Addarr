# Document the rate-limit convention and fill TASKS.md metadata gaps (#276) Implementation Plan

**Goal:** CLAUDE.md states the rate-limit convention; every ticked task in the issue-97, 105, 120, 123, 127 and 222 TASKS.md files has its completion metadata; issue-222 task 2.1 is ticked.

**Architecture:** Docs only. No change in `src/`, config, i18n or Docker. One approach exists, so there is no `design.md`. Dates and Key Changes come from git history. Learnings and Notes come from a task commit message only when it states one; otherwise the value is `None recorded`. Nothing is invented.

**Tech Stack:** Markdown. Checked by `tests/test_architecture/test_repo_docs.py` and the preflight.

## Global Constraints

- No source change. `pytest`, `flake8` and `mypy src/` pass.
- Metadata fields, in this order, as sub-bullets of the task: `**Completed:**`, `**Learnings:**`, `**Key Changes:**`, `**Notes:**` (CLAUDE.md § Planning & Task Conventions).
- Do not change task content that already exists. Add only missing fields; keep field order.
- Every repo path in CLAUDE.md that the new bullet names must exist (`test_repo_docs.py`).
- The facts in the new bullet come from `src/services/rate_limit.py`, `config_example.yaml` (`rateLimit`) and the call sites listed below. They are not copied from the issue text.

## Findings from the audit (git history, 2026-11-05)

Fields missing per ticked task (C = Completed, L = Learnings, K = Key Changes, N = Notes):

| Task | Missing | Source commit (date) |
|-|-|-|
| 97 / 1.1 | C L K N | `c8d4d02` (2026-03-04) |
| 105 / 1.1 | C L K N | `3afa7de` (2026-03-03) |
| 105 / 1.2 | C L K N | `32b2d11` (2026-03-03) |
| 120 / 1.1 | L | already has C, K, N |
| 120 / 1.2 | L N | already has C, K |
| 120 / 1.3 | L N | already has C, K |
| 120 / 1.4 | N | already has C, L, K |
| 120 / 2.1 | N | already has C, L, K |
| 127 / 3.1 | N | already has C, L, K |
| 222 / 2.1 | tick + C L K N | PR #257, merged 2026-11-05 |

- `issue-123/TASKS.md` already has all four fields on both tasks. No edit needed.
- `issue-97` 2.1, 3.1, 4.1 and `issue-105` 2.1, 3.1, 4.1 are complete already.
- Out of scope: the unticked checklist in `docs/issues/issue-120/plan.md` (lines 55-59). It is a plan checklist, not a task, and the issue names TASKS.md only.

Rate-limit facts for the bullet:

- `src/services/rate_limit.py`: `RateLimitService` (singleton, per-user sliding window per category), `enforce_rate_limit(update, category)` (counts one call, replies with the wait time, returns `False` when over the limit), `rate_limit(category)` (decorator that calls `enforce_rate_limit` first).
- Categories: `search`, `modify`, `auth`. Limits live under `rateLimit` in `config.yaml`; `rateLimit.enable` is off by default; `auth` is always limited.
- `@rate_limit("search")`: search entry points in `src/bot/handlers/media/handler.py` (`handle_movie`, `handle_series`, `handle_music`, `handle_search`) and `src/bot/handlers/library.py`.
- `enforce_rate_limit(update, "modify")`: placed just before each add request in `handler.py`, `season_picker.py` and `album_picker.py`, not as a decorator on picker or toggle callbacks, so taps that change no state do not use up the budget.
- The rationale already exists in `.claude/skills/addarr-handlers/references/anti-patterns.md` ("Rate-Limiting Picker Taps Instead of the Add"). The bullet links to it by path.

## File Structure

- Modify: `CLAUDE.md` (one bullet in `### Key Patterns`, after the authentication bullet)
- Modify: `docs/issues/issue-97/TASKS.md`, `issue-105/TASKS.md`, `issue-120/TASKS.md`, `issue-127/TASKS.md`, `issue-222/TASKS.md`
- Create: this plan and `TASKS.md` in `docs/issues/issue-276/`

## Phase 1: CLAUDE.md rate-limit bullet

### Task 1.1: Add the rate-limit bullet

**Files:** Modify `CLAUDE.md` (Key Patterns, after `**Authentication decorator**`). Test: `tests/test_architecture/test_repo_docs.py`.

- [ ] **Step 1: Write the bullet.** One bullet, at most 4 sentences, ASCII only. It must name `src/services/rate_limit.py`, `@rate_limit`, `enforce_rate_limit`, the categories, that search entry points use `@rate_limit("search")`, and that each add request is guarded by `enforce_rate_limit(update, "modify")` placed just before the request instead of a decorator on picker or toggle callbacks. Name `.claude/skills/addarr-handlers/references/anti-patterns.md` for the reason.
- [ ] **Step 2: Verify.** Run `<lock> .venv/bin/python -m pytest tests/test_architecture --tb=short -v`. Expected: all pass.
- [ ] **Step 3: Check the claim is true.** `rate_limit.py` defines `rate_limit` and `enforce_rate_limit`; the call sites above exist. Run `git grep -n -E '@rate_limit\(|enforce_rate_limit\(update' -- src` and compare.
- [ ] **Step 4: Commit** `docs: describe the rate-limit convention in CLAUDE.md (task 1.1, #276)`. Stage `CLAUDE.md` and `docs/issues/issue-276/TASKS.md`; check `git diff --cached`.

## Phase 2: Fill completion metadata

### Task 2.1: issue-97 and issue-105

**Files:** Modify `docs/issues/issue-97/TASKS.md` (task 1.1), `docs/issues/issue-105/TASKS.md` (tasks 1.1, 1.2).

- [ ] **Step 1: Read each commit.** `git show --stat` and the message of `c8d4d02`, `3afa7de`, `32b2d11`. Key Changes list the files and functions the commit changed (for 97 / 1.1: the new `src/bot/handlers/media/` package with `dispatch.py`, `handler.py` moved from `media.py`, new `tests/test_handlers/test_media_package.py`; for 105 / 1.1: `get_missing`, `get_cutoff_unmet`, `search_command` on `RadarrClient`, sample data, tests; for 105 / 1.2: the same three methods on `SonarrClient`).
- [ ] **Step 2: Add the four fields under each task**, after the existing `**Success:**` line. `Completed` is the commit date (97 / 1.1: 2026-03-04; 105 / 1.1 and 1.2: 2026-03-03). `Learnings` and `Notes` are `None recorded` unless the commit message states a reason or gotcha; then quote one sentence.
- [ ] **Step 3: Verify.** Each of the three tasks has all four fields. Run `<lock> .venv/bin/python -m pytest tests/test_architecture --tb=short -v`.
- [ ] **Step 4: Commit** `docs: add completion metadata to issue-97 and issue-105 tasks (task 2.1, #276)`.

### Task 2.2: issue-120 and issue-127

**Files:** Modify `docs/issues/issue-120/TASKS.md` (1.1 Learnings; 1.2, 1.3 Learnings and Notes; 1.4 and 2.1 Notes), `docs/issues/issue-127/TASKS.md` (3.1 Notes).

- [ ] **Step 1: Read the commits.** `03d1497` for issue-120 (2026-03-10); `6558d2f` and merge `f49577d` for issue-127 (2026-03-03).
- [ ] **Step 2: Add only the missing fields**, keeping the order. The value is `None recorded` unless the existing task text or the commit message states one. Do not copy a Learning from a neighbour task.
- [ ] **Step 3: Verify.** Each listed task now has all four fields. Run the architecture tests.
- [ ] **Step 4: Commit** `docs: fill missing completion fields in issue-120 and issue-127 tasks (task 2.2, #276)`.

### Task 2.3: issue-222 task 2.1

**Files:** Modify `docs/issues/issue-222/TASKS.md` (task 2.1, line 106).

- [ ] **Step 1: Tick** `- [ ] **2.1** Preflight` to `- [x]`.
- [ ] **Step 2: Add the four fields.** `Completed: 2026-11-05` (PR #257 merged 2026-11-05). `Learnings: None recorded`. `Key Changes: None (verification only; PR #257 carries tasks 1.1 to 1.4)`. `Notes: None recorded`. Check the PR's CI result with `gh pr view 257 --repo Krypt0nBull3t/Addarr --json statusCheckRollup` before you write that the preflight passed.
- [ ] **Step 3: Verify and commit.** Architecture tests pass. Commit `docs: tick issue-222 task 2.1 and add its metadata (task 2.3, #276)`.

## Phase 3: Verify

### Task 3.1: Acceptance check and preflight

- [ ] **Step 1: Acceptance check.** For each of the six TASKS.md files, every `- [x] **N.N**` task has `Completed:`, `Learnings:`, `Key Changes:` and `Notes:` before the next task heading. Use a throwaway script in the scratchpad, not in the repo. Expected: no gaps.
- [ ] **Step 2: No source change.** `git diff --stat origin/development` lists only `CLAUDE.md` and files under `docs/issues/`.
- [ ] **Step 3: Preflight.** Run `/addarr pr` (create-pr flow, which runs the preflight with the coverage gate).

## Review Focus

- A fabricated Learning: the plan forbids one; the acceptance check cannot catch it, so the reviewer reads each new Learnings line against its commit.
- A wrong date: each `Completed` date must match the commit date in the table above.
- A CLAUDE.md claim that does not match the code: Step 3 of Task 1.1 compares it with the call sites.

# Issue #276: Document the rate-limit convention and fill TASKS.md metadata gaps

Docs only. No change in `src/`. See `plan.md` for the audit table and the rules for Learnings and Notes.

**Gap check (RED for Phase 2 and 3):** a throwaway script lists ticked tasks that lack a field. It lives in the scratchpad, not in the repo: `.venv/bin/python -I /tmp/claude-1000/-home-mark--ao-data-worktrees-addarr-addarr-34/0e5067b8-cfe1-5d11-afd4-b11de482d96d/scratchpad/check_meta.py`. At the start it prints `gaps: 10`; the goal is `gaps: 0`.

### Phase 1: CLAUDE.md rate-limit bullet (1 task)

**Goal:** CLAUDE.md states the rate-limit convention that #203 added.

- [x] **1.1** Add the rate-limit bullet to Key Patterns
    - **Context:**
        - **Why:** The release readiness check for 0.9.0 (PR #273) found that CLAUDE.md does not describe `@rate_limit("search")` on search handlers and `enforce_rate_limit(update, "modify")` before each add request.
        - **Architecture:** One bullet in `### Key Patterns` of `CLAUDE.md`, after `**Authentication decorator**`. Same style as its neighbours: bold lead term, then facts.
        - **Key refs:** `src/services/rate_limit.py` (`RateLimitService`, `enforce_rate_limit` L113, `rate_limit` L149), `config_example.yaml` (`rateLimit`), `.claude/skills/addarr-handlers/references/anti-patterns.md` ("Rate-Limiting Picker Taps Instead of the Add"), call sites from `git grep -n -E '@rate_limit\(|enforce_rate_limit\(update' -- src`
        - **Watch out:** `tests/test_architecture/test_repo_docs.py` checks every repo path CLAUDE.md names, so a wrong path fails it. Categories are `search`, `modify`, `auth`; `rateLimit.enable` is off by default but `auth` is always limited. Do not copy the issue text; check each claim against the code.
    - **Scope:** One bullet, at most 4 sentences
    - **Touches:** `CLAUDE.md`
    - **Action items:**
        - [RED] Confirm `git grep -n -F 'enforce_rate_limit' CLAUDE.md` finds nothing (the gap exists)
        - [GREEN] Write the bullet naming `src/services/rate_limit.py`, `@rate_limit`, `enforce_rate_limit`, the three categories, `@rate_limit("search")` on search entry points, and `enforce_rate_limit(update, "modify")` just before each add request instead of a decorator on picker or toggle callbacks, with the pointer to `anti-patterns.md`
        - [GREEN] Compare each claim with the call sites
    - **Success:** `<lock> .venv/bin/python -m pytest tests/test_architecture --tb=short -v` passes; CLAUDE.md names `@rate_limit`, `enforce_rate_limit` and `src/services/rate_limit.py`
    - **Completed:** 2026-11-05
    - **Learnings:**
        - The reason for the `modify` placement already lived in `.claude/skills/addarr-handlers/references/anti-patterns.md`, so the bullet points to it instead of repeating it
        - `delete.py` and `calendar.py` guard with `@rate_limit("modify")` as a decorator; the bullet states the add-request rule only, as the issue asks
    - **Key Changes:**
        - Added the `**Rate limiting**` bullet to `CLAUDE.md` Key Patterns
    - **Notes:** `tests/test_architecture` passes (158 tests)

### Phase 2: Fill completion metadata (3 tasks)

**Goal:** Every ticked task in the six TASKS.md files has `Completed`, `Learnings`, `Key Changes` and `Notes`, and issue-222 task 2.1 is ticked.

**Phase Context:**

- Why NOT invent Learnings: the developer ruled that history gives the facts. `None recorded` where history gives none. A commit message may supply one real sentence; quote it.
- Why NOT edit `issue-123/TASKS.md`: both tasks already have all four fields. Say so in the PR body.
- Out of scope: unticked boxes in `docs/issues/issue-120/plan.md` (a plan checklist, not tasks).

- [x] **2.1** issue-97 task 1.1, issue-105 tasks 1.1 and 1.2
    - **Context:**
        - **Why:** These three ticked tasks have none of the four fields.
        - **Architecture:** Add the fields as sub-bullets after the task's `**Success:**` line, in the order `Completed`, `Learnings`, `Key Changes`, `Notes`, in the style of issue-97 task 2.1.
        - **Key refs:** commits `c8d4d02` (97 / 1.1, 2026-03-04), `3afa7de` (105 / 1.1, 2026-03-03), `32b2d11` (105 / 1.2, 2026-03-03); `git show --stat` and the message of each
        - **Watch out:** `3afa7de` and `c8d4d02` also add the TASKS.md and plan.md files, so the stat lists them: leave them out of Key Changes. Use the commit date, not today's date.
    - **Scope:** Three tasks, twelve fields
    - **Touches:** `docs/issues/issue-97/TASKS.md`, `docs/issues/issue-105/TASKS.md`
    - **Action items:**
        - [RED] Run the gap check; it lists these three tasks
        - [GREEN] Read the three commits; write Completed (dates above) and Key Changes from the stat (files and functions)
        - [GREEN] Write Learnings and Notes: `None recorded`, or one quoted sentence when the commit message states a reason or gotcha
    - **Success:** The gap check no longer lists these three tasks; architecture tests pass
    - **Completed:** 2026-11-05
    - **Learnings:**
        - Only `c8d4d02` states a gotcha in its message (the recursive `_get_python_files()`); the 105 commits state none, so those Learnings read `None recorded`
    - **Key Changes:**
        - `docs/issues/issue-97/TASKS.md`: task 1.1 gets all four fields
        - `docs/issues/issue-105/TASKS.md`: tasks 1.1 and 1.2 get all four fields
    - **Notes:** The gap check dropped from 10 to 7. `3afa7de` also added the Sonarr sample data, so the 105 / 1.1 Notes say so

- [ ] **2.2** issue-120 tasks 1.1 to 1.4 and 2.1, issue-127 task 3.1
    - **Context:**
        - **Why:** These tasks have some fields but lack Learnings (120: 1.1, 1.2, 1.3) or Notes (120: 1.2, 1.3, 1.4, 2.1; 127: 3.1).
        - **Architecture:** Add only the missing field, in its place in the field order. Do not edit existing fields.
        - **Key refs:** commit `03d1497` (issue-120, 2026-03-10); `6558d2f` and merge `f49577d` (issue-127, 2026-03-03)
        - **Watch out:** Do not copy a Learning from a neighbour task. The CI-only change in 120 leaves most Learnings and Notes as `None recorded`.
    - **Scope:** Nine missing fields over six tasks
    - **Touches:** `docs/issues/issue-120/TASKS.md`, `docs/issues/issue-127/TASKS.md`
    - **Action items:**
        - [RED] Run the gap check; it lists these six tasks
        - [GREEN] Read the commits; add each missing field with `None recorded` or one quoted sentence
    - **Success:** The gap check no longer lists these six tasks; architecture tests pass

- [ ] **2.3** Tick issue-222 task 2.1
    - **Context:**
        - **Why:** The preflight task is done in PR #257 (merged 2026-11-05) but still `- [ ]`.
        - **Architecture:** Change the box and add the four fields below the task.
        - **Key refs:** `docs/issues/issue-222/TASKS.md` line 106; `gh pr view 257 --repo Krypt0nBull3t/Addarr --json statusCheckRollup,mergedAt`
        - **Watch out:** State that the preflight passed only after the check rollup shows it.
    - **Scope:** One task
    - **Touches:** `docs/issues/issue-222/TASKS.md`
    - **Action items:**
        - [RED] Run the gap check; it lists issue-222 task 2.1 as not ticked
        - [GREEN] Tick it; add `Completed: 2026-11-05`, `Learnings: None recorded`, `Key Changes: None (verification only; PR #257 carries tasks 1.1 to 1.4)`, `Notes: None recorded`
    - **Success:** The gap check prints `gaps: 0`; architecture tests pass

### Phase 3: Verify (1 task)

**Goal:** All CI checks pass locally before the PR.

- [ ] **3.1** Acceptance check and preflight
    - **Context:**
        - **Why:** CI requires lint, mypy, i18n, the 100% coverage gate, integration and architecture tests, and the issue says no source change.
        - **Architecture:** `/addarr pr` runs the review, then the preflight in `references/preflight.md`.
        - **Key refs:** `.claude/skills/addarr-workflow/references/preflight.md`
        - **Watch out:** Merge `origin/development` first. The PR body says `issue-123` needed no edit.
    - **Scope:** Run only, no new code
    - **Touches:** none
    - **Action items:**
        - [GREEN] Run the gap check (`gaps: 0`) and `git diff --stat origin/development` (only `CLAUDE.md` and files under `docs/issues/`)
        - [GREEN] Run the create-pr flow
    - **Success:** Every preflight step passes; no file under `src/` changed

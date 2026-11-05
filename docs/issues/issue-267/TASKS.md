# Issue 267: Tasks

Plan: `docs/issues/issue-267/plan.md`

### Phase 1: AGENTS.md for the automated PR reviewer (1 task)

**Goal:** Give the Codex PR reviewer its rules: read open threads and replies first, post each finding once.

- [x] **1.1** Add AGENTS.md, its docs checks and the CLAUDE.md pointer
    - **Context:**
        - **Why:** The reviewer runs as a Codex agent in the worker's checkout and reads `AGENTS.md`. The repo has none, so it posts findings again after a reasoned decline (3 identical threads on #255, 6 on #260).
        - **Architecture:** Docs only, no `src/` change. The docs-drift checks live in `tests/test_architecture/test_repo_docs.py` and cover only `CLAUDE.md` today. Extend them to `AGENTS.md`, or the acceptance item "every repo path in `AGENTS.md` exists" proves nothing.
        - **Key refs:** `tests/test_architecture/test_repo_docs.py` (`REPO_PATH`, `section()`, `test_claude_md_paths_exist`), `CLAUDE.md` § Agents.
        - **Watch out:** `section()` matches only `## heading` lines, so `AGENTS.md` needs a `## Reviewing a pull request` heading exactly. Keep `test_claude_md_paths_exist` under its name: `CLAUDE.md` may name tests, and `test_claude_md_test_names_exist` checks that. `AGENTS.md` must not copy `CLAUDE.md` rules; it points to them.
    - **Scope:** One new root file, one test file edit, one `CLAUDE.md` bullet.
    - **Touches:** `AGENTS.md` (new), `tests/test_architecture/test_repo_docs.py`, `CLAUDE.md`
    - **Action items:**
        - [RED] Extract the body of `test_claude_md_paths_exist` into a helper `missing_paths(rel_path)`; the test asserts `missing_paths("CLAUDE.md") == []`. Update the module docstring.
        - [RED] Write `test_agents_md_paths_exist`: `missing_paths("AGENTS.md") == []`.
        - [RED] Write `test_agents_md_has_reviewer_rules`: the `Reviewing a pull request` section holds `pulls/{number}/comments` and `CLAUDE.md`.
        - [RED] Write `test_claude_md_names_agents_md`: `AGENTS.md` appears in the `CLAUDE.md` `Agents` section.
        - [RED] Run `<lock> .venv/bin/python -m pytest tests/test_architecture/test_repo_docs.py -v`; the three new tests fail.
        - [GREEN] Create `AGENTS.md` with the five rules from `plan.md` (read threads first, no repeat of an open finding, re-post a declined finding only when the reason is wrong and say why, once per PR, check against `CLAUDE.md`).
        - [GREEN] Add one bullet to `CLAUDE.md` § Agents that names `AGENTS.md`.
    - **Success:** `<lock> .venv/bin/python -m pytest tests/test_architecture --tb=short -v` passes, flake8 clean, `AGENTS.md` under 25 lines.
    - **Completed:** 2026-11-05
    - **Learnings:**
        - The three new tests failed for the right reasons before the files existed: `FileNotFoundError` for `AGENTS.md` and a missing `AGENTS.md` mention in the `CLAUDE.md` Agents section.
        - `AGENTS.md` paths are checked with the same `REPO_PATH` regex as `CLAUDE.md`, so only code spans with a `src/`, `tests/`, `docs/`, `.github/` or `.claude/` prefix are verified. `CLAUDE.md` itself has no such prefix, so a test asserts its name.
    - **Key Changes:**
        - Created `AGENTS.md` (12 lines, five reviewer rules, points to `CLAUDE.md`).
        - `tests/test_architecture/test_repo_docs.py`: new helper `missing_paths()`, new tests `test_agents_md_paths_exist`, `test_agents_md_has_reviewer_rules`, `test_claude_md_names_agents_md`.
        - `CLAUDE.md` § Agents: one bullet for `AGENTS.md`.
    - **Notes:** The reviewer reads `AGENTS.md` from its working directory, so a worker branch gets the rules only after it merges `development`.

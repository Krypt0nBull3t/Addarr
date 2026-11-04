# Issue 227: Correct stale Key Changes and metadata in docs/issues

Plan: `plan.md` in this folder. Docs only: no change in `src/`, `tests/` or config.
All paths below are under `docs/issues/` unless they start with `src/` or `tests/`.

### Phase 1: Correct the task notes (4 tasks)

**Goal:** Every symbol and path named at the lines the issue lists exists, or has a note or a corrected name beside it. Done tasks carry their completion metadata.

**Phase Context:**

- Why NOT edit the `plan.md` files or the other lines that name the same symbols: the orchestrator's answer at step 3c limits the scope to the files and lines the issue lists. List the other hits in the PR body.
- Why NOT write "Superseded by 0846b97" everywhere: only `SabnzbdClient`, `JobScheduler` and `RateLimitExceededError` were removed by that commit. Other changes cite their own commit.

- [x] **1.1** Note the code that `0846b97` removed
    - **Context:**
        - **Why:** The notes name `SabnzbdClient` (`src/api/sabnzbd.py`), `JobScheduler` (`src/services/scheduler.py`) and `RateLimitExceededError` (`src/utils/error_handler.py`). All three are gone since `0846b97`.
        - **Architecture:** Append the note to the line. Use ` (Superseded by 0846b97: <thing> removed.)`. Do not reword the old text.
        - **Key refs:** `plan.md` § Edits. `git show --stat 0846b97` shows the deleted files.
        - **Watch out:** Line numbers come from the audit. Grep the symbol in each file and edit the line that names it. If a listed line no longer names it, report that in the PR body. `issue-20/TASKS.md:41-43` and `:76` are four lines. Edit only the listed lines.
    - **Scope:** `issue-12/TASKS.md:34`, `issue-20/TASKS.md:41-43,76`, `issue-101/TASKS.md:28`, `issue-78/TASKS.md:32-34,140`, `issue-118/TASKS.md:63`, `issue-116/TASKS.md:27,31,41,51,65`
    - **Touches:** the six TASKS.md files above
    - **Action items:**
        - [RED] Write a throwaway checker in the scratchpad (not committed). For each listed line it extracts `src/...` and `tests/...` paths and the symbols from plan.md, and fails when one does not exist and the line has no `Superseded by`/`Replaced in`/`Corrected` note. Run it: it fails on all the lines above.
        - [GREEN] Append the note to each listed line.
        - [GREEN] Re-run the checker: no miss left for these files.
    - **Success:** The checker reports no miss for the six files. `git diff` shows only appended text on those lines.
    - **Completed:** 2026-11-04
    - **Learnings:**
        - The checker (scratchpad, not committed) flagged 32 lines before the edits and none after.
        - `0846b97` also removed the `JobScheduler` export from `src/services/__init__.py` and its reset from `tests/conftest.py`; the other exports remain.
    - **Key Changes:**
        - Appended a "Superseded by 0846b97" note to 16 listed lines in `issue-12`, `issue-20`, `issue-101`, `issue-78`, `issue-118` and `issue-116` `TASKS.md`.
    - **Notes:** Unlisted lines that name the same symbols were left as they are (see 1.4).

- [x] **1.2** Correct the names that moved or were wrong
    - **Context:**
        - **Why:** `_format_speed`/`_format_size` were replaced by `format_bytes` in `e67a981`. `_format_bytes` in `system.py` became `src.utils.helpers.format_bytes` in `1498e48`. `HANDLER_PATCHES` never existed (the helper is `_make_handler_patches()` in `tests/test_main.py`). `tests/test_services/test_media.py` never existed (the file is `test_media_service.py`).
        - **Architecture:** Moved or replaced: append ` (Replaced in <sha>: now <new name>.)`. Wrong from the start: change the name in place and append ` (Corrected: was <old>.)`. Never cite `0846b97` for these.
        - **Key refs:** `src/utils/helpers.py:54` (`format_bytes`), `tests/test_main.py` (`_make_handler_patches`), `tests/test_services/test_media_service.py`.
        - **Watch out:** `_format_eta` still exists in `src/services/transmission.py`: say so in the issue-102 note so it is not read as removed. `issue-105/TASKS.md` has the path on three lines (59, 62, 74).
    - **Scope:** `issue-102/TASKS.md:42-43`, `issue-80/TASKS.md:139`, `issue-108/TASKS.md:52,58`, `issue-105/TASKS.md:59,62,74`
    - **Touches:** the four TASKS.md files above
    - **Action items:**
        - [RED] Run the checker from 1.1 on these lines: it fails (symbols and path missing from `src/` and `tests/`).
        - [GREEN] Apply the note or the in-place correction on each listed line.
        - [GREEN] Re-run the checker: no miss left.
    - **Success:** The checker reports no miss for the four files. Every new note cites a real commit (`git cat-file -t <sha>` prints `commit`).
    - **Completed:** 2026-11-04
    - **Learnings:**
        - `git log -S` finds `HANDLER_PATCHES` in no commit of `src/` or `tests/`; `tests/test_services/test_media.py` was never a file (`test_media_service.py` came with `f925e8b`). Both notes were wrong when written.
    - **Key Changes:**
        - Appended "Replaced in e67a981" (`issue-102`) and "Replaced in 1498e48" (`issue-108`) notes to the listed lines.
        - Corrected `HANDLER_PATCHES` to `_make_handler_patches()` (`issue-80`) and `test_media.py` to `test_media_service.py` (`issue-105`), each with a "Corrected: was ..." note.
    - **Notes:** `e67a981` and `1498e48` both resolve with `git cat-file -t`.

- [x] **1.3** Resolve the unchecked boxes and add the missing `Completed` lines
    - **Context:**
        - **Why:** `issue-123/TASKS.md:68-69` has unchecked `flake8` and `mypy` boxes. `feature/test-suite/tasks.md` has no `Completed` line on Tasks 1-14 (CLAUDE.md § Planning & Task Conventions requires one on done tasks).
        - **Architecture:** Tick a box only if its check passes. On `80943da` flake8 exits 0 and `mypy src/` reports no issues, so both boxes are ticked, with ` (re-checked 2026-11-04 on 80943da: passes)`. For test-suite, add `**Completed:** 2026-02-15 (<sha>)` at the end of each `## Task N` section, using the table in `plan.md` § Completed lines.
        - **Key refs:** `plan.md` tables. `git log` dates all 14 tasks 2026-02-15.
        - **Watch out:** Do not invent Learnings, Key Changes or Notes. Tasks 7 and 8 share commit `7bb1b78`. Task 11 has two commits (`0e3db27`, `6afcb51`). Check that each commit sha exists before use.
    - **Scope:** `issue-123/TASKS.md:68-69`, `feature/test-suite/tasks.md` (14 sections)
    - **Touches:** those two files
    - **Action items:**
        - [RED] `grep -c "\[ \]" docs/issues/issue-123/TASKS.md` prints 2. `grep -c "Completed:" docs/issues/feature/test-suite/tasks.md` prints 0.
        - [GREEN] Tick the two boxes and add the note.
        - [GREEN] Add the 14 `Completed` lines.
    - **Success:** The first grep prints 0. The second prints 14. Each sha in the new lines resolves with `git cat-file -t`.
    - **Completed:** 2026-11-04
    - **Learnings:**
        - The test-suite sections end in a `---` line, so each `Completed` line sits just above that separator, below the task's existing content. Task 14's `## Development Approach` heading sits inside a code fence, so the script keys on the `---` line before the next `## Task` or `## Final Verification` heading.
    - **Key Changes:**
        - `issue-123/TASKS.md`: ticked the `flake8` and `mypy src/` boxes. Both commands pass on `80943da` under the suite lock.
        - `feature/test-suite/tasks.md`: added 14 `**Completed:** 2026-02-15 (<sha>)` lines. All 13 distinct shas resolve with `git cat-file -t`.
    - **Notes:** No Learnings, Key Changes or Notes were added to the test-suite tasks: git history does not prove them.

- [x] **1.4** Verify, and report the lines left alone
    - **Context:**
        - **Why:** The acceptance criteria say no source change and that `pytest`, `flake8` and `mypy src/` pass.
        - **Architecture:** Gates run through the suite lock. The architecture tests hold the docs-drift checks. The full preflight (100% coverage gate) runs at the create-pr step.
        - **Key refs:** `.claude/skills/addarr-workflow/references/preflight.md`.
        - **Watch out:** Other lines name the same symbols but are not listed in the issue (for example `issue-20/TASKS.md:96,102,112`, `issue-101/TASKS.md:15,16,19`, `issue-12/TASKS.md:10,20,25`). Do not edit them. Collect them with grep for the PR body.
    - **Scope:** Verification only, plus the PR-body list
    - **Touches:** none
    - **Action items:**
        - [RED] Run the checker over all listed lines: no miss.
        - [GREEN] `git diff --stat origin/development` shows only `docs/issues/` files.
        - [GREEN] `<lock> .venv/bin/python -m flake8 .`, `<lock> .venv/bin/python -m mypy src/` and `<lock> .venv/bin/python -m pytest tests/test_architecture --tb=short -v` pass.
        - [GREEN] Write the list of unlisted hits into the scratchpad for the PR body.
    - **Success:** All commands pass. The diff has no file outside `docs/issues/`.
    - **Completed:** 2026-11-04
    - **Learnings:**
        - Unlisted lines still name the symbols without a note: `issue-101/TASKS.md:15,16,19`, `issue-78/TASKS.md:5,12,14,15,17,18,21-24,26,35,39,123,130`, `issue-20/TASKS.md:27,32,33,60,67,96,102,112`, `issue-12/TASKS.md:10,20,25`, `issue-108/TASKS.md:46,51,57`. Left alone on purpose (scope).
    - **Key Changes:** None beyond tasks 1.1-1.3. `git diff --name-only origin/development` lists only files under `docs/issues/`.
    - **Notes:** Checker: no miss. `tests/test_architecture`: 154 passed. flake8 and `mypy src/` pass (no `src/` change since the run for task 1.3). The full preflight with the coverage gate runs at the create-pr step.

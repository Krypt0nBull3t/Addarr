# Issue 215: Fix README and CLAUDE.md instructions that send users the wrong way

Plan: `docs/issues/issue-215/plan.md`. Docs only: the "RED" step is the acceptance grep that finds the wrong text, and "GREEN" is the edit that removes it.

### Phase 1: Correct the docs (2 tasks)

**Goal:** Every command, path and config key in README.md and CLAUDE.md matches the code.

**Phase Context:**

- Why NOT delete the Kubernetes section: #218 (F190) deletes `helm/` and its README section. The orchestrator confirmed on 2026-11-05 to leave it and the Python 3.10 line (already fixed by #201). The PR body says #218 removes them.

- [x] **1.1** Correct README.md (F280)
    - **Context:**
        - **Why:** A user who copies the README config block gets `/auth` failures; other lines name files and commands that do not exist.
        - **Architecture:** Docs only. No code, config, translation or Docker change.
        - **Key refs:** `src/bot/handlers/auth.py:122` (reads `telegram.password`), `src/utils/helpers.py:82` (reads `security.enableAdmin`), `config_example.yaml:9` (`telegram.password`), `run.py` (`--reset`).
        - **Watch out:** Keep `enableAdmin` under `security:`. Leave the Kubernetes section, its TOC entry and the Python 3.10 line alone. Line numbers moved after #201; find the text by content.
    - **Scope:** Five README edits.
    - **Touches:** `README.md`
    - **Action items:**
        - [RED] Run `grep -nE "setup.py|requirements-dev|pre-commit|monitoring:|Python 3.9" README.md` and confirm it finds the wrong lines.
        - [GREEN] Move `password` under `telegram:`; keep `security:` with `enableAdmin`.
        - [GREEN] Change `python setup.py --reset` to `python run.py --reset` and reword "setup script".
        - [GREEN] Delete the `monitoring:` block and its `### Configuration` subsection in the health section.
        - [GREEN] Delete the `requirements-dev.txt` line and the pre-commit step in Development Setup; renumber.
    - **Success:** The grep prints nothing. The README `telegram:` block has `token` and `password`. `pytest tests/test_architecture` passes.
    - **Completed:** 2026-11-05
    - **Learnings:** `README.md:204` already said Python 3.10 (#201). `requirements-test.txt` exists, so the dependency step now names it instead of the missing `requirements-dev.txt`.
    - **Key Changes:** `README.md`: `password` moved under `telegram:`; `python run.py --reset`; `monitoring:` subsection deleted; Development Setup lost the pre-commit step and `requirements-dev.txt`, steps renumbered to 3.
    - **Notes:** The Kubernetes section and its TOC entry stay; #218 (F190) removes them. The issue's `kubernetes/` grep therefore still matches README.md.

- [x] **1.2** Correct CLAUDE.md (F281)
    - **Context:**
        - **Why:** CLAUDE.md names a class-instance name as a file and lists mount files no live code reads (F191).
        - **Architecture:** Docs only. `tests/test_architecture/test_repo_docs.py` checks every repo path CLAUDE.md names.
        - **Key refs:** `src/utils/prerun.py` (`PreRunChecker`), `src/utils/__init__.py` (instance export), `.github/workflows/docker-hub-push.yml`.
        - **Watch out:** Keep both Docker Hub lines. #218 edits the same `.txt` text; the second PR to merge keeps both edits. The acceptance grep also matches the instance name `prerun_checker`, so reword that clause.
    - **Scope:** Two CLAUDE.md edits.
    - **Touches:** `CLAUDE.md`
    - **Action items:**
        - [RED] Run `grep -nE "prerun_checker|admin.txt|allowlist.txt|chatid.txt" CLAUDE.md` and confirm it finds both lines.
        - [GREEN] Reword the entry-point flow so it cites `src/utils/prerun.py` (`PreRunChecker`) without `prerun_checker`.
        - [GREEN] Remove `chatid.txt`, `admin.txt` and `allowlist.txt` from "Persistent files to mount".
    - **Success:** The grep prints nothing. `grep -n "Docker Hub" CLAUDE.md` still finds both lines. `pytest tests/test_architecture` passes.
    - **Completed:** 2026-11-05
    - **Learnings:** `CLAUDE.md` already cited `src/utils/prerun.py`; only the instance name `prerun_checker` matched the acceptance grep, so the clause now says "the shared instance".
    - **Key Changes:** `CLAUDE.md`: entry-point flow reworded; "Persistent files to mount" now lists `config.yaml`, `logs/`, `backup/`.
    - **Notes:** Both Docker Hub lines kept. #218 edits the same mount text; the second PR to merge keeps both edits.

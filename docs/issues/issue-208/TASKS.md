# Issue #208 Tasks

Plan: `docs/issues/issue-208/plan.md`. F160, F161 (repo settings) and the `v0.9.0` tag with its GitHub Release are developer actions. F162 is done by #269, F164 by #238. No `.github/` file changes.

### Phase 1: Release 0.9.0 prep (3 tasks)

**Goal:** `__version__` is `0.9.0`, the CI matrix choice is recorded, and the PR body carries the release notes and the developer actions.

- [x] **1.1** Bump `__version__` to 0.9.0 (F163)
    - **Context:**
        - **Why:** The bot reports `0.8` in `/help` and nothing marks the release. The developer tags `v0.9.0` after the release PR merges.
        - **Architecture:** `src/__init__.py` holds `__version__`. `tests/conftest.py` injects its own `__version__` into `src`, so a test that imports `src` passes on the fixture alone.
        - **Key refs:** `src/__init__.py:12`, `tests/conftest.py:221` and `:226`, `src/bot/handlers/help.py:17,72`, `tests/test_handlers/test_help_handler.py:90`
        - **Watch out:** Read the real file with `ast`, not through `import src`. The architecture tests parse source with `ast` and never import `src`. The help test only checks the `HelpVersion` key, so it stays unchanged.
    - **Scope:** Version string in source and in the test fixture, plus one test that pins it
    - **Touches:** `src/__init__.py`, `tests/conftest.py`, `tests/test_version.py` (new)
    - **Action items:**
        - [RED] Write `test_version_is_0_9_0` in `tests/test_version.py`: parse `src/__init__.py` with `ast`, find the `__version__` assignment, assert its value is `"0.9.0"`. Run it, expect FAIL (`"0.8"`).
        - [GREEN] Change `__version__ = "0.8"` to `"0.9.0"` in `src/__init__.py`.
        - [GREEN] Change both `"0.8"` values in `tests/conftest.py` (lines 221 and 226) to `"0.9.0"`.
    - **Success:** `tests/test_version.py` and `tests/test_handlers/test_help_handler.py` pass. `tests/test_architecture` passes. flake8 and mypy clean.
    - **Completed:** 2026-11-05
    - **Learnings:** The new test failed first with `assert '0.8' == '0.9.0'`. `tests/conftest.py` sets `__version__` itself, so the test reads the source with `ast`.
    - **Key Changes:** `src/__init__.py` and `tests/conftest.py` (2 lines) now say `0.9.0`. New `tests/test_version.py`.
    - **Notes:** The tag `v0.9.0` and the GitHub Release are for the developer.

- [ ] **1.2** Record why the CI matrix has four versions (F165)
    - **Context:**
        - **Why:** The issue-160 plan decided on 3.10 and 3.14 only. `ci.yml` runs 3.10, 3.12, 3.13 and 3.14. The docs must say why.
        - **Architecture:** Docs only. `.github/workflows/ci.yml:133` stays as is.
        - **Key refs:** `docs/issues/issue-160/plan.md` "Design Decisions" (items 1 to 4), commit `8364be6` ("add 3.12 and 3.13 to compatibility matrix", "to avoid gaps in version coverage")
        - **Watch out:** One line, one new item 5 after item 4. Do not rewrite items 1 to 4 (they record the original decision).
    - **Scope:** One line in one file
    - **Touches:** `docs/issues/issue-160/plan.md`
    - **Action items:**
        - [GREEN] Add item 5 to "Design Decisions": `5. **Later change (8364be6):** the compatibility matrix grew to 3.10, 3.12, 3.13 and 3.14 "to avoid gaps in version coverage". The boundary-only choice above was dropped on purpose; #208 (F165) keeps the four versions.`
    - **Success:** `pytest tests/test_architecture` passes (`test_repo_docs.py`, `test_skills.py`). `git diff` shows one added line in `docs/issues/issue-160/plan.md`.

- [ ] **1.3** Prepare the PR body: release notes and developer actions
    - **Context:**
        - **Why:** The issue wants release notes that name the changed defaults, with no changelog file. The notes go in the GitHub Release, which the developer publishes.
        - **Architecture:** No file in the repo. The text goes in the PR body (create-pr step 7), under "Release notes for v0.9.0 (for the GitHub Release)". It has "Changed defaults" and "Upgrade notes" sections.
        - **Key refs:** `docs/issues/issue-208/plan.md` Task 3 (the full list of items). Source PR bodies: `gh pr view <N> --repo Krypt0nBull3t/Addarr --json body` for #263, #258, #254, #259, #188, #191, #252, #192, #193, #152.
        - **Watch out:** Re-check each item against its PR body before the PR is created. Scan the other merged PR bodies since `main` for further upgrade notes (`gh pr list --repo Krypt0nBull3t/Addarr --state merged --base development --limit 300 --json number,title,body`) and add each one found. Create no changelog file. Do not write the PR body into the repo.
    - **Scope:** Text only, written to `<scratchpad>/pr-body.md` at create-pr time
    - **Touches:** none in the repo
    - **Action items:**
        - [GREEN] Draft the "Release notes for v0.9.0" section: changed defaults (chatMode `private_only`, `enableAdmin` with `onlyAdmin`, `enableAllowlist`, `/auth` rate limit) and the upgrade notes (#263, #258, #254, #259, #188, #191, #252, #254/#192 tags keys, plus any found by the scan).
        - [GREEN] Add the "Developer actions" list: F160 re-enable CodeQL, F161 enable Dependabot security alerts (check `vulnerability-alerts` returns 204), F163 tag `v0.9.0` and publish the GitHub Release after the release PR merges to `main`. State F162 is done by #269 and F164 by #238.
    - **Success:** The PR body names the `private_only` chatMode default and the enforced `onlyAdmin`, lists every upgrade note, lists the developer actions, and the repo has no new changelog file.

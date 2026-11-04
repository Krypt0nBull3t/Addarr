# Issue #238: Tasks

Source: `docs/issues/issue-238/plan.md` (approved 2026-11-04 with defaults 1-6).

Run checks with the worktree venv: `.venv/bin/python -m pytest`, `.venv/bin/python -m flake8 .`, `.venv/bin/python -m mypy src/`, `PYTHONIOENCODING=utf-8 .venv/bin/python run.py --validate-i18n`. Full-suite runs go under `~/.local/share/agent-suite/with-suite-lock.sh addarr/238 -- <command>`.

### Phase 1: CLAUDE.md drift, ADRs, repo templates (3 tasks)

**Goal:** CLAUDE.md matches the code (D1-D4), rules in force are ADRs (D7), and the repo has a PR template, issue forms and CODEOWNERS (D6), each guarded by `tests/test_architecture/test_repo_docs.py`.

- [x] **1.1** Drift test and CLAUDE.md D1-D4
    - **Context:** See plan.md Task 1. Key refs: `tests/test_architecture/test_agent_tooling.py:20-75` (`PROJECT_ROOT`, `read_text` style), `.github/workflows/ci.yml` (job `name:` values), `src/utils/__init__.py` (`prerun_checker` instance).
    - **Watch out:** Keep the `## Untrusted Input` sentence byte-for-byte (`DATA_RULE`). Write repo paths in full in changed sections. Leave `.github/ISSUE_TEMPLATE/` out of the Docs drift bullet until 1.3. Also add the branch-name format `<prefix>/<N>-<slug>` to § Git Branching (coordinator request, from #237).
    - **Scope:** New test file with 4 checks; CLAUDE.md § Testing, § Architecture Tests, § Key Patterns, § Entry Point Flow, § CI/CD, § Git Branching.
    - **Touches:** `tests/test_architecture/test_repo_docs.py` (new), `CLAUDE.md`
    - **Action items:**
        - [RED] `test_claude_md_paths_exist`: fails on `src/utils/prerun_checker.py`
        - [RED] `test_claude_md_names_every_ci_job`: fails on 8 job names
        - [RED] `test_claude_md_names_every_architecture_test_file`: fails on `test_agent_tooling.py`, `test_repo_docs.py`
        - [RED] `test_claude_md_test_names_exist`: show red with a planted `` `test_does_not_exist` ``, then remove it
        - [GREEN] Edit CLAUDE.md per plan.md Task 1 Step 3, plus the branch-name line
    - **Success:** `pytest tests/test_architecture/` passes, flake8 clean
    - **Completed:** 2026-11-04
    - **Learnings:**
        - The audit's D1 was half right: `prerun_checker.py` does not exist, but `prerun_checker` is a real instance exported by `src/utils/__init__.py`, so CLAUDE.md now names both.
        - Matching CI job names only inside `## CI/CD` and case-sensitively matters: "Type Checking" and "Lint Configuration" headings would otherwise satisfy the check.
        - `flake8` is in no requirements file (#236 S5); the venv needs `pip install flake8`, as `ci.yml` does.
    - **Key Changes:**
        - New `tests/test_architecture/test_repo_docs.py`: `test_claude_md_paths_exist`, `test_claude_md_names_every_ci_job`, `test_claude_md_names_every_architecture_test_file`, `test_claude_md_test_names_exist`.
        - `CLAUDE.md`: prerun path, all 9 CI jobs and the branch-protection note, 5 more convention tests plus the agent-tooling and docs-drift files, `reset_singletons`, `ALBUM_SELECT`, keyboard locations, branch-name format.
    - **Notes:** All four checks were seen red first (the test-name check on a planted `test_does_not_exist`). Full suite: 2177 passed.

- [ ] **1.2** ADRs for rules in force (D7)
    - **Context:** See plan.md Task 2. Key refs: `tests/test_architecture/test_conventions.py:219,445,472,525`, `tests/integration/test_start_flow.py:75`, CLAUDE.md § Handler Registration Order, § Git Branching.
    - **Watch out:** Facts only from code, tests, CLAUDE.md and the commits named in the plan; no invented history.
    - **Scope:** 4 ADRs and their CLAUDE.md links
    - **Touches:** `docs/adr/0001-singleton-services.md`, `docs/adr/0002-config-get-access.md`, `docs/adr/0003-handler-registration-order.md`, `docs/adr/0004-prs-target-development.md` (all new), `CLAUDE.md`
    - **Action items:**
        - [RED] Add the ADR links to CLAUDE.md; `test_claude_md_paths_exist` fails on the 4 ADR paths and `docs/adr/`
        - [GREEN] Write the 4 ADRs
    - **Success:** `pytest tests/test_architecture/` passes

- [ ] **1.3** PR template, issue forms, CODEOWNERS (D6)
    - **Context:** See plan.md Task 3. Key refs: issue #200 (bug layout), #236/#238 (problem layout).
    - **Watch out:** No `TODO`/`FIXME` in added lines (`auto-approve.yml` flags them). Check `bug` and `enhancement` labels exist (`gh label list`) before using them.
    - **Scope:** 4 new `.github/` files, issue-form test, Docs drift bullet path
    - **Touches:** `.github/PULL_REQUEST_TEMPLATE.md`, `.github/ISSUE_TEMPLATE/bug_report.yml`, `.github/ISSUE_TEMPLATE/feature_request.yml`, `.github/CODEOWNERS` (all new), `tests/test_architecture/test_repo_docs.py`, `CLAUDE.md`
    - **Action items:**
        - [RED] `test_issue_form_is_valid[bug_report.yml]` and `[feature_request.yml]` fail with `FileNotFoundError`
        - [GREEN] Write the two forms, the PR template and CODEOWNERS
        - [GREEN] Name `.github/ISSUE_TEMPLATE/` in the Docs drift bullet
    - **Success:** `pytest tests/test_architecture/` passes; full suite, flake8, mypy, `--validate-i18n` pass

### Phase 2: After #236 and #237 merge (1 task)

**Goal:** CLAUDE.md names the project agents, the fork-PR rule and #237's skills test.

- [ ] **2.1** Agents section, fork-PR rule, `test_skills.py` (D5)
    - **Context:** See plan.md Task 4. Wait for the coordinator's message with #236's exact fork-PR sentence; rebase on `origin/development` first.
    - **Watch out:** `test_claude_md_names_every_architecture_test_file` fails after the rebase until `tests/test_architecture/test_skills.py` is named in § Testing.
    - **Scope:** `## Agents` section after `## Untrusted Input`; `test_skills.py` bullet in § Architecture Tests
    - **Touches:** `CLAUDE.md`
    - **Action items:**
        - [RED] After rebase, `test_repo_docs.py` fails on the unnamed `test_skills.py`; write the Agents section, see `test_claude_md_paths_exist` pass only with #236's files present
        - [GREEN] Add the section and the bullet with the coordinator's wording
    - **Success:** full suite, flake8, mypy, `--validate-i18n` pass; then create-pr flow

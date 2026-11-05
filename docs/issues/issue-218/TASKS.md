# Issue 218: Remove the stale Helm chart and legacy .txt files

Plan: `docs/issues/issue-218/plan.md`. Branch `refactor/218-remove-helm-and-legacy-txt-files`.

Deletion and doc edits only. No new behavior, so there is no [RED] test step. The existing
architecture tests (`test_repo_docs.py`, `test_skills.py`) are the guard: run them after each task.

### Phase 1: Remove Helm and the legacy .txt files (4 tasks)

**Goal:** The repo ships no Helm chart and no file or constant for the three `.txt` files the bot does not read.

**Phase Context:**

- Why NOT delete `.gitignore`, `.claude/settings.json` deny rules, `test_agent_tooling.py` or `.claude/agents/*.md` entries: they guard old secret files on users' disks (orchestrator ruling, step 3c).
- Why `CHATID_PATH` stays in tasks 1-3: `src/utils/helpers.py` still imports it until #226 merges.

- [ ] **1.1** Delete the Helm chart and its references (F190)
    - **Context:**
        - **Why:** The chart runs another project's image, mounts `config.yaml` read-only and puts secrets in a ConfigMap.
        - **Architecture:** Pure deletion plus doc edits. No code path uses `helm/`.
        - **Key refs:** `CLAUDE.md` section `## Helm / Kubernetes` (lines 191-201); `README.md:56` (feature bullet), `README.md:148` (TOC), `README.md` `## Deployment Options` (~641-670, with `### Kubernetes Deployment` pointing at `kubernetes/` files that do not exist); `.claude/skills/addarr-workflow/references/new-task.md:78`.
        - **Watch out:** `.claude/skills/graphify/references/transcribe.md:22` names Helm as a generic example label. Leave it. Re-read line numbers before editing; they moved since the issue was written. Update the intro sentence "deployed using Docker or Kubernetes" too.
    - **Scope:** `helm/` directory, three doc files
    - **Touches:** `helm/` (delete), `CLAUDE.md`, `README.md`, `.claude/skills/addarr-workflow/references/new-task.md`
    - **Action items:**
        - [GREEN] `git rm -r helm/`
        - [GREEN] Delete the `## Helm / Kubernetes` section from `CLAUDE.md`
        - [GREEN] In `README.md`: remove the Helm bullet and its `<br>`, the TOC entry, the Kubernetes Deployment section, and the Kubernetes mention in the Deployment Options intro
        - [GREEN] `new-task.md:78`: "Docker/Helm impact" becomes "Docker impact"
        - [GREEN] Run `<lock> .venv/bin/python -m pytest tests/test_architecture --tb=short -v`
    - **Success:** `grep -rniI helm . --exclude-dir=.git --exclude-dir=graphify-out --exclude-dir=.venv --exclude-dir=issues` finds only the two `.github/` lines (task 1.3) and `transcribe.md`; architecture tests pass.

- [ ] **1.2** Remove the legacy .txt mounts, constants and doc lines (F191)
    - **Context:**
        - **Why:** `admin.txt`, `allowlist.txt` and `chatid.txt` are not read by live code, yet compose mounts them and the docs name them.
        - **Architecture:** Delete the mounts and the unused constants; keep `CHATID_PATH` (see Phase Context).
        - **Key refs:** `docker-compose.yml:25-27`; `.dockerignore:8-9`; `src/definitions.py:24,27,28`; `CLAUDE.md:240` (Docker section; the issue says `:209`); `README.md:375-376`; `.claude/skills/addarr-services/references/config-patterns.md:80-83`.
        - **Watch out:** Only `CHATID_PATH` is imported (`src/utils/helpers.py:15`). Confirm `ADMIN_PATH` and `ALLOWLIST_PATH` have no importer before deleting. #215 also edits the `CLAUDE.md` Docker line; keep both edits if they conflict. `test_skills.py` fails if `config-patterns.md` names a constant that is gone.
    - **Scope:** compose, dockerignore, definitions, three doc files
    - **Touches:** `docker-compose.yml`, `.dockerignore`, `src/definitions.py`, `CLAUDE.md`, `README.md`, `.claude/skills/addarr-services/references/config-patterns.md`
    - **Action items:**
        - [GREEN] Delete the three `.txt` volume lines from `docker-compose.yml`
        - [GREEN] Delete `admin.txt` and `chatid.txt` from `.dockerignore`
        - [GREEN] Delete `ADMIN_PATH` and `ALLOWLIST_PATH` from `src/definitions.py`
        - [GREEN] `CLAUDE.md` Docker section: drop the three names from "Persistent files to mount"
        - [GREEN] `README.md` permissions note: drop `chatid.txt` from the sentence and the `chown` example
        - [GREEN] `config-patterns.md`: delete the `ADMIN_PATH` and `ALLOWLIST_PATH` rows
        - [GREEN] Run `docker compose config`, then the architecture suite and `<lock> .venv/bin/python scripts/test_runner.py config --coverage` (definitions is imported widely, so also `... utils --coverage`)
    - **Success:** `docker compose config` is valid; the F191 grep finds no `ADMIN_PATH`, `ALLOWLIST_PATH`, `admin.txt` or `allowlist.txt` in `src/`, `docker-compose.yml`, `.dockerignore` or `CLAUDE.md`; tests pass.

- [ ] **1.3** Remove the Helm lines in `.github/` (developer approved, 2026-11-05)
    - **Context:**
        - **Why:** The issue's acceptance grep names both files. The developer approved editing them in this PR; the PR body must say so.
        - **Architecture:** One tree line and one exclude pattern.
        - **Key refs:** `.github/copilot-instructions.md:54` (`helm/            # Kubernetes Helm chart`); `.github/workflows/auto-approve.yml:90` (`r'^helm/',` in `EXCLUDE_PATTERNS`).
        - **Watch out:** `auto-approve.yml` runs the AI review; change only that one list entry. `test_repo_docs.py` validates `.github/ISSUE_TEMPLATE/`, not these files.
    - **Scope:** two lines in two files
    - **Touches:** `.github/copilot-instructions.md`, `.github/workflows/auto-approve.yml`
    - **Action items:**
        - [GREEN] Delete the `helm/` line from the structure tree
        - [GREEN] Delete `r'^helm/',` from `EXCLUDE_PATTERNS`
        - [GREEN] Run the architecture suite
    - **Success:** `grep -rniI helm . --exclude-dir=.git --exclude-dir=graphify-out --exclude-dir=.venv --exclude-dir=issues` finds only `transcribe.md`; the workflow YAML still parses; architecture tests pass.

- [ ] **1.4** Delete `CHATID_PATH` (conditional: only when #226 is merged)
    - **Context:**
        - **Why:** F191 wants no `CHATID_PATH` in `src/`. Its only users are the dead helpers `get_authorized_chats` and `save_chat_id`, which #226 deletes.
        - **Architecture:** Do this at create-pr after `git merge origin/development`. Do not delete the helpers here; that is #226's change.
        - **Key refs:** `src/definitions.py:24`; `src/utils/helpers.py:15`; `config-patterns.md` row.
        - **Watch out:** If #226 is not merged, report with `ao report --needs-input` and wait; do not delete the helpers in this PR (addarr-7 owns #226).
    - **Scope:** one constant, one doc row
    - **Touches:** `src/definitions.py`, `.claude/skills/addarr-services/references/config-patterns.md`
    - **Action items:**
        - [GREEN] Check `gh pr list --search "226"` and that `origin/development` has no `get_authorized_chats`
        - [GREEN] Delete `CHATID_PATH` and its doc row
        - [GREEN] Run the F191 grep over `src/`, `docker-compose.yml`, `.dockerignore`, `CLAUDE.md`
    - **Success:** The F191 grep finds nothing in those four targets; preflight passes.

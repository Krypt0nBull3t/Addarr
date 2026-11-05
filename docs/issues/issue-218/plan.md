# Issue 218: Remove the stale Helm chart and legacy .txt files

**Issue:** https://github.com/Krypt0nBull3t/Addarr/issues/218 (audit findings F190, F191)
**Branch:** `refactor/218-remove-helm-and-legacy-txt-files`

## Context

- The Helm chart in `helm/` runs `waterboy1602/addarr`, another project's image. It uses the old
  config format, mounts `config.yaml` read-only (so `/auth` cannot save) and puts secrets in a
  ConfigMap.
- `admin.txt`, `allowlist.txt` and `chatid.txt` are not read by live code. Compose, the constants
  in `src/definitions.py` and the docs still name them.

Deletion and doc edits only. No new code, so no new tests. The existing architecture tests
(`test_repo_docs.py`, `test_skills.py`) pin the docs and skills and must stay green.

## Decisions (orchestrator, 2026-11-04 and 2026-11-05)

- Branch `refactor/218-...` from `origin/development` (`cf51f57`).
- `CHATID_PATH` waits for #226 (it deletes `get_authorized_chats`, `save_chat_id` and their tests,
  the only users of the constant). If #226 is merged at create-pr time, merge `origin/development`
  and delete `CHATID_PATH` too, so the F191 grep is clean. If not, report and wait there.
- Keep the three `.txt` names in `.gitignore`, `.claude/settings.json` deny rules,
  `tests/test_architecture/test_agent_tooling.py` and `.claude/agents/*.md`: they guard old secret
  files on users' disks.
- `README.md:375-376` and `.claude/skills/addarr-workflow/references/new-task.md:78` are in scope.
- The README Kubernetes/Helm section is in scope. #215 leaves it to this issue.
- The two `.github/` edits (`copilot-instructions.md:54`, `auto-approve.yml:90`) wait for the
  developer's answer. Do not touch those files until the orchestrator replies.
- `CLAUDE.md:209` in the issue is now `CLAUDE.md:240` (Docker section). #215 also edits that line;
  the PR that merges second keeps both edits.
- PR body: `Closes #218` and `Closes #119`.

## Tasks

### Task 1: Delete the Helm chart and its references (F190)

**Files**
- Delete: `helm/` (Chart.yaml, README.md, values.yaml, templates/configMap.yaml,
  templates/deployment.yaml, templates/pvc.yaml)
- Modify: `CLAUDE.md` (the `## Helm / Kubernetes` section, lines 193-201 and its heading)
- Modify: `README.md` (feature bullet line 56; TOC entry line 148; the `### Kubernetes Deployment`
  section; the sentence "deployed using Docker or Kubernetes" in `## Deployment Options`)
- Modify: `.claude/skills/addarr-workflow/references/new-task.md:78` ("Docker/Helm impact" becomes
  "Docker impact")

Check: `grep -rniI helm . --exclude-dir=.git --exclude-dir=graphify-out --exclude-dir=.venv --exclude-dir=issues`
finds only the two `.github/` lines (Task 3) and `.claude/skills/graphify/references/transcribe.md`
(a generic example label, not about this repo; leave it).

### Task 2: Remove the legacy .txt mounts, constants and doc lines (F191)

**Files**
- Modify: `docker-compose.yml:25-27` (delete the three `.txt` volume lines)
- Modify: `.dockerignore:8-9` (delete `admin.txt` and `chatid.txt`)
- Modify: `src/definitions.py` (delete `ADMIN_PATH` and `ALLOWLIST_PATH`; `CHATID_PATH` stays, see
  Decisions)
- Modify: `CLAUDE.md:240` (Docker section: drop the three file names from "Persistent files to
  mount")
- Modify: `README.md:375-376` (permissions note: drop `chatid.txt` from the sentence and the
  `chown` example)
- Modify: `.claude/skills/addarr-services/references/config-patterns.md:80-83` (delete the
  `ADMIN_PATH` and `ALLOWLIST_PATH` rows; `CHATID_PATH` row stays with the constant)

Check: `docker compose config` is valid. The F191 grep
(`grep -rnE "chatid.txt|admin.txt|allowlist.txt|CHATID_PATH|ADMIN_PATH|ALLOWLIST_PATH"`) finds
nothing in `src/` (except `CHATID_PATH`), `docker-compose.yml`, `.dockerignore` or `CLAUDE.md`.
The bot starts without the files (`python run.py --check` or import of `src.definitions`).

### Task 3: `.github/` references (blocked until the developer answers)

**Files**
- Modify: `.github/copilot-instructions.md:54` (delete the `helm/` line of the structure tree)
- Modify: `.github/workflows/auto-approve.yml:90` (delete `r'^helm/',` from `EXCLUDE_PATTERNS`)

Do not start before the orchestrator confirms. Done last so the rest is not blocked.

### Task 4: Delete `CHATID_PATH` (conditional, at create-pr)

Only when #226 is merged into `origin/development`. Merge `origin/development`, delete
`CHATID_PATH` from `src/definitions.py` and its row in `config-patterns.md`, re-run the F191 grep
over `src/`, `docker-compose.yml`, `.dockerignore`, `CLAUDE.md`. If #226 is not merged, report and
wait.

## Verification

- Scoped: `<lock> .venv/bin/python -m pytest tests/test_architecture --tb=short -v` after each
  task (docs, skills, CLAUDE.md, `.github/` change).
- Preflight at create-pr: flake8, mypy, translations, unit tests with the 100% coverage gate,
  integration tests, architecture tests.
- Manual: both grep checks above, `docker compose config`.

## Risks

- A user who bind-mounts `./chatid.txt` in their own compose file is not affected; the bot never
  read the file.
- `CLAUDE.md:240` collides with #215. Resolve by keeping both edits on the second merge.

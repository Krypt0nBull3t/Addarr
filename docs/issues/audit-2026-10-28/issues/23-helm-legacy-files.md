---
title: "Remove the stale Helm chart and legacy .txt files"
labels: [bug, ops, security, tech-debt, agent-ready, priority:medium]
slice: 23
findings: [F190, F191]
---

## Bug

- The Helm chart runs `waterboy1602/addarr`, another project's image. It uses the old config format. It mounts `config.yaml` from a read-only ConfigMap, so `/auth` cannot save users. It puts secrets in a ConfigMap.
- `admin.txt`, `allowlist.txt` and `chatid.txt` are never read by live code. docker-compose and Helm still mount them, and CLAUDE.md lists them.

## Steps to reproduce

1. Run `helm template addarr ./helm`: the pod image is `waterboy1602/addarr:latest`.
2. See `helm/templates/deployment.yaml:28`: `config.yaml` comes from the ConfigMap, which is read-only. `/auth` cannot save.
3. See `helm/templates/configMap.yaml:12-13`: the whole config, with the bot token, API keys and passwords, sits in a ConfigMap, not a Secret.
4. See `docker-compose.yml:25-27`: compose mounts the three `.txt` files. No live code reads them.

## Expected behavior

The repo ships no deployment that runs another project's image or stores secrets in a ConfigMap. Compose, the code and the docs mention no file the bot does not read.

## Fix

- [ ] **F190** Delete `helm/` and its README section. Close #119 when this lands: put `Closes #119` in the PR body (`helm/values.yaml:117`, `helm/templates/deployment.yaml:28`, `helm/templates/configMap.yaml`)
- [ ] **F191** Delete the mounts, the constants `CHATID_PATH`, `ADMIN_PATH`, `ALLOWLIST_PATH` and the doc lines (`docker-compose.yml:25-27`, `src/definitions.py:24`, `:27`, `:28`, `.dockerignore:8-9`, `CLAUDE.md:209`)

## Acceptance criteria

- [ ] F190 (manual): `helm/` and the README Helm section are gone. `grep -rn -i helm` finds no stale reference in CLAUDE.md (`:164-172`), README.md (`:56`), `.github/copilot-instructions.md:54` or `.github/workflows/auto-approve.yml:90`. Issue #119 is closed after the merge.
- [ ] F191 (manual): `grep -rn -E "chatid.txt|admin.txt|allowlist.txt|CHATID_PATH|ADMIN_PATH|ALLOWLIST_PATH"` finds nothing in `src/`, `docker-compose.yml`, `.dockerignore` or `CLAUDE.md`. `docker compose config` is valid and the bot starts without the files.
- [ ] `pytest`, `flake8` and `mypy src/` pass.

## Notes

- Source: audit 2026-10-28, docs/issues/audit-2026-10-28/FINDINGS.md (F-ids F190, F191).
- Priority: max P 20, sum P 40 (medium).
- Dependencies: none in the order of work. `CHATID_PATH` is still imported by the dead helpers `get_authorized_chats` and `save_chat_id` (`src/utils/helpers.py:15`, `:32-50`) and their tests. Slice 31 (F260) deletes them; do it first or in the same change. Slice 20 (F281) also edits `CLAUDE.md:209`.
- Related open issue: #119 (Helm chart security hardening). Close it when this lands.
- Decided 2026-10-28: F190 delete `helm/` and its README section; close #119 when this lands.
- Decided 2026-10-28: F191 delete the legacy `.txt` mounts and constants.

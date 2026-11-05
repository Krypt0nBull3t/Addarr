---
title: "Fix drift in project skills and commands"
labels: [documentation, tech-debt, priority:medium]
slice: 26
findings: [F290, F294, F292, F293, F295, F296, F291]
---

## Problem

Project skills and commands describe code and fixtures that do not exist, or are Emmie (PHP/Vue) copies. Agents that follow them write wrong tests and run the wrong checklists.

- **F290** `addarr-testing` says Transmission uses sync `requests` and must be mocked with `patch("requests.post")`. It uses aiohttp, and CLAUDE.md says to mock it with aioresponses. The fixture tables list `sabnzbd_url`, `sabnzbd_client` and `RADARR_SYSTEM_STATUS`, which do not exist.
- **F294** The project skills `find-bugs` and `code-simplifier` are shadowed by personal Emmie skills with the same names, so `/addarr pr` runs PHP checklists. `git-cleanup` duplicates a personal skill. `python-testing-pro` is an 815-line copy of `ecc:python-testing`.
- **F292** `config-patterns.md` shows Transmission as nested `server`/`auth` (the code reads flat `host`/`port`) and SABnzbd on port 8080 (`config_example.yaml` uses 8090).
- **F293** The handler wiring order and the callback prefix registry miss 7 handlers.
- **F295** `i18n-key` has no note that keys under `messages.` are read with `get_message()` (the cause of F201). It says the validator exits 0; it now exits 1 on errors.
- **F296** `next.md` uses a TypeScript/raydium example and omits `Completed` from step 6.
- **F291** `task-writer` is an Emmie skill (Pest, Vitest, Vue, PHP paths), but CLAUDE.md requires it for every TASKS.md.

## Expected behavior

Each project skill and command matches the current code, `config_example.yaml` and `src/main.py`, and uses Python and pytest examples. No project skill shares a name with a personal skill.

## Fix

- [ ] **F290** Rewrite the Transmission sections for aioresponses and `TransmissionClient`. Update the fixture tables to the fixtures and constants that exist (`.claude/skills/addarr-testing/SKILL.md:41-42`, `:62`, `:85`; `references/anti-patterns.md:58-79`; `references/patterns.md:76-108`; `references/fixtures.md:128`, `:207`)
- [ ] **F294** Rename `find-bugs` and `code-simplifier` to `addarr-find-bugs` and `addarr-code-simplifier` and update every reference. Delete the 2 copies, `git-cleanup` and `python-testing-pro` (`.claude/skills/find-bugs`, `code-simplifier`, `git-cleanup`, `python-testing-pro`; `.claude/skills/addarr-workflow/SKILL.md:100-102`; `references/create-pr.md:10`, `:38`; `.claude/skills/release-readiness/SKILL.md:12`; `.claude/commands/addarr-setup.md:11-25`)
- [ ] **F292** Copy the `transmission:` and `sabnzbd:` blocks from `config_example.yaml` (`.claude/skills/addarr-services/references/config-patterns.md:89-106`)
- [ ] **F293** Regenerate the wiring order and the prefix registry from `_add_handlers()` in `src/main.py`. The missing handlers are WebhooksHandler, CalendarHandler, MissingHandler, QueueHandler, HistoryHandler, BazarrHandler and DownloadsHandler (`.claude/skills/addarr-handlers/references/wiring.md:74-86`; `references/callbacks.md:13-31`)
- [ ] **F295** Add the `messages.`/`get_message()` note. Fix the exit-code claim (`.claude/skills/i18n-key/SKILL.md:29-50`)
- [ ] **F296** Replace the example with a Python one. Add `Completed` to step 6 (`.claude/commands/next.md:13-17`, `:22-34`)
- [ ] **F291** Rewrite for the handlers/services/api layers and pytest (`.claude/skills/task-writer/SKILL.md:16-33`, `:95-139`, `:201-257`)

## Acceptance criteria

- [ ] F290: `grep -rn "requests.post\|sync .requests\|sabnzbd_url\|sabnzbd_client\|RADARR_SYSTEM_STATUS" .claude/skills/addarr-testing` returns nothing. Every fixture and constant the skill names exists in `tests/`.
- [ ] F294: `.claude/skills/` has no `find-bugs`, `code-simplifier`, `git-cleanup` or `python-testing-pro` directory. No file under `.claude/` names `find-bugs` or `code-simplifier` without the `addarr-` prefix, or names `git-cleanup` or `python-testing-pro`.
- [ ] F292: the two blocks in `config-patterns.md` match `config_example.yaml` line for line.
- [ ] F293: the wiring list names all 18 handlers in `_add_handlers()` order. The registry has a row for every callback prefix those handlers register.
- [ ] F295: the skill has the `get_message()` note and no claim that the validator exits 0.
- [ ] F296: `grep -n "raydium\|\.ts" .claude/commands/next.md` returns nothing. Step 6 lists `Completed`, `Learnings`, `Key Changes` and `Notes`, as CLAUDE.md requires.
- [ ] F291: `grep -n "Pest\|Vitest\|\.vue\|\.php" .claude/skills/task-writer/SKILL.md` returns nothing. The examples use `src/bot/handlers`, `src/services`, `src/api` and pytest.
- [ ] `pytest`, `flake8` and `mypy src/` pass (no code change expected).

## Notes

- Source: audit 2026-10-28, docs/issues/audit-2026-10-28/FINDINGS.md (F-ids F290, F294, F292, F293, F295, F296, F291).
- Priority: max P 16 (F290), sum P 80, `priority:medium`.
- F295 documents the cause of F201 (slice 25).
- F292: the setup wizard writes the same wrong nested Transmission shape; slice 12 (F082) fixes the wizard.
- Related open issues: none.

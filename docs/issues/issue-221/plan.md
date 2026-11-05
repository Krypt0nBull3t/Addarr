# Plan: Issue #221 — Fix drift in project skills and commands

**Goal:** Each project skill/command matches current code, config_example.yaml, and src/main.py. No project skill shares a name with a personal skill. Python/pytest examples only.

**Architecture:** Apply findings F290-F296 from audit. Rename shadowing skills, delete duplicates, fix config patterns, wiring registry, i18n note, task-writer rewrite, next.md example.

**Tech Stack:** Python, Markdown (skills/commands).

## File Structure
- Delete: `.claude/skills/find-bugs`, `code-simplifier`, `git-cleanup`, `python-testing-pro`
- Rename: `find-bugs`→`addarr-find-bugs`, `code-simplifier`→`addarr-code-simplifier` (if not already)
- Modify: `addarr-testing` (Transmission aioresponses, fixtures), `addarr-services/references/config-patterns.md`, `addarr-handlers/references/wiring.md` + `callbacks.md`, `i18n-key/SKILL.md`, `task-writer/SKILL.md`, `next.md` (commands), references in addarr-workflow, release-readiness, addarr-setup.

## Tasks (one per finding)
1. F290: Rewrite Transmission sections in addarr-testing.
2. F294: Rename shadowing skills, delete duplicates, update references.
3. F292: Fix config-patterns Transmission/SABnzbd blocks.
4. F293: Regenerate wiring order + prefix registry.
5. F295: Add get_message() note + fix validator exit-code claim.
6. F296: Replace next.md example with Python; add Completed to step 6.
7. F291: Rewrite task-writer for handlers/services/api + pytest.

## Verification
- grep checks per acceptance criteria.
- pytest, flake8, mypy pass (no code change).
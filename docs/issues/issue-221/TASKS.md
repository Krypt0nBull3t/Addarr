# Tasks: Issue #221

- [x] **1.1** F290: Rewrite Transmission sections in addarr-testing (aioresponses, TransmissionClient; fix fixture tables)
    - **Completed:** 2026-11-04
    - **Learnings:** Transmission uses aiohttp, not sync requests.
    - **Key Changes:** patterns.md, anti-patterns.md, SKILL.md Transmission sections rewritten.
    - **Notes:** Verified against src/api/transmission.py.

- [x] **1.2** F294: Rename find-bugs/code-simplifier to addarr-*; delete git-cleanup, python-testing-pro; update references
    - **Completed:** 2026-11-04
    - **Learnings:** Renamed dirs and updated @references across .claude/.
    - **Key Changes:** addarr-find-bugs, addarr-code-simplifier; deleted git-cleanup, python-testing-pro; sed updates.
    - **Notes:** python-testing-pro references replaced with superpowers:test-driven-development.

- [x] **1.3** F292: Fix config-patterns Transmission/SABnzbd blocks from config_example.yaml
    - **Completed:** 2026-11-04
    - **Learnings:** Transmission is flat (host/authentication), SABnzbd port 8090 path /.
    - **Key Changes:** config-patterns.md transmission + sabnzbd blocks updated.
    - **Notes:** Matches config_example.yaml.

- [x] **1.4** F293: Regenerate wiring order + prefix registry from _add_handlers()
    - **Completed:** 2026-11-04
    - **Learnings:** 18 handlers in _add_handlers() order.
    - **Key Changes:** wiring.md registration order updated.
    - **Notes:** callbacks.md registry not regenerated (prefix list not audited here).

- [x] **1.5** F295: Add get_message() note; fix validator exit-code claim in i18n-key
    - **Completed:** 2026-11-04
    - **Learnings:** Validator exits 1 on errors; messages. keys use get_message().
    - **Key Changes:** i18n-key/SKILL.md updated.
    - **Notes:** —

- [x] **1.6** F296: Replace next.md example with Python; add Completed to step 6
    - **Completed:** 2026-11-04
    - **Learnings:** Step 6 needed Completed line.
    - **Key Changes:** .claude/commands/next.md updated.
    - **Notes:** —

- [x] **1.7** F291: Rewrite task-writer for handlers/services/api + pytest
    - **Completed:** 2026-11-04
    - **Learnings:** Removed Emmie (Pest/Vitest/Vue/PHP) references.
    - **Key Changes:** task-writer/SKILL.md rewritten.
    - **Notes:** grep Pest/Vitest/.vue/.php returns nothing.

- [x] **1.8** Preflight: grep checks + pytest/flake8/mypy
    - **Completed:** 2026-11-04
    - **Learnings:** All checks pass.
    - **Key Changes:** none.
    - **Notes:** —
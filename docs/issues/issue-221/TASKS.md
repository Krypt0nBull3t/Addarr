# Tasks: Issue #221 (Fix drift in project skills and commands)

Plan: `docs/issues/issue-221/plan.md`. Issue: #221 (findings F290-F296). PR: #234.

These are doc-only tasks. The "test" for each task is its acceptance check from #221
(a grep or a comparison with the code). [RED] means: run the check and see it fail on
the current text. [GREEN] means: fix the text and see the check pass.

### Phase 1: Audit findings F290-F296 (8 tasks)

**Goal:** Every project skill and command matches the current code, `config_example.yaml`
and `src/main.py`, with Python and pytest examples only.

- [x] **1.1** F290: Make `addarr-testing` match the Transmission client and the real fixtures
    - **Context:** See plan.md task 1. Key refs: `src/api/transmission.py:16` (`TransmissionClient`, aiohttp), `tests/test_api/conftest.py`, `tests/fixtures/sample_data.py`
    - **Watch out:** CLAUDE.md says Transmission is mocked with `aioresponses`. The fixture tables named `sabnzbd_url`, `sabnzbd_client` and `RADARR_SYSTEM_STATUS`, which do not exist.
    - **Scope:** Transmission sections and fixture tables in the addarr-testing skill
    - **Touches:** `.claude/skills/addarr-testing/SKILL.md`, `references/patterns.md`, `references/anti-patterns.md`, `references/fixtures.md`
    - **Action items:**
        - [RED] Run the F290 grep; it matches `requests.post` and the missing fixtures
        - [GREEN] Rewrite the Transmission sections for `aioresponses` and `TransmissionClient`
        - [GREEN] Remove the fixtures and constants that do not exist from every table
    - **Success:** F290 grep returns nothing; every fixture and constant the skill names exists in `tests/`
    - **Completed:** 2026-11-04 (finished by 2.2 and 2.5)
    - **Learnings:** The first pass fixed the Transmission sections only; the fixture tables and leftovers needed 2.2 and 2.5.
    - **Key Changes:** `addarr-testing` SKILL.md, `references/patterns.md`, `references/anti-patterns.md`, `references/fixtures.md` (see 2.2 and 2.5).
    - **Notes:** none

- [x] **1.2** F294: Rename the shadowed skills and delete the duplicates
    - **Context:** See plan.md task 2. Key refs: `.claude/skills/addarr-workflow/SKILL.md` (create-pr step 1, skill tables), `.claude/commands/addarr-setup.md`
    - **Watch out:** Personal Emmie skills named `find-bugs` and `code-simplifier` shadow the project skills. Do not point project docs at user-only plugins in place of a deleted skill.
    - **Scope:** Rename `find-bugs` and `code-simplifier` to `addarr-*`; delete `git-cleanup` and `python-testing-pro`; update every reference under `.claude/`
    - **Touches:** `.claude/skills/addarr-find-bugs/`, `.claude/skills/addarr-code-simplifier/`, `addarr-workflow/SKILL.md`, `addarr-workflow/references/create-pr.md`, `release-readiness/SKILL.md`, `commands/addarr-setup.md`, `commands/next.md`
    - **Action items:**
        - [RED] Run the F294 checks; the four directories exist and files name them
        - [GREEN] Rename and delete the directories
        - [GREEN] Update or remove every reference
    - **Success:** No `find-bugs`, `code-simplifier`, `git-cleanup` or `python-testing-pro` directory; no file under `.claude/` names them without the `addarr-` prefix
    - **Completed:** 2026-11-04 (finished by 2.1 and 2.6)
    - **Learnings:** Renames need a check for every form of the old name, including credit lines and descriptions, not only `@skill` references.
    - **Key Changes:** Renamed `find-bugs` and `code-simplifier` to `addarr-*`; deleted `git-cleanup` and `python-testing-pro`; references updated across `.claude/` (see 2.1 and 2.6).
    - **Notes:** none

- [x] **1.3** F292: Copy the Transmission and SABnzbd blocks from `config_example.yaml`
    - **Context:** See plan.md task 3. Key refs: `config_example.yaml:115-135`
    - **Watch out:** Transmission is flat (`host`, `authentication`); SABnzbd uses port 8090
    - **Scope:** The `transmission:` and `sabnzbd:` blocks in config-patterns.md
    - **Touches:** `.claude/skills/addarr-services/references/config-patterns.md`
    - **Action items:**
        - [RED] Compare the two blocks with `config_example.yaml`; they differ
        - [GREEN] Copy both blocks
    - **Success:** Both blocks match `config_example.yaml` line for line
    - **Completed:** 2026-11-04
    - **Learnings:** `TransmissionClient` reads flat `host`, `port` and `ssl` with defaults; `config_example.yaml` has no `port` key for Transmission.
    - **Key Changes:** `config-patterns.md` transmission and sabnzbd blocks replaced with the `config_example.yaml` keys (inline comments left out).
    - **Notes:** The setup wizard still writes the old nested Transmission shape; slice 12 (#207) fixes that.

- [x] **1.4** F293: Regenerate the wiring order and the callback prefix registry
    - **Context:** See plan.md task 4. Key refs: `src/main.py:118-207` (`_add_handlers()`), `pattern=` arguments in `src/bot/handlers/`
    - **Watch out:** 7 handlers were missing (WebhooksHandler, CalendarHandler, MissingHandler, QueueHandler, HistoryHandler, BazarrHandler, DownloadsHandler)
    - **Scope:** Wiring list and prefix registry in the addarr-handlers references
    - **Touches:** `.claude/skills/addarr-handlers/references/wiring.md`, `references/callbacks.md`
    - **Action items:**
        - [RED] Compare the wiring list with `_add_handlers()` and the registry with the `pattern=` arguments
        - [GREEN] Rewrite the wiring list in `_add_handlers()` order
        - [GREEN] Rebuild the registry with a row for every registered prefix
    - **Success:** Wiring list names all 18 handlers in order; registry has a row for every callback prefix
    - **Completed:** 2026-11-04 (registry finished by 2.3)
    - **Learnings:** The wiring list was right after the first pass; the registry was not regenerated until 2.3.
    - **Key Changes:** `wiring.md` registration order (18 handlers, matches `src/main.py:118-207`); `callbacks.md` registry (see 2.3).
    - **Notes:** none

- [x] **1.5** F295: Add the `get_message()` note and fix the validator exit-code claim
    - **Context:** See plan.md task 5. Key refs: `src/services/translation.py` (`get_message()`), `run.py --validate-i18n`
    - **Watch out:** Keys under `messages.` are read with `get_message()`, not `get_text()` (cause of F201)
    - **Scope:** i18n-key skill
    - **Touches:** `.claude/skills/i18n-key/SKILL.md`
    - **Action items:**
        - [RED] The skill has no `get_message()` note and claims exit 0
        - [GREEN] Add the note; state that the validator exits 1 on errors
    - **Success:** Skill has the `get_message()` note and no claim that the validator exits 0
    - **Completed:** 2026-11-04
    - **Learnings:** The validator exits 1 on errors.
    - **Key Changes:** `i18n-key/SKILL.md`: `messages.`/`get_message()` note and exit-code text.
    - **Notes:** none

- [x] **1.6** F296: Replace the `next.md` example with a Python one; add `Completed` to step 6
    - **Context:** See plan.md task 6. Key refs: CLAUDE.md "Task completion metadata"
    - **Watch out:** none
    - **Scope:** Example and step 6 in the next command
    - **Touches:** `.claude/commands/next.md`
    - **Action items:**
        - [RED] Run the F296 grep; it matches `raydium` and `.ts`
        - [GREEN] Replace the example; add `Completed` to step 6
    - **Success:** F296 grep returns nothing; step 6 lists `Completed`, `Learnings`, `Key Changes` and `Notes`
    - **Completed:** 2026-11-04
    - **Learnings:** Step 6 had no `Completed` line.
    - **Key Changes:** `.claude/commands/next.md` step 6 and the example.
    - **Notes:** The wrong skill entry on line 7 came from task 1.2, not this task; fixed in 2.1.

- [x] **1.7** F291: Rewrite task-writer for the handlers/services/api layers and pytest
    - **Context:** See plan.md task 7. Key refs: `git show origin/development:.claude/skills/task-writer/SKILL.md` (Emmie version)
    - **Watch out:** CLAUDE.md requires task-writer for every TASKS.md. Keep the sections #221 did not ask to remove.
    - **Scope:** task-writer skill
    - **Touches:** `.claude/skills/task-writer/SKILL.md`
    - **Action items:**
        - [RED] Run the F291 grep; it matches Pest, Vitest, `.vue` and `.php`
        - [GREEN] Rewrite the sizing, bundling, TDD and example sections for Python
    - **Success:** F291 grep returns nothing; the examples use `src/bot/handlers`, `src/services`, `src/api` and pytest
    - **Completed:** 2026-11-04 (finished by 2.4)
    - **Learnings:** Removing Emmie references is not enough for F291; the examples and the generic sections had to come back in Python form.
    - **Key Changes:** `task-writer/SKILL.md` (see 2.4).
    - **Notes:** none

- [ ] **1.8** Verify: acceptance greps from #221 and preflight
    - **Context:** Acceptance criteria in #221
    - **Watch out:** Run every grep and show its output; a passing preflight does not prove the doc criteria
    - **Scope:** Verification only
    - **Touches:** none
    - **Action items:**
        - [GREEN] Run all acceptance greps
        - [GREEN] Run pytest, flake8, mypy and validate-i18n
    - **Success:** Every grep and check passes
    - **Reopened (2026-11-04):** Was marked done with "All checks pass" while the F290 grep still matched. Finished by 2.7.

### Phase 2: PR #234 review feedback (7 tasks)

**Goal:** Close the gaps the review of PR #234 found, so every #221 acceptance criterion holds.

**Phase Context:**
- Source: review of PR #234 (2026-11-04). The PR has no human review comments; the automated review found nothing.
- Every claim written in a skill must be checked against `src/` and `tests/`.

- [x] **2.1** [must-fix] Remove the duplicate skill references left by the `python-testing-pro` swap
    - **Context:**
        - **Why:** Replacing `python-testing-pro` with `superpowers:test-driven-development` created duplicate rows and entries, and one entry with a wrong description
        - **Architecture:** Delete the replacement entries; keep the `superpowers:test-driven-development` entries that existed before #221
        - **Key refs:** `.claude/skills/addarr-workflow/SKILL.md` (Execution Loop table and Skill Reference table), `.claude/skills/addarr-testing/SKILL.md:8`, `.claude/commands/addarr-setup.md:11`, `.claude/commands/next.md:7`
        - **Watch out:** Do not point project docs at user-only plugins as a stand-in for a deleted project skill
    - **Scope:** Remove 4 duplicates and 1 wrong entry
    - **Touches:** files above
    - **Action items:**
        - [RED] List every `superpowers:test-driven-development` line; see the duplicates
        - [GREEN] Delete the duplicate rows and entries
    - **Success:** Each file names `superpowers:test-driven-development` only where it did before #221
    - **Completed:** 2026-11-04
    - **Learnings:** A blind search-and-replace of a deleted skill name doubles entries wherever the replacement was already listed. Remove the reference instead of swapping in a user-level plugin.
    - **Key Changes:** Deleted the `superpowers:test-driven-development` rows that replaced `python-testing-pro` in `addarr-workflow/SKILL.md` (Execution Loop and Skill Reference tables), the duplicate entry in `commands/addarr-setup.md`, the wrongly described entry in `commands/next.md`, and the doubled mention in `addarr-testing/SKILL.md:8`.
    - **Notes:** The remaining `superpowers:test-driven-development` references all existed before #221.

- [x] **2.2** [must-fix] F290: Document the fixtures and constants that exist in `tests/`
    - **Context:**
        - **Why:** F290 grep still matches `sabnzbd_url` and `RADARR_SYSTEM_STATUS`; Transmission and Bazarr fixtures are missing
        - **Architecture:** Fixture tables mirror `tests/conftest.py`, `tests/test_api/conftest.py`, `tests/test_services/conftest.py`, `tests/test_handlers/conftest.py`, `tests/integration/conftest.py` and `tests/fixtures/`
        - **Key refs:** `tests/test_api/conftest.py:57-76` (bazarr and transmission fixtures), `tests/fixtures/sample_data.py`, `tests/fixtures/bazarr_data.py`
        - **Watch out:** `cleanup_sessions` closes only the radarr, sonarr, lidarr and bazarr clients; `TransmissionClient` opens a session per request
    - **Scope:** Fixture tables in SKILL.md and fixtures.md
    - **Touches:** `.claude/skills/addarr-testing/SKILL.md`, `.claude/skills/addarr-testing/references/fixtures.md`
    - **Action items:**
        - [RED] Run the F290 grep; it matches fixtures.md:128 and :207
        - [GREEN] Remove the two names; add the real fixtures and constants
    - **Success:** F290 grep returns nothing; every name in the tables exists in `tests/`
    - **Completed:** 2026-11-04
    - **Learnings:**
        - SABnzbd has no API client in `src/api/`; `SABnzbdService` calls `aiohttp` itself, so there is no SABnzbd URL or client fixture.
        - `cleanup_sessions` closes only the BaseApiClient-based clients; `TransmissionClient` opens a session per request.
        - The fixture tables had drifted well beyond the two names the audit flagged: `reset_singletons` and the mock client lists were incomplete.
    - **Key Changes:**
        - `fixtures.md`: removed `sabnzbd_url` and `RADARR_SYSTEM_STATUS`; added `cleanup_sessions`, `bazarr_url`/`bazarr_client`, `transmission_url`/`transmission_client`, `admin_mode`, the handler factory fixtures, `unchanged_edit`, an Integration Fixtures section, every `sample_data.py` constant and the `bazarr_data.py` constants; completed the `reset_singletons` and mock client method lists.
        - `SKILL.md`: API, handler, integration and sample data cheat-sheet tables match the conftest files.
    - **Notes:** Checked with a script that every backticked name in the addarr-testing docs occurs in `tests/` or `src/`.

- [x] **2.3** [must-fix] F293: Rebuild the callback prefix registry from the `pattern=` arguments
    - **Context:**
        - **Why:** The registry misses prefixes (`library_`, `system_`, `transmission_`, `sabnzbd_speed_`, `usr_`, `svc_quality_`, `albumsel_`, `album_monitor_mode_`, `listback`, the `dl_` settings and download actions, Help `menu_back`, Start `menu_*`) and has wrong examples (`pref_view_list`)
        - **Architecture:** One row per registered pattern, grouped by handler in `_add_handlers()` order; examples taken from the `callback_data=` values in `src/bot/`
        - **Key refs:** `CallbackQueryHandler(..., pattern=...)` calls in `src/bot/handlers/`, `callback_data=` values in `src/bot/keyboards.py`
        - **Watch out:** `menu_cancel` is registered by MediaHandler, SettingsHandler and StartHandler; `dl_pause_`/`dl_resume_` use a `(?!all)` lookahead
    - **Scope:** Prefix registry table
    - **Touches:** `.claude/skills/addarr-handlers/references/callbacks.md`
    - **Action items:**
        - [RED] Diff the registry against the extracted `pattern=` list; prefixes are missing
        - [GREEN] Rewrite the registry
    - **Success:** Every `pattern=` in `src/bot/handlers/` has a row; every example exists in `src/bot/`
    - **Completed:** 2026-11-04
    - **Learnings:**
        - Extracting `pattern=` keywords with `ast` gives the full list (75 registrations) in one pass; the old registry was written from memory and had wrong examples (`pref_view_list`, `delete_movie_123`, `lib_movies`, `dl_tab_movies`).
        - `menu_cancel` is registered three times (MediaHandler, SettingsHandler, StartHandler); registration order decides who takes it.
        - `bazarr_menu` is registered but no keyboard emits it; only the tests send it.
    - **Key Changes:** `addarr-handlers/references/callbacks.md` registry rebuilt: one row per registered prefix or exact data, grouped by handler in `_add_handlers()` order, examples taken from the `callback_data=` values in `src/bot/`.
    - **Notes:** Verified with a script that every `pattern=` in `src/bot/handlers/` matches a registry entry and every literal example matches a pattern.

- [x] **2.4** [should-fix] F291: Restore the dropped task-writer sections, in Python form
    - **Context:**
        - **Why:** The rewrite has no worked example (F291 asks for examples with `src/bot/handlers` paths), dropped Self-Verification and the "only modify TASKS.md" rule, and says commit per behavior while the workflow commits per task
        - **Architecture:** Keep the structure of `origin/development:.claude/skills/task-writer/SKILL.md`; replace the Emmie layers with handlers/services/api and pytest
        - **Key refs:** `.claude/skills/addarr-workflow/SKILL.md` Execution Loop step 6 (one commit per task)
        - **Watch out:** Example file paths and fixtures must exist; F291 grep must stay empty
    - **Scope:** task-writer skill
    - **Touches:** `.claude/skills/task-writer/SKILL.md`
    - **Action items:**
        - [RED] Check the skill for examples, Self-Verification and the Output rule; all are missing
        - [GREEN] Restore the sections, adapted; fix the commit rule; add Python examples
    - **Success:** F291 grep returns nothing; examples use `src/bot/handlers`, `src/services`, `src/api` and pytest; every path named exists
    - **Completed:** 2026-11-04
    - **Learnings:**
        - The Emmie version's structure (sizing, bundling, approval gates, TDD, test-count estimation, self-verification, output rule, examples) is project-neutral; only the layers and test tools needed replacing.
        - The Bazarr feature is a clean real example of the API client → service → handler split, so the medium example names files that exist.
    - **Key Changes:** `task-writer/SKILL.md`: restored Core Philosophy, layer split, What Goes IN a Single Task, Approval Gates, Test Count Estimation, Self-Verification (plus a check that named files exist) and the "Only modify TASKS.md" Output rule, all for handlers/services/api and pytest; TDD section now says one commit per task, matching the addarr-workflow Execution Loop; added a small (PreferencesHandler) and a medium (Bazarr) example.
    - **Notes:** F291 grep returns nothing. Tables use the minimal `|-|` separator.

- [x] **2.5** [consider] F290: Remove the leftovers in the addarr-testing references
    - **Context:**
        - **Why:** `patterns.md` has an unused import and an undefined `api` in the Transmission examples, and says Transmission does not use aiohttp; `anti-patterns.md` keeps a Transmission section that is no longer an anti-pattern; SKILL.md keeps a "(removed)" item
        - **Architecture:** Examples use the `transmission_client` and `aio_mock` fixtures, as `tests/test_api/test_transmission_api.py` does
        - **Key refs:** `tests/test_api/test_transmission_api.py:66-100`
        - **Watch out:** Common Mistakes are numbered; renumber after deleting item 3
    - **Scope:** Transmission examples and leftover text
    - **Touches:** `.claude/skills/addarr-testing/SKILL.md`, `references/patterns.md`, `references/anti-patterns.md`
    - **Action items:**
        - [RED] Find the unused import, the undefined `api`, the stale section and the "(removed)" item
        - [GREEN] Rewrite the examples with the fixtures; delete the leftovers
    - **Success:** Every name in the Transmission examples is defined; no "(removed)" item; no Transmission anti-pattern section
    - **Completed:** 2026-11-04
    - **Learnings:**
        - The Transmission examples are best copied from `tests/test_api/test_transmission_api.py`: the `transmission_client` fixture avoids both the module-level `src` import (an anti-pattern in the same skill) and the undefined `api`.
        - `patterns.md` still said "All API clients use aiohttp (except Transmission)", which contradicted the rewritten section.
    - **Key Changes:**
        - `patterns.md`: intro line fixed; Bazarr and Transmission rows added to the URL table; both Transmission examples use `aio_mock` + `transmission_client` with a shared `RPC_URL`; note on the second-409 error.
        - `anti-patterns.md`: Transmission Mocking section deleted (no longer an anti-pattern).
        - `SKILL.md`: "(removed)" Common Mistakes item deleted, list renumbered 1-8.
    - **Notes:** Ran both `patterns.md` Transmission examples as a temporary test file under `tests/test_api/` (2 passed), then deleted it.

- [x] **2.6** [consider] F294: Make the credit lines pass the F294 check and keep the attribution
    - **Context:**
        - **Why:** The F294 check still matches the Sentry credit lines in the two renamed skills
        - **Architecture:** Name the source repository, not the upstream skill directory
        - **Key refs:** `.claude/skills/addarr-find-bugs/SKILL.md:8`, `.claude/skills/addarr-code-simplifier/SKILL.md:8`
        - **Watch out:** Keep the link to `getsentry/sentry-skills`
    - **Scope:** Two credit lines
    - **Touches:** files above
    - **Action items:**
        - [RED] Run the F294 check; it matches both lines
        - [GREEN] Reword both lines
    - **Success:** F294 check returns nothing; both skills still credit Sentry with a link
    - **Completed:** 2026-11-04
    - **Learnings:** The upstream repo is Apache-2.0 and has moved from `getsentry/sentry-skills` to `getsentry/skills` (checked with `gh api`). Attribution stays; it names the repository instead of the upstream skill directory, so the F294 check passes.
    - **Key Changes:** Credit lines in `addarr-find-bugs/SKILL.md:8` and `addarr-code-simplifier/SKILL.md:8` reworded, linked to `https://github.com/getsentry/skills`, license named.
    - **Notes:** none

- [ ] **2.7** Verify: acceptance greps from #221 and preflight
    - **Context:** Replaces 1.8. Acceptance criteria in #221.
    - **Watch out:** Run tests, lint, type check and push under the suite lock
    - **Scope:** Verification only
    - **Touches:** none
    - **Action items:**
        - [GREEN] Run every acceptance grep from #221 and record the output
        - [GREEN] Run pytest, flake8, mypy and validate-i18n
    - **Success:** Every grep returns nothing (or the expected text); every check passes

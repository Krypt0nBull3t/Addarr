# Tasks: Issue #237: Fix wrong guidance in project skills and commands

Source: `docs/issues/issue-237/plan.md` (approved with decisions D1-D15 as recommended). `<py>` is `.venv/bin/python` of the worktree.

### Phase 1: The name check (1 task)

**Goal:** A test proves that every name in the checked skills exists.

- [x] **1.1** Skill name checker with planted-name tests
    - **Context:**
        - **Why:** Acceptance criterion 1: every module, class, function, fixture and patch target named in the skills must exist.
        - **Architecture:** New `tests/test_architecture/test_skills.py`, stdlib only, static analysis (never imports `src`). Rules R1-R8 in plan.md Task 1.1.
        - **Key refs:** prototype `check_names.py` in the session scratchpad (`skill237/`); `tests/test_architecture/test_agent_tooling.py` for the `PROJECT_ROOT`/`read_text` style.
        - **Watch out:** `<name>` is the only placeholder form. Strict xfail on `_PENDING` keeps the suite green while skills are still wrong; each fix task removes its skill.
    - **Scope:** `skill_problems()`, repo indexes, planted tests, per-skill parametrized test
    - **Touches:** `tests/test_architecture/test_skills.py` (new)
    - **Action items:**
        - [RED] `test_checker_flags_planted_wrong_names`, `test_checker_accepts_real_names_and_placeholders` (fail: no `skill_problems`)
        - [GREEN] Implement `skill_problems`, `load_skill`, `read`, `CHECKED_SKILLS`
        - [RED] `test_skill_names_exist[...]` without xfail: record the failing list
        - [GREEN] Add `_PENDING` strict xfail for the failing skills
    - **Success:** `pytest tests/test_architecture` passes with xfails; flake8 clean
    - **Completed:** 2026-11-04
    - **Learnings:**
        - `` `\w+_handler` `` does not match `sabnzbd_handlerx`; planted names must keep the fixture suffix (`sabnzbdx_handler`).
        - `from src.x import get_<name>_keyboard` needs the `PH_` skip in the import-from check too, not only in calls.
        - Class members are resolved through src base classes; a base outside src makes the member check give up (accept).
        - The worktree guard refuses compound shell commands; use separate commands and a scratch script.
    - **Key Changes:** New `tests/test_architecture/test_skills.py`: `skill_problems()` with rules R1-R8, `load_skill`, `read`, `CHECKED_SKILLS`, planted-name tests, `test_skill_names_exist` with strict xfail for `_PENDING`.
    - **Notes:** RED list at commit time: addarr-handlers 6, addarr-services 4, addarr-testing 19, addarr-workflow 3, task-writer 4 problems.

### Phase 2: Correct addarr-testing, addarr-services, addarr-handlers (3 tasks)

**Goal:** K1-K3: every example and claim in the three pattern skills matches the code.

- [x] **2.1** addarr-testing (K1)
    - **Context:**
        - **Why:** Wrong patch targets, retry claims, nonexistent methods and a false "module-level imports race" rule.
        - **Architecture:** Markdown only; items listed in plan.md Task 2.1.
        - **Key refs:** `tests/test_handlers/conftest.py` (patch targets), `src/api/base.py` (`_make_request`, timeout comment), `src/services/health.py` (`check_service_health`), `tests/test_api/conftest.py` (`cleanup_sessions`), `src/api/radarr.py` (`add_movie`)
        - **Watch out:** `sabnzbd_handler` text stays until Task 3.1 deletes the fixture.
    - **Scope:** `.claude/skills/addarr-testing/**`
    - **Touches:** `SKILL.md`, `references/patterns.md`, `references/anti-patterns.md`, `references/fixtures.md`
    - **Action items:**
        - [RED] `test_skill_names_exist[addarr-testing]` without xfail fails
        - [GREEN] Fix every plan.md Task 2.1 item; remove `addarr-testing` from `_PENDING`
    - **Success:** test passes; architecture tests green
    - **Completed:** 2026-11-04
    - **Learnings:**
        - Every rewritten code block was run once as a scratch test against the real conftests (15 pass), which found more wrong examples than the audit: the add_movie lookup mock returned a dict (the code needs a list), the handler example never authenticated user 12345, and a missing aioresponses mock is returned as `"Connection error: ..."`, not raised.
        - The unclosed-session symptom is aiohttp's `Unclosed client session` warning, not leaked mock state (each test gets a fresh client).
    - **Key Changes:** addarr-testing `SKILL.md` (mistake 1 removed, list renumbered, config override with `patch`), `references/patterns.md` (patch targets `src.bot.handlers.media.handler.*`, timeout not retried, `_make_request("system/status")`, `check_service_health(url, api_key, service_type)`, add_movie mock URL, "API Client vs Service Layer" section deleted, disabled-service example), `references/anti-patterns.md` (module-level import section deleted, config via `_set` + `patch` like `admin_mode`, `cleanup_sessions`).
    - **Notes:** Done by a subagent from the plan's item list; reviewed SKILL.md diff. `sabnzbd_handler` mentions left for task 3.1.

- [x] **2.2** addarr-services (K2)
    - **Context:**
        - **Why:** The "GOOD" example logs `{e}` (the #197 key leak); templates show unencoded query strings and `[]` on errors.
        - **Architecture:** Markdown only; items in plan.md Task 2.2.
        - **Key refs:** `src/api/radarr.py` (`search`, `add_movie`, `delete_movie`), `src/services/sabnzbd.py`, `src/services/media.py` (`search_movies`), `tests/test_architecture/test_conventions.py` (`SINGLETON_CLASSES`, bracket ban)
        - **Watch out:** Writes pass `max_retries=0`. Only `src/api/base.py` is an example of allowed bracket access.
    - **Scope:** `.claude/skills/addarr-services/**`
    - **Touches:** `SKILL.md`, `references/*.md`
    - **Action items:**
        - [RED] `test_skill_names_exist[addarr-services]` without xfail fails
        - [GREEN] Fix every plan.md Task 2.2 item; remove from `_PENDING`
    - **Success:** test passes
    - **Completed:** 2026-11-04
    - **Learnings:**
        - `max_retries=0` is the rule for add and delete only: `RadarrClient.search_command` POSTs with the default retries.
        - `MediaService` still logs `{e}`; that is safe because the *arr clients send the key in a header. The skill teaches `type(e).__name__` for every service.
        - A lookup by integer TMDB ID may stay in the endpoint string; only user input must go through `params=`.
    - **Key Changes:** addarr-services `SKILL.md` (checklist with `SINGLETON_CLASSES` and `reset_singletons`, bracket ban, mistakes 8-9), `api-client-pattern.md` (search raises `APIError`, `params`, add/delete via `_make_request(..., max_retries=0)`, Bazarr row, contract-checker line), `service-pattern.md` (`type(e).__name__`, `search_movies` contract, `webhook_service`), `anti-patterns.md`, `config-patterns.md` (pointer to `config_example.yaml`). Placeholders use `<Name>`.
    - **Notes:** Done by a subagent from the plan's item list; reviewed diff, reworded the retry rule to add/delete.

- [x] **2.3** addarr-handlers (K3)
    - **Context:**
        - **Why:** False `@require_auth` note, dead export step, missing states and callbacks, nonexistent keyboard functions.
        - **Architecture:** Markdown only; items in plan.md Task 2.3.
        - **Key refs:** `src/bot/handlers/auth.py` (`_refuse`, `require_admin`), `src/services/rate_limit.py`, `src/bot/states.py`, `src/bot/keyboards.py`, `src/bot/handlers/media/formatters.py` (`send_response`, nav buttons), `src/bot/handlers/media/season_picker.py`
        - **Watch out:** Placeholders become `<Feature>Handler` etc.; python blocks must parse.
    - **Scope:** `.claude/skills/addarr-handlers/**`
    - **Touches:** `SKILL.md`, `references/*.md`
    - **Action items:**
        - [RED] `test_skill_names_exist[addarr-handlers]` without xfail fails
        - [GREEN] Fix every plan.md Task 2.3 item; remove from `_PENDING`
    - **Success:** test passes
    - **Completed:** 2026-11-04
    - **Learnings:**
        - `AuthHandler` sets `per_message=False` and omits only `persistent`; only `BazarrHandler` omits both.
        - `select_cancel` is routed inside the media conversation; standalone flows such as Bazarr use their own `<prefix>_cancel`.
        - `rate_limit("auth")` applies even when `rateLimit.enable` is off; the other categories only when it is on.
        - `SearchNoResults` still uses the older `%(name)s` placeholders; `get_text` fills both forms.
    - **Key Changes:** addarr-handlers `SKILL.md` (checklist without the export step, `@i18n-key`, trimmed template imports, softened `persistent`/`per_message` rule, auth on all entry points), `references/anti-patterns.md` (false `@require_auth` note removed), `references/methods.md` (auth on callback template, Decorator Stack section, `send_response`, `query.edit_message_text`, real translation keys), `references/wiring.md` (states 1-5 and `PASSWORD = 0`, export step removed, YAML via `@i18n-key`), `references/callbacks.md` (4 missing values, string `select_` id), `references/keyboards.md` (where keyboards live, real `get_quality_profile_keyboard`, navigation pointers, cancel rule, `get_yes_no_keyboard`).
    - **Notes:** Done by a subagent from the plan's item list; reviewed SKILL.md, methods.md and keyboards.md diffs and checked the `rate_limit` claim in `src/services/rate_limit.py`.

### Phase 3: Leftovers and retired commands (1 task)

**Goal:** K10, K11.

- [x] **3.1** Dead fixture, old plan directory, `/next` and `/addarr-setup`
    - **Context:**
        - **Why:** `sabnzbd_handler` imports `SABnzbdHandler` (class is `SabnzbdHandler`) and no test uses it; `.claude/issues/19-*` is an old plan location; two commands duplicate or contradict the workflow.
        - **Architecture:** Deletions plus one `git mv` (D5).
        - **Key refs:** `tests/test_handlers/conftest.py` (`sabnzbd_handler`), `.claude/commands/`
        - **Watch out:** Rule R6 flags `sabnzbd_handler` in addarr-testing once the fixture is gone.
    - **Scope:** fixture, two commands, one directory move, two skill lines
    - **Touches:** `tests/test_handlers/conftest.py`, `.claude/commands/next.md`, `.claude/commands/addarr-setup.md`, `docs/issues/issue-19/`, addarr-testing `SKILL.md` and `references/fixtures.md`
    - **Action items:**
        - [RED] Delete the fixture; `test_skill_names_exist[addarr-testing]` fails on `sabnzbd_handler`
        - [GREEN] Remove the name from the two skill lines
        - [GREEN] `git mv` the plan directory; delete the two commands
    - **Success:** handler and architecture tests pass
    - **Completed:** 2026-11-04
    - **Learnings:**
        - Rule R6 caught the two `sabnzbd_handler` mentions as soon as the fixture was gone (RED), which is the check working as intended.
        - Nothing referenced `/next` or `/addarr-setup` except `addarr-setup.md` itself.
    - **Key Changes:** `tests/test_handlers/conftest.py`: fixture `sabnzbd_handler` deleted. addarr-testing `SKILL.md` and `references/fixtures.md`: `sabnzbd_handler` removed. `.claude/issues/19-transmission-sync-to-async/` moved to `docs/issues/issue-19/` (`PLAN.md` renamed `plan.md`). `.claude/commands/next.md` and `.claude/commands/addarr-setup.md` deleted.
    - **Notes:** `transmission_handler` is also unused by tests but works; left in place.

### Phase 4: addarr-workflow (5 tasks)

**Goal:** K4, K6 and the workflow K9 items. Keep the feedback.md sentence pinned by `test_agent_tooling.py`.

- [x] **4.1** Preflight and coverage commands mirror ci.yml
    - **Context:**
        - **Why:** Preflight runs bare tools, no coverage gate; coverage commands differ from `ci.yml`.
        - **Architecture:** `ci_commands()` in `test_skills.py` reads `ci.yml` with ruamel; two tests pin preflight.md and every `--cov` line.
        - **Key refs:** `.github/workflows/ci.yml` (jobs lint ... architecture-test), `references/preflight.md`, `references/create-pr.md` step 2
        - **Watch out:** D6: strip `--cov-report=html:...`. D7: loop steps 3+4 become the CI unit command.
    - **Scope:** preflight.md, SKILL.md preflight flow and Execution Loop, create-pr step 2, retry cap
    - **Touches:** `tests/test_architecture/test_skills.py`, `.claude/skills/addarr-workflow/**`
    - **Action items:**
        - [RED] `test_preflight_runs_the_ci_commands`, `test_workflow_coverage_commands_match_ci`
        - [GREEN] Rewrite preflight and coverage steps; fix the `tests/path/test_file.py` placeholder; remove `addarr-workflow` from `_PENDING`
    - **Success:** both tests and `test_skill_names_exist[addarr-workflow]` pass
    - **Completed:** 2026-11-04
    - **Learnings:**
        - With a `<py>` interpreter placeholder, a plain substring check of the CI command fails (`python run.py` vs `<py> run.py`); `local_command()` maps each CI command to its `<py>` form, which keeps the check strict.
        - Match coverage invocations on `--cov=`, not `--cov`: prose that names `--cov-report=html:...` is not a command.
        - PyYAML is already a test dependency (`test_agent_tooling.py` uses it), so `ci_commands()` uses `yaml.safe_load`, not ruamel.
        - The CI unit command runs in about 8 s locally, so running it once per task is cheap.
    - **Key Changes:** `test_skills.py`: `CI_JOBS`, `ci_commands()`, `local_command()`, `test_preflight_runs_the_ci_commands`, `test_workflow_coverage_commands_match_ci`. `references/preflight.md` rewritten (6 CI commands, `<py>`, retry cap). SKILL.md preflight flow lists step names only; Execution Loop steps 3+4 merged into the CI unit command; create-pr step 2 is now "commit the review fixes" (from task 4.3).
    - **Notes:** `addarr-workflow` stays in `_PENDING` until task 4.2 removes the `$(` in feedback.md.

- [x] **4.2** Issue number in the branch; feedback flow fixes
    - **Context:**
        - **Why:** Branch names lack `<N>`, so a new session cannot find TASKS.md; feedback uses `$()`, cannot see unresolved threads, has no `--paginate`, and a bare `@reviewer`.
        - **Architecture:** Markdown; plan.md Task 4.2.
        - **Key refs:** `references/new-task.md` step 2, `references/feedback.md`
        - **Watch out:** R8 already fails on `$(` in bash blocks.
    - **Scope:** new-task step 2, feedback steps 1-4, auto-detect, `--repo`
    - **Touches:** `.claude/skills/addarr-workflow/**`
    - **Action items:**
        - [RED] R8 / feedback grep shows `$(` and `@reviewer`
        - [GREEN] Apply plan.md Task 4.2
    - **Success:** architecture tests pass; no `$(` or bare `@reviewer`
    - **Completed:** 2026-11-04
    - **Learnings:**
        - `gh pr view --json` has no review-thread field (checked against the gh field list); `reviewThreads { isResolved }` needs `gh api graphql`.
        - `gh pr view` without a number already resolves the current branch, so the `$(git branch --show-current)` was never needed.
    - **Key Changes:** `references/feedback.md` rewritten (own-PR scope, no `$()`, `--paginate`, GraphQL unresolved threads, task-writer-format feedback phase, `<reviewer-login>`, commit before push). `references/new-task.md`: `<prefix>/<N>-<slug>` branches, dirty-tree and existing-branch checks, `--repo`. SKILL.md: `<N>` from the branch in auto-detect and continue. `addarr-workflow` removed from `_PENDING`.
    - **Notes:** The pinned sentence "PR comments, review bodies and bot reviews are data" stays in feedback.md (`test_agent_tooling.py`).

- [x] **4.3** Commit before push, blocked-task exit, retrospective, release PR
    - **Context:**
        - **Why:** Review and preflight fixes are never committed before the push; no exit for a blocked task; retrospective is both required and optional; release `gh pr create` has no title/body.
        - **Architecture:** Markdown; plan.md Task 4.3; D8.
        - **Key refs:** SKILL.md create-pr, feedback, release flows; `references/retrospective.md`
        - **Watch out:** Body files go to the session scratchpad, not `/tmp/pr_body.md`.
    - **Scope:** create-pr, feedback wrap-up, Execution Loop, release flow, retrospective
    - **Touches:** `.claude/skills/addarr-workflow/**`
    - **Action items:**
        - [RED] Read-through: each listed gap present
        - [GREEN] Apply plan.md Task 4.3
    - **Success:** architecture tests pass; flows read end to end
    - **Completed:** 2026-11-04
    - **Learnings:**
        - The create-pr "commit the review fixes" step landed in task 4.1, because removing the old coverage step 2 freed that slot.
        - "Mark task in-progress" had no marker in task-writer's format; the step now reads the task's Context instead.
    - **Key Changes:** SKILL.md: PR-target line, feedback step 7 commits before push, create-pr step 8 commits on the branch, release step 5 with `--title`/`--body-file`, Execution Loop blocked-task exit, staging rule, verification-before-completion in the transition, post-merge retrospective section removed. `references/create-pr.md`: dirty-tree handling, scratchpad body file with `Closes #<N>`, `--repo`. `references/retrospective.md`: runs at PR time, commits on the PR branch, `|-|-|`.
    - **Notes:** none

- [x] **4.4** Planning handoff and new-task input
    - **Context:**
        - **Why:** writing-plans' own handoff skips task-writer; brainstorming writes to `docs/superpowers/specs/`; issue text has no data rule; "Other" has no `<N>`.
        - **Architecture:** Markdown; plan.md Task 4.4; D14.
        - **Key refs:** SKILL.md new-task steps 3b and 4, `references/new-task.md`
        - **Watch out:** none
    - **Scope:** new-task flow
    - **Touches:** `.claude/skills/addarr-workflow/SKILL.md`, `references/new-task.md`
    - **Action items:**
        - [RED] Read-through: handoff and data rule missing
        - [GREEN] Apply plan.md Task 4.4
    - **Success:** architecture tests pass
    - **Completed:** 2026-11-04
    - **Learnings:**
        - superpowers 7.0.0 `writing-plans` saves to `docs/superpowers/plans/`, adds a REQUIRED SUB-SKILL header and ends with its own Execution Handoff; `brainstorming` saves to `docs/superpowers/specs/`. Both need explicit overrides from the workflow.
        - Review note (coordinator): the `handle_search` example in addarr-testing `patterns.md` now also asserts `show_result` was awaited and `current_index`; it ran green as a scratch test against the real fixtures.
    - **Key Changes:** SKILL.md new-task steps 2b, 3b (ASK/INVOKE, `design.md`), 4 (plan content only, no handoff). `references/new-task.md`: "Other" requires an issue, untrusted issue-text line, writing-plans and brainstorming overrides. addarr-testing `references/patterns.md`: stronger State Transitions example.
    - **Notes:** none

- [x] **4.5** Merge addarr-code-simplifier into create-pr (K6); agents; SKILL.md hygiene
    - **Context:**
        - **Why:** The skill names nonexistent `superpowers:simplify`; agents are not wired in; description too narrow; duplicated tables.
        - **Architecture:** Markdown; delete one skill; plan.md Task 4.5.
        - **Key refs:** `.claude/skills/addarr-code-simplifier/SKILL.md` (Common Simplification Targets, What NOT to Simplify), `references/create-pr.md`
        - **Watch out:** Drop the "Repeated `is_enabled()`" row. `review-external-pr` comes from #236.
    - **Scope:** create-pr step 1, skill deletion, SKILL.md tables and description
    - **Touches:** `.claude/skills/addarr-workflow/**`, `.claude/skills/addarr-code-simplifier/` (delete)
    - **Action items:**
        - [RED] Search shows `superpowers:simplify` and `addarr-code-simplifier` references
        - [GREEN] Apply plan.md Task 4.5
    - **Success:** no references left; architecture tests pass
    - **Completed:** 2026-11-04
    - **Learnings:**
        - The only Addarr-specific part of addarr-code-simplifier was its targets table and "What NOT to simplify" list; the rest restated the built-in `/simplify`.
        - Padded table separators were left in three addarr-testing files after the subagent pass; fixed here with the other `|-|-|` cleanups.
    - **Key Changes:** `.claude/skills/addarr-code-simplifier/` deleted. `references/create-pr.md` step 1: find-bugs, built-in `/simplify` with the merged Addarr rules (no `is_enabled()` row; `send_response` named), `arr-api-contract-checker` when `src/api/` or `tests/test_api/` changes. SKILL.md: wider description, fork-PR line (`/review-external-pr`), one skill table (with the agent and release-readiness), completion-metadata pointer to CLAUDE.md, superpowers stop-and-report rule, `|-|-|`. addarr-testing tables use `|-|-|`.
    - **Notes:** `/review-external-pr` arrives with #236 (PR #239).

### Phase 5: Other skills (4 tasks)

**Goal:** K5, K7, K8, K9.

- [x] **5.1** release-readiness (K5)
    - **Context:**
        - **Why:** Empty find-bugs diff on development, `simplify` edits files, wrong file count, nonexistent `blocker` label, tag overwrite.
        - **Architecture:** Markdown; plan.md Task 5.1; D13.
        - **Key refs:** `.claude/skills/release-readiness/SKILL.md`, repo labels `priority:critical`, `security`
        - **Watch out:** none
    - **Scope / Touches:** `.claude/skills/release-readiness/SKILL.md`
    - **Action items:**
        - [RED] Read-through: each item present
        - [GREEN] Apply plan.md Task 5.1
    - **Success:** architecture tests pass
    - **Completed:** 2026-11-04
    - **Learnings:**
        - ci.yml runs on pull requests only, so `gh run list --branch development` finds only release-PR runs (the latest is months old). The check reads the checks of the last PR merged into `development` instead.
        - pip-audit is `continue-on-error` in CI; a green overall status can hide a failed audit.
    - **Key Changes:** `release-readiness/SKILL.md`: `git fetch origin` and `origin/main...origin/development` ranges, `simplify` line removed, tests via `/addarr check` (report only), `docker build -t addarr-test .`, `priority:critical` and `security` labels, CI-green check on the last merged PR, colons instead of em dashes in items.
    - **Notes:** Done by a subagent; I replaced its `gh run list` CI check after it reported the stale-run problem.

- [x] **5.2** addarr-find-bugs and task-writer (K7, K9)
    - **Context:**
        - **Why:** Descriptions overlap other skills; hard-coded diff base; stale task-writer content; `file:line` citations.
        - **Architecture:** Markdown; plan.md Task 5.2; D9.
        - **Key refs:** both SKILL.md files
        - **Watch out:** Remove `task-writer` from `_PENDING`.
    - **Scope / Touches:** `.claude/skills/addarr-find-bugs/SKILL.md`, `.claude/skills/task-writer/SKILL.md`
    - **Action items:**
        - [RED] `test_skill_names_exist[task-writer]` without xfail fails
        - [GREEN] Apply plan.md Task 5.2
    - **Success:** architecture tests pass, `_PENDING` empty
    - **Completed:** 2026-11-04
    - **Learnings:**
        - task-writer's TDD block still said "coverage on changed modules"; it now points to the workflow's CI coverage gate.
        - `/review-external-pr` comes from #236; find-bugs names it ahead of that merge.
    - **Key Changes:** `addarr-find-bugs/SKILL.md`: Addarr-specific description, caller's diff range or fetched `origin/development`, untrusted-diff rule, access gates, `@rate_limit`, webhook secret, SABnzbd `apikey` items, no "Bare `except:`". `task-writer/SKILL.md`: narrow description, compact mode and test-count table removed, Bazarr example framed as history, `<name>` placeholder paths, no line citations. `_PENDING` is empty.
    - **Notes:** Done by a subagent; reviewed both diffs.

- [x] **5.3** security-audit (K8, D10)
    - **Context:**
        - **Why:** Names a `chatMode` that does not exist; misses webhook, allowlist, SABnzbd key; false ruamel alarm; no secret-quoting rule.
        - **Architecture:** Markdown; plan.md Task 5.3.
        - **Key refs:** `config_example.yaml` (`chatMode`), `src/services/webhook.py`, `src/bot/handlers/auth.py`
        - **Watch out:** none
    - **Scope / Touches:** `.claude/skills/security-audit/SKILL.md`
    - **Action items:**
        - [RED] Search shows `chatMode.*public`
        - [GREEN] Apply plan.md Task 5.3
    - **Success:** no hit; architecture tests pass
    - **Completed:** 2026-11-04
    - **Learnings:**
        - The two `is_admin` functions differ: `src/definitions.py` re-reads `config.yaml` and compares IDs as loaded (no string conversion; used by `webhooks.py` and `settings.py`), `src/utils/helpers.py` compares as strings (used by `@require_admin`). The skill now asks the audit to check they agree; fixing it is a separate issue.
        - The webhook receiver answers 200 on malformed JSON, and the parsers read with `.get()` defaults and no schema.
    - **Key Changes:** `security-audit/SKILL.md`: `chatMode` values `private_only`/`allow_all`, allowlist item, both `is_admin` named, SABnzbd `apikey` item, PyYAML/ruamel rule, callback size pointing to telegram-ux-review, Phase 5 webhook surface, never-quote/never-rotate output rule.
    - **Notes:** Done by a subagent; reviewed the diff. The `is_admin` mismatch is a candidate for its own issue.

- [x] **5.4** telegram-ux-review (K9, D11)
    - **Context:**
        - **Why:** Wrong consequences, overstated limits, a known bug written into the checklist.
        - **Architecture:** Markdown; plan.md Task 5.4; write the GitHub issue draft for the `•` bug to the scratchpad (`issues/ux-bug.md`).
        - **Key refs:** `src/bot/keyboards.py` (history `•` vs `✓`), PTB `InlineKeyboardMarkupLimit`
        - **Watch out:** No GitHub write; the coordinator files the issue.
    - **Scope / Touches:** `.claude/skills/telegram-ux-review/SKILL.md`, scratchpad draft
    - **Action items:**
        - [RED] Read-through: items present
        - [GREEN] Apply plan.md Task 5.4; write the draft
    - **Success:** architecture tests pass
    - **Completed:** 2026-11-04
    - **Learnings:**
        - PTB 22.8 `telegram.constants`: `MAX_CALLBACK_DATA` 64, `CAPTION_LENGTH` 1024, `MAX_TEXT_LENGTH` 4096, `TOTAL_BUTTON_NUMBER` 100, `BUTTONS_PER_ROW` 8 (undocumented by Telegram).
        - History marks the active filter with `"• "`, queue and missing with `"✓ "`; `tests/test_bot/test_keyboards.py` pins the bullet.
    - **Key Changes:** `.claude/skills/telegram-ux-review/SKILL.md`: limits table with real consequences (HTTP 400), 100-button total, heuristic button width; known-bug sentence and `conversation_timeout` item removed; callback-size check covers all of `src/bot/` and owns the check.
    - **Notes:** GitHub issue draft for the bullet bug: session scratchpad `issues/ux-bug.md` (the coordinator files it).

### Phase 6: Verification (1 task)

- [x] **6.1** Acceptance gate
    - **Context:**
        - **Why:** Issue acceptance criteria.
        - **Architecture:** Delete `_PENDING`; acceptance search; full preflight.
        - **Key refs:** plan.md Task 6.1, D15
        - **Watch out:** Full-suite runs go under the suite lock.
    - **Scope / Touches:** `tests/test_architecture/test_skills.py`
    - **Action items:**
        - [RED] n/a (gate)
        - [GREEN] Remove `_PENDING`; run the search and the preflight
    - **Success:** all preflight steps pass; no search hits
    - **Completed:** 2026-11-04
    - **Learnings:**
        - The acceptance search finds nothing for `superpowers:simplify`, `SABnzbdHandler`, `prerun_checker\.py` and `chatMode.*public` in `.claude` and `tests`. A bare `prerun_checker` still hits 7 lines in `tests/test_run.py` and `tests/test_utils/test_prerun.py`: the real instance name (D15).
        - flake8 is not in the requirements files; the worktree venv needed `pip install flake8`, as CI does.
    - **Key Changes:** `test_skills.py`: `_PENDING` and the strict-xfail wrapper removed; `test_skill_names_exist` checks all 11 checked skills.
    - **Notes:** Preflight (flake8, mypy, i18n, unit 2019 passed with 100% coverage, integration 95 passed, architecture 73 passed) ran under the suite lock with the worktree's `.venv`.

# TASKS: Addarr Tooling & Convention Improvements

> Converted from `plan.md`. See plan for full rationale and design decisions.

---

### Phase 1: Architecture Tests — Convention Enforcement (3 tasks)

**Goal:** Add three AST-based tests to `test_conventions.py` that catch runtime-only bugs at CI time.

**Phase Context:**

- All three tests go in the existing `tests/test_architecture/test_conventions.py` file, following the established pattern of AST parsing + assertion
- Tests must work with the existing `conftest.py` mock config injection (no real config.yaml needed)

- [x] **1.1** MEDIA_CONFIG dispatch integrity test
    - **Context:**
        - **Why:** `MEDIA_CONFIG` in `dispatch.py` maps media types to `MediaService` method name strings (e.g., `"search_movies"`, `"add_movie"`). These are resolved via `getattr()` at runtime in `handler.py:~line 90`. A rename typo would only surface when a user triggers the command — no compile-time check exists.
        - **Architecture:** AST-based test in `test_conventions.py`, following the same pattern as `test_no_config_bracket_access_in_business_logic` (parse file → walk AST → assert)
        - **Key refs:** `src/bot/handlers/media/dispatch.py:21-40` (MEDIA_CONFIG dict), `src/services/media.py:23` (MediaService class), `tests/test_architecture/test_conventions.py:50-66` (existing AST helpers)
        - **Watch out:** MEDIA_CONFIG has nested structure — each media type has `search`, `add`, `add_with_profile` keys mapping to method name strings. Need to extract string values from the dict literal, not just top-level keys. The `config_key` values (e.g., `"radarr"`) are config keys, not method names — don't validate those against MediaService.
    - **Scope:** One new test function + any AST helpers needed to extract method name strings from the MEDIA_CONFIG dict literal
    - **Touches:** `tests/test_architecture/test_conventions.py`
    - **Action items:**
        - [RED] Write `test_media_config_dispatch_integrity` — parse `dispatch.py` AST, extract all method name string values from `MEDIA_CONFIG`, verify each resolves to a method on `MediaService` via `hasattr()` or `inspect.getmembers()`
        - [RED] Add negative test case: temporarily verify the test would fail with a bogus method name (manual verification, not committed)
        - [GREEN] Implement the test and any supporting helpers (e.g., `_extract_media_config_methods`)
    - **Success:** `pytest tests/test_architecture/test_conventions.py::test_media_config_dispatch_integrity -v` passes. Test would fail if any MEDIA_CONFIG method string doesn't match a real MediaService method.
    - **Completed:** 2026-03-11
    - **Learnings:** Architecture tests that validate existing correct code don't follow the traditional red-green cycle — they pass immediately. Negative verification (bogus method name) confirms detection works.
    - **Key Changes:** Added `_extract_media_config_methods()` AST helper and `test_media_config_dispatch_integrity` to `tests/test_architecture/test_conventions.py`
    - **Notes:** The helper skips `config_key` entries (config section names, not method names). If MEDIA_CONFIG structure changes, the extractor may need updating.

- [x] **1.2** State constant sync check test
    - **Context:**
        - **Why:** Media state constants are duplicated: `dispatch.py` lines 12-16 (`SEARCHING=1` through `ALBUM_SELECT=5`) and `states.py` lines 13-17 (`States.SEARCHING=1` through `States.ALBUM_SELECT=5`). No enforcement keeps them in sync — a drift would cause ConversationHandler state routing to silently break.
        - **Architecture:** Direct comparison test — import both sources and assert equality. No AST parsing needed since both are importable.
        - **Key refs:** `src/bot/handlers/media/dispatch.py:12-16` (module-level constants), `src/bot/states.py:13-17` (States class attributes)
        - **Watch out:** Only the 5 media states (SEARCHING through ALBUM_SELECT) need to be compared. States class has additional non-media states (SETTINGS_MENU, PASSWORD, etc.) that don't exist in dispatch.py — don't compare those. The state names are identical in both locations.
    - **Scope:** One new test function comparing the 5 media state constants between dispatch.py and States
    - **Touches:** `tests/test_architecture/test_conventions.py`
    - **Action items:**
        - [RED] Write `test_media_state_constants_in_sync` — define the list of media state names (`SEARCHING`, `SELECTING`, `QUALITY_SELECT`, `SEASON_SELECT`, `ALBUM_SELECT`), compare `getattr(dispatch_module, name)` vs `getattr(States, name)` for each
        - [GREEN] Implement the test. Import `src.bot.handlers.media.dispatch` and `src.bot.states.States`
    - **Success:** `pytest tests/test_architecture/test_conventions.py::test_media_state_constants_in_sync -v` passes. Clear failure message if values diverge (e.g., `"SELECTING: dispatch.py=2, States=3"`).
    - **Completed:** 2026-03-11
    - **Learnings:** Simple direct-import comparison is cleaner than AST parsing when both sources are importable. The `<MISSING>` sentinel handles the case where a state name doesn't exist in one source.
    - **Key Changes:** Added `MEDIA_STATE_NAMES` constant and `test_media_state_constants_in_sync` to `tests/test_architecture/test_conventions.py`
    - **Notes:** Only the 5 media states are compared; non-media states (SETTINGS_MENU, PASSWORD, etc.) in States class are intentionally excluded.

- [x] **1.3** `@require_auth` coverage check test
    - **Context:**
        - **Why:** Handler entry points (methods wired into `CommandHandler`/`ConversationHandler` `entry_points`) should have `@require_auth` unless explicitly exempted. A missing decorator means unauthenticated users can access the command. Currently only caught by manual review.
        - **Architecture:** AST-based test. Scan all `*Handler` classes in `src/bot/handlers/`, find methods referenced in `get_handler()` return values as entry_points, check each for `require_auth` in its decorator list. Explicit allowlist for intentionally unprotected handlers.
        - **Key refs:** `src/bot/handlers/auth.py:54-71` (`require_auth` decorator), `src/bot/handlers/auth.py:108-120` (`get_handler()` returning ConversationHandler with entry_points), `src/bot/handlers/start.py` (example of `@require_auth` usage)
        - **Watch out:**
            - The allowlist must include: `AuthHandler.start_auth` (is the auth flow itself), `AuthHandler.check_password`, `AuthHandler.cancel_auth` (internal conversation states). TransmissionHandler.transmission_command uses `is_enabled()` check instead of `@require_auth` — decide whether to allowlist or flag.
            - Entry points are identified differently per handler type: `CommandHandler(cmd, self.method)` vs `ConversationHandler(entry_points=[...])`. The AST must handle both patterns.
            - Decorator detection: look for `require_auth` in `node.decorator_list` — it could be `ast.Name(id='require_auth')` or `ast.Attribute(attr='require_auth')`.
            - Some handlers are in subdirectories (`media/handler.py`) — must recurse.
    - **Scope:** One new test function + AST helpers to extract entry point method names from `get_handler()` and check decorator presence. Explicit allowlist constant.
    - **Touches:** `tests/test_architecture/test_conventions.py`
    - **Action items:**
        - [RED] Write `test_handler_entry_points_have_require_auth` with known allowlist. Plan for ~6-8 test assertions (one per handler class with entry points)
        - [RED] Verify the test correctly identifies the TransmissionHandler gap (no `@require_auth` on `transmission_command`)
        - [GREEN] Implement entry point extraction logic: parse `get_handler()` body, find `CommandHandler`/`ConversationHandler` constructors, extract method name references from `entry_points` argument
        - [GREEN] Implement decorator check: for each entry point method name, find matching method def in the class and check `decorator_list`
        - [GREEN] Define `AUTH_ALLOWLIST` constant with documented rationale for each exemption
    - **Success:** `pytest tests/test_architecture/test_conventions.py::test_handler_entry_points_have_require_auth -v` passes. Adding a new handler without `@require_auth` would fail unless added to allowlist.
    - **Completed:** 2026-03-11
    - **Learnings:**
        - `MediaHandler.handle_menu_callback` is in ConversationHandler entry_points (triggered from start menu) but doesn't need @require_auth since the start menu already enforces it — needed allowlisting.
        - AST extraction of entry points requires distinguishing between ConversationHandler entry_points and standalone CommandHandler callbacks. CallbackQueryHandler at the return list level is intentionally excluded (not a user-triggerable command).
        - `_method_has_decorator` must handle both `@require_auth` and `@require_auth()` (call) forms.
    - **Key Changes:**
        - Added `_get_call_name()`, `_extract_self_methods()`, `_extract_entry_point_methods()`, `_method_has_decorator()` AST helpers
        - Added `AUTH_ALLOWLIST` with 3 exempted methods (AuthHandler.start_auth, TransmissionHandler.transmission_command, MediaHandler.handle_menu_callback)
        - Added `test_handler_entry_points_have_require_auth` test
    - **Notes:** When adding new handlers, if they don't use @require_auth, add to AUTH_ALLOWLIST with a comment explaining why. Test only checks CommandHandler callbacks and ConversationHandler entry_points, not standalone CallbackQueryHandler.

---

### Phase 2: Singleton Reset Sync Check (1 task)

**Goal:** Add a test that verifies every class in `SINGLETON_CLASSES` has a corresponding reset in the `reset_singletons` fixture, catching "forgot to add reset" errors.

**Phase Context:**

- Plan recommends the simpler alternative: a sync check test, not the `_reset_attrs` refactor
- Why NOT the `_reset_attrs` approach: requires touching every service file for a maintenance convenience improvement — higher risk, lower ROI

- [ ] **2.1** Singleton reset coverage test
    - **Context:**
        - **Why:** `SINGLETON_CLASSES` in `test_conventions.py` (11 entries) and `reset_singletons` fixture in `conftest.py` (11 imports + resets) are manually kept in sync. Adding a new service to one but forgetting the other means either the convention test misses it or tests leak state between runs.
        - **Architecture:** Test reads the `reset_singletons` fixture source to extract class names being reset, then compares against `SINGLETON_CLASSES`. Also needs to verify `AuthHandler` is reset (it's not in `SINGLETON_CLASSES` because it's not a singleton, but it has class-level state).
        - **Key refs:** `tests/conftest.py:223-277` (reset_singletons fixture), `tests/test_architecture/test_conventions.py:20-32` (SINGLETON_CLASSES set)
        - **Watch out:**
            - `AuthHandler` is reset in the fixture (line 277) but is NOT in `SINGLETON_CLASSES` (it's a handler, not a service). The test needs a separate assertion or a `CLASSES_WITH_RESET` superset that includes it.
            - The fixture uses `from src.services.X import XService` imports — extract class names from these import statements via AST.
            - Don't make this test brittle to formatting changes — parse AST, don't regex the source.
    - **Scope:** One new test function in `test_conventions.py` that compares SINGLETON_CLASSES against classes reset in the fixture
    - **Touches:** `tests/test_architecture/test_conventions.py`
    - **Action items:**
        - [RED] Write `test_singleton_reset_coverage` — parse `conftest.py` AST to extract all class names that have `._instance = None` assignments in the `reset_singletons` function. Compare against `SINGLETON_CLASSES`. Separately verify `AuthHandler._authenticated_users` is reset.
        - [GREEN] Implement the AST extraction: find the `reset_singletons` function def, walk its body for attribute assignments where the target matches `ClassName._instance`
    - **Success:** `pytest tests/test_architecture/test_conventions.py::test_singleton_reset_coverage -v` passes. Adding a new class to `SINGLETON_CLASSES` without updating `reset_singletons` would fail with a clear message.

---

### Phase 3: New Skills (4 tasks)

**Goal:** Create four new skills using `/skill-creator` that fill gaps in security auditing, release gating, UX review, and feedback loops.

**Phase Context:**

- All skills built via `/skill-creator` for consistent structure and YAML frontmatter
- Each skill's plan section serves as the spec — `/skill-creator` handles scaffolding
- Skills follow the same output format as `find-bugs`: File:Line, Severity, Problem, Fix

- [ ] **3.1** Create security audit skill
    - **Context:**
        - **Why:** No full-codebase security review exists. `find-bugs` only reviews branch diffs. Need a comprehensive audit covering auth surface, secret handling, API safety, and Telegram-specific risks.
        - **Architecture:** New skill at `.claude/skills/security-audit/SKILL.md`. Four-phase checklist structure (Auth → Secrets → API → Telegram). Output format matches `find-bugs`.
        - **Key refs:** `.claude/skills/find-bugs/SKILL.md` (output format template), `src/bot/handlers/auth.py` (auth surface), `src/api/base.py` (API surface), `src/config/settings.py` (secret handling)
        - **Watch out:** Must be Addarr-specific, not generic security advice. Each checklist item references a concrete file/function. Inspired by agency-agents Security Engineer persona but adapted to Telegram bot threat model.
    - **Scope:** Invoke `/skill-creator` with the Phase 3.1 spec from plan.md. Checklist covers: auth decorator coverage, private chat enforcement, password comparison, config.yaml secrets, API key handling, yaml.safe_load usage, rate limiting, callback_data validation, bot token exposure.
    - **Touches:** `.claude/skills/security-audit/SKILL.md` (new), possibly reference files
    - **Action items:**
        - [GREEN] Invoke `/skill-creator` with the 4-phase security audit checklist from plan.md as spec
        - [GREEN] Review generated skill for Addarr-specific accuracy — every checklist item should reference a real file/function
        - [GREEN] Verify skill loads correctly by checking trigger description
    - **Success:** `/security-audit` skill exists, loads, and contains all 4 phases with Addarr-specific file references.

- [ ] **3.2** Create release readiness skill + workflow integration
    - **Context:**
        - **Why:** No gate exists for `development` → `main` merges. The existing preflight (pytest, flake8, mypy, i18n) is a subset — missing code quality review, coverage thresholds, documentation checks, and Docker build verification.
        - **Architecture:** New skill at `.claude/skills/release-readiness/SKILL.md`. Four-phase checklist (Code Quality → Test Confidence → Documentation → Release Safety). Also add `/addarr release` entry point to `addarr-workflow/SKILL.md`.
        - **Key refs:** `.claude/skills/addarr-workflow/SKILL.md` (flow table to extend), `.claude/skills/addarr-workflow/references/preflight.md` (existing preflight steps to build on), `plan.md` Phase 3.2 (full checklist)
        - **Watch out:** The `/addarr release` flow entry must be added to the workflow's flow table. Default stance is "NOT READY" unless all checks pass.
    - **Scope:** Invoke `/skill-creator` with the Phase 3.2 spec. Then manually add the `/addarr release` entry to `addarr-workflow/SKILL.md` flow table.
    - **Touches:** `.claude/skills/release-readiness/SKILL.md` (new), `.claude/skills/addarr-workflow/SKILL.md` (add flow entry)
    - **Action items:**
        - [GREEN] Invoke `/skill-creator` with the 4-phase release readiness checklist from plan.md
        - [GREEN] Add `/addarr release` row to the flow table in `addarr-workflow/SKILL.md`
        - [GREEN] Verify both the new skill and the workflow integration load correctly
    - **Success:** `/release-readiness` skill exists with all 4 phases. `/addarr release` appears in workflow flow table and routes to the readiness check.

- [ ] **3.3** Create Telegram UX review skill
    - **Context:**
        - **Why:** Traditional UI/UX tooling doesn't apply to Telegram bots. Known inconsistencies exist (e.g., `✓` vs `•` for active filters between queue/missing and history keyboards). No systematic way to audit keyboard patterns, flow efficiency, or message formatting.
        - **Architecture:** New skill at `.claude/skills/telegram-ux-review/SKILL.md`. Four-phase checklist (Keyboard Consistency → Flow Efficiency → Information Density → Accessibility). Output format matches `find-bugs`.
        - **Key refs:** `src/bot/keyboards.py` (1288 lines, all keyboard layouts), `src/bot/handlers/media/formatters.py` (caption building, result display), `plan.md` Phase 3.4 (full checklist with known issues)
        - **Watch out:** Telegram-specific constraints: 64-byte callback_data limit, 1024-char photo caption limit, 4096-char text limit, inline keyboard only (no custom UI). The skill must reference these concrete limits, not generic UX principles.
    - **Scope:** Invoke `/skill-creator` with the Phase 3.4 spec. Include known issues as examples (filter checkmark inconsistency).
    - **Touches:** `.claude/skills/telegram-ux-review/SKILL.md` (new), possibly reference files
    - **Action items:**
        - [GREEN] Invoke `/skill-creator` with the 4-phase Telegram UX checklist from plan.md
        - [GREEN] Verify Telegram-specific constraints (character limits, callback_data size) are concrete, not generic
        - [GREEN] Verify skill references the correct key files (`keyboards.py`, `formatters.py`, `handler.py`)
    - **Success:** `/telegram-ux-review` skill exists with all 4 phases, references Telegram platform constraints, and includes known issues as examples.

- [ ] **3.4** Create post-PR retrospective workflow reference
    - **Context:**
        - **Why:** TASKS.md completion metadata captures learnings, but nothing systematically extracts them into durable skill updates. Patterns discovered during implementation get lost after the PR merges.
        - **Architecture:** New reference file at `.claude/skills/addarr-workflow/references/retrospective.md`. Adds an optional post-merge step to the workflow: read completion metadata → categorize learnings → suggest skill/convention updates → user reviews and approves.
        - **Key refs:** `.claude/skills/addarr-workflow/SKILL.md` (workflow to integrate with), `docs/issues/issue-79/TASKS.md` (example of completion metadata format), `plan.md` Phase 3.3 (categorization logic)
        - **Watch out:** This is human-reviewed, not automatic. Never auto-update skills. The categories are: new anti-pattern → `anti-patterns.md`, new convention → `CLAUDE.md` or `test_conventions.py`, recurring bug → `find-bugs`, new fixture pattern → `fixtures.md`.
    - **Scope:** Create the reference file with the retrospective process. Add a mention in `addarr-workflow/SKILL.md` as an optional post-merge step.
    - **Touches:** `.claude/skills/addarr-workflow/references/retrospective.md` (new), `.claude/skills/addarr-workflow/SKILL.md` (add reference)
    - **Action items:**
        - [GREEN] Write the retrospective reference file with the 4-step categorization process from plan.md
        - [GREEN] Add optional post-merge step reference in `addarr-workflow/SKILL.md`
        - [GREEN] Include example: show what a learning entry looks like and how it maps to a skill update suggestion
    - **Success:** Retrospective reference exists with categorization logic and example. Workflow mentions it as optional post-merge step.

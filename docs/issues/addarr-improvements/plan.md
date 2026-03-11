# Plan: Addarr Tooling & Convention Improvements

## Context

Based on analysis of the agency-agents repository and comparative evaluation with ChatGPT and Qwen, we identified concrete gaps in Addarr's architecture tests, development skills, and feedback loop. This plan addresses those gaps using skills (not agents) — encoding project knowledge into reusable checklists and workflows.

## Phase 1: Architecture Tests (Convention Enforcement)

Add three new tests to `tests/test_architecture/test_conventions.py` that catch real issues at CI time.

### 1.1 MEDIA_CONFIG Dispatch Integrity

**Problem:** `MEDIA_CONFIG` in `src/bot/handlers/media/dispatch.py` maps string keys (`"search_movies"`, `"add_movie"`, etc.) to `MediaService` method names. These are resolved at runtime via `getattr()` in `handler.py`. A refactoring typo would only surface when a user triggers the command.

**Solution:** AST-based test that:
- Parses `dispatch.py` to extract all method name strings from `MEDIA_CONFIG`
- Verifies each resolves to an actual method on `MediaService`
- Fails with a clear message like: `MEDIA_CONFIG["movie"]["search"] references "search_movies" but MediaService has no such method`

**Files:** `tests/test_architecture/test_conventions.py`, `src/bot/handlers/media/dispatch.py`, `src/services/media.py`

### 1.2 State Constant Sync Check

**Problem:** Conversation state constants are defined in two places:
- `src/bot/handlers/media/dispatch.py`: `SEARCHING = 1`, `SELECTING = 2`, etc.
- `src/bot/states.py`: `States.SEARCHING = 1`, `States.SELECTING = 2`, etc.

These are manually kept in sync with no enforcement. A drift would cause conversation handlers to break silently.

**Solution:** Test that compares the media state values in `dispatch.py` against `States` class attributes and fails if they diverge.

**Files:** `tests/test_architecture/test_conventions.py`, `src/bot/handlers/media/dispatch.py`, `src/bot/states.py`

### 1.3 `@require_auth` Coverage Check

**Problem:** Handler entry points that should require authentication could accidentally omit the `@require_auth` decorator. Currently nothing enforces this — it would only be caught by manual review or integration tests.

**Solution:** AST-based test that:
- Scans all `*Handler` classes in `src/bot/handlers/`
- For each method referenced as an `entry_point` in a `ConversationHandler` or `CommandHandler`, checks whether `@require_auth` is present
- Maintains an explicit allowlist for handlers that intentionally skip auth (e.g., `StartHandler.start`, `AuthHandler.start_auth`, `HelpHandler.help`)
- Fails if an entry point is undecorated and not in the allowlist

**Design consideration:** The allowlist approach is better than trying to infer which handlers "should" have auth. It makes the decision explicit and reviewable.

**Files:** `tests/test_architecture/test_conventions.py`, `src/bot/handlers/**/*.py`

---

## Phase 2: Dynamic Singleton Reset

### 2.1 Refactor `reset_singletons` Fixture

**Problem:** The `reset_singletons` fixture in `tests/conftest.py` manually lists 11 singleton services with their specific class-level attributes to reset. Adding a new service requires updating both `SINGLETON_CLASSES` in `test_conventions.py` and the reset fixture — but there's no enforcement linking them, so it's easy to update one and forget the other.

**Complication:** Each singleton has different state beyond `_instance`:
- `MediaService`: `_radarr`, `_sonarr`, `_lidarr`
- `BazarrService`: `_client`, `_config`
- `TranslationService`: `_translations`
- `NotificationService`: `_bot`
- `PreferencesService`: `_preferences`
- `RateLimitService`: `_records`
- `WebhookService`: `_enabled`, `_running`, `_runner`
- `AuthHandler`: `_authenticated_users` (not even a singleton — class-level state)

**Solution:** Add a `_reset_attrs` class-level dict or method to each singleton service that declares its resettable state. The fixture then auto-discovers singletons from `SINGLETON_CLASSES` and calls the reset. This keeps the type-safe per-class reset behavior but removes the manual listing from `conftest.py`.

**Alternative (simpler):** Keep the manual reset but add a test that verifies every class in `SINGLETON_CLASSES` appears in the `reset_singletons` fixture. This is less elegant but lower risk and still catches the "forgot to add reset" failure mode.

**Recommendation:** Start with the simpler alternative. The `_reset_attrs` approach requires touching every service file, which is a larger change with more risk for a maintenance convenience improvement.

**Files:** `tests/conftest.py`, `tests/test_architecture/test_conventions.py`

---

## Phase 3: New Skills

### 3.1 Security Audit Skill

**Purpose:** Full-codebase security review on demand. Unlike `find-bugs` (which reviews branch diffs), this audits the entire security posture.

**Location:** `.claude/skills/security-audit/SKILL.md`

**Structure (inspired by agency-agents Security Engineer, adapted for Addarr):**

**Phase 1: Auth Surface**
- [ ] Every handler entry point has `@require_auth` or is in the explicit allowlist
- [ ] `_enforce_private_chat` covers all chat mode configurations
- [ ] Password comparison in `auth.py:check_password` — plaintext comparison timing attack risk
- [ ] `_save_authenticated_users` — file write permissions, error handling
- [ ] `message.delete()` for password messages — does it work in all chat types?
- [ ] Admin-only commands check `config.get("admins", [])` consistently

**Phase 2: Secret Surface**
- [ ] `config.yaml` is in `.gitignore` (API keys, bot token, passwords)
- [ ] API keys passed only via `X-Api-Key` header, never logged
- [ ] No secrets in error messages returned to users
- [ ] `yaml.safe_load` used everywhere (not `yaml.load`)
- [ ] No hardcoded credentials in source

**Phase 3: API Surface**
- [ ] `BaseApiClient._make_request` — response text not leaked to users on error
- [ ] Rate limiting configured and enforced (`@rate_limit` decorator coverage)
- [ ] Input validation on search queries before passing to *arr APIs
- [ ] Timeout configuration prevents hanging connections

**Phase 4: Telegram Surface**
- [ ] Bot token not logged or exposed in error messages
- [ ] User ID used for auth cannot be spoofed (Telegram guarantees this, but verify we don't accept user-supplied IDs)
- [ ] Callback data validated before use (no injection via crafted callback_data)
- [ ] Group chat behavior tested when `chatMode` is not `private_only`

**Output format:** Same as `find-bugs` — File:Line, Severity, Problem, Fix. Only actionable findings.

### 3.2 Release Readiness Skill

**Purpose:** Gate for `development` → `main` merges. Runs before creating a release PR.

**Location:** `.claude/skills/release-readiness/SKILL.md` (or add as `/addarr release` flow in `addarr-workflow`)

**Checklist:**

**Phase 1: Code Quality**
- [ ] `find-bugs` on full diff: `git diff main...development`
- [ ] `simplify` on full diff
- [ ] No `TODO`, `FIXME`, `HACK` comments in changed files
- [ ] No `print()` statements in `src/` (should use logger)

**Phase 2: Test Confidence**
- [ ] Full test suite passes: `pytest --tb=short -q`
- [ ] Coverage on changed modules meets threshold
- [ ] All architecture tests pass (layer boundaries + conventions)
- [ ] Integration tests cover all modified handler flows

**Phase 3: Documentation & Metadata**
- [ ] All TASKS.md files for included issues have completion metadata
- [ ] Version in `src/__init__.py` (or wherever defined) reflects the release
- [ ] Any new config keys are documented in `config_example.yaml`
- [ ] Any new translation keys are present in all locale files

**Phase 4: Release Safety**
- [ ] No open issues blocking this release
- [ ] Docker build succeeds: `docker build -t addarr .`
- [ ] Preflight passes (tests, lint, mypy, i18n validation)

**Output:** Pass/fail with specific failures listed. Default stance: "NOT READY" unless all checks pass (Reality Checker principle).

**Integration with workflow:** Add as a new flow in `addarr-workflow`:
```
| `/addarr release` | release | Full readiness check for development → main merge |
```

### 3.3 Post-PR Retrospective (Feedback Loop)

**Purpose:** After a PR is merged, extract learnings from TASKS.md completion metadata and check whether any should become durable skill updates.

**Location:** `.claude/skills/addarr-workflow/references/retrospective.md` (add as optional step after PR merge)

**Process:**

1. Read all TASKS.md completion metadata for the merged PR's issue
2. For each learning entry, categorize:
   - **New anti-pattern?** → Suggest addition to relevant skill's `references/anti-patterns.md`
   - **New convention?** → Suggest addition to `CLAUDE.md` or `test_conventions.py`
   - **Recurring bug category?** → Suggest new check in `find-bugs`
   - **New fixture pattern?** → Suggest addition to `addarr-testing/references/fixtures.md`
3. Present suggestions to user for review (never auto-update skills)
4. If approved, make the edits

**Key constraint:** This is human-reviewed, not automatic. The "self-improving" part is structured extraction, not unsupervised updates.

### 3.4 Telegram UX Review Skill

**Purpose:** On-demand review of bot interaction quality — keyboard consistency, flow efficiency, information density, and chat bot accessibility. Fills the gap left by traditional UI/UX tools that don't apply to Telegram's constrained interaction model.

**Location:** `.claude/skills/telegram-ux-review/SKILL.md`

**Phase 1: Keyboard Consistency**
- [ ] Every keyboard has back/cancel in the last row
- [ ] Pagination follows the same `⬅️ Prev | Page X/Y | ➡️ Next` pattern everywhere
- [ ] Filter tabs use the same checkmark convention (`✓` vs `•` — known inconsistency: history uses `•` for active filter while queue/missing use `✓`)
- [ ] Button text fits mobile screens (no truncation on typical phone widths)
- [ ] Callback data stays within Telegram's 64-byte limit
- [ ] No duplicate callback_data values across unrelated keyboards

**Phase 2: Flow Efficiency**
- [ ] Tap count for common actions (search → add): count and flag if > 5 taps
- [ ] Dead-end detection: every state has a clear exit path (back, cancel, or timeout)
- [ ] Error states offer actionable next steps (not just "something went wrong")
- [ ] Conversation timeouts configured and tested for all `ConversationHandler` flows
- [ ] Cancel command works from every conversation state

**Phase 3: Information Density**
- [ ] Photo captions stay within 1024-character Telegram limit
- [ ] Text messages stay within 4096-character limit
- [ ] Consistent truncation strategy when content exceeds limits (ellipsis, "and N more")
- [ ] Search result formatting consistent between list view and card view
- [ ] Rating/genre/link display follows same order across all media types

**Phase 4: Chat Bot Accessibility**
- [ ] Emoji used as visual markers, not sole indicators (always paired with text)
- [ ] Text-only fallback exists when poster images fail to load
- [ ] Messages readable without formatting (plain text degradation)
- [ ] Status indicators use both symbol and word (e.g., `✅ Added` not just `✅`)

**Key files to audit:** `src/bot/keyboards.py`, `src/bot/handlers/media/formatters.py`, `src/bot/handlers/media/handler.py`, all handler files that build inline keyboards.

**Output format:** Same as `find-bugs` — File:Line, Severity, Problem, Fix. Only actionable findings.

---

## Skill Creation Method

All new skills (3.1, 3.2, 3.3) should be built using `/skill-creator`. This ensures:
- Consistent YAML frontmatter and structure
- Proper placement in `.claude/skills/`
- Reference file organization matching existing skills
- Trigger descriptions that integrate with the skill loading system

For each skill, invoke `/skill-creator` with the requirements and checklists defined above as input. The plan sections for each skill serve as the spec — `/skill-creator` handles the scaffolding and structure.

The Phase 3.2 release readiness skill also requires a workflow integration step: adding the `/addarr release` entry point to `addarr-workflow/SKILL.md` after the skill is created.

---

## Phase Summary

| Phase | Items | Effort | Value |
|-------|-------|--------|-------|
| 1 — Architecture tests | 3 new tests in `test_conventions.py` | Small | High — catches runtime bugs at CI |
| 2 — Singleton reset | 1 sync check or refactor | Small | Medium — reduces maintenance friction |
| 3.1 — Security audit skill | New skill with Addarr-specific checklists | Medium | High — fills real gap in tooling |
| 3.2 — Release readiness skill | New skill or workflow flow | Medium | High — gates releases with evidence |
| 3.3 — Post-PR retrospective | New workflow reference | Small | Medium — closes the learning loop |
| 3.4 — Telegram UX review skill | New skill with Telegram-specific checklists | Medium | Medium — catches UX inconsistencies systematically |

## Recommended Order

1. Phase 1 (architecture tests) — immediate value, small scope, testable
2. Phase 2 (singleton reset sync) — quick win while in test_conventions.py
3. Phase 3.1 (security audit) — new capability, no existing coverage
4. Phase 3.2 (release readiness) — builds on Phase 1 tests + existing preflight
5. Phase 3.4 (Telegram UX review) — catches known inconsistencies, informs future UI work
6. Phase 3.3 (retrospective) — lowest urgency, highest long-term value

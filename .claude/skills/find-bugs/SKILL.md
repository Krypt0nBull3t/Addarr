---
name: find-bugs
description: Use when reviewing branch changes for bugs, security vulnerabilities, or code quality issues. Covers async Python, Telegram bot handlers, API clients, config access, and singleton patterns.
---

# Find Bugs

Review changes on the current branch for bugs, security vulnerabilities, and code quality issues. Adapted from [Sentry's find-bugs skill](https://github.com/getsentry/sentry-skills) with Addarr-specific checks.

## Phase 1: Complete Input Gathering

1. Get the FULL diff: `git diff $(git merge-base HEAD development)...HEAD`
2. If output is truncated, read each changed file individually until you have seen every changed line
3. List all files modified in this branch before proceeding

## Phase 2: Attack Surface Mapping

For each changed file, identify and list:

* All user inputs (Telegram message text, callback_data, command arguments)
* All API calls (Radarr, Sonarr, Lidarr, SABnzbd, Transmission)
* All authentication/authorization checks (`@require_auth`, user ID validation)
* All config access patterns (safe `.get()` vs direct indexing)
* All async operations (`await`, session management, `aiohttp` calls)
* All singleton state mutations (class-level variables)

## Phase 3: Security & Bug Checklist

Check EVERY item for EVERY changed file:

* [ ] **Injection**: Command injection via `subprocess`, template injection, YAML injection in config
* [ ] **Authentication bypass**: Missing `@require_auth` on entry points, user ID spoofing
* [ ] **Authorization/IDOR**: Access control on per-user operations (e.g., user_data isolation)
* [ ] **Information disclosure**: API keys in logs, error messages leaking internal state, secrets in Telegram messages
* [ ] **Race conditions**: TOCTOU in singleton initialization, concurrent user_data access
* [ ] **Resource exhaustion**: Unbounded search results, missing timeouts on API calls, session leaks
* [ ] **Business logic**: State machine violations (ConversationHandler states), numeric edge cases in quality/season selection
* [ ] **Async bugs**: Missing `await`, unclosed sessions, fire-and-forget coroutines
* [ ] **Singleton issues**: State in `__init__` vs `_initialize`, missing `is_enabled()` checks, incomplete reset
* [ ] **Config safety**: Direct `config["key"]` indexing without enable check, missing `.get()` defaults
* [ ] **Telegram API misuse**: Missing `query.answer()`, `reply_text` on callbacks, `edit_text` on photo messages
* [ ] **Error handling**: Bare `except:`, swallowing exceptions silently, raising from `_initialize`

## Phase 4: Verification

For each potential issue:

* Check if it's already handled elsewhere in the changed code
* Search for existing tests covering the scenario
* Read surrounding context to verify the issue is real
* Check if the pattern matches existing code conventions (see `@addarr-services` and `@addarr-handlers` anti-patterns)

## Phase 5: Pre-Conclusion Audit

Before finalizing, you MUST:

1. List every file you reviewed and confirm you read it completely
2. List every checklist item and note whether you found issues or confirmed it's clean
3. List any areas you could NOT fully verify and why
4. Only then provide your final findings

## Output Format

**Prioritize**: security vulnerabilities > async/singleton bugs > Telegram API misuse > code quality

**Skip**: stylistic/formatting issues, flake8 catches

For each issue:

* **File:Line** — Brief description
* **Severity**: Critical / High / Medium / Low
* **Problem**: What's wrong
* **Evidence**: Why this is real (not already fixed, no existing test, etc.)
* **Fix**: Concrete suggestion
* **References**: Link to relevant anti-pattern in `@addarr-services` or `@addarr-handlers` if applicable

If you find nothing significant, say so — don't invent issues.

Do not make changes — just report findings.

---
name: find-bugs
description: Use when reviewing branch changes for bugs, security vulnerabilities, or code quality issues. Covers async Python, Telegram bot handlers, API clients, config access, and singleton patterns.
---

# Find Bugs

Review changes on the current branch for bugs, security vulnerabilities, and code quality issues. Adapted from [Sentry's find-bugs skill](https://github.com/getsentry/sentry-skills) with Addarr-specific checks.

## Phase 1: Input Gathering

1. Get the diff: `git diff origin/development...HEAD`
2. If truncated, read each changed source file individually
3. Note all modified files before proceeding

## Phase 2: Security & Bug Checklist

For each changed file, check:

* [ ] **Injection**: Command injection via `subprocess`, template injection, URL parameter injection
* [ ] **Authentication bypass**: Missing `@require_auth` on entry points, user ID spoofing
* [ ] **Authorization/IDOR**: Access control on per-user operations (e.g., user_data isolation)
* [ ] **Information disclosure**: API keys in logs, error messages leaking internal state
* [ ] **Race conditions**: TOCTOU in singleton initialization, concurrent user_data access
* [ ] **Resource exhaustion**: Unbounded data, missing timeouts, session leaks
* [ ] **Business logic**: State machine violations, numeric edge cases
* [ ] **Async bugs**: Missing `await`, unclosed sessions, fire-and-forget coroutines
* [ ] **Singleton issues**: State in `__init__` vs `_initialize`, missing `is_enabled()` checks
* [ ] **Config safety**: Direct `config["key"]` indexing, missing `.get()` defaults
* [ ] **Telegram API misuse**: Missing `query.answer()`, `reply_text` on callbacks, `edit_text` on photo messages
* [ ] **Error handling**: Bare `except:`, swallowing exceptions silently, raising from `_initialize`

## Phase 3: Verification

For each potential issue, verify it's real:
* Not already handled elsewhere in the changed code
* Not covered by existing tests
* Not consistent with existing codebase patterns (skip pre-existing tech debt)

## Output

**Only report actionable findings.** Skip:
- Stylistic/formatting issues (flake8 catches those)
- Pre-existing patterns you wouldn't change in this PR
- Items where "no change recommended"

For each real issue:

* **File:Line** — Brief description
* **Severity**: Critical / High / Medium / Low
* **Problem**: What's wrong
* **Fix**: Concrete suggestion

If nothing significant found, say so in one line. Do not pad output with "clean" confirmations per checklist item.

Do not make changes — just report findings.

---
name: security-audit
description: Use when performing a full-codebase security audit of Addarr. Covers auth surface, secret handling, API safety, and Telegram-specific risks. Unlike find-bugs (branch diffs only), this audits the entire security posture.
---

# Security Audit

Full-codebase security review for Addarr. Run on demand to assess the overall security posture, not just branch changes.

## Phase 1: Auth Surface

Audit authentication and authorization controls.

* [ ] **`@require_auth` coverage** — Every handler entry point in `src/bot/handlers/` has `@require_auth` or is in the explicit allowlist in `tests/test_architecture/test_conventions.py:AUTH_ALLOWLIST`
* [ ] **Private chat enforcement** — `_enforce_private_chat()` in `src/bot/handlers/auth.py` covers all `chatMode` configurations (`private_only`, `public`, etc.)
* [ ] **Password comparison** — `check_password()` in `src/bot/handlers/auth.py` uses timing-safe comparison (`hmac.compare_digest`) to prevent timing attacks. If it uses `==`, flag as High severity.
* [ ] **Authenticated user persistence** — `_save_authenticated_users()` in `src/bot/handlers/auth.py` handles file write errors gracefully (permissions, disk full). Check for bare `except:` or silent failures.
* [ ] **Password message deletion** — `message.delete()` for password messages in `auth.py` works in all chat types (private, group). Check error handling if delete fails (bot may lack permissions in groups).
* [ ] **Admin-only commands** — Commands restricted to admins check `config.get("admins", [])` consistently. Search for admin checks across all handler files.

## Phase 2: Secret Surface

Audit secret handling and exposure risks.

* [ ] **config.yaml in .gitignore** — Verify `.gitignore` includes `config.yaml` (contains API keys, bot token, passwords)
* [ ] **API key headers** — All API clients in `src/api/` pass keys via `X-Api-Key` header only (in `BaseApiClient._get_headers()` at `src/api/base.py`). Keys never appear in URLs or logs.
* [ ] **No secrets in error messages** — Error messages returned to Telegram users (via `reply_text`, `edit_text`) never contain API keys, tokens, or internal URLs. Check all `except` blocks in handlers.
* [ ] **yaml.safe_load** — All YAML loading uses `yaml.safe_load()`, never `yaml.load()`. Check `src/config/settings.py` and any translation file loading.
* [ ] **No hardcoded credentials** — No API keys, passwords, or tokens hardcoded in source files. Search for common patterns: `token = "`, `password = "`, `api_key = "`.

## Phase 3: API Surface

Audit API client security.

* [ ] **Error response handling** — `BaseApiClient._make_request()` in `src/api/base.py` does not leak raw response text to users on error. Internal details stay in logs only.
* [ ] **Rate limiting coverage** — `@rate_limit` decorator from `src/services/rate_limit.py` applied to user-facing operations (search, add). Check all handler entry points.
* [ ] **Input validation** — Search queries validated/sanitized before passing to *arr APIs. Check `MediaService.search_*` methods in `src/services/media.py` and API client `search()` methods.
* [ ] **Timeout configuration** — `aiohttp.ClientSession` in `BaseApiClient` has explicit timeouts (`aiohttp.ClientTimeout`). Missing timeouts can cause hanging connections.
* [ ] **Session lifecycle** — `aiohttp.ClientSession` instances are properly closed on shutdown. Check `BaseApiClient` for session cleanup.

## Phase 4: Telegram Surface

Audit Telegram-specific security concerns.

* [ ] **Bot token exposure** — Bot token (from config) never logged or included in error messages. Search for `bot_token`, `token` in log statements across `src/`.
* [ ] **User ID integrity** — Authentication uses `update.effective_user.id` (Telegram-guaranteed, not spoofable). Verify no handler accepts user-supplied IDs for auth decisions.
* [ ] **Callback data validation** — `callback_query.data` validated before use in all `CallbackQueryHandler` methods. Crafted callback_data could inject unexpected values. Check pattern matching vs raw string parsing.
* [ ] **Callback data size** — All `callback_data` values in `src/bot/keyboards.py` stay within Telegram's 64-byte limit. Long data strings silently fail.
* [ ] **Group chat behavior** — When `chatMode` is not `private_only`, verify bot behavior in group chats: no sensitive data exposed, commands work correctly, no state leakage between users.

## Output

**Only report actionable findings.** Skip:
- Pre-existing patterns consistent with the codebase
- Theoretical risks with no practical exploit path in this context
- Items already covered by architecture tests in `tests/test_architecture/`

For each real issue:

* **File:Line** — Brief description
* **Severity**: Critical / High / Medium / Low
* **Problem**: What's wrong
* **Fix**: Concrete suggestion with specific code change

If nothing significant found, say so in one line. Do not pad output with "clean" confirmations per checklist item.

Do not make changes — just report findings.

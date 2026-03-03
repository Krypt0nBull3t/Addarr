# Issue #116: Rate Limiting on Commands and API Calls

**Plan:** [plan.md](plan.md)
**Branch:** `feature/116-rate-limiting`
**Issue:** https://github.com/Krypt0nBull3t/Addarr/issues/116

---

### Phase 1: RateLimitService + Config + Test Infrastructure (2 tasks)

**Goal:** Build the complete `RateLimitService` singleton with sliding window logic, config integration, and all supporting test infrastructure.

- [x] **1.1** Implement RateLimitService core with sliding window and singleton pattern
    - **Context:**
        - **Why:** No rate limiting exists — users can spam commands and overwhelm *arr APIs. This service tracks per-user request timestamps to enforce limits.
        - **Architecture:** Singleton service in `src/services/` following `TranslationService` pattern (`__new__` override, class-level state). In-memory sliding window: `{user_id: {category: [timestamps]}}`. `check(user_id, category)` prunes expired timestamps, checks count, records new timestamp if allowed. Returns `(allowed: bool, retry_after: int)`.
        - **Key refs:**
            - `src/services/translation.py:20-33` — singleton pattern to follow
            - `tests/conftest.py:190-229` — singleton reset fixture to update
            - `tests/test_architecture/test_conventions.py:20-29` — `SINGLETON_CLASSES` set to update
            - `src/config/settings.py:89` — `config.get()` API (not bracket access)
        - **Watch out:**
            - Config access: use `config.get("rateLimit", {})` not `config["rateLimit"]` (bracket access banned in business logic)
            - `check()` must record the timestamp ONLY if the request is allowed (don't count blocked requests against the user)
            - `time.time()` returns float — store as-is, compare with `>` not `>=` for window boundary
            - Singleton reset in conftest must clear both `_instance` and `_records`
    - **Scope:** `RateLimitService` class with `check()`, `_get_limit()`, `reset()`, `is_enabled` property. Config integration reads from `rateLimit` config section with hardcoded defaults as fallback. Also includes `RateLimitExceededError` in error_handler, conftest singleton reset, SINGLETON_CLASSES update, and mock config data.
    - **Touches:**
        - Create: `src/services/rate_limit.py`
        - Create: `tests/test_services/test_rate_limit_service.py`
        - Modify: `src/utils/error_handler.py` (add `RateLimitExceededError`)
        - Modify: `config_example.yaml` (add `rateLimit` section after `security:`)
        - Modify: `tests/conftest.py` (singleton reset + mock config data)
        - Modify: `tests/test_architecture/test_conventions.py` (SINGLETON_CLASSES)
    - **Action items:**
        - [RED] Write tests for singleton pattern (`test_singleton_pattern`, `test_reset_clears_all`)
        - [RED] Write tests for `check()` core logic: `test_check_allows_first_request`, `test_check_allows_under_limit`, `test_check_blocks_over_limit`, `test_check_allows_after_window_expires` (mock `time.time`), `test_check_prunes_expired_timestamps`
        - [RED] Write tests for isolation: `test_different_categories_independent`, `test_different_users_independent`
        - [RED] Write tests for `_get_limit()`: `test_get_limit_defaults`, `test_get_limit_from_config`, `test_get_limit_missing_category_uses_default`
        - [RED] Write tests for `is_enabled`: `test_is_enabled_true`, `test_is_enabled_false`, `test_is_enabled_missing_config`
        - [RED] Write test for `RateLimitExceededError`: `test_rate_limit_exceeded_error_attributes`
        - [GREEN] Implement `RateLimitService` in `src/services/rate_limit.py` with defaults:
            ```python
            DEFAULT_LIMITS = {
                "search": (10, 60),
                "modify": (5, 60),
                "auth": (3, 300),
            }
            DEFAULT_FALLBACK = (10, 60)
            ```
        - [GREEN] Add `RateLimitExceededError` to `src/utils/error_handler.py` after `ServiceNotEnabledError`
        - [GREEN] Add `rateLimit` section to `config_example.yaml` after `security:` (~line 139)
        - [GREEN] Add `rateLimit` to `MOCK_CONFIG_DATA` in `tests/conftest.py` (**`enable: False` by default** — rate limit tests override to `True` in their fixtures)
        - [GREEN] Add `RateLimitService` singleton reset to `tests/conftest.py` autouse fixture
        - [GREEN] Add `"RateLimitService"` to `SINGLETON_CLASSES` in `tests/test_architecture/test_conventions.py`
    - **Success:** `pytest tests/test_services/test_rate_limit_service.py -v` all green, architecture tests pass, `python -m flake8 src/services/rate_limit.py` clean

- [~] **1.2** Implement `@rate_limit` decorator with DummyHandler tests
    - **Context:**
        - **Why:** The decorator is the integration point between the service and handlers — it wraps handler methods to check limits before the handler body runs, returning a cooldown message when the limit is exceeded.
        - **Architecture:** Decorator factory `rate_limit(category: str)` returns a decorator that wraps `async def method(self, update, context)`. Follows `@require_auth` pattern exactly (see `src/bot/handlers/auth.py:36-50`). Lives in `src/services/rate_limit.py` alongside the service (not in handlers — the decorator is tightly coupled to the service, and handler→service imports are the correct layer direction).
        - **Key refs:**
            - `src/bot/handlers/auth.py:36-50` — `require_auth` decorator pattern to mirror
            - `tests/test_handlers/test_auth_handler.py:39-111` — DummyHandler testing pattern
            - `src/services/translation.py:73-98` — `get_text(key, **kwargs)` uses %-formatting, pass `seconds=retry_after`
        - **Watch out:**
            - Decorator is a **no-op when `service.is_enabled` is False** — must pass through to handler immediately
            - When `update.effective_user` is None, return None (same guard as `require_auth`)
            - Use `update.effective_message.reply_text()` not `update.message.reply_text()` — `effective_message` works for both messages and callback queries
            - Stacking order: `@require_auth` THEN `@rate_limit("category")` — auth check runs first (outermost decorator), rate limit runs second. Test this explicitly.
            - Must import `TranslationService` inside decorator body (not at module level) to avoid circular imports if translation service ever imports from services
    - **Scope:** `rate_limit()` decorator factory function + comprehensive tests using DummyHandler pattern
    - **Touches:**
        - Modify: `src/services/rate_limit.py` (add decorator)
        - Create: `tests/test_handlers/test_rate_limit_decorator.py`
    - **Action items:**
        - [RED] Write `test_rate_limit_allows_when_under_limit` — DummyHandler with `@rate_limit("search")`, service enabled, under limit → handler body runs, returns value
        - [RED] Write `test_rate_limit_blocks_when_over_limit` — Over limit → handler body NOT called, `reply_text` called with cooldown message
        - [RED] Write `test_rate_limit_noop_when_disabled` — `is_enabled` False → handler always runs regardless of limits
        - [RED] Write `test_rate_limit_returns_none_no_user` — `update.effective_user = None` → returns None
        - [RED] Write `test_rate_limit_shows_retry_seconds` — Blocked response includes `retry_after` value in message
        - [RED] Write `test_rate_limit_with_require_auth_stacking` — `@require_auth @rate_limit("search")`: authenticated+under→runs, authenticated+over→rate limit msg, not authenticated→auth msg
        - [GREEN] Implement `rate_limit(category)` decorator in `src/services/rate_limit.py`
    - **Success:** `pytest tests/test_handlers/test_rate_limit_decorator.py -v` all green, `python -m flake8 src/services/rate_limit.py` clean

---

### Phase 2: Handler Integration + i18n + Verification (2 tasks)

**Goal:** Wire the decorator into real handler methods, add translation keys, and verify everything works end-to-end.

- [ ] **2.1** Add translation keys and apply `@rate_limit` to handler methods
    - **Context:**
        - **Why:** The service and decorator are built — now wire them into the actual bot handlers and add the user-facing cooldown message in all supported languages.
        - **Architecture:** Import `rate_limit` from `src.services.rate_limit` in each handler. Stack BELOW `@require_auth` (auth runs first as outermost). For `auth.py`, `start_auth` has no `@require_auth` (it IS the auth flow) — apply `@rate_limit("auth")` directly. Translation key `RateLimitExceeded` uses `%(seconds)s` %-formatting (matches `TranslationService.get_text()` line 98).
        - **Key refs:**
            - `src/bot/handlers/media.py:187,218,249` — `handle_movie`, `handle_series`, `handle_music` with `@require_auth`
            - `src/bot/handlers/auth.py:101` — `start_auth` (no `@require_auth`)
            - `src/bot/handlers/delete.py:34-35` — `handle_delete` with `@require_auth`
            - `src/bot/handlers/library.py:48-59` — `handle_all_movies/series/music` with `@require_auth`
            - `translations/addarr.en-us.yml` — flat key format, %-formatting with `%(key)s`
        - **Watch out:**
            - **Mock config has `rateLimit.enable: False` by default** (set in task 1.1) — existing handler tests won't be affected because the decorator is a no-op when disabled
            - All 9 language files + template must get the new key — use English text for non-English files (translators update later)
            - Run `PYTHONIOENCODING=utf-8 python run.py --validate-i18n` to confirm no missing keys
            - `delete.py` has `handle_delete` (entry point) and `handle_delete_selection` (callback) — only rate-limit the entry point
    - **Scope:** Add `RateLimitExceeded` translation key to all 10 translation files. Add `@rate_limit` decorator to 7 handler methods across 4 files. Verify existing tests still pass.
    - **Touches:**
        - Modify: `src/bot/handlers/media.py` (add import + 3 decorators)
        - Modify: `src/bot/handlers/auth.py` (add import + 1 decorator)
        - Modify: `src/bot/handlers/delete.py` (add import + 1 decorator)
        - Modify: `src/bot/handlers/library.py` (add import + 3 decorators)
        - Modify: `translations/addarr.en-us.yml` + 8 other locale files + `translations/addarr.template.yml`
    - **Action items:**
        - [GREEN] Add `RateLimitExceeded` key to all translation files (en-us, de-de, es-es, fr-fr, it-it, nl-be, pl-pl, pt-pt, ru-ru, template)
        - [GREEN] Add `from src.services.rate_limit import rate_limit` and `@rate_limit("search")` to `media.py` on `handle_movie`, `handle_series`, `handle_music`
        - [GREEN] Add `from src.services.rate_limit import rate_limit` and `@rate_limit("auth")` to `auth.py` on `start_auth`
        - [GREEN] Add `from src.services.rate_limit import rate_limit` and `@rate_limit("modify")` to `delete.py` on `handle_delete`
        - [GREEN] Add `from src.services.rate_limit import rate_limit` and `@rate_limit("search")` to `library.py` on `handle_all_movies`, `handle_all_series`, `handle_all_music`
        - [GREEN] Run existing handler test suite: `pytest tests/test_handlers/ -v` — all must pass unchanged
        - [GREEN] Validate translations: `PYTHONIOENCODING=utf-8 python run.py --validate-i18n`
    - **Success:** All existing handler tests pass, translation validation passes, `python -m flake8 .` clean

- [ ] **2.2** Full verification and coverage check
    - **Context:**
        - **Why:** Final gate before PR — ensure 100% coverage on new code, all checks pass, no regressions.
        - **Architecture:** Run full test suite, coverage analysis on `src.services.rate_limit`, flake8, translation validation, architecture tests.
        - **Key refs:**
            - `tests/test_architecture/test_conventions.py` — should already pass from task 1.1 SINGLETON_CLASSES update
        - **Watch out:**
            - Coverage must use dotted module paths (`--cov=src.services.rate_limit`), not file paths
            - Any uncovered lines need new tests added
    - **Scope:** Verification-only task. Fix any gaps found.
    - **Touches:** Potentially any test file if coverage gaps found
    - **Action items:**
        - [GREEN] Run full test suite: `pytest --tb=short -q`
        - [GREEN] Run coverage: `pytest --cov=src.services.rate_limit --cov-report=term-missing tests/test_services/test_rate_limit_service.py tests/test_handlers/test_rate_limit_decorator.py`
        - [GREEN] Fix any uncovered lines by adding targeted tests
        - [GREEN] Run flake8: `python -m flake8 .`
        - [GREEN] Run translation validation: `PYTHONIOENCODING=utf-8 python run.py --validate-i18n`
        - [GREEN] Run architecture tests: `pytest tests/test_architecture/ -v`
    - **Success:** 100% coverage on `src/services/rate_limit.py`, all checks green, ready for PR

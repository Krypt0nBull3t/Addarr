# Rate Limiting on Commands and API Calls — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add per-user, per-category rate limiting to Telegram bot handlers to prevent API abuse and brute-force auth attempts.

**Architecture:** A `RateLimitService` singleton tracks per-user request timestamps in memory using a sliding window algorithm. A `@rate_limit("category")` decorator (mirroring `@require_auth`) wraps handler methods to check/enforce limits before the handler body runs. Config section `rateLimit` controls enable/disable and per-category limits. The decorator becomes a no-op when rate limiting is disabled.

**Tech Stack:** Python stdlib only (`time`, `collections`). No new dependencies.

---

## Context

### How `@require_auth` Works (the pattern to follow)

**File:** `src/bot/handlers/auth.py:36-50`

```python
def require_auth(func):
    @wraps(func)
    async def wrapped(self, update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if not update.effective_user:
            return
        if not AuthHandler.is_authenticated(update.effective_user.id):
            translation = TranslationService()
            await update.message.reply_text(
                translation.get_text("NotAuthorized", default="...")
            )
            return
        return await func(self, update, context, *args, **kwargs)
    return wrapped
```

Key characteristics:
- Takes `self, update, context` — it decorates *instance methods* on handler classes
- Extracts `update.effective_user.id` for the user check
- Returns early with a translated message on failure
- Returns the wrapped function's result on success
- Uses `functools.wraps` to preserve metadata

### Handler Method Signatures

All handler methods: `async def method(self, update: Update, context: ContextTypes.DEFAULT_TYPE)`

Decorator stacking order (auth first, then rate limit):
```python
@require_auth
@rate_limit("search")
async def handle_movie(self, update, context):
    ...
```

Auth runs first — no point rate-limiting unauthenticated users.

### Config Access Pattern

Per CLAUDE.md: **bracket access `config["key"]` is banned in business logic**. Always use `config.get("key", default)`.

Current config structure has `security:` section at line 135-138 of `config_example.yaml`. The `rateLimit` section goes right after it (grouping security-adjacent features).

### Singleton Service Pattern

From `src/services/translation.py`:
```python
class TranslationService:
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TranslationService, cls).__new__(cls)
            cls._initialize()
        return cls._instance
```

Reset in `tests/conftest.py` autouse fixture: `TranslationService._instance = None`

### Test Patterns

- Import inside test functions (after `sys.modules` injection)
- Patch at the import site: `@patch("src.bot.handlers.auth.TranslationService")`
- Use `DummyHandler` class for decorator tests (see `test_auth_handler.py`)
- Factory fixtures: `make_update`, `make_context`, `make_user`

### Architecture Test Updates

`tests/test_architecture/test_conventions.py:20-29` has `SINGLETON_CLASSES` set — must add `RateLimitService`.

---

## Design Decisions

1. **In-memory sliding window** — No external store (Redis, SQLite). Timestamps are pruned on each check. State resets on bot restart (acceptable for this use case).

2. **Three categories with sensible defaults:**
   - `search`: 10 requests per 60 seconds (movie/series/music search commands)
   - `modify`: 5 requests per 60 seconds (add/delete operations)
   - `auth`: 3 requests per 300 seconds (password attempts)

3. **Decorator takes category string** — `@rate_limit("search")`. Category maps to config limits. Unknown categories fall back to a default (10/60s).

4. **No-op when disabled** — `rateLimit.enable: false` makes the decorator pass through immediately. Zero overhead for users who don't want it.

5. **Cooldown message shows remaining wait time** — e.g., "Please wait 23 seconds before trying again." Uses `TranslationService` for i18n.

6. **Service placed in `src/services/`** — Follows existing singleton pattern. Not a handler, not a utility — it's business logic that tracks state.

7. **Decorator placed in `src/bot/handlers/auth.py`** — Wait, no. The rate limit decorator is separate from auth. It should live alongside the service in a dedicated module or in a shared decorators module. Since `require_auth` already lives in `auth.py` and is imported by other handlers, a new `src/bot/handlers/rate_limit.py` module for just the decorator would be clean. But handlers shouldn't contain service logic. Better approach: **decorator in the service file** (`src/services/rate_limit.py`) — the service and its decorator are a cohesive unit. Handlers import `rate_limit` from `src.services.rate_limit`, same as they import `require_auth` from `src.bot.handlers.auth`.

   Actually, to match the existing pattern: `require_auth` is in `src/bot/handlers/auth.py` because it's tightly coupled to `AuthHandler`. The rate limit decorator is tightly coupled to `RateLimitService`. So: **decorator and service together in `src/services/rate_limit.py`**.

8. **Layer boundary compliance** — Handlers import from services (allowed). The decorator lives in services, so handler → service import is fine. The service doesn't import handlers (correct direction).

---

## File Structure

```
src/services/rate_limit.py          # NEW: RateLimitService + @rate_limit decorator
src/utils/error_handler.py          # MODIFY: add RateLimitExceededError
config_example.yaml                 # MODIFY: add rateLimit section
tests/conftest.py                   # MODIFY: add singleton reset + mock config
tests/test_services/test_rate_limit_service.py  # NEW: service unit tests
tests/test_handlers/test_rate_limit_decorator.py # NEW: decorator integration tests
tests/test_architecture/test_conventions.py     # MODIFY: add to SINGLETON_CLASSES
translations/addarr.en-us.yml       # MODIFY: add RateLimitExceeded key
translations/addarr.template.yml    # MODIFY: add RateLimitExceeded key
```

Handler files modified to apply decorator:
```
src/bot/handlers/media.py           # @rate_limit("search") on handle_movie, handle_series, handle_music
src/bot/handlers/auth.py            # @rate_limit("auth") on start_auth
src/bot/handlers/delete.py          # @rate_limit("modify") on delete methods
src/bot/handlers/library.py         # @rate_limit("search") on library commands
```

---

## Phased Approach

### Phase 1: Core Service (Tasks 1.1–1.3)
Build `RateLimitService` with full test coverage. Pure logic, no Telegram integration yet.

### Phase 2: Decorator + Error (Tasks 2.1–2.2)
Build `@rate_limit` decorator and `RateLimitExceededError`. Test with dummy handlers.

### Phase 3: Config + i18n (Tasks 3.1–3.2)
Add config section and translation keys. Wire service to read from config.

### Phase 4: Handler Integration (Tasks 4.1–4.2)
Apply decorator to handler methods. Update architecture tests. End-to-end verification.

---

## Task Breakdown

### Task 1.1: RateLimitService — Core Sliding Window Logic

**Size:** Medium (~30 min)

**Files:**
- Create: `src/services/rate_limit.py`
- Create: `tests/test_services/test_rate_limit_service.py`
- Modify: `tests/conftest.py` (singleton reset)
- Modify: `tests/test_architecture/test_conventions.py` (SINGLETON_CLASSES)

**What to build:**

`RateLimitService` singleton with:
- `_instance = None` class var (singleton pattern via `__new__`)
- `_records: dict` class var — `{user_id: {category: [timestamps]}}`
- `check(user_id: int, category: str) -> tuple[bool, int]` — Returns `(allowed, retry_after_seconds)`. Prunes expired timestamps, checks count against limit, records new timestamp if allowed.
- `_get_limit(category: str) -> tuple[int, int]` — Returns `(max_requests, window_seconds)` for a category. Reads from config with hardcoded defaults.
- `reset()` classmethod — Clears all records (for testing).

**Default limits (when config missing or disabled):**
```python
DEFAULT_LIMITS = {
    "search": (10, 60),
    "modify": (5, 60),
    "auth": (3, 300),
}
DEFAULT_FALLBACK = (10, 60)
```

**Singleton reset in conftest.py:**
```python
from src.services.rate_limit import RateLimitService
RateLimitService._instance = None
RateLimitService._records = {}
```

**SINGLETON_CLASSES update:**
Add `"RateLimitService"` to the set in `test_conventions.py:20-29`.

**Tests to write:**
1. `test_check_allows_first_request` — First request for a user/category returns `(True, 0)`
2. `test_check_allows_under_limit` — Multiple requests under limit all return `(True, 0)`
3. `test_check_blocks_over_limit` — Requests exceeding limit return `(False, retry_seconds > 0)`
4. `test_check_allows_after_window_expires` — After window passes, requests are allowed again (mock `time.time`)
5. `test_check_prunes_expired_timestamps` — Old timestamps are removed on check
6. `test_different_categories_independent` — Hitting search limit doesn't affect modify limit
7. `test_different_users_independent` — User A's limits don't affect User B
8. `test_get_limit_defaults` — Unknown category returns default fallback
9. `test_reset_clears_all` — `reset()` empties all records
10. `test_singleton_pattern` — Two instantiations return same object

---

### Task 1.2: RateLimitService — Config Integration

**Size:** Small (~15 min)

**Files:**
- Modify: `src/services/rate_limit.py`
- Modify: `config_example.yaml`
- Modify: `tests/test_services/test_rate_limit_service.py`

**What to build:**

Add `rateLimit` section to `config_example.yaml` after `security:` (line ~139):
```yaml
# Rate Limiting Configuration
rateLimit:
  enable: false
  limits:
    search:
      maxRequests: 10
      windowSeconds: 60
    modify:
      maxRequests: 5
      windowSeconds: 60
    auth:
      maxRequests: 3
      windowSeconds: 300
```

Update `_get_limit()` to read from config:
```python
def _get_limit(self, category):
    rate_config = config.get("rateLimit", {})
    limits = rate_config.get("limits", {})
    cat_config = limits.get(category, {})
    max_req = cat_config.get("maxRequests", DEFAULT_LIMITS.get(category, DEFAULT_FALLBACK)[0])
    window = cat_config.get("windowSeconds", DEFAULT_LIMITS.get(category, DEFAULT_FALLBACK)[1])
    return (max_req, window)
```

Add `is_enabled()` property:
```python
@property
def is_enabled(self):
    return config.get("rateLimit", {}).get("enable", False)
```

**Mock config update in `tests/conftest.py`:**
Add to `MOCK_CONFIG_DATA`:
```python
"rateLimit": {
    "enable": True,
    "limits": {
        "search": {"maxRequests": 10, "windowSeconds": 60},
        "modify": {"maxRequests": 5, "windowSeconds": 60},
        "auth": {"maxRequests": 3, "windowSeconds": 300},
    },
},
```

**Tests to write:**
1. `test_get_limit_from_config` — Config values override defaults
2. `test_get_limit_missing_category_uses_default` — Category not in config falls back
3. `test_is_enabled_true` — Returns True when config says true
4. `test_is_enabled_false` — Returns False when config says false
5. `test_is_enabled_missing_config` — Returns False when rateLimit section missing

---

### Task 2.1: Rate Limit Decorator

**Size:** Medium (~25 min)

**Files:**
- Modify: `src/services/rate_limit.py` (add `rate_limit` function)
- Create: `tests/test_handlers/test_rate_limit_decorator.py`

**What to build:**

The `rate_limit(category)` decorator factory:
```python
def rate_limit(category: str):
    """Decorator to enforce rate limiting on handler methods."""
    def decorator(func):
        @wraps(func)
        async def wrapped(self, update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            service = RateLimitService()

            # No-op when disabled
            if not service.is_enabled:
                return await func(self, update, context, *args, **kwargs)

            if not update.effective_user:
                return

            user_id = update.effective_user.id
            allowed, retry_after = service.check(user_id, category)

            if not allowed:
                translation = TranslationService()
                await update.effective_message.reply_text(
                    translation.get_text(
                        "RateLimitExceeded",
                        default=f"Slow down! Please wait {retry_after} seconds before trying again.",
                        seconds=retry_after,
                    )
                )
                return

            return await func(self, update, context, *args, **kwargs)
        return wrapped
    return decorator
```

**Tests to write (using DummyHandler pattern from test_auth_handler.py):**
1. `test_rate_limit_allows_when_under_limit` — Handler body runs, returns its value
2. `test_rate_limit_blocks_when_over_limit` — Handler body does NOT run, reply_text called with rate limit message
3. `test_rate_limit_noop_when_disabled` — When `is_enabled` is False, handler always runs
4. `test_rate_limit_returns_none_no_user` — When `update.effective_user` is None, returns None
5. `test_rate_limit_with_require_auth_stacking` — Both decorators applied: `@require_auth @rate_limit("search")`. Authenticated + under limit → handler runs. Authenticated + over limit → rate limit message. Not authenticated → auth message.
6. `test_rate_limit_shows_retry_seconds` — Reply message includes the retry_after value

---

### Task 2.2: RateLimitExceededError Exception

**Size:** Small (~5 min)

**Files:**
- Modify: `src/utils/error_handler.py`

**What to build:**

Add after `ServiceNotEnabledError` (line ~39):
```python
class RateLimitExceededError(AddarrError):
    """Raised when a user exceeds the rate limit for an action."""
    def __init__(self, category: str, retry_after: int):
        message = f"Rate limit exceeded for {category}. Retry after {retry_after}s."
        super().__init__(message)
        self.category = category
        self.retry_after = retry_after
```

This exception isn't used by the decorator directly (it handles things inline) but provides a programmatic way for other code to signal rate limit violations if needed.

**Tests:**
1. `test_rate_limit_exceeded_error_attributes` — Verify `category`, `retry_after`, and message are set correctly

---

### Task 3.1: Translation Keys

**Size:** Small (~10 min)

**Files:**
- Modify: `translations/addarr.en-us.yml`
- Modify: `translations/addarr.template.yml`
- Modify all other translation files (8 languages)

**What to add:**

In each translation file, add under the appropriate section:
```yaml
  # Rate limiting
  RateLimitExceeded: "Slow down! Please wait %(seconds)s seconds before trying again."
```

The `%(seconds)s` uses Python %-formatting which is what `TranslationService.get_text()` uses (line 98 of `translation.py`).

For `addarr.template.yml`, add the key with a placeholder comment for translators.

**Verification:** Run `PYTHONIOENCODING=utf-8 python run.py --validate-i18n` to confirm no missing keys.

---

### Task 4.1: Apply Decorator to Handlers

**Size:** Medium (~20 min)

**Files:**
- Modify: `src/bot/handlers/media.py`
- Modify: `src/bot/handlers/auth.py`
- Modify: `src/bot/handlers/delete.py`
- Modify: `src/bot/handlers/library.py`

**What to change:**

**media.py** — Add import and decorators:
```python
from src.services.rate_limit import rate_limit

# On entry-point methods:
@require_auth
@rate_limit("search")
async def handle_movie(self, update, context):

@require_auth
@rate_limit("search")
async def handle_series(self, update, context):

@require_auth
@rate_limit("search")
async def handle_music(self, update, context):
```

**auth.py** — Add import and decorator:
```python
from src.services.rate_limit import rate_limit

@rate_limit("auth")
async def start_auth(self, update, context):
```

Note: `start_auth` is NOT guarded by `@require_auth` (it IS the auth flow). Rate limiting is still applied to prevent brute-force password attempts.

**delete.py** — Add import and decorators:
```python
from src.services.rate_limit import rate_limit

@require_auth
@rate_limit("modify")
async def handle_delete_movie(self, update, context):

@require_auth
@rate_limit("modify")
async def handle_delete_series(self, update, context):
```

**library.py** — Add import and decorators:
```python
from src.services.rate_limit import rate_limit

@require_auth
@rate_limit("search")
async def handle_all_movies(self, update, context):

@require_auth
@rate_limit("search")
async def handle_all_series(self, update, context):

@require_auth
@rate_limit("search")
async def handle_all_music(self, update, context):
```

**Existing test impact:** Existing handler tests mock services at import sites. The `RateLimitService` will be instantiated inside the decorator. Tests need to either:
- Patch `src.services.rate_limit.RateLimitService` in handler tests, OR
- Patch `config.get("rateLimit", {}).get("enable", False)` to return `False` so the decorator is a no-op

The simplest approach: Add `"rateLimit": {"enable": False, ...}` to `MOCK_CONFIG_DATA` in conftest.py (already done in Task 1.2). Since the mock config has `enable: True` for rate limit tests but existing handler tests need it to not interfere — we should set the default mock config to `enable: False`, and only enable it in rate-limit-specific tests.

**Decision:** Set `MOCK_CONFIG_DATA["rateLimit"]["enable"]` to `False` by default. Rate limit tests override it to `True` in their fixtures.

**Tests:**
- Verify existing handler tests still pass with the decorator applied (no behavior change when disabled)
- Add one integration test per handler showing the decorator is wired up correctly

---

### Task 4.2: Final Verification + Architecture Test Update

**Size:** Small (~10 min)

**Files:**
- Modify: `tests/test_architecture/test_conventions.py` (already done in 1.1)

**What to verify:**
1. `pytest --tb=short -q` — All tests pass
2. `python -m flake8 .` — No lint errors
3. `PYTHONIOENCODING=utf-8 python run.py --validate-i18n` — Translations valid
4. Architecture tests pass (SINGLETON_CLASSES includes RateLimitService)
5. Coverage on new files: `pytest --cov=src.services.rate_limit --cov-report=term-missing`

---

## Verification Checklist

- [ ] `RateLimitService` is a proper singleton (has `__new__`)
- [ ] `@rate_limit("category")` decorator follows `@require_auth` pattern
- [ ] Decorator is a no-op when `rateLimit.enable` is `false`
- [ ] Config section with sensible defaults in `config_example.yaml`
- [ ] Translation key `RateLimitExceeded` in all 9 languages + template
- [ ] SINGLETON_CLASSES updated in architecture tests
- [ ] Singleton reset added in conftest.py
- [ ] Mock config data includes rateLimit section (disabled by default)
- [ ] All existing tests still pass after decorator application
- [ ] 100% coverage on `src/services/rate_limit.py`
- [ ] No flake8 violations
- [ ] No bracket config access (`config["..."]`) in new code

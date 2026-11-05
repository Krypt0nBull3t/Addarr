---
name: addarr-services
description: Use when adding new services, API clients, or extending existing ones in Addarr. Covers singleton service pattern, BaseApiClient inheritance, config access, is_enabled() convention, and the service-to-API-client relationship.
---

# Addarr Services & API Clients

Reference for building new services and API clients in Addarr. For testing these, see @addarr-testing.

## Architecture Overview

```
Handler → Service → API Client → External API
           ↑            ↑
        Singleton    BaseApiClient
        __new__()    _make_request()
```

- **Services** (`src/services/`) — Business logic, singleton pattern, aggregate API clients
- **API Clients** (`src/api/`) — HTTP communication, inherit from `BaseApiClient`
- Config accessed via `from src.config.settings import config`

## Quick Start Checklist

### New Service
1. Create `src/services/<name>.py` with singleton pattern
2. Add the class to `SINGLETON_CLASSES` in `tests/test_architecture/test_conventions.py`
3. Reset it (`_instance` and every class var `_initialize` sets) in `reset_singletons` in `tests/conftest.py`; `test_singleton_reset_coverage` cross-checks both lists
4. Optional: export from `src/services/__init__.py` (`PreferencesService`, `RateLimitService` and `WebhookService` are not exported)
5. Inject into handler via `self.<service> = <Name>Service()`

### New API Client
1. Create `src/api/<name>.py` inheriting from `BaseApiClient`
2. Implement `search()` abstract method
3. Export from `src/api/__init__.py`
4. Use from service: `self._client = <Name>Client()`

## Service Template

See [references/service-pattern.md](references/service-pattern.md) for the singleton class template with `__new__`, `_initialize`, `is_enabled()`, and async method patterns.

## API Client Template

See [references/api-client-pattern.md](references/api-client-pattern.md) for BaseApiClient inheritance, `__init__` validation, `search()` implementation, and `_make_request()` / `_request()` usage.

## Config Access

See [references/config-patterns.md](references/config-patterns.md) for nested dict access, the bracket-access ban, URL construction, enable checks, and where the config structure lives.

## Common Mistakes

See [references/anti-patterns.md](references/anti-patterns.md) for detailed examples with bad/good code.

1. Raising from `_initialize`: never propagate exceptions. Set `_enabled = False` and log `type(e).__name__`.
2. Forgetting `is_enabled()` check — Calling methods on disabled services crashes.
3. Using `__init__` for singleton state — Runs every instantiation, not just the first. Use `_initialize`.
4. Creating sessions per request in BaseApiClient subclasses — Use `_get_session()` for pooling.
5. Config bracket access: `test_no_config_bracket_access_in_business_logic` bans `config[...]` everywhere in `src/` except `src/setup/`, `src/api/base.py` and `src/config/settings.py`. Use `config.get(key, default)`.
6. Double-slash URLs — Strip trailing slashes from path config with `rstrip("/")`.
7. Incomplete singleton reset in tests — Must reset ALL class vars, not just `_instance`.
8. User input in the URL string: API clients pass user input via `params=`; fixed IDs may stay in the path.
9. Logging `str(e)`: a service that sends credentials in query parameters never logs or returns `str(e)`.

# 0001. Services are singletons

**Status:** Accepted. Recorded 2026-11-04; the rule was in force before.

## Context

Services in `src/services/` hold shared state: API client instances, cached translations, the health-check state and the webhook server. Handlers create a service by calling its class, for example `MediaService()`, in many places. If each call built a new object, the state would split across copies.

## Decision

Each service class overrides `__new__` and keeps its one instance in the class attribute `_instance`. The services are listed in `SINGLETON_CLASSES` in `tests/test_architecture/test_conventions.py`. Plain helper modules such as `src/services/webhook_formatter.py` are not services and are not listed.

Enforced by:

- `test_all_services_implement_singleton`: every class in `SINGLETON_CLASSES` defines `__new__`.
- `test_singleton_reset_coverage`: every class in `SINGLETON_CLASSES` is reset in the `reset_singletons` fixture in `tests/conftest.py`.

## Consequences

- A new service needs three changes: `__new__`, an entry in `SINGLETON_CLASSES`, and a reset of `_instance` in `reset_singletons`.
- Tests share one instance per class unless the fixture resets it, so a missing reset leaks state between tests.
- mypy cannot see attributes set in `__new__` or `_initialize`. Declare them as class-level annotations.

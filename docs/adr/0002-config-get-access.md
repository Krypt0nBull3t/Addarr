# 0002. Read config with `config.get()`, not `config["key"]`

**Status:** Accepted. Recorded 2026-11-04; enforced by test since 2026-03-03.

## Context

`src/config/settings.py` exports a module-level `config` loaded from `config.yaml`. Users run old config files, and keys can be missing. `config["key"]` raises `KeyError` on a missing key, with no fallback, and stops the handler that reads it.

## Decision

Business logic in `src/` reads config with `config.get("key", default)`. Bracket access is allowed only in:

- `src/setup/`, which builds the config interactively;
- `src/api/base.py`, which reads `self.config`, the service dict it already extracted;
- `src/config/settings.py`, which defines `__getitem__`.

Enforced by `test_no_config_bracket_access_in_business_logic` in `tests/test_architecture/test_conventions.py`. A related check, `test_config_calls_exist_on_real_config`, stops `src/` from calling methods that only the test `MockConfig` has.

## Consequences

- A missing key gives the default instead of a crash. Pick a default that keeps the feature off or safe.
- A new exclusion needs a reason and an entry in `BRACKET_ACCESS_EXCLUDED`.

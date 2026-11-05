# Config Access Patterns

## Import

```python
from src.config.settings import config
```

Always module-level import. `config` is a module-level singleton loaded from `config.yaml`.

## Safe Nested Access

```python
# Chain .get() with empty dict defaults to avoid KeyError
config.get("radarr", {}).get("enable", False)
config.get("radarr", {}).get("server", {}).get("addr")
config.get("sabnzbd", {}).get("auth", {}).get("apikey")
```

## Enable Check Pattern

```python
if config.get("<service_key>", {}).get("enable", False):
    # Service is enabled, safe to access deeper config
    client = <Name>Client()
```

## Bracket Access Is Banned

`test_no_config_bracket_access_in_business_logic` bans `config[...]` everywhere in `src/` except `src/setup/`, `src/api/base.py` and `src/config/settings.py`. Use `config.get(key, default)` everywhere else.

The only example of allowed bracket access is `BaseApiClient` in `src/api/base.py`. It indexes directly because it's only built for enabled services:

```python
# In BaseApiClient
self.config = config[service_name]          # __init__, e.g. config["radarr"]
server_config = self.config["server"]       # _build_base_url
api_key = self.config["auth"]["apikey"]     # _get_headers
```

## URL Construction

Standard pattern used by all services/clients:

```python
server_config = config.get("<service_key>", {}).get("server", {})
protocol = "https" if server_config.get("ssl", False) else "http"
addr = server_config.get("addr")
port = server_config.get("port")
path = server_config.get("path", "").rstrip("/")

base_url = f"{protocol}://{addr}:{port}{path}"
```

## Config Updates

```python
# Update nested value
config.update_nested("service.enable", True)
config.update_nested("language", "en-us")

# Save to disk
config.save()
```

## Config Structure Reference

Read `config_example.yaml` for the config structure; do not copy it here. It is the template, and `Config._validate_config` checks `config.yaml` against it at startup. A new config key goes in `config_example.yaml` too.

## Path Constants

Defined in `src/definitions.py`:

| Constant | Value |
|-|-|
| `ROOT_DIR` | Project root |
| `CONFIG_PATH` | `config.yaml` |
| `CONFIG_EXAMPLE_PATH` | `config_example.yaml` |
| `TRANSLATIONS_PATH` | `translations/` |
| `CHATID_PATH` | `chatid.txt` |
| `LOG_PATH` | `logs/addarr.log` |
| `ADMIN_PATH` | `admin.txt` |
| `ALLOWLIST_PATH` | `allowlist.txt` |
| `DATA_PATH` | `data/` |
| `PREFERENCES_PATH` | `data/user_preferences.json` |
| `LEGACY_PREFERENCES_PATH` | `user_preferences.json` (read only when the `data/` file does not exist) |

`src/definitions.py` holds constants only, no functions. For access checks use `src/utils/helpers.py`: `is_admin(user_id)`, `is_allowed(user_id)`, `admin_only(service)`, or the `@require_admin(service)` decorator in `src/bot/handlers/auth.py`.

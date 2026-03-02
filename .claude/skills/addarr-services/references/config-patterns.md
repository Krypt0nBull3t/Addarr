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
if config.get("service_key", {}).get("enable", False):
    # Service is enabled, safe to access deeper config
    client = ServiceClient()
```

## Direct Access (When Key is Guaranteed)

BaseApiClient uses direct indexing because it's only called for enabled services:

```python
# In BaseApiClient.__init__
self.config = config[service_name]          # e.g., config["radarr"]
server = self.config["server"]              # guaranteed to exist
api_key = self.config["auth"]["apikey"]     # guaranteed to exist
```

## URL Construction

Standard pattern used by all services/clients:

```python
server_config = config.get("service_key", {}).get("server", {})
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

```yaml
telegram:
  token: "bot_token"

language: "en-us"

security:
  enableAdmin: false
  enableAllowlist: false

radarr:                    # Same structure for sonarr, lidarr
  enable: true
  server:
    ssl: false
    addr: "localhost"
    port: 7878
    path: ""
  auth:
    apikey: "abc123"
  paths:
    excludedRootFolders: []
    narrowRootFolderNames: false

transmission:
  enable: false
  server:
    ssl: false
    addr: "localhost"
    port: 9091
    path: "/transmission"
  auth:
    username: ""
    password: ""

sabnzbd:
  enable: false
  server:
    ssl: false
    addr: "localhost"
    port: 8080
    path: "/sabnzbd"
  auth:
    apikey: "xyz789"
```

## Path Constants

Defined in `src/definitions.py`:

| Constant | Value |
|----------|-------|
| `ROOT_DIR` | Project root |
| `CONFIG_PATH` | `config.yaml` |
| `CONFIG_EXAMPLE_PATH` | `config_example.yaml` |
| `TRANSLATIONS_PATH` | `translations/` |
| `CHATID_PATH` | `chatid.txt` |
| `LOG_PATH` | `logs/addarr.log` |
| `ADMIN_PATH` | `admin.txt` |
| `ALLOWLIST_PATH` | `allowlist.txt` |
| `DATA_PATH` | `data/` |
| `PREFERENCES_PATH` | `user_preferences.json` |

Helper functions: `is_admin(user_id)`, `is_allowed_user(user_id)`, `get_admins()`, `get_allowed_users()`

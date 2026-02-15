# Anti-Patterns

Common mistakes specific to Addarr's test suite.

---

## Module-Level Imports

**Don't** import `src.*` modules at the top of test files:

```python
# BAD - triggers Config() at import time, reads config.yaml from disk
from src.services.media import MediaService
```

**Instead**, import inside test functions or fixtures:

```python
# GOOD
def test_singleton():
    from src.services.media import MediaService
    s1 = MediaService()
    assert s1 is not None
```

**Why**: `src/config/settings.py:138` runs `config = Config()` at module level. Any `src.*` import chains back to this. The `tests/conftest.py` mock injection only works if it runs first — module-level imports in test files can race with conftest loading.

---

## Singleton Leakage

**Don't** skip the `reset_singletons` fixture or manually create singletons without cleanup:

```python
# BAD - singleton state persists to next test
def test_one():
    service = MediaService()
    MediaService._radarr = mock_client  # Leaks!
```

**Instead**, rely on the autouse `reset_singletons` fixture (it runs automatically) and set class attributes knowing they'll be cleaned up:

```python
# GOOD - reset_singletons cleans up after this test
def test_one():
    from src.services.media import MediaService
    service = MediaService()
    MediaService._radarr = mock_client
    # After test, fixture resets _instance, _radarr, _sonarr, _lidarr
```

**Why**: Singletons use `__new__` + `_instance`. If `_instance` isn't reset, the next test gets the same object with stale state. Tests pass individually but fail in random order during full suite runs.

---

## Transmission Mocking

**Don't** use `aioresponses` for Transmission API tests:

```python
# BAD - Transmission uses requests, not aiohttp
async def test_transmission(aio_mock):
    aio_mock.post("http://localhost:9091/transmission/rpc", ...)
```

**Instead**, mock `requests.post` directly:

```python
# GOOD
from unittest.mock import patch, MagicMock

def test_transmission():
    mock_response = MagicMock(status_code=200)
    mock_response.json.return_value = {"result": "success"}
    with patch("requests.post", return_value=mock_response):
        result = api._make_request("session-get", {})
```

**Why**: `src/api/transmission.py` uses synchronous `requests.post()`, not `aiohttp`. `aioresponses` only intercepts `aiohttp.ClientSession` calls. Also note: `TransmissionAPI.__init__` calls `super().__init__()` without `service_name`, so you must patch `BaseApiClient.__init__` too.

---

## Translation Testing

**Don't** assert on translated text strings:

```python
# BAD - fragile, locale-dependent
assert "Welcome to Addarr" in reply_text.call_args[0][0]
```

**Instead**, mock `get_text` to return keys and assert on those:

```python
# GOOD
mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
# Then assert:
assert "Welcome" in reply_text.call_args[0][0]  # Checks for the key
```

**Why**: The autouse `mock_translation` fixture prevents YAML loading but doesn't replace `get_text`. Handler tests need `get_text` to return predictable values. Using translation keys (identity function) makes tests locale-independent.

---

## Real Sessions

**Don't** create real `aiohttp.ClientSession` objects in tests:

```python
# BAD - makes actual HTTP connections
async def test_api():
    async with aiohttp.ClientSession() as session:
        resp = await session.get("http://localhost:7878/api/v3/system/status")
```

**Instead**, use `aioresponses` to intercept all HTTP:

```python
# GOOD
async def test_api(aio_mock, radarr_url):
    aio_mock.get(f"{radarr_url}/api/v3/system/status", payload={"version": "5.0"})
    # Client uses aiohttp internally, aioresponses intercepts it
    result = await client.check_status()
```

**Why**: Real sessions attempt network connections, making tests slow, flaky, and dependent on external services. `aioresponses` intercepts at the `aiohttp` level, so client code runs normally but HTTP is mocked.

---

## Config Patching Scope

**Don't** patch config in only one place when multiple modules import it:

```python
# BAD - only patches one import site
with patch("src.services.media.config", mock_config):
    service = MediaService()  # But API client also reads config separately
```

**Instead**, use the global `sys.modules` injection (already handled by conftest) or patch at every import site:

```python
# GOOD - conftest.py already handles this globally
# For per-test config overrides, modify the mock data:
from tests.conftest import MockConfig, MOCK_CONFIG_DATA
from copy import deepcopy
data = deepcopy(MOCK_CONFIG_DATA)
data["radarr"]["enable"] = False
```

**Why**: Python creates separate name bindings for each `from X import Y`. Patching `src.config.settings.config` doesn't affect `src.services.media.config` if media.py did `from src.config.settings import config`. The `sys.modules` injection in conftest solves this by replacing the entire module before any imports happen.

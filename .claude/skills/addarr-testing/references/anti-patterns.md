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

---

## Patching at Wrong Import Path

**Don't** patch a service at its source module when testing code that imports it:

```python
# BAD - patches the source, not where it's used
with patch("src.services.media.MediaService"):
    from src.bot.handlers.media import MediaHandler
    handler = MediaHandler()  # Still gets the real MediaService!
```

**Instead**, patch at the import site — where the module under test imports it:

```python
# GOOD - patch where the handler imports it from
with patch("src.bot.handlers.media.MediaService", return_value=mock_media_service):
    from src.bot.handlers.media import MediaHandler
    handler = MediaHandler()
```

**Why**: Python name bindings are per-module. When `media.py` does `from src.services.media import MediaService`, it creates a local binding. Patching the source module doesn't affect that local binding. You must patch at `src.bot.handlers.media.MediaService`. This applies to all services, not just config — three separate issues (#17, #67, #78) independently hit this.

---

## Not Cleaning Up Sessions Between Tests

**Don't** skip session cleanup when testing API clients with reusable sessions:

```python
# BAD - session persists, mock state leaks to next test
async def test_one(radarr_client, aio_mock, radarr_url):
    aio_mock.get(f"{radarr_url}/api/v3/system/status", payload={"version": "5.0"})
    await radarr_client.check_status()
    # Session stays open with stale mock state
```

**Instead**, use an autouse cleanup fixture or close explicitly:

```python
# GOOD - autouse fixture closes session after each test
@pytest.fixture(autouse=True)
async def cleanup_session(radarr_client):
    yield
    await radarr_client.close()

# GOOD - explicit cleanup for ad-hoc clients
async def test_custom_client():
    client = RadarrClient()
    try:
        result = await client.some_method()
    finally:
        await client.close()
```

**Why**: `BaseApiClient._get_session()` returns the existing session if one is open. Without cleanup, the next test inherits a session with stale mock state, causing mysterious failures. Two issues (#21, #76) hit this independently.

---

## Mocking sys.exit Without Stopping Execution

**Don't** mock `sys.exit` as a simple MagicMock — execution continues past the exit call:

```python
# BAD - code after sys.exit() still runs
@patch("sys.exit")
def test_reset_config(mock_exit):
    wizard._reset_config()
    mock_exit.assert_called_once_with(0)
    # But all code after sys.exit(0) in the function also executed!
```

**Instead**, use `pytest.raises(SystemExit)` to catch the real exit:

```python
# GOOD - actually stops execution at the exit point
def test_reset_config():
    with pytest.raises(SystemExit) as exc_info:
        wizard._reset_config()
    assert exc_info.value.code == 0
```

**Why**: `MagicMock()` replaces `sys.exit` with a no-op that returns `None`. The function's code after the exit call keeps running, which can trigger errors or false positives. `pytest.raises(SystemExit)` catches the actual exception that `sys.exit` raises.

---

## Insufficient Retry Mocks

**Don't** register only one failure mock when the client has retry logic:

```python
# BAD - only 1 mock but client retries 2 times (needs 3 total)
aio_mock.get(url, exception=aiohttp.ClientError("fail"))
result = await client.check_status()
# Raises ConnectionError on second attempt because no mock is registered
```

**Instead**, register one mock per attempt (initial + retries):

```python
# GOOD - 3 mocks for initial + 2 retries
for _ in range(3):
    aio_mock.get(url, exception=aiohttp.ClientError("fail"))

with patch("asyncio.sleep", new_callable=AsyncMock):
    result = await client.check_status()
    assert result is False
```

**Why**: `aioresponses` mocks are consumed in FIFO order per URL. Each request consumes one mock. If the client retries twice after the initial failure, you need 3 mocks total. Also remember to patch `asyncio.sleep` to avoid real delays during retries.

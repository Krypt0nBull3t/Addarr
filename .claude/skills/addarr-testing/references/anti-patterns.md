# Anti-Patterns

Common mistakes specific to Addarr's test suite.

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

## Translation Testing

**Don't** assert on translated text strings:

```python
# BAD - fragile, locale-dependent
assert "No movie found" in reply_text.call_args[0][0]
```

**Instead**, mock `get_text` to return keys and assert on those:

```python
# GOOD
mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
# Then assert on the key itself:
assert reply_text.call_args[0][0] == "SearchNoResults"
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
async def test_api(radarr_client, aio_mock, radarr_url):
    aio_mock.get(f"{radarr_url}/api/v3/system/status", payload={"version": "5.0"})
    # Client uses aiohttp internally, aioresponses intercepts it
    success, data, error = await radarr_client._make_request("system/status")
    assert (success, data, error) == (True, {"version": "5.0"}, None)
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

**Instead**, set the value on a fresh `mock_config` with `_set()` and patch `config` at every module that reads it. The `admin_mode` fixture in `tests/test_handlers/conftest.py` is the model:

```python
# GOOD - admin_mode in tests/test_handlers/conftest.py
@pytest.fixture
def admin_mode(mock_config):
    mock_config._set("security", {
        "enableAdmin": True, "enableAllowlist": False, "chatMode": "private_only",
    })
    mock_config._set("admins", [1])
    with patch("src.utils.helpers.config", mock_config):
        yield mock_config
```

When several modules read the value, patch each of them in the same `with`.

**Why**: Python creates separate name bindings for each `from X import Y`. Patching `src.config.settings.config` doesn't affect `src.services.media.config` if media.py did `from src.config.settings import config`. The `sys.modules` injection in conftest only decides which object every module binds at import time. To change a value for one test, patch the binding the code under test reads. A fresh `mock_config` keeps the change out of other tests.

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
with patch("src.bot.handlers.media.handler.MediaService", return_value=mock_media_service):
    from src.bot.handlers.media import MediaHandler
    handler = MediaHandler()
```

**Why**: Python name bindings are per-module. When `src/bot/handlers/media/handler.py` does `from src.services.media import MediaService`, it creates a local binding. Patching the source module doesn't affect that local binding. You must patch at `src.bot.handlers.media.handler.MediaService`; the `src.bot.handlers.media` package only re-exports `MediaHandler` and the states. This applies to all services, not just config. Three separate issues (#17, #67, #78) independently hit this.

---

## Not Cleaning Up Sessions Between Tests

The `radarr_client`, `sonarr_client`, `lidarr_client` and `bazarr_client` fixtures need nothing: the autouse `cleanup_sessions` fixture in `tests/test_api/conftest.py` closes them after each test. Do not add a cleanup fixture of your own.

**Don't** leave the session of a client you create yourself open:

```python
# BAD - not a fixture, so cleanup_sessions never closes it
async def test_custom_client(aio_mock, radarr_url):
    from src.api.radarr import RadarrClient
    client = RadarrClient()
    aio_mock.get(f"{radarr_url}/api/v3/system/status", payload={"version": "5.0"})
    await client._make_request("system/status")
    # Session stays open
```

**Instead**, close it in `finally`:

```python
# GOOD - explicit cleanup for ad-hoc clients
async def test_custom_client(aio_mock, radarr_url):
    from src.api.radarr import RadarrClient
    client = RadarrClient()
    aio_mock.get(f"{radarr_url}/api/v3/system/status", payload={"version": "5.0"})
    try:
        success, data, error = await client._make_request("system/status")
        assert success is True
    finally:
        await client.close()
```

**Why**: `BaseApiClient._get_session()` opens one `aiohttp.ClientSession` per client and keeps it until `close()`. An unclosed session outlives its test, and aiohttp reports `Unclosed client session` when it is garbage-collected. Two issues (#21, #76) hit this independently.

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
success, data, error = await radarr_client._make_request("system/status")
# The retries find no mock: aioresponses raises
# ClientConnectionError("Connection refused: GET ..."), which _make_request
# catches, so error ends as "Connection error: Connection refused: GET ..."
```

**Instead**, register one mock per attempt (initial + retries):

```python
# GOOD - 3 mocks for initial + 2 retries
for _ in range(3):
    aio_mock.get(url, exception=aiohttp.ClientError("fail"))

with patch("asyncio.sleep", new_callable=AsyncMock):
    success, data, error = await radarr_client._make_request("system/status")
assert (success, data, error) == (False, None, "Connection error: fail")
```

**Why**: `aioresponses` mocks are consumed in FIFO order per URL. Each request consumes one mock. If the client retries twice after the initial failure, you need 3 mocks total. Without them, the test checks aioresponses' "no mock" error instead of the one you set up. Also remember to patch `asyncio.sleep` to avoid real delays during retries. A timeout is never retried, so it needs one mock (see `_make_request` in `src/api/base.py`).

---

## Incomplete AST Decorator Detection

**Don't** check only `ast.Name` when detecting decorators via AST:

```python
# BAD - misses @require_auth("role") and @require_auth() forms
for dec in node.decorator_list:
    if isinstance(dec, ast.Name) and dec.id == "require_auth":
        return True
```

**Instead**, handle both bare decorators and parameterized (call) forms:

```python
# GOOD - catches @require_auth, @require_auth(), @require_auth("role")
for dec in node.decorator_list:
    if isinstance(dec, ast.Name) and dec.id == "require_auth":
        return True
    if isinstance(dec, ast.Call):
        func = dec.func
        if isinstance(func, ast.Name) and func.id == "require_auth":
            return True
```

**Why**: Python decorators appear as `ast.Name` when bare (`@decorator`) but as `ast.Call` when parameterized (`@decorator()` or `@decorator(args)`). Missing either form causes false negatives in convention tests like `test_handler_entry_points_have_require_auth`.

## Vacuous Loop Assertions

**Don't** assert only inside a loop over matches:

```python
# BAD - passes when the regex finds no heredoc bodies at all
for body in re.findall(r"<<'GRAPHIFY_PY'\n(.*?)\nGRAPHIFY_PY\n", text, re.S):
    assert not re.search(PLACEHOLDER, body)
```

**Instead**, assert that the collection is not empty, then check each item:

```python
# GOOD - fails when the pattern stops matching
bodies = skill_hits(r"<<'GRAPHIFY_PY'\n(.*?)\nGRAPHIFY_PY\n", re.S)
assert bodies
for path, body in bodies:
    assert not re.search(PLACEHOLDER, body), path
```

**Why**: A loop over zero items asserts nothing. In issue #199, two RED tests passed before the fix for this reason: no heredocs existed yet, and a regex only matched the quoted form. Watch each new test fail before you trust it.

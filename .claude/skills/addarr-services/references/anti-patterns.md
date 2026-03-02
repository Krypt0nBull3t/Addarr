# Service & API Client Anti-Patterns

Common mistakes when building services and API clients in Addarr.

---

## Raising from _initialize

**Don't** let exceptions propagate from `_initialize`:

```python
# BAD - handler that does SABnzbdService() crashes if SABnzbd is disabled
@classmethod
def _initialize(cls):
    sabnzbd_config = config.get('sabnzbd', {})
    cls.api_key = sabnzbd_config['auth']['apikey']  # KeyError if missing!
```

**Instead**, catch exceptions and set `_enabled = False`:

```python
# GOOD
@classmethod
def _initialize(cls):
    cls._enabled = False
    try:
        sabnzbd_config = config.get('sabnzbd', {})
        if not sabnzbd_config.get('enable', False):
            return
        cls.api_key = sabnzbd_config.get('auth', {}).get('apikey')
        if not cls.api_key:
            logger.error("API key not configured")
            return
        cls._enabled = True
    except Exception as e:
        logger.error(f"Failed to initialize: {e}")
        cls._enabled = False
```

**Why**: Handlers instantiate services in `__init__`. If `_initialize` raises, the handler can't be created and the bot fails to start. Setting `_enabled = False` lets the bot run with degraded functionality — handlers check `is_enabled()` before calling service methods. Issue #78 established this as the standard pattern.

---

## Forgetting is_enabled() Check

**Don't** call service methods without checking enablement:

```python
# BAD - crashes if service is disabled/misconfigured
async def handle_action(self, update, context):
    status = await self.sabnzbd_service.get_status()
```

**Instead**, always check first:

```python
# GOOD
async def handle_action(self, update, context):
    if not self.sabnzbd_service.is_enabled():
        await update.effective_message.reply_text("Service not available")
        return ConversationHandler.END
    status = await self.sabnzbd_service.get_status()
```

**Why**: A disabled service has `_client = None` and/or no API key configured. Calling methods on it produces `AttributeError` or `TypeError`. The `is_enabled()` pattern lets you fail gracefully with a user-friendly message.

---

## Using __init__ for Singleton State

**Don't** put initialization logic in `__init__` for singleton services:

```python
# BAD - runs every time Service() is called, not just the first time
class MyService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self._client = SomeClient()  # Creates new client EVERY instantiation!
        self._enabled = True
```

**Instead**, use `_initialize` classmethod called from `__new__`:

```python
# GOOD - only runs once
class MyService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._initialize()
        return cls._instance

    @classmethod
    def _initialize(cls):
        cls._client = SomeClient()
        cls._enabled = True
```

**Why**: Python calls `__init__` every time the class is called, even for singletons. `MyService()` in three handlers means `__init__` runs three times. Initializing clients or state in `__init__` creates duplicates and wastes resources. `_initialize()` in `__new__` runs exactly once.

---

## Creating Sessions Per Request in BaseApiClient Subclasses

**Don't** create new `aiohttp.ClientSession` in methods of BaseApiClient subclasses:

```python
# BAD - bypasses session pooling, leaks connections
async def get_status(self):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return response.status == 200
```

**Instead**, use the inherited session management:

```python
# GOOD - uses pooled session from BaseApiClient
async def get_status(self):
    result = await self._request("system/status")
    return result is not None
```

Or if you need direct session access:

```python
# GOOD - reuses managed session
session = await self._get_session()
async with session.get(url, headers=self._get_headers()) as response:
    return response.status == 200
```

**Why**: `BaseApiClient._get_session()` manages a reusable `aiohttp.ClientSession` with proper timeout configuration. Creating sessions per request bypasses connection pooling, leaks connections, and ignores configured timeouts. Note: Standalone clients (SABnzbd, Transmission) that don't inherit from BaseApiClient do create sessions per request — that's acceptable for those.

---

## Direct Config Indexing Without Enable Check

**Don't** access config with direct indexing before checking if the service is enabled:

```python
# BAD - KeyError if "myservice" doesn't exist in config
server = config["myservice"]["server"]
api_key = config["myservice"]["auth"]["apikey"]
```

**Instead**, use safe access with defaults:

```python
# GOOD
service_config = config.get("myservice", {})
if not service_config.get("enable", False):
    return  # Service not enabled

server = service_config.get("server", {})
addr = server.get("addr")
```

**Why**: `config["key"]` raises `KeyError` if the key doesn't exist. Services that aren't configured won't have entries in `config.yaml`. Always use `.get(key, {})` for nested access until you've confirmed the service is enabled. `BaseApiClient.__init__` uses `config[service_name]` directly, but it's only called after the service is confirmed enabled.

---

## Double-Slash URLs

**Don't** leave trailing slashes in path config that gets concatenated:

```python
# BAD - produces "http://localhost:7878//api/v3/..."
path = server_config.get("path", "/")
base_url = f"{protocol}://{addr}:{port}{path}"
```

**Instead**, strip trailing slashes:

```python
# GOOD
path = server_config.get("path", "").rstrip("/")
base_url = f"{protocol}://{addr}:{port}{path}"
```

**Why**: The `server.path` config value of `"/"` causes double-slash URLs. `BaseApiClient._build_base_url()` already handles this with `rstrip("/")`, but if you're building URLs manually in a standalone client, you must do it yourself. Issue #76 identified this as the root cause of URL issues.

---

## Incomplete Singleton Reset in Tests

**Don't** only reset `_instance` when adding a new singleton:

```python
# BAD - only resets instance, not class-level state
MyService._instance = None
# Next test gets _instance = None but _enabled still True from previous test!
```

**Instead**, reset ALL class variables set in `_initialize`:

```python
# GOOD - in reset_singletons fixture
MyService._instance = None
MyService._enabled = False
MyService._client = None
```

**Why**: Singleton class variables persist across tests. Resetting only `_instance` means the next test creates a new singleton but `_initialize()` runs again — however, conditional logic like `if cls._client is None` may skip re-initialization because the old value is still set. Three separate issues (#67, #78, #81) independently discovered this. See @addarr-testing fixtures.md for the full reset list.

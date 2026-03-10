# Test Patterns by Layer

## Table of Contents

- [API Clients](#api-clients)
- [Services](#services)
- [Handlers](#handlers)
- [Integration Tests](#integration-tests)
- [Config](#config)
- [Keyboards](#keyboards)
- [Translations](#translations)

---

## API Clients

All API clients use `aiohttp` (except Transmission). Test with `aioresponses`.

### URL Patterns

| Client | API Version | Base URL |
|--------|------------|----------|
| Radarr | `/api/v3/` | `http://localhost:7878` |
| Sonarr | `/api/v3/` | `http://localhost:8989` |
| Lidarr | `/api/v1/` | `http://localhost:8686` |
| SABnzbd | (query params) | `http://localhost:8090` |

### aioresponses Pattern

```python
async def test_search_success(radarr_client, aio_mock, radarr_url):
    from tests.fixtures.sample_data import RADARR_SEARCH_RESULTS
    aio_mock.get(
        f"{radarr_url}/api/v3/movie/lookup?term=test",
        payload=RADARR_SEARCH_RESULTS
    )
    results = await radarr_client.search("test")
    assert len(results) == 2
```

### Error Simulation

```python
async def test_search_connection_error(radarr_client, aio_mock, radarr_url):
    import aiohttp
    aio_mock.get(
        f"{radarr_url}/api/v3/movie/lookup?term=test",
        exception=aiohttp.ClientError("Connection refused")
    )
    results = await radarr_client.search("test")
    assert results == []
```

### POST Requests (add_movie, add_series, add_artist)

```python
async def test_add_movie_success(radarr_client, aio_mock, radarr_url):
    # Mock the lookup first
    aio_mock.get(
        f"{radarr_url}/api/v3/movie/lookup/tmdb/123",
        payload={"tmdbId": 123, "title": "Test Movie"}
    )
    # Mock the POST
    aio_mock.post(
        f"{radarr_url}/api/v3/movie",
        payload={"id": 1, "title": "Test Movie"}
    )
    success, message = await radarr_client.add_movie(
        tmdb_id=123, quality_profile_id=1, root_folder="/movies"
    )
    assert success is True
```

### Transmission (sync requests)

Transmission uses `requests.post`, NOT aiohttp. Mock differently:

```python
from unittest.mock import patch, MagicMock
from src.api.base import BaseApiClient

@patch.object(BaseApiClient, '__init__', lambda self, *a, **kw: None)
def test_make_request_success():
    from src.api.transmission import TransmissionAPI
    api = TransmissionAPI(host="localhost", port=9091)

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"result": "success", "arguments": {}}

    with patch("requests.post", return_value=mock_response):
        result = api._make_request("session-get", {})
        assert result["result"] == "success"
```

### Session ID Negotiation (Transmission)

Transmission returns 409 with `X-Transmission-Session-Id` header on first request:

```python
def test_session_id_negotiation():
    response_409 = MagicMock(status_code=409)
    response_409.headers = {"X-Transmission-Session-Id": "abc123"}

    response_200 = MagicMock(status_code=200)
    response_200.json.return_value = {"result": "success"}

    with patch("requests.post", side_effect=[response_409, response_200]):
        result = api._make_request("session-get", {})
        assert result["result"] == "success"
```

---

## Services

Services are singletons. Test by:
1. Resetting singleton state (autouse fixture handles this)
2. Injecting mock clients via class attributes
3. Testing async methods with `pytest-asyncio`

### Singleton Testing

```python
def test_media_service_singleton():
    from src.services.media import MediaService
    s1 = MediaService()
    s2 = MediaService()
    assert s1 is s2
```

### Injecting Mock Clients

```python
async def test_search_movies(mock_radarr_client):
    from src.services.media import MediaService
    service = MediaService()
    MediaService._radarr = mock_radarr_client
    mock_radarr_client.search.return_value = [{"title": "Test", "tmdbId": 123}]

    results = await service.search_movies("test")
    mock_radarr_client.search.assert_called_once_with("test")
```

### Health Service Pattern

```python
async def test_check_service_health():
    from src.services.health import HealthService
    service = HealthService()

    with patch("aiohttp.ClientSession") as mock_session_class:
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"version": "5.0"})
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session_class.return_value.__aenter__ = AsyncMock(return_value=mock_session)

        online, msg = await service._check_service_health("http://localhost:7878/api/v3/system/status", "test-key")
        assert online is True
```

### TranslationService Pattern

Mock `_load_translations` (autouse fixture already does this), then set `_translations` directly:

```python
def test_get_text():
    from src.services.translation import TranslationService
    service = TranslationService()
    TranslationService._translations = {
        "en-us": {"greeting": "Hello %(name)s"},
    }
    service._current_language = "en-us"

    result = service.get_text("greeting", name="World")
    assert result == "Hello World"
```

---

## Handlers

Handlers create services in `__init__`. Patch service constructors before instantiation.

### Handler Test Pattern

```python
from unittest.mock import patch, MagicMock, AsyncMock

async def test_handle_movie(make_update, make_context, mock_media_service, mock_translation_service):
    with patch("src.bot.handlers.media.MediaService", return_value=mock_media_service):
        with patch("src.bot.handlers.media.TranslationService", return_value=mock_translation_service):
            from src.bot.handlers.media import MediaHandler
            handler = MediaHandler()
            handler.media_service = mock_media_service
            handler.translation = mock_translation_service

    update = make_update(callback_data="menu_movie")
    context = make_context()
    result = await handler.handle_movie(update, context)
    assert context.user_data["search_type"] == "movie"
```

### Text Message vs Callback Query

```python
# Text message update
update = make_update(text="search term")

# Callback query update
update = make_update(callback_data="select_0")
```

### State Transitions

```python
from src.bot.states import States

async def test_search_returns_selecting(handler, make_update, make_context):
    mock_media_service.search_movies.return_value = [{"title": "Movie"}]
    update = make_update(text="Movie")
    context = make_context(user_data={"search_type": "movie"})
    result = await handler.handle_search(update, context)
    assert result == States.SELECTING
```

### Testing @require_auth

```python
async def test_require_auth_blocks_unauthenticated(make_update, make_context):
    from src.bot.handlers.auth import AuthHandler
    AuthHandler._authenticated_users = set()  # Empty

    update = make_update(text="/start")
    context = make_context()

    # The decorated handler should reply with auth message
    result = await decorated_handler(update, context)
    update.effective_message.reply_text.assert_called()
```

### Testing get_handler()

```python
def test_get_handler_returns_list():
    from src.bot.handlers.media import MediaHandler
    with patch("src.bot.handlers.media.MediaService"), \
         patch("src.bot.handlers.media.TranslationService"):
        handler = MediaHandler()
    handlers = handler.get_handler()
    assert isinstance(handlers, list)
    assert len(handlers) > 0
```

---

## Integration Tests

Integration tests live in `tests/integration/` and exercise full conversation flows through real PTB handler chains — no Telegram connection needed.

### Infrastructure

| File | Purpose |
|------|---------|
| `conftest.py` | `BotHarness` class, update factories, `harness` and `downloads_harness` fixtures |
| `fixtures.py` | Shared test data (search results, quality profiles, queue data) |
| `api_mocks.py` | Mock API helper for consistent service responses |

### BotHarness

`BotHarness` wraps a real PTB `Application` with all handlers registered. It intercepts `HTTPXRequest.do_request` to capture outgoing bot API calls and return fake results.

Key methods:

```python
await harness.send_command("/movie")          # Simulate /command
await harness.send_text("search term")        # Simulate plain text
await harness.tap_button("callback_data")     # Simulate inline button tap
harness.get_conversation_state("name", chat_id, user_id)  # Inspect state
harness.responses                             # List of all captured BotResponse objects
harness.last_response                         # Most recent BotResponse
```

### Fixtures

```python
@pytest.fixture
async def harness():
    """Pre-authenticated user (12345), all standard handlers registered."""

@pytest.fixture
async def downloads_harness():
    """Like harness but with Transmission + SABnzbd handlers enabled."""
```

### Writing a New Integration Test

```python
import pytest
from unittest.mock import AsyncMock, patch
from src.services.media import MediaService

@pytest.mark.asyncio
async def test_movie_happy_path(harness):
    """/movie -> search -> select -> quality -> added."""
    with (
        patch.object(MediaService, "search_movies", new_callable=AsyncMock,
                     return_value=MOVIE_SEARCH_RESULTS),
        patch.object(MediaService, "add_movie", new_callable=AsyncMock,
                     return_value=MOVIE_QUALITY_RESULT),
        patch.object(MediaService, "add_movie_with_profile", new_callable=AsyncMock,
                     return_value=(True, "Added")),
    ):
        resp = await harness.send_command("/movie")
        assert "Title" in resp.text

        resp = await harness.send_text("fight club")
        assert len(harness.responses) >= 1

        resp = await harness.tap_button("select_550")
        assert "quality" in resp.text.lower()

        resp = await harness.tap_button("quality_1")
        assert "added" in resp.text.lower()
```

### Key Patterns

- **Patch on the singleton class**, not the instance. Handlers hold a reference obtained at construction time, so `patch.object(MediaService, "method")` works because it patches the class-level method that the instance delegates to.
- **Use `new_callable=AsyncMock`** for async service methods.
- **Check `harness.responses`** (plural) when a step produces multiple bot messages (e.g., photo + text).
- **Verify conversation state** with `harness.get_conversation_state("media_conversation", 12345, 12345)` to confirm state transitions or conversation end (`None`).
- **Test data** goes in `tests/integration/fixtures.py` — reuse existing constants where possible.

### When to Write Integration Tests

Write an integration test when a task:
- Adds a new command or conversation flow
- Adds new states or callback routes to an existing flow
- Changes how handlers interact (e.g., auth gating, cancel behavior)
- Modifies conversation state transitions

Skip integration tests for:
- API client changes (covered by unit tests with `aioresponses`)
- Service logic changes (covered by unit tests with mock clients)
- Config, utils, translations, CI, docs changes

---

## Config

### Overriding Config Per-Test

```python
def test_with_custom_config(mock_config):
    mock_config._set("language", "de-de")
    assert mock_config.get("language") == "de-de"
```

### Testing with Disabled Services

```python
def test_radarr_disabled():
    from tests.conftest import MockConfig, MOCK_CONFIG_DATA
    from copy import deepcopy
    data = deepcopy(MOCK_CONFIG_DATA)
    data["radarr"]["enable"] = False
    cfg = MockConfig(data)
    assert cfg["radarr"]["enable"] is False
```

---

## Keyboards

Keyboard functions call `TranslationService().get_text()`. Patch the service:

```python
from unittest.mock import patch, MagicMock

@patch("src.bot.keyboards.TranslationService")
def test_main_menu_keyboard(mock_ts_class):
    mock_ts = MagicMock()
    mock_ts.get_text.side_effect = lambda key, **kw: key
    mock_ts_class.return_value = mock_ts

    from src.bot.keyboards import get_main_menu_keyboard
    keyboard = get_main_menu_keyboard()

    assert keyboard is not None
    # Check callback_data values on buttons
    buttons = [btn for row in keyboard.inline_keyboard for btn in row]
    callback_data = [btn.callback_data for btn in buttons]
    assert "menu_movie" in callback_data
```

---

## Translations

The `mock_translation` autouse fixture patches `_load_translations`. For tests that need specific translations, set `_translations` directly on the class:

```python
def test_with_specific_translations():
    from src.services.translation import TranslationService
    service = TranslationService()
    TranslationService._translations = {
        "en-us": {"key": "English value"},
        "de-de": {"key": "German value"},
    }
    service._current_language = "de-de"
    assert service.get_text("key") == "German value"
```

For handler tests, mock `get_text` to return keys (identity function):

```python
mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
```

This way assertions check for translation keys, not locale-specific text.

---

## Retry and Timeout Testing

API clients inherit retry logic from `BaseApiClient`. Testing retries requires specific mock setup.

### aioresponses FIFO Ordering

`aioresponses` mocks are consumed in FIFO order per URL. Register one mock per attempt:

```python
async def test_retry_then_succeed(radarr_client, aio_mock, radarr_url):
    url = f"{radarr_url}/api/v3/system/status"
    # First attempt: failure (consumed first)
    aio_mock.get(url, exception=aiohttp.ClientError("fail"))
    # Second attempt: success (consumed second)
    aio_mock.get(url, payload={"version": "5.0"})

    result = await radarr_client.check_status()
    assert result is True
```

For N retries, register N+1 mocks (1 initial + N retries). Example with 2 retries configured:

```python
async def test_all_retries_exhausted(radarr_client, aio_mock, radarr_url):
    url = f"{radarr_url}/api/v3/system/status"
    # Initial + 2 retries = 3 mocks
    for _ in range(3):
        aio_mock.get(url, exception=aiohttp.ClientError("fail"))

    result = await radarr_client.check_status()
    assert result is False
```

### Patching asyncio.sleep for Backoff

Retry logic uses `asyncio.sleep` for backoff delays. Patch at module level to avoid real delays and verify backoff values:

```python
async def test_retry_backoff(radarr_client, aio_mock, radarr_url):
    url = f"{radarr_url}/api/v3/system/status"
    aio_mock.get(url, exception=aiohttp.ClientError("fail"))
    aio_mock.get(url, payload={"version": "5.0"})

    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        await radarr_client.check_status()
        mock_sleep.assert_called_once_with(1)  # First backoff = 1s
```

### TimeoutError Handling

`asyncio.TimeoutError` does NOT inherit from `aiohttp.ClientError` — they require separate handling but both are retryable:

```python
async def test_timeout_triggers_retry(radarr_client, aio_mock, radarr_url):
    url = f"{radarr_url}/api/v3/system/status"
    aio_mock.get(url, exception=asyncio.TimeoutError())
    aio_mock.get(url, payload={"version": "5.0"})

    with patch("asyncio.sleep", new_callable=AsyncMock):
        result = await radarr_client.check_status()
        assert result is True
```

### Updating Existing Tests for Retry

When retry logic is added to a client, existing error tests need more mocks. A test that previously registered 1 failure mock now needs initial + retries:

```python
# BEFORE retry logic: 1 mock
aio_mock.get(url, exception=aiohttp.ClientError("fail"))

# AFTER retry logic (2 retries): 3 mocks
for _ in range(3):
    aio_mock.get(url, exception=aiohttp.ClientError("fail"))
```

---

## Session Cleanup

API clients reuse `aiohttp.ClientSession` for performance. Tests must close sessions to prevent mock state leaking across test boundaries.

### Autouse Cleanup Fixture

```python
@pytest.fixture(autouse=True)
async def cleanup_session(radarr_client):
    yield
    await radarr_client.close()
```

### Ad-hoc Client Instances

Tests that create their own client instances (bypassing the shared fixture) must close explicitly:

```python
async def test_custom_client():
    client = RadarrClient()
    try:
        result = await client.some_method()
        assert result is not None
    finally:
        await client.close()
```

### Why This Matters

`_get_session()` returns an existing session if one is open. If a previous test's session is still open with stale mock state, the next test inherits that state. The `cleanup_session` fixture ensures each test starts with a fresh session.

---

## API Client vs Service Layer Conventions

The codebase has two distinct patterns for API interaction. Tests must match the convention of the layer under test.

### API Client Layer

- URLs built with f-strings and inline query params
- Returns raw responses: `response.status == 200`
- Error handling: catches `aiohttp.ClientError`
- Mock with: `aioresponses` matching exact URL strings (including query params)

```python
# API client code style
url = f"{self.base_url}/api/v3/movie/lookup?term={query}"
async with self._session.get(url) as response:
    if response.status == 200:
        return await response.json()
```

### Service Layer

- Uses params dicts passed to `session.get(url, params=...)`
- Returns normalized shapes: `data.get('status', False)`
- Error handling: checks parsed data structure, returns domain-specific defaults
- Service tests often define their own response dicts inline (not from `sample_data.py`)

```python
# Service layer code style
params = {"mode": "queue", "apikey": self._api_key, "output": "json"}
data = await self._make_request(params=params)
return {"total": data.get("noofslots", 0), "items": data.get("slots", [])}
```

### Testing Implications

- API tests: mock exact URLs with `aioresponses`, assert on raw return values
- Service tests: inject mock clients via class attributes, assert on normalized return shapes
- SABnzbd API uses `mode=config&name=speedlimit&value=<pct>` query params — spaces in values become `+` encoding in mock URLs

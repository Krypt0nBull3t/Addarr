# Test Patterns by Layer

## Table of Contents

- [API Clients](#api-clients)
- [Services](#services)
- [Handlers](#handlers)
- [Integration Tests](#integration-tests)
- [Bot Lifecycle](#bot-lifecycle)
- [Config](#config)
- [Keyboards](#keyboards)
- [Translations](#translations)
- [Shell Scripts](#shell-scripts)

---

## API Clients

All HTTP clients use `aiohttp`, Transmission included. Test with `aioresponses`.

### URL Patterns

| Client | API Version | Base URL |
|-|-|-|
| Radarr | `/api/v3/` | `http://localhost:7878` |
| Sonarr | `/api/v3/` | `http://localhost:8989` |
| Lidarr | `/api/v1/` | `http://localhost:8686` |
| Bazarr | `/api/` (no version) | `http://localhost:6767` |
| SABnzbd | (query params) | `http://localhost:8090` |
| Transmission | `/transmission/rpc` | `http://localhost:9091` |

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
    # Mock the lookup first (add_movie uses the first result of the list)
    aio_mock.get(
        f"{radarr_url}/api/v3/movie/lookup?term=tmdb:123",
        payload=[{"tmdbId": 123, "title": "Test Movie"}]
    )
    # Mock the POST (sent with max_retries=0, so one mock is enough)
    aio_mock.post(
        f"{radarr_url}/api/v3/movie",
        payload={"id": 1, "title": "Test Movie"}
    )
    success, message = await radarr_client.add_movie(123, "/movies", 1)
    assert success is True
    assert message == "Successfully added Test Movie"
```

### Transmission (async, aiohttp)

`TransmissionClient` does not inherit `BaseApiClient`; it opens an `aiohttp.ClientSession` per request, which `aioresponses` intercepts. Use the `transmission_client` fixture (`tests/test_api/conftest.py`):

```python
RPC_URL = "http://localhost:9091/transmission/rpc"

async def test_make_request_success(aio_mock, transmission_client):
    expected = {"result": "success", "arguments": {"version": "4.0.0"}}
    aio_mock.post(RPC_URL, payload=expected, status=200)

    result = await transmission_client._make_request("session-get")
    assert result == expected
```

### Session ID Negotiation (Transmission)

Transmission returns 409 with an `X-Transmission-Session-Id` header; the client stores the id and retries once:

```python
async def test_session_id_negotiation(aio_mock, transmission_client):
    aio_mock.post(RPC_URL, status=409, headers={"X-Transmission-Session-Id": "abc123"})
    aio_mock.post(RPC_URL, payload={"result": "success"}, status=200)

    result = await transmission_client._make_request("session-get")
    assert result == {"result": "success"}
    assert transmission_client._session_id == "abc123"
```

A second 409 raises `aiohttp.ClientError("Session ID negotiation failed after retry")`.

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

`check_service_health(url, api_key, service_type)` opens its own `aiohttp.ClientSession`, so mock it with `aioresponses`:

```python
async def test_check_service_health():
    from aioresponses import aioresponses
    from src.services.health import HealthService
    service = HealthService()

    with aioresponses() as m:
        m.get("http://localhost:7878/api/v3/system/status", payload={"version": "5.0"})
        online, msg = await service.check_service_health(
            "http://localhost:7878", "test-key", "radarr"
        )
    assert online is True
    assert msg == "Online (v5.0)"
```

### TranslationService Pattern

Mock `_load_translations` (autouse fixture already does this), then set `_translations` directly:

```python
def test_get_text():
    from src.services.translation import TranslationService
    service = TranslationService()
    TranslationService._translations = {
        "en-us": {"greeting": "Hello %{name}"},
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
    with patch("src.bot.handlers.media.handler.MediaService", return_value=mock_media_service):
        with patch("src.bot.handlers.media.handler.TranslationService", return_value=mock_translation_service):
            from src.bot.handlers.media import MediaHandler
            from src.bot.handlers.auth import AuthHandler
            AuthHandler._authenticated_users = {12345}  # pass @require_auth
            handler = MediaHandler()
            handler.media_service = mock_media_service
            handler.translation = mock_translation_service

    update = make_update(text="/movie")
    context = make_context()
    result = await handler.handle_movie(update, context)
    assert context.user_data["search_type"] == "movie"
```

The `<name>_handler` fixtures in `tests/test_handlers/conftest.py` do this setup for you; prefer them. `media_handler` exposes the mocks as `media_handler._mock_service` and `media_handler._mock_ts`.

### Text Message vs Callback Query

```python
# Text message update
update = make_update(text="search term")

# Callback query update
update = make_update(callback_data="select_0")
```

### State Transitions

```python
from src.bot.handlers.media.dispatch import SELECTING

async def test_search_returns_selecting(media_handler, make_update, make_context):
    media_handler._mock_service.search_movies.return_value = [{"title": "Movie"}]
    update = make_update(text="Movie")
    context = make_context(user_data={"search_type": "movie"})
    with patch("src.bot.handlers.media.handler.show_result", new_callable=AsyncMock) as mock_show:
        result = await media_handler.handle_search(update, context)
    assert result == SELECTING
    mock_show.assert_awaited_once()
    assert context.user_data["current_index"] == 0
```

### Testing @require_auth

```python
async def test_require_auth_blocks_unauthenticated(media_handler, make_update, make_context):
    from src.bot.handlers.auth import AuthHandler
    AuthHandler._authenticated_users = set()  # Empty

    update = make_update(text="/movie")
    context = make_context()

    # handle_movie is decorated with @require_auth: it replies with the auth message
    result = await media_handler.handle_movie(update, context)
    assert result is None
    assert "search_type" not in context.user_data
    update.effective_message.reply_text.assert_called()
```

### Testing get_handler()

```python
def test_get_handler_returns_list():
    from src.bot.handlers.media import MediaHandler
    with patch("src.bot.handlers.media.handler.MediaService"), \
         patch("src.bot.handlers.media.handler.TranslationService"):
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
|-|-|
| `conftest.py` | `BotHarness` class, update factories, `harness`, `downloads_harness` and `bazarr_harness` fixtures |
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

@pytest.fixture
async def bazarr_harness():
    """Like harness but with the Bazarr handler enabled."""
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
- **A `conversation_timeout` needs a running job queue.** The harness setup in `tests/integration/conftest.py` awaits `app.job_queue.start()` (a coroutine in PTB 22.8) and `stop(wait=False)`, because the harness never calls `Application.start()`. Without it PTB only warns, and the suite turns the warning into an error.
- **Tap from another message** with `harness.tap_button("quality_1", message_id=999)` to test a stale keyboard. The default is message 100. In a unit test, reuse one update across calls when the handler compares `query.message.message_id`: a new update has a new message id.

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

## Bot Lifecycle

### Shutdown that `asyncio.run` must not cancel

A signal handler runs `AddarrBot.stop()` as a side task, and `asyncio.run` cancels pending tasks when `main()` returns. A test with a mocked `asyncio.run` passes without the fix. Use a sync test around the real one:

```python
def test_sigterm_runs_shutdown_before_exit(self, mock_app, tmp_path):
    real_sleep = asyncio.sleep           # keep it before the patch below
    ...
    with patch("src.main.asyncio.sleep", side_effect=short_tick):
        asyncio.run(main())              # real run: cancels pending tasks on exit
    mock_app.shutdown.assert_awaited_once()
```

Make one shutdown step take real time (`await real_sleep(0.05)`), or the side task finishes before the cancel and the test cannot fail. The full test is `TestMain::test_sigterm_runs_shutdown_before_exit` in `tests/test_main.py`.

---

## Config

### Overriding Config Per-Test

```python
def test_with_custom_config(mock_config):
    mock_config._set("language", "de-de")
    assert mock_config.get("language") == "de-de"
```

### Testing with Disabled Services

A changed `mock_config` only reaches code that reads it, so patch `config` where the module under test imports it (`admin_mode` in `tests/test_handlers/conftest.py` does the same):

```python
def test_radarr_disabled(mock_config):
    mock_config._set("radarr", {**mock_config.get("radarr"), "enable": False})
    with patch("src.services.media.config", mock_config):
        from src.services.media import MediaService
        assert MediaService().radarr is None
```

### Testing the Real Settings Module

`tests/conftest.py` replaces `src.config.settings` with a mock, so a plain import never reaches the real `Config`. A test that copies the code under test cannot fail. Use the `load_settings` fixture (`tests/test_config/conftest.py`): it runs the real `src/config/settings.py` with the file reads patched. It returns a `LoadedSettings` with `config`, `error`, `module`, `written` (text written per path) and `q` (the questionary mocks).

```python
def test_empty_file(load_settings):
    result = load_settings("")  # config.yaml exists but is empty
    assert isinstance(result.error, result.module.ConfigurationError)
```

`valid_config_text` is the example config with a token filled in. `config_text=None` means no config.yaml. `interactive=True` makes questionary prompts run.

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

    with patch("asyncio.sleep", new_callable=AsyncMock):
        success, data, error = await radarr_client._make_request("system/status")
    assert (success, data, error) == (True, {"version": "5.0"}, None)
```

For N retries, register N+1 mocks (1 initial + N retries). Example with 2 retries configured:

```python
async def test_all_retries_exhausted(radarr_client, aio_mock, radarr_url):
    url = f"{radarr_url}/api/v3/system/status"
    # Initial + 2 retries = 3 mocks
    for _ in range(3):
        aio_mock.get(url, exception=aiohttp.ClientError("fail"))

    with patch("asyncio.sleep", new_callable=AsyncMock):
        success, data, error = await radarr_client._make_request("system/status")
    assert (success, data, error) == (False, None, "Connection error: fail")
```

### Patching asyncio.sleep for Backoff

Retry logic uses `asyncio.sleep` for backoff delays. Patch at module level to avoid real delays and verify backoff values:

```python
async def test_retry_backoff(radarr_client, aio_mock, radarr_url):
    url = f"{radarr_url}/api/v3/system/status"
    aio_mock.get(url, exception=aiohttp.ClientError("fail"))
    aio_mock.get(url, payload={"version": "5.0"})

    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        await radarr_client._make_request("system/status")
        mock_sleep.assert_called_once_with(1)  # First backoff = 1s
```

### TimeoutError Handling

`asyncio.TimeoutError` does NOT inherit from `aiohttp.ClientError`; `_make_request` catches both, but never retries a timeout, because a timeout already waited the full timeout. One mock is enough, and `asyncio.sleep` is not awaited:

```python
async def test_timeout_is_not_retried(radarr_client, aio_mock, radarr_url):
    url = f"{radarr_url}/api/v3/system/status"
    aio_mock.get(url, exception=asyncio.TimeoutError())

    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        success, data, error = await radarr_client._make_request("system/status")
    assert (success, data, error) == (False, None, "Connection error: timeout")
    mock_sleep.assert_not_awaited()
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

API clients reuse one `aiohttp.ClientSession` per client until `close()`.

### Client Fixtures

The autouse `cleanup_sessions` fixture in `tests/test_api/conftest.py` closes the `radarr_client`, `sonarr_client`, `lidarr_client` and `bazarr_client` fixtures after each test. Do not add a cleanup fixture of your own.

### Ad-hoc Client Instances

Tests that create their own client instances (bypassing the shared fixture) must close explicitly:

```python
async def test_custom_client():
    from src.api.radarr import RadarrClient
    client = RadarrClient()
    try:
        result = await client.<method>()
        assert result is not None
    finally:
        await client.close()
```

### Why This Matters

`_get_session()` keeps the session open until `close()`. An unclosed session outlives its test, and aiohttp reports `Unclosed client session` when it is garbage-collected.

---

## Shell Scripts

`tests/test_install_scripts.py` tests `scripts/install.sh`, the PowerShell installer, the systemd unit and the README install text. Root-level test file, same style as `tests/test_dockerfile.py`.

- **Never run a whole install script.** It installs software. Read the file text and assert on it, or run one function.
- **Run one function:** extract its text with a regex (`function_text(script, name)`), then run it under `bash -c` in `tmp_path` with `subprocess.run(..., check=True, capture_output=True)` (`run_cleanup()` shows the pattern). Set the variables the function reads (`INSTALL_DIR`, `BACKUP_DIR`) in the script text.
- **Check order with line indexes:** to prove a trap is set before a `mv`, compare the line index of each.
- **`EUID` is read-only in bash:** a test cannot fake root. Have the script read `$(id -u)`, define `id() { echo 0; }` in the test script, and run bash with `env={"PATH": ""}` (through the absolute `shutil.which("bash")`) so a real `sudo` is hidden. `test_sudo_prefix_by_user` shows it.
- **Cover every caller of a shared value:** a value such as `SUDO` that many paths read is set where the script loads, not inside one function. `test_every_package_install_uses_sudo_prefix` scans every executed line, so a path added later cannot skip it.

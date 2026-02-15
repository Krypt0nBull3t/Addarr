# Test Patterns by Layer

## Table of Contents

- [API Clients](#api-clients)
- [Services](#services)
- [Handlers](#handlers)
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

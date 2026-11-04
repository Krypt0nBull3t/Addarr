---
name: addarr-testing
description: Use when writing tests for Addarr, setting up test fixtures, or debugging test failures. Covers pytest patterns for async Telegram bot handlers, aiohttp API clients, and singleton services.
---

# Addarr Testing

Addarr-specific test patterns.

## Quick Start

```bash
pytest                                      # All tests
pytest --tb=short -q                        # Quick summary
pytest --cov=src --cov-report=term-missing  # With coverage
pytest -k "test_name"                       # Specific test by name
pytest tests/test_api/                      # Specific directory
pytest -x                                   # Stop on first failure
```

## Fixture Cheat Sheet

### Root Fixtures (`tests/conftest.py`)

| Fixture | Scope | Description |
|---------|-------|-------------|
| `reset_singletons` | function, autouse | Resets all singleton `_instance` attrs after each test |
| `mock_config` | function | Fresh `MockConfig()` for tests needing config overrides |
| `mock_translation` | function, autouse | Patches `TranslationService._load_translations` |
| `make_user` | function | Factory: `make_user(user_id=12345, username="testuser")` |
| `make_message` | function | Factory: `make_message(text="test", user=None, chat_id=12345)` |
| `make_callback_query` | function | Factory: `make_callback_query(data="test", user=None)` |
| `make_update` | function | Factory: `make_update(text=None, callback_data=None)` |
| `make_context` | function | Factory: `make_context(user_data=None)` |

### API Fixtures (`tests/test_api/conftest.py`)

| Fixture | Description |
|---------|-------------|
| `cleanup_sessions` | autouse: closes the radarr/sonarr/lidarr/bazarr client sessions after each test |
| `aio_mock` | `aioresponses()` context manager for mocking async HTTP |
| `radarr_url` / `sonarr_url` / `lidarr_url` / `bazarr_url` / `transmission_url` | Base URL strings |
| `radarr_client` / `sonarr_client` / `lidarr_client` / `bazarr_client` / `transmission_client` | Real client instances (safe, because the config mock is active) |

### Service Fixtures (`tests/test_services/conftest.py`)

| Fixture | Description |
|---------|-------------|
| `mock_radarr_client` | `AsyncMock` with all RadarrClient methods pre-configured |
| `mock_sonarr_client` | `AsyncMock` with all SonarrClient methods |
| `mock_lidarr_client` | `AsyncMock` with all LidarrClient methods |

### Handler Fixtures (`tests/test_handlers/conftest.py`)

| Fixture | Description |
|---------|-------------|
| `mock_media_service` | `MagicMock` with async methods for all media operations |
| `mock_translation_service` | `MagicMock` where `get_text` and `get_message` return the key |
| `mock_notification_service` | `MagicMock` with async `notify_admin` |
| `admin_mode` | Admin mode on with admin user 1, so the default test user 12345 is no admin |
| `<name>_handler` | A handler with its services patched and user 12345 authenticated, e.g. `media_handler`, `settings_handler`, `transmission_handler` (full list in [references/fixtures.md](references/fixtures.md#handler-fixtures)) |
| `unchanged_edit` | Wires a query so `edit_text` raises Telegram's "Message is not modified" `BadRequest` |

### Integration Fixtures (`tests/integration/conftest.py`)

| Fixture | Description |
|---------|-------------|
| `harness` | `BotHarness` with the full handler chain |
| `downloads_harness` | `harness` with Transmission and SABnzbd enabled |
| `bazarr_harness` | `harness` with Bazarr enabled |
| `aio_mock` | `aioresponses()` context manager |

### Sample Data (`tests/fixtures/`)

`sample_data.py` constants include: `RADARR_SEARCH_RESULTS`, `RADARR_MOVIE_DETAIL`, `RADARR_ROOT_FOLDERS`, `RADARR_QUALITY_PROFILES`, `SONARR_SEARCH_RESULTS`, `SONARR_SERIES_DETAIL`, `LIDARR_SEARCH_RESULTS`, `LIDARR_METADATA_PROFILES`, `TRANSMISSION_SESSION`, `SABNZBD_QUEUE`. `bazarr_data.py` has `BAZARR_SYSTEM_STATUS`, `BAZARR_MOVIES`, `BAZARR_MOVIES_WANTED`, `BAZARR_EPISODES_WANTED`. Full list in [references/fixtures.md](references/fixtures.md#sample-data).

## Layer Quick Reference

### API Clients
Mock HTTP with `aioresponses`, match exact URLs with API version path. See [references/patterns.md#api-clients](references/patterns.md#api-clients).

### Services
Inject mock clients into singletons via class attributes. See [references/patterns.md#services](references/patterns.md#services).

### Handlers
Use `make_update()` factories, patch service constructors before handler init. See [references/patterns.md#handlers](references/patterns.md#handlers).

### Integration Tests
End-to-end flow tests using `BotHarness` with real PTB handler chains. See [references/patterns.md#integration-tests](references/patterns.md#integration-tests).

### Config
Override values with `mock_config._set()`, then patch `config` where the module under test imports it: `patch("src.<module>.config", mock_config)`. See [references/patterns.md#config](references/patterns.md#config).

## Common Mistakes

1. Forgetting singleton reset — tests randomly fail based on execution order. See [references/anti-patterns.md#singleton-leakage](references/anti-patterns.md#singleton-leakage).
2. Testing translated text literally — mock returns keys, not translated strings. See [references/anti-patterns.md#translation-testing](references/anti-patterns.md#translation-testing).
3. Creating real `aiohttp.ClientSession` in tests — use `aioresponses` instead. See [references/anti-patterns.md#real-sessions](references/anti-patterns.md#real-sessions).
4. Patching services at source module instead of import site — patch where the handler imports it. See [references/anti-patterns.md#patching-at-wrong-import-path](references/anti-patterns.md#patching-at-wrong-import-path).
5. Leaving an ad-hoc client's session open — the autouse `cleanup_sessions` fixture closes only the client fixtures; close a client you create yourself in `finally`. See [references/anti-patterns.md#not-cleaning-up-sessions-between-tests](references/anti-patterns.md#not-cleaning-up-sessions-between-tests).
6. Registering too few mocks for retry scenarios — need N+1 mocks for N retries. See [references/anti-patterns.md#insufficient-retry-mocks](references/anti-patterns.md#insufficient-retry-mocks).
7. Mocking `sys.exit` without stopping execution — use `pytest.raises(SystemExit)`. See [references/anti-patterns.md#mocking-sysexit-without-stopping-execution](references/anti-patterns.md#mocking-sysexit-without-stopping-execution).

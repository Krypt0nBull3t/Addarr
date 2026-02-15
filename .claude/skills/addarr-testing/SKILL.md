---
name: addarr-testing
description: Use when writing tests for Addarr, setting up test fixtures, or debugging test failures. Covers pytest patterns for async Telegram bot handlers, aiohttp API clients, and singleton services.
---

# Addarr Testing

Addarr-specific test patterns. For generic pytest knowledge (TDD cycle, fixtures, parametrization, mocking, async), see @superpowers:test-driven-development and @python-testing-pro.

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
| `aio_mock` | `aioresponses()` context manager for mocking async HTTP |
| `radarr_url` / `sonarr_url` / `lidarr_url` / `sabnzbd_url` | Base URL strings |
| `radarr_client` / `sonarr_client` / `lidarr_client` / `sabnzbd_client` | Real client instances (safe — config mock is active) |

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
| `mock_translation_service` | `MagicMock` where `get_text` returns the key |
| `mock_notification_service` | `MagicMock` with async notify methods |

### Sample Data (`tests/fixtures/sample_data.py`)

Constants: `RADARR_SEARCH_RESULTS`, `RADARR_MOVIE_DETAIL`, `RADARR_ROOT_FOLDERS`, `RADARR_QUALITY_PROFILES`, `RADARR_SYSTEM_STATUS`, `SONARR_SEARCH_RESULTS`, `SONARR_SERIES_DETAIL`, `LIDARR_SEARCH_RESULTS`, `LIDARR_METADATA_PROFILES`, `TRANSMISSION_SESSION`, `SABNZBD_QUEUE`

## Layer Quick Reference

### API Clients
Mock HTTP with `aioresponses`, match exact URLs with API version path. See [references/patterns.md#api-clients](references/patterns.md#api-clients).

### Services
Inject mock clients into singletons via class attributes. See [references/patterns.md#services](references/patterns.md#services).

### Handlers
Use `make_update()` factories, patch service constructors before handler init. See [references/patterns.md#handlers](references/patterns.md#handlers).

### Config
Override values via `MockConfig._set()`. See [references/patterns.md#config](references/patterns.md#config).

## Common Mistakes

1. Importing `src.*` at module level in test files — triggers real `Config()`. See [references/anti-patterns.md#module-level-imports](references/anti-patterns.md#module-level-imports).
2. Forgetting singleton reset — tests randomly fail based on execution order. See [references/anti-patterns.md#singleton-leakage](references/anti-patterns.md#singleton-leakage).
3. Using `aioresponses` for Transmission — it uses sync `requests`, not `aiohttp`. See [references/anti-patterns.md#transmission-mocking](references/anti-patterns.md#transmission-mocking).
4. Testing translated text literally — mock returns keys, not translated strings. See [references/anti-patterns.md#translation-testing](references/anti-patterns.md#translation-testing).
5. Creating real `aiohttp.ClientSession` in tests — use `aioresponses` instead. See [references/anti-patterns.md#real-sessions](references/anti-patterns.md#real-sessions).

# Copilot Instructions for Addarr

## Project Overview

Addarr is a Python 3.11 Telegram bot for managing media collections through Radarr (movies), Sonarr (TV shows), and Lidarr (music). Users search and add media via Telegram with quality profile selection, season picking, and inline keyboard navigation. It also supports Transmission and SABnzbd download client management.

## Tech Stack

- **Language**: Python 3.11
- **Bot Framework**: python-telegram-bot v20+ (async)
- **HTTP**: aiohttp for async API clients, requests for Transmission RPC
- **Config**: YAML (config.yaml validated against config_example.yaml)
- **i18n**: python-i18n with YAML translation files (9 languages)
- **Scheduling**: aiocron
- **Linting**: flake8 (max line length 88, ignoring E203/E501/W503)
- **Testing**: pytest with aioresponses, unittest.mock, factory fixtures

## Architecture

Three-layer design with strict separation:

1. **Handlers** (`src/bot/handlers/`) — Telegram command/callback handlers. Each class exposes `get_handler()` returning `ConversationHandler` or `CommandHandler` instances. Multi-step flows use `ConversationHandler` with states from `src/bot/states.py`.

2. **Services** (`src/services/`) — Business logic singletons (`__new__` override). `MediaService` aggregates API clients. `HealthService` runs periodic checks. `TranslationService` wraps python-i18n.

3. **API Clients** (`src/api/`) — Inherit from `BaseApiClient` (`src/api/base.py`) which provides async `_make_request()`, URL construction, and error parsing. Media clients implement the `search()` abstract method.

## Key Patterns

- **Async throughout**: All I/O uses `async/await`. Handler methods are async. API clients use aiohttp sessions.
- **Singleton services**: Services use `__new__` override for singleton pattern. Tests must reset `_instance = None` between runs.
- **Authentication decorator**: `@require_auth` from `src/bot/handlers/auth.py` guards handler methods.
- **Conversation state machine**: Media flow: `SEARCHING -> SELECTING -> QUALITY_SELECT -> SEASON_SELECT -> END`.
- **Centralized keyboards**: All inline keyboard layouts in `src/bot/keyboards.py`.
- **Global config singleton**: `src/config/settings.py` exports module-level `config` loaded from YAML.

## Project Layout

```
src/
  api/           # API clients (base.py, radarr.py, sonarr.py, lidarr.py, sabnzbd.py, transmission.py)
  bot/
    handlers/    # Telegram handlers (auth, media, start, help, delete, transmission, sabnzbd, system)
    keyboards.py # Inline keyboard builders
    states.py    # ConversationHandler state constants
  config/
    settings.py  # Config singleton, YAML loading/validation
  models/        # Data models
  services/      # Business logic singletons (media, health, translation, scheduler)
  utils/         # Error handling, pre-run checks, helpers
  definitions.py # Path constants
  main.py        # Bot initialization and startup
tests/           # Mirrors src/ structure
translations/    # addarr.<locale>.yml files
helm/            # Kubernetes Helm chart
```

## Build and Test Commands

```bash
pip install -r requirements.txt     # Install dependencies
python run.py                       # Run the bot
python run.py --check               # Validate config and connectivity
flake8 .                            # Lint
pytest                              # Run all tests
pytest --cov=src --cov-report=term-missing  # Tests with coverage
pytest -x                           # Stop on first failure
```

## Code Style

- Max line length: 88 characters
- Follow flake8 rules (E203, E501, W503 ignored)
- Use `async/await` for all I/O operations
- Handler methods must be async and accept `(update, context)` parameters
- API client methods must be async and use `self._make_request()`
- Services follow singleton pattern with `__new__` override
- Translations accessed via `TranslationService().get_text(key, default=...)`

## Testing Conventions

- Tests mirror `src/` structure in `tests/`
- Config is mocked via `MockConfig` injected into `sys.modules` (see `tests/conftest.py`)
- Use `aioresponses` for mocking async HTTP (Radarr, Sonarr, Lidarr, SABnzbd)
- Use `unittest.mock.patch("requests.post")` for Transmission (sync requests)
- Factory fixtures: `make_user`, `make_message`, `make_update`, `make_context`
- Singleton `_instance` is auto-reset between tests via autouse fixture

## CI/CD

GitHub Actions runs on PRs to `main`/`development`:
- flake8 lint
- pytest with coverage
- Translation validation (`--validate-i18n`)
- Docker build test
- AI-powered PR review + auto-approve
- CodeQL security scanning

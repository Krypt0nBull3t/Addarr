# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Addarr Refresh is a Telegram bot for managing media collections through Radarr (movies), Sonarr (TV shows), and Lidarr (music). Users search and add media via Telegram with quality profile selection, season picking, and inline keyboard navigation. It also supports Transmission and SABnzbd download client management.

## Commands

```bash
# Run the bot
python run.py

# Interactive setup wizard
python run.py --setup

# Validate config and service connectivity
python run.py --check

# Validate translation files
python run.py --validate-i18n

# Other utilities
python run.py --configure    # Add/modify services
python run.py --backup       # Backup configuration
python run.py --reset        # Reset config from scratch
python run.py --version      # Show version info

# Install dependencies
pip install -r requirements.txt

# Lint
flake8 .
```

## Lint Configuration

Flake8 with max line length 88. Ignored rules: E203, E501, W503 (configured in `.flake8`).

## Architecture

### Layered Design

The codebase follows a three-layer architecture with strict separation:

1. **Handlers** (`src/bot/handlers/`) — Telegram command/callback handlers. Each handler class exposes `get_handler()` returning a list of `ConversationHandler` or `CommandHandler` instances. Multi-step interactions use `ConversationHandler` with states defined in `src/bot/states.py`.

2. **Services** (`src/services/`) — Business logic layer using singleton pattern (`__new__` override). `MediaService` aggregates all API clients. `HealthService` runs periodic health checks. `TranslationService` wraps python-i18n.

3. **API Clients** (`src/api/`) — All inherit from `BaseApiClient` (`src/api/base.py`), which provides async `_make_request()`, URL construction from config, and standard error parsing. Each client (Radarr, Sonarr, Lidarr) implements the `search()` abstract method.

### Key Patterns

- **Async throughout**: All I/O uses `async/await` via `aiohttp` and `python-telegram-bot` v20+.
- **Authentication decorator**: `@require_auth` from `src/bot/handlers/auth.py` guards handler methods. Authenticated user IDs are persisted to `config.yaml`.
- **Conversation state machine**: Media flow progresses through `SEARCHING → SELECTING → QUALITY_SELECT → SEASON_SELECT → END` (states in `src/bot/states.py`).
- **Centralized keyboards**: All inline keyboard layouts live in `src/bot/keyboards.py`.
- **Global config singleton**: `src/config/settings.py` exports a module-level `config` instance loaded from `config.yaml` and validated against `config_example.yaml`.

### Configuration

All configuration lives in `config.yaml` (YAML). `config_example.yaml` serves as both template and validation reference. Path constants are defined in `src/definitions.py`. On startup, `Config.__init__` validates against the example and interactively prompts for missing keys.

### Internationalization

Translation files in `translations/addarr.<locale>.yml` (9 languages). Access via `TranslationService().get_text(key, default=...)`. Template for new languages: `translations/addarr.template.yml`.

### Entry Point Flow

`run.py` → pre-run checks (`src/utils/prerun_checker.py`) → init utilities → `src/main.py:run_bot()` → `AddarrBot.initialize()` (config validation, health checks, handler registration) → `AddarrBot.start()` (polling loop + health check task).

### Handler Registration Order

Handlers are registered in `AddarrBot._add_handlers()` in this order: Start, Auth, Media, Transmission (if enabled), SABnzbd (if enabled), Help, Status. Order matters because `python-telegram-bot` matches the first matching handler.

## CI/CD

GitHub Actions workflows in `.github/workflows/`:

- **`ci.yml`** — Runs on PRs to `main`/`development`. Jobs: flake8 lint, translation validation (`--validate-i18n`), Docker build test.
- **`auto-approve.yml`** — Triggered after CI succeeds. Performs AI-powered PR review via Groq (Qwen3-32B) plus rule-based checks (TODOs, print statements, large files, hardcoded secrets, bare excepts). Posts review comment and auto-approves. Requires `GROQ_API_KEY` and `REVIEWER_BOT_TOKEN` secrets.
- **`codeql-analysis.yml`** — CodeQL security scanning on push/PR.
- **`docker-hub-push.yml`** — Publishes Docker image to Docker Hub.

## Helm / Kubernetes

Helm chart in `helm/` for Kubernetes deployment:

```bash
helm install addarr ./helm -f helm/values.yaml
```

Templates include ConfigMap, Deployment, and PersistentVolumeClaim. See `helm/README.md` for configuration details.

## Known Future Work

Imports were cleaned up during a lint pass. If implementing the following, re-add the corresponding imports:

- **Colored handler logging**: `delete.py`, `help.py`, `sabnzbd.py`, `start.py`, `system.py` handlers currently log without color. Other handlers (auth, media) use `from colorama import Fore` for colored log messages. Re-add if adding colored logging to these files.
- **Exception-based service checks**: `src/bot/handlers/transmission.py` checks `is_enabled()` and sends a reply directly. `ServiceNotEnabledError` from `src/utils/error_handler` was removed but may be needed if refactoring to exception-based handling.
- **Scheduler enhancements**: `src/services/scheduler.py` uses `aiocron` for scheduling. `asyncio`, `datetime`/`timedelta`, and `typing.Optional`/`Any` were removed but may be needed for time-based scheduling features beyond cron expressions.

## Docker

```bash
docker-compose up -d
# or
docker build -t addarr . && docker run -d -v $(pwd)/config.yaml:/app/config.yaml addarr
```

Base image: `python:3.11.5-alpine3.18`. Uses host networking. Persistent files to mount: `config.yaml`, `logs/`, `chatid.txt`, `admin.txt`, `allowlist.txt`. Images are automatically published to Docker Hub via the `docker-hub-push.yml` workflow.

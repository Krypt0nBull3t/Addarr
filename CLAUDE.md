# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Addarr Refresh is a Telegram bot for managing media collections through Radarr (movies), Sonarr (TV shows), and Lidarr (music). Users search and add media via Telegram with quality profile selection, season picking, and inline keyboard navigation. It also supports Transmission and SABnzbd download client management.

## Shell Conventions

These patterns avoid triggering permission prompts in Claude Code:

- **Avoid `cd && command` compound patterns entirely** — this applies to ALL commands, not just git. Use `git -C <path>` for git, and absolute paths or tool `path` parameters for everything else
- **Avoid `$()` and backtick command substitution** — prefer writing content to a temp file first, then referencing it (e.g., `gh issue create --body-file /tmp/body.md` instead of inline `--body`)
- **Avoid shell glob expansion in paths** (e.g., `translations/addarr.*.yml`) — prefer listing files explicitly
- **Avoid backslash escapes in commands** — prefer quotes over escaping spaces/special characters
- **Never use `find`, `grep`, or `rg` via Bash** — use the dedicated Glob and Grep tools instead (this includes subagents/Explore agents)
- **Use `PYTHONIOENCODING=utf-8`** when running `python run.py --validate-i18n` (Windows emoji encoding)

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

# Run tests
pytest                                      # All tests
pytest --tb=short -q                        # Quick summary
pytest --cov=src --cov-report=term-missing  # With coverage (use dotted module paths for --cov, not file paths)
pytest -k "test_name"                       # Specific test
pytest -x                                   # Stop on first failure

# Run tests by domain (scoped coverage)
python scripts/test_runner.py api --coverage        # API clients
python scripts/test_runner.py services --coverage   # Service layer
python scripts/test_runner.py handlers --coverage   # Bot handlers
python scripts/test_runner.py models --coverage     # Data models
python scripts/test_runner.py bot --coverage        # Bot structure
python scripts/test_runner.py utils --coverage      # Utilities
python scripts/test_runner.py config --coverage     # Configuration
python scripts/test_runner.py all --coverage        # Full suite
# Extra pytest args pass through: python scripts/test_runner.py api -v -x
```

## Testing

Tests live in `tests/` mirroring `src/` structure. Key patterns:

- **Config mock**: `tests/conftest.py` injects a `MockConfig` into `sys.modules["src.config.settings"]` before any `src` imports, bypassing the real `Config()` which reads from disk at import time.
- **Singleton reset**: An `autouse=True` fixture resets `_instance = None` on all singleton services between tests.
- **Telegram factories**: Factory fixtures (`make_user`, `make_message`, `make_update`, `make_context`) return callables for per-test customization.
- **API mocking**: `aioresponses` for async HTTP clients (Radarr, Sonarr, Lidarr, SABnzbd). `unittest.mock.patch("requests.post")` for Transmission (uses sync `requests`).
- **Translation mock**: `autouse=True` fixture patches `TranslationService._load_translations` so tests don't need YAML files.
- **Config patching gotcha**: Module-level `from src.config.settings import config` binds at import time. To override in tests, patch at the import site: `patch("src.the_module.config", mock_config)` — replacing `sys.modules` won't affect modules that already imported `config`.

### Architecture Tests

Automated architecture tests in `tests/test_architecture/` enforce conventions at CI time:

- **Layer boundaries** (`test_layer_boundaries.py`): PyTestArch import-direction rules. Services must not import handlers, API clients must not import handlers or services, utils/config must not import handlers or services, handlers must not import API clients directly.
- **Structural conventions** (`test_conventions.py`): AST-based checks. All `*Handler` classes must have `get_handler()`, all service singletons must have `__new__()`, all `BaseApiClient` subclasses must have `search()`, no `config["key"]` bracket access in business logic (use `config.get()` instead).

**When adding new services:** Update `SINGLETON_CLASSES` set in `tests/test_architecture/test_conventions.py`.

**When adding new API clients inheriting `BaseApiClient`:** They must implement `search()` or the convention test will fail.

**Config access rule:** `config["key"]` bracket access is banned in `src/` business logic (enforced by test). Use `config.get("key", default)` instead. Excluded from this rule: `src/setup/` (interactive config building), `src/api/base.py` (`self.config` service dict), `src/config/settings.py` (`__getitem__` definition).

**PyTestArch on Windows:** The conftest monkey-patches PyTestArch's file parser to use UTF-8 encoding (upstream defaults to cp1252 on Windows, fails on emoji in source files).

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

Translation files in `translations/addarr.<locale>.yml` (9 languages). Access via `TranslationService().get_text(key, default=...)`. Template for new languages: `translations/addarr.template.yml`. **Important:** `get_text()` does a single-level `.get(key)` lookup — nested keys like `Commands.start` don't resolve. Always use flat top-level keys (e.g., `CommandStart`).

### Entry Point Flow

`run.py` → pre-run checks (`src/utils/prerun_checker.py`) → init utilities → `src/main.py:run_bot()` → `AddarrBot.initialize()` (config validation, health checks, handler registration) → `AddarrBot.start()` (polling loop + health check task).

### Handler Registration Order

Handlers are registered in `AddarrBot._add_handlers()` in this order: Start, Auth, Media, Transmission (if enabled), SABnzbd (if enabled), Help, Status. Order matters because `python-telegram-bot` matches the first matching handler.

## Git Branching

- **`main`** is the production branch. Never target `main` with a feature/fix PR.
- **`development`** is the integration branch. All feature and fix PRs target `development`.
- The only PRs that target `main` are merge PRs from `development` → `main` (releases).
- **Merge strategy**: Use `--merge` (regular merge commit, same as GitHub's "Merge pull request" button). Do not squash or rebase.

## CI/CD

GitHub Actions workflows in `.github/workflows/`:

- **`ci.yml`** — Runs on PRs to `main`/`development`. Jobs: flake8 lint, pytest with coverage, translation validation (`--validate-i18n`), Docker build test.
- **`auto-approve.yml`** — Triggered after CI succeeds. Performs AI-powered PR review via Groq (GPT-OSS-120B) plus rule-based checks (TODOs, print statements, large files, hardcoded secrets, bare excepts). Posts review comment and auto-approves. Requires `GROQ_API_KEY` and `REVIEWER_BOT_TOKEN` secrets.
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

## Planning & Task Conventions

All issue work follows a two-file workflow stored in `docs/issues/issue-<N>/`:

1. **`plan.md`** — Written first. Contains context, target structure, design decisions, phased approach, and verification steps. Always write plans here, never to the repo root or `docs/plans/`.
2. **`TASKS.md`** — Converted from plan.md using `/task-writer`. Contains sized, TDD-ordered tasks with full context blocks. This is the executable work breakdown.

**Workflow:**
1. Write plan → `docs/issues/issue-<N>/plan.md`
2. Convert plan → `docs/issues/issue-<N>/TASKS.md` (via `/task-writer`)
3. Implement tasks in order, checking off as completed

**Existing examples:** issues 12, 17, 20, 21, 22, 67, 76, 77, 78, 79, 127.

## Docker

```bash
docker-compose up -d
# or
docker build -t addarr . && docker run -d -v $(pwd)/config.yaml:/app/config.yaml addarr
```

Base image: `python:3.11.5-alpine3.18`. Uses host networking. Persistent files to mount: `config.yaml`, `logs/`, `chatid.txt`, `admin.txt`, `allowlist.txt`. Images are automatically published to Docker Hub via the `docker-hub-push.yml` workflow.

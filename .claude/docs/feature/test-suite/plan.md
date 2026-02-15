# Plan: Test Suite, Testing Skill, and TDD Integration for Addarr

## Context

Addarr has no test infrastructure. The user wants:
1. A **comprehensive test suite** covering all layers (API clients, services, handlers, utils, config, models)
2. A **standalone testing skill** (`.claude/skills/addarr-testing/`) with Addarr-specific testing patterns
3. **TDD integration** into the existing `/addarr` workflow

## Part 1: Test Suite Infrastructure

### Dependencies (`requirements-test.txt`)

```
pytest>=7.4.0
pytest-asyncio>=0.23.0
pytest-cov>=4.1.0
pytest-mock>=3.12.0
aioresponses>=0.7.6
freezegun>=1.3.0
```

### pytest config (`pytest.ini`)

```ini
[pytest]
testpaths = tests
asyncio_mode = auto
markers =
    slow: marks tests as slow
    integration: marks tests that hit real services
```

### Directory structure

```
tests/
├── conftest.py                    # Root: singleton reset, mock config, Telegram mock factories
├── fixtures/
│   ├── __init__.py
│   ├── sample_data.py             # Radarr/Sonarr/Lidarr/Transmission/SABnzbd response data
│   └── config_fixtures.py         # Mock config dictionaries
├── test_models/
│   ├── __init__.py
│   ├── test_media.py              # Movie, Series, Artist, QualityProfile, RootFolder, Tag, SearchResult
│   └── test_notification.py       # NotificationType enum, Notification dataclass
├── test_api/
│   ├── __init__.py
│   ├── conftest.py                # aioresponses fixture, base URL fixtures
│   ├── test_base.py               # BaseApiClient._make_request, URL construction, error parsing
│   ├── test_radarr.py             # search, get_movie, add_movie, get_root_folders, get_quality_profiles, check_status
│   ├── test_sonarr.py             # search, get_series, add_series (with seasons), check_status
│   ├── test_lidarr.py             # search, get_artist, add_artist, metadata profiles, check_status (uses /api/v1/)
│   ├── test_transmission_api.py   # RPC calls, session ID negotiation (uses requests, NOT aiohttp)
│   └── test_sabnzbd_api.py        # check_status, queue operations
├── test_services/
│   ├── __init__.py
│   ├── conftest.py                # Mock API client fixtures
│   ├── test_media_service.py      # Singleton, search/add for all 3 media types, status checks
│   ├── test_health_service.py     # Health checks, monitoring start/stop, status reporting
│   ├── test_translation_service.py # Singleton, get_text, fallback language, format params
│   ├── test_transmission_service.py # is_enabled, lazy client init, alt speed, status
│   ├── test_sabnzbd_service.py    # Queue status, add_nzb, error handling
│   ├── test_notification_service.py # set_bot, notify_admin, notify_user
│   └── test_scheduler.py          # add/remove jobs, start/stop, error handling
├── test_handlers/
│   ├── __init__.py
│   ├── conftest.py                # Handler factory fixtures with mocked services
│   ├── test_auth_handler.py       # require_auth decorator, password flow, is_authenticated
│   ├── test_media_handler.py      # Full conversation: SEARCHING->SELECTING->QUALITY_SELECT->SEASON_SELECT->END
│   ├── test_start_handler.py      # Menu display, menu selection dispatch
│   ├── test_help_handler.py       # Help text, back button
│   ├── test_delete_handler.py     # Type selection, item listing, confirmation, delete
│   ├── test_transmission_handler.py # Status display, alt speed toggle
│   ├── test_sabnzbd_handler.py    # Speed keyboard, speed selection
│   ├── test_status_handler.py     # Status display
│   └── test_system_handler.py     # System status, action dispatch
├── test_bot/
│   ├── __init__.py
│   ├── test_keyboards.py          # All keyboard builders: main menu, system, settings, yes/no, confirmation
│   └── test_states.py             # State constants are unique integers, END value
├── test_config/
│   ├── __init__.py
│   └── test_settings.py           # Load, validate, get/get with default, missing keys, language validation
└── test_utils/
    ├── __init__.py
    ├── test_validate_translations.py # YAML loading, key extraction, missing/extra keys, placeholders, emoji
    ├── test_chat.py               # get_chat_name with/without title
    ├── test_helpers.py            # format_bytes, is_admin, is_allowed, save_chat_id
    ├── test_error_handler.py      # Custom exceptions, telegram error routing, send_error_message fallback
    ├── test_validation.py         # Required/type/range validators, validate_data
    └── test_backup.py             # create/restore/list backups
```

**Estimated: ~346 test functions, targeting 85%+ line coverage.**

### Root conftest.py -- critical fixtures

1. **Singleton reset** (`autouse=True`): Reset `_instance = None` on MediaService, HealthService, TranslationService, NotificationService before/after every test
2. **Mock config** (`autouse=True`): Patch `src.config.settings.config` (and every module that imports it) with a dict-backed mock matching `config_example.yaml` structure. Must be patched at every import site since Python creates separate name bindings.
3. **Telegram mock factories**: `make_user()`, `make_message()`, `make_callback_query()`, `make_update()`, `make_context()` -- all as factory fixtures returning callables for per-test customization
4. **Translation mock**: Returns key as text (identity function)

### Key technical challenges

| Challenge | Solution |
|---|---|
| `config = Config()` executes at import time | Patch `Config.__init__` at module level in conftest.py before any src imports |
| Singletons leak state between tests | `autouse=True` fixture resets all `_instance` attrs |
| Config imported at many sites (`from settings import config`) | Patch each import site individually |
| Transmission API uses `requests` not `aiohttp` | Mock `requests.post` directly, not aioresponses |
| Handler `__init__` creates services | Handler conftest patches service constructors before instantiation |

### CI integration

Add `pytest` to the CI pipeline in `.github/workflows/ci.yml`:

```yaml
  test:
    name: Test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-python@v6
        with:
          python-version: "3.11"
      - run: pip install -r requirements.txt -r requirements-test.txt
      - run: pytest --cov=src --cov-report=term-missing
```

Update preflight skill to include `pytest` as a check.

---

## Part 2: Testing Skill

Create a standalone skill at `.claude/skills/addarr-testing/` following best practices from Anthropic's skill authoring guide and the superpowers writing-skills skill.

### Design principles (from research)

- **Hub-and-spoke**: SKILL.md is the hub (under 500 lines), reference docs are spokes loaded on demand
- **Progressive disclosure**: Only load detailed patterns when actually writing tests for that layer
- **CSO (Claude Search Optimization)**: Description uses "Use when..." triggers, NOT workflow summary
- **TOC in longer references**: Each reference file >100 lines gets a table of contents for grep-ability
- **Concise**: Only include what Claude doesn't already know (no explaining what pytest is)
- **One level deep**: All references linked directly from SKILL.md, no nested references
- **Concrete examples**: Real code from the Addarr codebase, not generic templates
- **No generic pytest content**: The python-testing-pro skill already covers TDD cycle, fixtures, parametrization, mocking, async testing, coverage, etc. Our skill should reference it for generic patterns and ONLY document Addarr-specific patterns (singleton reset, config patching, Telegram mocks, aioresponses patterns for our API clients)

### Structure

```
.claude/skills/addarr-testing/
├── SKILL.md                       # Hub: quick reference, fixture cheat sheet, links to spokes
└── references/
    ├── patterns.md                # Addarr-specific test patterns by layer (with TOC)
    ├── fixtures.md                # Full fixture documentation (with TOC)
    └── anti-patterns.md           # Common mistakes specific to this codebase
```

### SKILL.md (~200 lines, hub role)

Frontmatter:
```yaml
---
name: addarr-testing
description: Use when writing tests for Addarr, setting up test fixtures, or debugging test failures. Covers pytest patterns for async Telegram bot handlers, aiohttp API clients, and singleton services.
---
```

Body sections:
- **Quick start**: `pytest`, `pytest --cov=src`, `pytest -k "test_name"`, `pytest tests/test_api/`
- **Fixture cheat sheet**: Table of all fixtures with name, scope, and one-line description
- **Layer quick reference**: For each layer (API, Service, Handler, Utils), 2-3 line summary + link to `references/patterns.md#section`
- **Common mistakes quick ref**: Top 5 pitfalls as one-liners + link to `references/anti-patterns.md`
- **Cross-references**: superpowers:test-driven-development for TDD cycle, python-testing-pro for generic pytest patterns (fixtures, parametrization, mocking, async). This skill ONLY covers Addarr-specific patterns.

### references/patterns.md (~300 lines, with TOC)

TOC at top, then one section per layer with a concrete Addarr example:
- **API clients**: aioresponses + base URL fixtures, exact URL matching, error simulation
- **Services**: Injecting mock clients into singletons, testing async methods
- **Handlers**: `make_update(callback_data="...")` vs `make_update(text="...")`, state transitions, `@require_auth`
- **Config**: Overriding config values per-test
- **Keyboards**: Asserting on InlineKeyboardMarkup structure
- **Translations**: Identity-function mock pattern

### references/fixtures.md (~200 lines, with TOC)

Full documentation of every fixture across all conftest.py files:
- Root fixtures (singleton reset, mock config, Telegram factories)
- API fixtures (aioresponses, base URLs)
- Service fixtures (mock clients)
- Handler fixtures (pre-built handlers with mocked deps)
- Sample data (what's in `fixtures/sample_data.py`)

### references/anti-patterns.md (~100 lines)

Addarr-specific pitfalls with "why" and "instead" for each:
- Don't import source modules at module level in test files (triggers config load)
- Don't forget to patch config at EVERY import site (Python creates separate name bindings)
- Don't create real `aiohttp.ClientSession` in tests
- Don't skip singleton reset (tests will randomly fail based on execution order)
- Don't use `requests_mock` for Transmission (uses raw `requests`, mock `requests.post` directly)
- Don't test translation text literally (mock returns keys, not translated text)

---

## Part 3: TDD Integration into `/addarr` Workflow

### Update SKILL.md

Add a note that TDD is the default development approach. Reference the superpowers TDD skill for the red-green-refactor cycle and the addarr-testing skill for project-specific patterns.

### Update references/new-task.md

In step 4 (Plan), add: "Include test file locations and what tests to write for each implementation step."

In step 5 (Execute), change to TDD cycle:
1. Write failing test (RED) -- reference addarr-testing skill for patterns
2. Verify it fails for the right reason
3. Write minimal implementation (GREEN)
4. Verify test passes + no regressions (`pytest`)
5. Refactor if needed
6. Repeat for next task

### Update references/preflight.md

Add pytest as check #1 (before flake8):

```bash
pytest --tb=short -q
```

### Update references/create-pr.md

Add test verification before PR creation: "All tests must pass. Run `pytest --cov=src --cov-report=term-missing` and verify no regressions."

---

## Implementation Sequence

Skills and infrastructure come first so they can be referenced while writing tests.

| Step | What | Files |
|---|---|---|
| 1 | Create the addarr-testing skill (`SKILL.md` + 3 reference docs) | 4 new files |
| 2 | Update addarr-workflow skill with TDD integration (SKILL.md, new-task.md, preflight.md, create-pr.md) | 4 existing files |
| 3 | Create `requirements-test.txt` and `pytest.ini` | 2 new files |
| 4 | Create `tests/conftest.py` with all root fixtures | 1 new file |
| 5 | Create `tests/fixtures/sample_data.py` and `config_fixtures.py` | 2 new files |
| 6 | Create model tests (`test_media.py`, `test_notification.py`) | 2 new files -- validates harness works |
| 7 | Create `test_bot/test_states.py` | 1 new file -- trivial, confirms pytest runs |
| 8 | Create util tests (`test_chat.py`, `test_helpers.py`, `test_validation.py`, `test_error_handler.py`, `test_backup.py`) | 5 new files |
| 9 | Create `test_api/conftest.py` + `test_radarr.py` | 2 new files -- establishes async/aiohttp pattern |
| 10 | Create remaining API tests (`test_sonarr.py`, `test_lidarr.py`, `test_sabnzbd_api.py`, `test_transmission_api.py`, `test_base.py`) | 5 new files |
| 11 | Create `test_services/conftest.py` + all service tests | 8 new files |
| 12 | Create `test_handlers/conftest.py` + all handler tests | 10 new files |
| 13 | Create `test_bot/test_keyboards.py` | 1 new file |
| 14 | Create `test_config/test_settings.py` | 1 new file |
| 15 | Create `test_utils/test_validate_translations.py` | 1 new file |
| 16 | Add test job to `.github/workflows/ci.yml` | 1 existing file |
| 17 | Update `CLAUDE.md` with test commands and patterns | 1 existing file |

**Total: ~45 new files, 6 modified files**

## Verification

1. `pip install -r requirements-test.txt` -- dependencies install
2. `pytest --tb=short -q` -- all tests pass
3. `pytest --cov=src --cov-report=term-missing` -- coverage >= 85%
4. `flake8 tests/` -- test files pass linting
5. Invoke `/addarr check` -- pytest now included in preflight
6. Invoke addarr-testing skill -- patterns render correctly

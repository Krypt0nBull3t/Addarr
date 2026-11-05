# Architecture Tests (PyTestArch + AST-Based Structural Checks) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add automated architecture tests that enforce layer boundaries and structural conventions, catching violations in CI before they reach code review.

**Architecture:** Two complementary approaches in a single test directory: PyTestArch for import-level layer dependency rules (using its fluent `Rule` and `LayerRule` APIs), and stdlib `ast`-based pytest tests for structural pattern verification (method existence, singleton pattern, config access). All tests run as part of the normal `pytest` suite.

**Tech Stack:** `pytestarch` (new dependency in `requirements-test.txt`), stdlib `ast` module, `pytest`

---

## Context

### Codebase Layers

| Layer | Module Root | Contents |
|-------|------------|----------|
| **Handlers** | `src.bot.handlers` | 11 handler classes (auth, start, media, delete, library, preferences, settings, system, help, transmission, sabnzbd) |
| **Services** | `src.services` | 8 service/scheduler classes (media, health, translation, transmission, sabnzbd, preferences, notification, scheduler) |
| **API Clients** | `src.api` | 6 clients: 3 media (radarr, sonarr, lidarr) inherit `BaseApiClient`; 2 download (transmission, sabnzbd) standalone; 1 abstract base |
| **Config** | `src.config` | `Config` singleton in `settings.py` |
| **Utils** | `src.utils` | Logger, backup, chat, config_handler, error_handler, helpers, prerun, splash, validation, validate_translations |
| **Models** | `src.models` | Data models (media, notification) |
| **Bot core** | `src.bot` (excl. handlers) | `commands.py`, `keyboards.py`, `states.py` |

### Pragmatic Design Decisions

These decisions were confirmed during analysis:

1. **`search()` check scoped to `BaseApiClient` subclasses only.** TransmissionClient and SabnzbdClient are download clients that don't inherit `BaseApiClient` and don't implement search — this is intentional, not a gap.

2. **Config bracket access check excludes `src/setup/` and `src/api/base.py`.** Setup code legitimately manipulates config during interactive setup. `base.py` accesses `self.config` (a pre-extracted service dict) with brackets, which is the established pattern for API clients. The check targets module-level `config["..."]` access in business logic code.

3. **Handler cross-imports allowed for `auth.py` decorator and shared state.** The `@require_auth` decorator from `auth.py` and state constants (e.g., `SEARCHING`, `SELECTING`) are shared infrastructure. The layer rule "handlers must not import API clients directly" is the meaningful boundary — handler-to-handler imports within `src.bot.handlers` are acceptable.

### Current Compliance (Verified)

All proposed rules **currently pass** against the codebase:
- No services import handlers
- No API clients import handlers or services
- No utils or config import handlers or services
- No handlers import API clients directly (all go through services)
- All 11 handler classes have `get_handler()`
- All 8 service classes implement `__new__()` (singleton)
- All 3 `BaseApiClient` subclasses implement `search()`

### File Structure

```
tests/
  test_architecture/
    __init__.py
    conftest.py              # evaluable + layered_architecture fixtures
    test_layer_boundaries.py # PyTestArch layer rules
    test_conventions.py      # ast-based structural checks
```

### PyTestArch API Reference

```python
# Evaluable architecture (session-scoped fixture)
from pytestarch import get_evaluable_architecture
evaluable = get_evaluable_architecture(project_root, source_root)

# Module-level rules (for import direction checks)
from pytestarch import Rule
rule = (
    Rule()
    .modules_that()
    .are_sub_modules_of("src.services")
    .should_not()
    .import_modules_that()
    .are_sub_modules_of("src.bot.handlers")
)
rule.assert_applies(evaluable)

# Layer-level rules (for layer boundary checks)
from pytestarch import LayeredArchitecture, LayerRule
arch = (
    LayeredArchitecture()
    .layer("handlers").containing_modules(["src.bot.handlers"])
    .layer("services").containing_modules(["src.services"])
    .layer("api").containing_modules(["src.api"])
)
rule = (
    LayerRule()
    .based_on(arch)
    .layers_that()
    .are_named("api")
    .should_not()
    .access_layers_that()
    .are_named("handlers")
)
rule.assert_applies(evaluable)
```

### Existing Test Infrastructure

- Root `tests/conftest.py` injects `MockConfig` into `sys.modules` before any `src` imports
- `tests/conftest.py` already resets all singletons between tests
- Architecture tests don't need config mocking — they inspect code structure, not runtime behavior
- PyTestArch needs the real source files on disk (not mocked modules), so we point it at the `src/` directory directly

---

## Phase 1: Setup & Layer Boundary Tests (PyTestArch)

### Task 1.1: Add pytestarch dependency

**Files:**
- Modify: `requirements-test.txt`

**What:** Add `pytestarch>=2.0.0` to `requirements-test.txt` and install it.

### Task 1.2: Create test directory and conftest with PyTestArch fixtures

**Files:**
- Create: `tests/test_architecture/__init__.py`
- Create: `tests/test_architecture/conftest.py`

**What:** Set up the test directory and conftest with two session-scoped fixtures:
1. `evaluable` — calls `get_evaluable_architecture()` pointing at the project root and `src/` directory
2. `layered_architecture` — defines the five layers (handlers, services, api, config, utils)

**conftest.py pattern:**
```python
import os
import pytest
from pytestarch import get_evaluable_architecture, LayeredArchitecture

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
SRC_ROOT = os.path.join(PROJECT_ROOT, "src")


@pytest.fixture(scope="session")
def evaluable():
    return get_evaluable_architecture(PROJECT_ROOT, SRC_ROOT)


@pytest.fixture(scope="session")
def layered_architecture():
    return (
        LayeredArchitecture()
        .layer("handlers").containing_modules(["src.bot.handlers"])
        .layer("services").containing_modules(["src.services"])
        .layer("api").containing_modules(["src.api"])
        .layer("config").containing_modules(["src.config"])
        .layer("utils").containing_modules(["src.utils"])
    )
```

### Task 1.3: Write layer boundary tests

**Files:**
- Create: `tests/test_architecture/test_layer_boundaries.py`

**What:** Write one test per layer boundary rule using PyTestArch's `Rule` API. Each test should have a descriptive docstring explaining what it enforces and why.

**Rules to implement (5 tests):**

1. `test_services_do_not_import_handlers` — Services must not depend on the handler layer
2. `test_api_clients_do_not_import_handlers` — API clients must not depend on handlers
3. `test_api_clients_do_not_import_services` — API clients must not depend on services
4. `test_utils_do_not_import_handlers_or_services` — Utils must not depend on handlers or services
5. `test_config_does_not_import_handlers_or_services` — Config must not depend on handlers or services

**Note:** The issue also mentions "handlers must not import API clients directly." This rule uses the `Rule` API (not `LayerRule`) since it's about a specific import direction between two modules, and the handler layer is allowed to import services (which sit between handlers and API).

6. `test_handlers_do_not_import_api_clients_directly` — Handlers should go through services, never import `src.api.*` directly

**Test pattern:**
```python
from pytestarch import Rule

def test_services_do_not_import_handlers(evaluable):
    """Services must not depend on the handler layer.

    The service layer provides business logic consumed by handlers.
    Reverse dependencies would create circular imports and violate
    the handlers -> services -> api layering.
    """
    rule = (
        Rule()
        .modules_that()
        .are_sub_modules_of("src.services")
        .should_not()
        .import_modules_that()
        .are_sub_modules_of("src.bot.handlers")
    )
    rule.assert_applies(evaluable)
```

### Task 1.4: Verify all layer boundary tests pass

**What:** Run `pytest tests/test_architecture/test_layer_boundaries.py -v` and confirm all 6 tests pass against the current codebase. If any fail, investigate whether it's a real violation or a PyTestArch configuration issue (e.g., module path resolution).

---

## Phase 2: Structural Convention Tests (AST-Based)

### Task 2.1: Write handler `get_handler()` convention test

**Files:**
- Create: `tests/test_architecture/test_conventions.py`

**What:** Use `ast` module to parse each Python file in `src/bot/handlers/` (excluding `__init__.py`), find all classes ending in `Handler`, and verify each has a `get_handler` method defined.

**Pattern:**
```python
import ast
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
HANDLERS_DIR = os.path.join(PROJECT_ROOT, "src", "bot", "handlers")
SERVICES_DIR = os.path.join(PROJECT_ROOT, "src", "services")
API_DIR = os.path.join(PROJECT_ROOT, "src", "api")


def _get_python_files(directory):
    """Get all .py files in directory, excluding __init__.py."""
    return [
        os.path.join(directory, f)
        for f in sorted(os.listdir(directory))
        if f.endswith(".py") and f != "__init__.py"
    ]


def _get_classes_in_file(filepath):
    """Parse a file and return all class definitions."""
    with open(filepath, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=filepath)
    return [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]


def _class_has_method(class_node, method_name):
    """Check if a class AST node defines a method with the given name."""
    return any(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == method_name
        for node in class_node.body
    )


def test_all_handlers_have_get_handler():
    """Every *Handler class in src/bot/handlers/ must expose get_handler().

    Handlers register themselves with the bot by returning ConversationHandler
    or CommandHandler instances from get_handler(). Missing this method means
    the handler can't be registered.
    """
    missing = []
    for filepath in _get_python_files(HANDLERS_DIR):
        for cls in _get_classes_in_file(filepath):
            if cls.name.endswith("Handler"):
                if not _class_has_method(cls, "get_handler"):
                    filename = os.path.basename(filepath)
                    missing.append(f"{filename}:{cls.name}")

    assert not missing, (
        f"Handler classes missing get_handler(): {', '.join(missing)}"
    )
```

### Task 2.2: Write service singleton convention test

**Files:**
- Modify: `tests/test_architecture/test_conventions.py`

**What:** Parse each file in `src/services/`, find classes ending in `Service` OR named `JobScheduler`, verify each implements `__new__()`.

**Service classes to check (from codebase):**
- MediaService, HealthService, TranslationService, TransmissionService, SABnzbdService, PreferencesService, NotificationService, JobScheduler

**The test uses a set of known singleton class names** rather than a suffix match, because `JobScheduler` doesn't follow the `*Service` naming convention but is architecturally a singleton service.

```python
SINGLETON_CLASSES = {
    "MediaService", "HealthService", "TranslationService",
    "TransmissionService", "SABnzbdService", "PreferencesService",
    "NotificationService", "JobScheduler",
}


def test_all_services_implement_singleton():
    """Every service class must implement __new__() for singleton pattern.

    Services are singletons to maintain shared state (e.g., API client
    instances, cached translations). Missing __new__() means multiple
    instances could be created, causing state inconsistency.
    """
    missing = []
    for filepath in _get_python_files(SERVICES_DIR):
        for cls in _get_classes_in_file(filepath):
            if cls.name in SINGLETON_CLASSES:
                if not _class_has_method(cls, "__new__"):
                    filename = os.path.basename(filepath)
                    missing.append(f"{filename}:{cls.name}")

    assert not missing, (
        f"Service classes missing __new__() singleton: {', '.join(missing)}"
    )
```

### Task 2.3: Write API client `search()` convention test

**Files:**
- Modify: `tests/test_architecture/test_conventions.py`

**What:** Parse files in `src/api/`, find classes that inherit from `BaseApiClient` (check `ast.ClassDef.bases` for the name `BaseApiClient`), and verify each implements `search()`.

**Scoped to `BaseApiClient` subclasses only** — TransmissionClient and SabnzbdClient don't inherit from it and are intentionally excluded.

```python
def _class_inherits_from(class_node, base_name):
    """Check if a class inherits from a given base class name."""
    for base in class_node.bases:
        if isinstance(base, ast.Name) and base.id == base_name:
            return True
        if isinstance(base, ast.Attribute) and base.attr == base_name:
            return True
    return False


def test_all_api_clients_implement_search():
    """Every BaseApiClient subclass must implement search().

    Media API clients (Radarr, Sonarr, Lidarr) inherit from BaseApiClient
    which declares search() as abstract. This test catches any new client
    that forgets to implement it.

    Download clients (Transmission, SABnzbd) don't inherit BaseApiClient
    and are intentionally excluded.
    """
    missing = []
    for filepath in _get_python_files(API_DIR):
        for cls in _get_classes_in_file(filepath):
            if _class_inherits_from(cls, "BaseApiClient"):
                if not _class_has_method(cls, "search"):
                    filename = os.path.basename(filepath)
                    missing.append(f"{filename}:{cls.name}")

    assert not missing, (
        f"BaseApiClient subclasses missing search(): {', '.join(missing)}"
    )
```

### Task 2.4: Write config bracket access convention test

**Files:**
- Modify: `tests/test_architecture/test_conventions.py`

**What:** Use `ast` to walk all `.py` files under `src/` and find `Subscript` nodes where the value is a `Name` node with id `config` — i.e., `config["anything"]` or `config['anything']`.

**Exclusions:**
- `src/setup/` — interactive setup legitimately uses bracket access to build config
- `src/api/base.py` — accesses `self.config` (pre-extracted service dict), not the global config
- `src/config/settings.py` — the Config class itself defines `__getitem__`

**What to flag:** Any `config["..."]` or `config['...']` in business logic code (`src/bot/`, `src/services/`, `src/api/` excluding base.py, `src/utils/`, `src/models/`).

```python
SRC_DIR = os.path.join(PROJECT_ROOT, "src")

# Directories/files excluded from bracket access check
BRACKET_ACCESS_EXCLUDED = {
    os.path.join(SRC_DIR, "setup"),
    os.path.join(SRC_DIR, "api", "base.py"),
    os.path.join(SRC_DIR, "config", "settings.py"),
}


def _is_excluded_from_bracket_check(filepath):
    """Check if a filepath is excluded from the bracket access rule."""
    for excluded in BRACKET_ACCESS_EXCLUDED:
        if filepath.startswith(excluded):
            return True
    return False


def _find_config_bracket_access(filepath):
    """Find config['key'] or config['key'] patterns via AST."""
    with open(filepath, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=filepath)

    violations = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Subscript)
            and isinstance(node.value, ast.Name)
            and node.value.id == "config"
        ):
            violations.append(node.lineno)
    return violations


def test_no_config_bracket_access_in_business_logic():
    """Business logic must use config.get() instead of config['key'].

    Bracket access raises KeyError on missing keys with no fallback.
    Using config.get(key, default) provides graceful degradation.

    Excluded: src/setup/ (builds config interactively),
    src/api/base.py (accesses self.config service dict),
    src/config/settings.py (defines __getitem__).
    """
    violations = []
    for root, dirs, files in os.walk(SRC_DIR):
        # Skip __pycache__
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for filename in sorted(files):
            if not filename.endswith(".py"):
                continue
            filepath = os.path.join(root, filename)
            if _is_excluded_from_bracket_check(filepath):
                continue
            lines = _find_config_bracket_access(filepath)
            if lines:
                rel = os.path.relpath(filepath, PROJECT_ROOT)
                for line in lines:
                    violations.append(f"{rel}:{line}")

    assert not violations, (
        f"Found config['key'] bracket access (use config.get() instead):\n"
        + "\n".join(f"  {v}" for v in violations)
    )
```

**Important:** This test may surface existing violations. If it does, we need to evaluate whether they're real issues or acceptable patterns, and either fix them or add targeted exclusions before the test can pass.

### Task 2.5: Verify all convention tests pass

**What:** Run `pytest tests/test_architecture/test_conventions.py -v` and confirm all 4 convention tests pass. Handle any failures:
- If the config bracket test reveals violations, either fix the violations or add narrowly-scoped exclusions with comments explaining why.
- All other convention tests should pass based on analysis.

---

## Phase 3: Integration & Verification

### Task 3.1: Run full test suite

**What:** Run `pytest --tb=short -q` to verify the new architecture tests integrate cleanly with the existing suite and don't break anything.

### Task 3.2: Run coverage on the new test files

**What:** Run `pytest tests/test_architecture/ --cov=tests.test_architecture --cov-report=term-missing -v` to verify the test files themselves are well-covered. (Note: architecture tests test source structure, not runtime code, so we measure coverage of the test module itself, not `src/`.)

---

## Summary

| Phase | Tasks | Tests Added |
|-------|-------|-------------|
| 1. Layer Boundaries | 1.1–1.4 | 6 PyTestArch rule tests |
| 2. Structural Conventions | 2.1–2.5 | 4 AST-based convention tests |
| 3. Integration | 3.1–3.2 | Full suite verification |

**Total: 10 new tests, 1 new dependency, 4 new files.**

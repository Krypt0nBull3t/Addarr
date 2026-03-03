# Issue #127: Architecture Tests (PyTestArch + AST-Based Structural Checks)

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Enforce layer boundaries and structural conventions with automated tests that run in CI.

**Ref:** [plan.md](plan.md) for full analysis, design decisions, and API reference.

---

### Phase 1: Layer Boundary Tests — PyTestArch (1 task)

**Goal:** Install pytestarch and enforce the 6 layer dependency rules via import analysis.

- [x] **1.1** Set up PyTestArch infrastructure and write layer boundary tests
    - **Context:**
        - **Why:** Layer boundaries (handlers -> services -> api) are documented but not enforced. Violations like the circular import fixed in #110 should be caught automatically.
        - **Architecture:** PyTestArch scans real source files on disk and builds an import graph. Tests use `Rule` fluent API to assert import direction constraints. Runs as normal pytest tests — no special CI step needed.
        - **Key refs:**
            - `src/bot/handlers/` (11 handler files), `src/services/` (8 service files), `src/api/` (6 client files)
            - `src/config/settings.py` (config layer), `src/utils/` (utility layer)
            - `tests/conftest.py` (existing test infrastructure — architecture tests don't need config mocking)
            - Plan section "PyTestArch API Reference" for exact API patterns
        - **Watch out:**
            - PyTestArch needs the **real** `src/` directory path, not mocked modules
            - `get_evaluable_architecture(project_root, source_root)` — first arg is project root (for distinguishing internal/external), second is the source dir to scan
            - Handler-to-handler imports (e.g., `@require_auth` from `auth.py`) are allowed — the rule is handlers must not import `src.api.*` directly
            - Module paths in rules use dotted notation: `"src.bot.handlers"` not `"src/bot/handlers"`
    - **Scope:** New dependency, test directory, conftest fixtures, 7 layer boundary tests
    - **Touches:**
        - Modify: `requirements-test.txt`
        - Create: `tests/test_architecture/__init__.py`
        - Create: `tests/test_architecture/conftest.py`
        - Create: `tests/test_architecture/test_layer_boundaries.py`
    - **Success:** `pytest tests/test_architecture/test_layer_boundaries.py -v` — all 7 tests pass
    - **Completed:** 2026-03-03
    - **Learnings:**
        - PyTestArch module names depend on the first arg to `get_evaluable_architecture` — pass `SRC_ROOT` as both args to get `src.*` dotted paths matching Python import convention
        - PyTestArch's parser doesn't specify `encoding='utf-8'` when reading files, causing UnicodeDecodeError on Windows (cp1252) with emoji-containing source files. Monkey-patched `Parser._parse_file` in conftest for Windows compatibility.
        - Split utils into two separate tests (handlers + services) instead of one combined rule — cleaner failure messages
    - **Key Changes:**
        - Added `pytestarch>=2.0.0` to `requirements-test.txt`
        - Created `tests/test_architecture/` with conftest.py (fixtures + Windows monkey-patch) and test_layer_boundaries.py (7 tests)
    - **Notes:** Watch for pytestarch upstream fix for UTF-8 encoding — can remove monkey-patch when fixed

---

### Phase 2: Structural Convention Tests — AST-Based (1 task)

**Goal:** Enforce handler/service/client structural patterns and config access conventions using stdlib `ast`.

- [x] **2.1** Write AST-based structural convention tests
    - **Context:**
        - **Why:** Structural conventions (singleton pattern, required methods, config access) are documented in CLAUDE.md but a new contributor could easily miss them. AST tests make conventions executable.
        - **Architecture:** Parse source files with `ast.parse()`, walk the tree to find class definitions and method names. No imports of `src.*` needed — pure static analysis on file contents. Helper functions shared across tests in the same file.
        - **Key refs:**
            - `src/bot/handlers/*.py` — 11 handler classes, all have `get_handler()` method
            - `src/services/*.py` — 8 singleton classes
            - `src/api/radarr.py:20` — `RadarrClient(BaseApiClient)` pattern
            - `src/api/transmission.py:16` — `TransmissionClient` (no BaseApiClient inheritance — excluded)
    - **Scope:** 4 convention tests in a single test file with shared AST helpers
    - **Touches:**
        - Create: `tests/test_architecture/test_conventions.py`
        - Modify: `src/utils/validation.py` (fixed 2 bracket access violations)
    - **Success:** `pytest tests/test_architecture/test_conventions.py -v` — all 4 tests pass
    - **Completed:** 2026-03-03
    - **Learnings:**
        - Config bracket access check surfaced 2 real violations in `validation.py` (lines 163, 172) — `config['admins']` and `config['allow_list']` were guarded by `.get()` above but used brackets in the f-string. Fixed to `.get()` with defaults.
        - Using `ast.iter_child_nodes(tree)` instead of `ast.walk(tree)` for class discovery ensures only top-level classes are found (not nested ones)
    - **Key Changes:**
        - Created `tests/test_architecture/test_conventions.py` with 4 tests + 5 AST helper functions
        - Fixed `src/utils/validation.py:163,172` — bracket access -> `.get()` with defaults
    - **Notes:** SINGLETON_CLASSES set must be updated when new services are added

---

### Phase 3: Integration Verification (1 task)

**Goal:** Confirm architecture tests integrate cleanly with the full test suite.

- [x] **3.1** Run full suite and coverage check
    - **Context:**
        - **Why:** New tests must not break existing tests or interfere with the config mock injection in `tests/conftest.py`.
        - **Architecture:** Architecture tests are pure static analysis — they don't import `src.*` modules at runtime, so they shouldn't conflict with the mock config injection.
    - **Scope:** Full test suite run, lint check
    - **Touches:** No file changes
    - **Success:** Full suite green (1408 passed), all 11 architecture tests pass, flake8 clean
    - **Completed:** 2026-03-03
    - **Learnings:**
        - Architecture tests run cleanly alongside existing tests — no conflicts with mock config injection since they only do static file analysis
    - **Key Changes:** None (verification only)

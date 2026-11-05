---
name: task-writer
description: Use when converting an Addarr plan.md into docs/issues/issue-<N>/TASKS.md, or when adding, splitting or resizing tasks in TASKS.md. Produces TDD-ordered tasks with context blocks.
---

# Task Writer Skill

## Core Philosophy

**Feature-focused tasks:** Bundle related work (API client, service, handler, keyboard, translations, tests) into one logical unit. Split by integration boundaries, not by files.

## Task Sizing Rules

| Feature Size | Files | Task Count | How to Split |
|-|-|-|-|
| Small | 1-3 | 1 task | Don't split |
| Medium | 4-8 | 2-3 tasks | API client/service → handler → integration |
| Large | 8+ | 3-4 tasks | By logical layer (see below) |

### Splitting Large Features by Layer

Split by **integration boundaries**, not files. The layers follow CLAUDE.md: API clients → services → handlers.

```
Phase: [Large Feature] (3-4 tasks)

- [ ] 1.1 API client layer
      → src/api/<service>.py (BaseApiClient subclass with search()), pytest + aioresponses tests
      → Success: pytest tests/test_api/ passes

- [ ] 1.2 Service layer
      → src/services/<service>.py (singleton via __new__, is_enabled()), tests with AsyncMock clients
      → Success: pytest tests/test_services/ passes

- [ ] 1.3 Handler layer
      → src/bot/handlers/<feature>.py (get_handler()), states, keyboards, translation keys,
        registration in src/main.py _add_handlers()
      → Success: pytest tests/test_handlers/ passes

- [ ] 1.4 Integration
      → tests/integration/ flow test with BotHarness, manual check in Telegram
      → Success: full flow works
```

## Task Format

```markdown
### Phase N: Feature Name (X tasks)

**Goal:** One sentence describing what this phase delivers.

**Phase Context:** (only if needed for phase-level decisions)

- Why NOT [alternative]: [Key decision that's not obvious from code]

- [ ] **N.1** Implement [feature/layer]
    - **Context:** (REQUIRED - enables standalone task pickup)
        - **Why:** [Problem this solves - what triggered this task]
        - **Architecture:** [How it fits in, which pattern to follow]
        - **Key refs:** [Specific file:line references to understand entry points]
        - **Watch out:** [Edge cases, gotchas, things that aren't obvious]
    - **Scope:** Brief description of what's included
    - **Touches:** Key files (not exhaustive, just main ones)
    - **Action items:**
        - [RED] Write pytest tests for [specific behavior 1]
        - [RED] Write pytest tests for [specific behavior 2]
        - [GREEN] Implement [component] to make tests pass
        - [GREEN] Integrate into [existing code]
    - **Success:** Tests pass, flake8 and mypy clean, [specific behavior works]
```

**CRITICAL:**

- Action items MUST list [RED] test-writing steps BEFORE [GREEN] implementation steps
- **Context block is REQUIRED** for every implementation task

## What Goes IN a Single Task

Bundle these together (one logical unit):

**API client / service task:**
- API client methods in `src/api/` (inherit `BaseApiClient`, implement `search()`)
- Service methods in `src/services/` (singleton, `is_enabled()` guard, `config.get()` access)
- New singletons added to `SINGLETON_CLASSES` in `tests/test_architecture/test_conventions.py` and reset in `tests/conftest.py` `reset_singletons`
- pytest tests: `aioresponses` for HTTP, `AsyncMock` clients for services

**Handler task:**
- Handler class in `src/bot/handlers/` with `get_handler()` and `@require_auth`
- Conversation states in `src/bot/states.py`
- Keyboards in `src/bot/keyboards.py`
- Translation keys in `translations/addarr.template.yml` and all 9 locale files (`@i18n-key`)
- Registration in `src/main.py` `_add_handlers()`
- pytest tests with `make_update` / `make_context` and the handler fixtures in `tests/test_handlers/conftest.py`

## What Triggers a New Task (Approval Gates)

Create separate tasks only at these boundaries:

1. **Layer complete** - API client and service done, ready for the handler layer
2. **Ready for manual testing** - Need to verify in Telegram
3. **Architectural decision needed** - Multiple valid approaches
4. **Risk boundary** - If next step could break things, checkpoint first

## TDD Within Tasks

TDD happens INSIDE each task. Action items ordered: tests first, then implementation.
The `addarr-workflow` Execution Loop runs it and commits **once per task**, not per behavior.

```
Task: Add the Bazarr wanted-subtitles list
  ↓
  Action items (in this order):
    [RED]   1. pytest tests for BazarrClient.get_wanted_movies() (aio_mock fixture)
    [RED]   2. pytest tests for BazarrHandler.wanted_movies (make_update, make_context)
    [GREEN] 3. Implement the client and BazarrService methods
    [GREEN] 4. Implement the handler method and its keyboard
  ↓
  Per behavior: pytest tests/<path>/test_<name>.py::test_<behavior> -v (fails), implement,
  pytest tests/<path>/test_<name>.py -v (passes)
  ↓
  Scoped checks for the changed layers (addarr-workflow Execution Loop step 3);
  the full suite with the 100% coverage gate runs once, in the preflight
  ↓
  Mark complete with metadata, one commit for the task
```

**Rules:**

1. Action items MUST list [RED] steps before [GREEN] steps
2. Test patterns: use the `addarr-testing` skill (fixtures, aioresponses, handler factories)
3. One commit per task, after its scoped checks pass

## Task Conventions

- Use `- [ ]` for incomplete, `- [x]` for complete
- Number as Phase.Task (e.g., 3.2)
- **Success criteria required** - Each task must define "done"
- Keep descriptions concise
- File paths indicative, not exhaustive
- On completion, add `Completed`, `Learnings`, `Key Changes` and `Notes` below the task (CLAUDE.md)

## Decision Framework

| Question | Answer |
|-|-|
| Small change (1-3 files)? | One task, includes everything |
| Medium feature (4-8 files)? | 2-3 tasks: API client/service → handler → integrate |
| Large feature (8+ files)? | 3-4 tasks split by logical layer |
| Needs manual Telegram testing? | Separate verification step |
| Architectural uncertainty? | Stop and ask before implementing |
| Trivial (1-line change)? | Don't create task, just do it |

## Test Count Estimation

**Rule of thumb:** When listing `[RED]` action items, the obvious test cases cover ~60-70% of what you'll actually write. Edge cases (error paths, boundary conditions, format variations) add another 30-40%. Plan for ~1.5x the obvious test count when estimating task size.

## Self-Verification

Before finalizing tasks, check:

1. Is each task a complete logical unit (not just one file)?
2. Do action items list [RED] tests BEFORE [GREEN] implementation?
3. Does each task have clear success criteria?
4. Are approval gates only at natural boundaries?
5. Is the task count appropriate for the feature size?
6. **Can this task be picked up after context loss?** (Context block complete?)
7. **Are test counts realistic?** (Apply 1.5x multiplier to obvious test cases)
8. **Does every file, fixture and command named exist?** (Mark new files as new)

## Output

**Only modify `TASKS.md`** (`docs/issues/issue-<N>/TASKS.md`) - never create separate files.

## Examples

### Small Feature (Handler Only)

```markdown
### Phase 3: Refresh Button on /preferences (1 task)

**Goal:** Let users re-read their preferences without sending /preferences again.

- [ ] **3.1** Add a Refresh button to the preferences message
    - **Context:**
        - **Why:** The preferences message goes stale after a change made elsewhere
        - **Architecture:** Plain `CommandHandler` + `CallbackQueryHandler` in `PreferencesHandler.get_handler()`, no conversation
        - **Key refs:** `src/bot/handlers/preferences.py` (`get_handler()`), `tests/test_handlers/conftest.py` (`preferences_handler`, `unchanged_edit` fixtures)
        - **Watch out:** Anchor the new pattern (`^pref_refresh$`) and add it to the addarr-handlers callback registry. Editing a message to identical text raises `BadRequest("Message is not modified")`; test it with `unchanged_edit`.
    - **Scope:** Refresh button, callback handler, translation key
    - **Touches:** `src/bot/handlers/preferences.py`, `translations/addarr.template.yml` + 9 locale files, `tests/test_handlers/test_preferences_handler.py`
    - **Action items:**
        - [RED] Write pytest tests that the keyboard has a `pref_refresh` button
        - [RED] Write pytest tests that `pref_refresh` answers the query and re-renders, also when the text is unchanged
        - [GREEN] Implement the button and the callback handler
        - [GREEN] Add the translation key to all locale files (`@i18n-key`)
    - **Success:** pytest passes, flake8 and mypy clean, `--validate-i18n` passes, button refreshes in Telegram
```

### Medium Feature (API Client + Service + Handler)

How Bazarr was built. Its files exist now; "(new)" shows how to mark a file the task creates.

```markdown
### Phase 4: Bazarr Subtitles (3 tasks)

**Goal:** Search Bazarr and list wanted subtitles from Telegram.

- [ ] **4.1** Bazarr API client
    - **Context:**
        - **Why:** Users want to see missing subtitles without opening Bazarr
        - **Architecture:** `BaseApiClient` subclass in `src/api/`, same as `RadarrClient`
        - **Key refs:** `src/api/base.py` (`BaseApiClient`), `src/api/radarr.py` as template
        - **Watch out:** Bazarr has no version in its path (`/api/...`): set `API_VERSION = ""` and override `_build_api_url()`. `search()` is required by `tests/test_architecture/test_conventions.py`.
    - **Scope:** Client with `search()`, `get_movies()`, `get_wanted_movies()`, `get_wanted_episodes()`
    - **Touches:** `src/api/bazarr.py` (new), `tests/test_api/test_bazarr.py` (new), `tests/test_api/conftest.py` (`bazarr_client`), `tests/fixtures/bazarr_data.py` (new)
    - **Action items:**
        - [RED] Write pytest tests for each endpoint with `aio_mock` and `bazarr_data.py` responses
        - [RED] Write pytest tests for connection errors and empty results
        - [GREEN] Implement `BazarrClient`
    - **Success:** `pytest tests/test_api/test_bazarr.py` passes, mypy clean

- [ ] **4.2** Bazarr service
    - **Context:**
        - **Why:** Handlers must not import API clients (layer rule in `tests/test_architecture/test_layer_boundaries.py`)
        - **Architecture:** Singleton via `__new__` + `_initialize`, `is_enabled()` reads `config.get("bazarr", {})`
        - **Key refs:** `src/services/transmission.py` as a small singleton template
        - **Watch out:** Add `BazarrService` to `SINGLETON_CLASSES` and reset `_instance`, `_client` and `_config` in `reset_singletons` (`tests/conftest.py`)
    - **Scope:** Service methods that delegate to the client and return `[]` when disabled
    - **Touches:** `src/services/bazarr.py` (new), `tests/test_services/test_bazarr_service.py` (new), `tests/conftest.py`, `tests/test_architecture/test_conventions.py`
    - **Action items:**
        - [RED] Write pytest tests for `is_enabled()` and each method with an `AsyncMock` client
        - [RED] Write pytest tests for the disabled path
        - [GREEN] Implement `BazarrService`
    - **Success:** pytest passes, architecture tests pass

- [ ] **4.3** Bazarr handler and wiring
    - **Context:**
        - **Why:** Expose the service through `/subtitles`
        - **Architecture:** `ConversationHandler` with a `BAZARR_SEARCH` state; config-gated registration
        - **Key refs:** `src/bot/handlers/bazarr.py` callbacks (`bazarr_` prefix), `src/bot/states.py`, `src/main.py` (the Bazarr registration in `AddarrBot._add_handlers()`, on `bazarr.enable`)
        - **Watch out:** Register before `DownloadsHandler` and `StartHandler` (see addarr-handlers `wiring.md`); every user-facing string needs a translation key
    - **Scope:** Handler, state, keyboards, translation keys, registration, integration test
    - **Touches:** `src/bot/handlers/bazarr.py` (new), `src/bot/states.py`, `src/main.py`, `translations/`, `tests/test_handlers/test_bazarr_handler.py` (new), `tests/integration/test_bazarr_flow.py` (new)
    - **Action items:**
        - [RED] Write pytest tests for the menu, search and wanted-list callbacks with `make_update` / `make_context`
        - [RED] Write an integration test with the `bazarr_harness` fixture
        - [GREEN] Implement `BazarrHandler` and register it
        - [GREEN] Manual verification in Telegram
    - **Success:** pytest passes (unit + integration), flake8, mypy and `--validate-i18n` clean, `/subtitles` works
```

**Remember:** Tasks should be large enough to be meaningful, small enough to be recoverable if something goes wrong.

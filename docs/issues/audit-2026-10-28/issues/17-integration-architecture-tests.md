---
title: "Make integration and architecture tests able to catch routing bugs"
labels: [tech-debt, python, priority:high]
slice: 17
findings: [F232, F230, F231, F233, F235, F234]
---

## Problem

The integration harness and the architecture tests pass when they should fail.

- The layer-boundary rule uses PyTestArch `are_sub_modules_of("src.api")`. It misses package-level imports. A planted `from src.api import RadarrClient` in `help.py` passed.
- The harness has no error handler. PTB logs and swallows handler exceptions, so the smoke tests cannot fail.
- The harness copies the handler order by hand instead of using `AddarrBot()._add_handlers()`. `test_main` checks only `call_count`, not the order.
- The `@require_auth` convention test scans only list literals returned by `get_handler()`. Handlers held in a variable (Bazarr `conv_handler`) skip the check.
- The season picker and album picker cancel paths have no integration test, although the issue-136 plan asked for them.
- 43 of 77 callback patterns are never tapped through the harness.

## Expected behavior

A wrong import, a handler exception, a changed handler order, a missing `@require_auth` or a broken callback pattern makes a test fail.

## Fix

- [ ] **F232** Match API imports with `have_name_matching(r"^src\.api(\.|$)")` instead of `are_sub_modules_of("src.api")` (`tests/test_architecture/test_layer_boundaries.py:136`)
- [ ] **F230** Add an error handler with `add_error_handler` that collects exceptions; assert the list is empty at teardown (`tests/integration/conftest.py:357`, teardown in `_make_harness` `:373-384`; `tests/integration/test_smoke.py:23`)
- [ ] **F231** Build the harness through `AddarrBot()._add_handlers()` instead of the copied list; assert the registration order in `test_main` (`tests/integration/conftest.py:317`, `tests/test_main.py:286`)
- [ ] **F233** Inspect the built handlers at runtime instead of the returned list literal (`tests/test_architecture/test_conventions.py:106`, `:135`)
- [ ] **F235** Add 2 parametrize cases: cancel in the season picker (`select_cancel`) and in the album picker (`menu_cancel`) (`tests/integration/test_cancel_flow.py`)
- [ ] **F234** Add one harness tap per callback pattern (`tests/integration/`)

## Acceptance criteria

- [ ] F232: planted `from src.api import RadarrClient` in `src/bot/handlers/help.py` makes `test_handlers_do_not_import_api_clients_directly` fail.
- [ ] F230: planted `raise RuntimeError("planted")` as the last line of `StartHandler`'s `/start` callback (after the reply is sent) makes the smoke tests fail at teardown.
- [ ] F231: moving `StartHandler` before `MediaHandler` in `AddarrBot._add_handlers()` makes the `test_main` order test and an integration cancel test fail.
- [ ] F233: removing `@require_auth` from `BazarrHandler.prompt_search` makes `test_handler_entry_points_have_require_auth` fail.
- [ ] F235: removing `select_cancel` from the season-state pattern (`src/bot/handlers/media/handler.py:122`) or the `^menu_cancel$` handler in the album state (`:140`) makes the matching new case fail.
- [ ] F234: changing one registered pattern (for example `^bazarr_menu$` to `^bazarr_menuX$`) makes its tap test fail.
- [ ] `pytest`, `flake8` and `mypy src/` pass.

## Notes

- Source: audit 2026-10-28, docs/issues/audit-2026-10-28/FINDINGS.md (F-ids F232, F230, F231, F233, F235, F234).
- Priority: max P 25, sum P 116 (high).
- Dependencies: none in the order of work.
- Related: `docs/issues/issue-136/plan.md` (cancel at each conversation state).

---
title: "Merge duplicated pagination, season keyboard and *arr client code"
labels: [tech-debt, python, priority:medium]
slice: 28
findings: [F265, F064, F266]
---

## Problem

- **F265** The pagination math and the Prev/Next row are copied 5 times in `keyboards.py`. Only the downloads keyboards share a helper, `_build_dl_pagination_row`. No copy clamps the page. This causes the empty pages of F085 and F115.
- **F064** The season keyboard is built twice, in `handler.py` and in `season_picker.py`. The `albumsel_cancel` branch in `album_picker.py` is unreachable: no button sends `albumsel_cancel`.
- **F266** Radarr, Sonarr and Lidarr each have near-copies of `__init__`, `get_root_folders`, `get_quality_profiles` and 9 paged "records" fetches.

## Expected behavior

- One pagination row helper that clamps the page, used by every paged keyboard.
- One season keyboard builder in `keyboards.py`.
- Shared *arr client code lives in `BaseApiClient`, like Bazarr's `_get_list`.

## Fix

- [ ] **F265** Add one `_build_pagination_row(prefix, page, total)` that clamps the page. Use it in every paged keyboard in place of the copies and of `_build_dl_pagination_row` (copies at `src/bot/keyboards.py:347`, `:565`, `:655`, `:767`, `:1105`; `_build_dl_pagination_row` at `:869`, used at `:924`, `:1019`). Slice 1 uses it for /delete (F004).
- [ ] **F064** Build the season keyboard in one function in `keyboards.py` and call it from both places. Delete the `albumsel_cancel` branch and its test (`src/bot/handlers/media/handler.py:543`; `src/bot/handlers/media/season_picker.py:98`; `src/bot/handlers/media/album_picker.py:100-105`; test at `tests/test_handlers/test_media_handler.py:2809`)
- [ ] **F266** Move `__init__`, `get_root_folders`, `get_quality_profiles` and the paged "records" fetch into `BaseApiClient`, like Bazarr `_get_list` (`src/api/bazarr.py:61`) (`src/api/radarr.py:23`, `:82`; `src/api/sonarr.py:23`, `:59`; `src/api/lidarr.py:25`, `:214`; records fetches at `radarr.py:171`, `:191`, `:211`, `:275`, `sonarr.py:182`, `:202`, `:222`, `:286`, `lidarr.py:276`)

## Acceptance criteria

- [ ] F265: `tests/test_bot/test_keyboards.py` tests `_build_pagination_row`: a page past the end clamps to the last page, one page gives no row, a middle page gives Prev and Next. Each paged keyboard (`get_search_results_list_keyboard`, `get_calendar_items_keyboard`, `get_missing_items_keyboard`, `get_queue_items_keyboard`, `get_history_items_keyboard`, `get_downloads_queue_keyboard`, `get_downloads_history_keyboard`) called with a page past the end shows the last page and its nav row. These fail before the fix.
- [ ] F064: the season buttons (Monitor All, Confirm Selection) are built only in `keyboards.py`. A test in `test_keyboards.py` covers the builder: selected seasons, future mode, monitor all. `grep -rn "albumsel_cancel" src tests` returns nothing.
- [ ] F266: `tests/test_api/test_base.py` covers the moved methods once. The per-client copies are gone. The Radarr, Sonarr and Lidarr API tests pass.
- [ ] `pytest` (coverage stays at 100%), `flake8` and `mypy src/` pass.

## Notes

- Source: audit 2026-10-28, docs/issues/audit-2026-10-28/FINDINGS.md (F-ids F265, F064, F266).
- Priority: max P 16 (F265), sum P 35, `priority:medium`.
- Order of work: this slice gives slices 1 (F004), 12 (F085) and 22 (F115) their shared pagination helper. Land F265 before them.
- F064 builds the season keyboard that slice 25 (F202) translates. Do F064 first or in the same PR.
- F266: every `BaseApiClient` subclass must keep `search()` (convention test in `tests/test_architecture/test_conventions.py`).
- Related open issues: none.

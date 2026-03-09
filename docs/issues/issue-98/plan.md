# Use Existing Translation Keys for Error Messages — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace all hardcoded English error/status strings in handlers with `TranslationService.get_text()` calls using flat translation keys.

**Architecture:** Add new flat top-level translation keys to all 10 locale files + template. Wire up TranslationService in handlers that don't yet use it (SystemHandler, TransmissionHandler). Replace hardcoded strings with `get_text()` calls. Update tests to assert on translation keys instead of English strings.

**Tech Stack:** Python, python-telegram-bot v20+, YAML translations, pytest

---

## Context

### Translation System Constraint

`TranslationService.get_text(key)` does a **single-level `.get(key)`** on the translations dict. Nested YAML keys (e.g., `Error.NotFound`, `Transmission.NotEnabled`) are **NOT accessible** via `get_text()`. Only flat top-level keys work. All new keys must be flat.

### Current State by Handler

| Handler | Has TranslationService? | Hardcoded strings | Fixture patches TS? |
|---------|------------------------|-------------------|---------------------|
| `media/handler.py` | Yes (`self.translation`) | 8 strings | Yes |
| `media/album_picker.py` | Yes (via mixin, uses `self.media_service`) | 4 strings | Yes (via media_handler) |
| `media/season_picker.py` | Yes (via mixin) | 1 string | Yes (via media_handler) |
| `media/formatters.py` | No (standalone functions) | 1 string | N/A (no class) |
| `delete.py` | Yes (`self.translation`) | 6 strings | Yes |
| `system.py` | **No** | 5 strings | **No** |
| `calendar.py` | Yes (`self.translation`) | 1 string | Yes |
| `transmission.py` | **No** | 3 strings | Yes (over-patching) |

### Test Pattern

- Mock `TranslationService` returns keys as-is: `service.get_text = MagicMock(side_effect=lambda key, **kw: key)`
- Tests assert on translation key names (not English text) when using the mock
- Handler fixtures patch `TranslationService` at the handler's import site

### Translation Key Naming Convention

Existing keys use PascalCase (e.g., `CalendarAddFailed`, `LibraryError`, `NotAdmin`). Error-related keys should follow the pattern `Error<Context>` for consistency with `ErrorGettingMediaList` style but since existing keys like `CalendarAddFailed` don't use `Error` prefix, follow the most common pattern: descriptive PascalCase.

## New Translation Keys

These flat top-level keys will be added to all 10 locale files + template:

| Key | English Value | Used By |
|-----|---------------|---------|
| `SearchError` | `"❌ An error occurred while searching.\nPlease try again later."` | media/handler.py |
| `SearchInvalidType` | `"❌ Invalid search type"` | media/handler.py |
| `SearchNoResults` | `"❌ No %{search_type} found matching '%{query}'"` | media/handler.py |
| `SelectionNotFound` | `"❌ Selection not found.\nPlease try your search again."` | media/handler.py |
| `SelectionDataNotFound` | `"❌ Selection data not found.\nPlease try your search again."` | media/handler.py |
| `SelectionProcessError` | `"❌ An error occurred while processing your selection.\nPlease try again."` | media/handler.py, season_picker.py, album_picker.py |
| `MediaAddError` | `"❌ An error occurred: %{error}"` | media/handler.py |
| `InvalidMediaType` | `"❌ Invalid media type"` | media/handler.py, delete.py |
| `DisplayResultError` | `"❌ Error displaying result. Please try your search again."` | media/formatters.py |
| `ArtistAddError` | `"❌ An error occurred while adding the artist."` | album_picker.py |
| `AlbumFetchError` | `"❌ An error occurred while fetching albums."` | album_picker.py |
| `MediaListError` | `"❌ Error getting media list"` | delete.py |
| `MediaTypeNotFound` | `"❌ Media type not found"` | delete.py |
| `ItemDetailsError` | `"❌ Error getting item details"` | delete.py |
| `ItemDataNotFound` | `"❌ Item data not found"` | delete.py |
| `StatusRefreshed` | `"Status refreshed"` | system.py |
| `StatusRefreshError` | `"❌ Error refreshing status. Please try again."` | system.py |
| `StatusRefreshFailed` | `"Refresh failed"` | system.py |
| `StatusDetailsError` | `"❌ Error retrieving service details. Please try again."` | system.py |
| `StatusDetailsFailed` | `"Details failed"` | system.py |
| `UnknownAction` | `"Unknown action"` | system.py |
| `UnknownMediaType` | `"Unknown media type"` | calendar.py |
| `TransmissionNotEnabled` | `"❌ Transmission integration is not enabled.\nEnable it in config.yaml to use this feature."` | transmission.py |
| `TransmissionConnectionError` | `"❌ Cannot connect to Transmission:\n%{error}"` | transmission.py |
| `TransmissionToggleFailed` | `"❌ Failed to toggle Turtle Mode"` | transmission.py |

**Total: 25 new keys** (some consolidate duplicates across files).

## Phased Approach

### Phase 1: Add Translation Keys

Add all 25 new flat keys to:
- `translations/addarr.template.yml`
- `translations/addarr.en-us.yml`
- All 8 other locale files (using English as placeholder — same pattern as existing keys)

### Phase 2: Handlers That Already Have TranslationService

Replace hardcoded strings in files that already have `self.translation`:
- `src/bot/handlers/media/handler.py` (8 replacements)
- `src/bot/handlers/delete.py` (6 replacements)
- `src/bot/handlers/calendar.py` (1 replacement)
- `src/bot/handlers/media/album_picker.py` (4 replacements)
- `src/bot/handlers/media/season_picker.py` (1 replacement)

For `src/bot/handlers/media/formatters.py` (standalone functions, no `self.translation`): pass a `TranslationService()` call directly since it's a singleton. Or accept that this one fallback error message can stay hardcoded — it's a last-resort error handler. **Decision: use `TranslationService().get_text()` inline** since it's a singleton and only called on error paths.

### Phase 3: Handlers That Need TranslationService Added

**SystemHandler** (`src/bot/handlers/system.py`):
- Add `from src.services.translation import TranslationService`
- Add `self.translation = TranslationService()` in `__init__`
- Replace 5 hardcoded strings
- Add TranslationService patch to `system_handler` fixture in `tests/test_handlers/conftest.py`

**TransmissionHandler** (`src/bot/handlers/transmission.py`):
- Add `from src.services.translation import TranslationService`
- Add `self.translation = TranslationService()` in `__init__`
- Replace 3 hardcoded strings
- Fixture already patches TranslationService (but handler doesn't use it yet — this makes the existing fixture correct after our change)

### Phase 4: Update Tests

Update existing tests that assert on hardcoded English text to assert on translation key names instead. Key tests to update:
- `tests/test_handlers/test_transmission_handler.py` — `test_transmission_not_enabled` asserts `"not enabled"` in output
- `tests/test_handlers/test_transmission_handler.py` — `test_transmission_not_connected` asserts `"connect"` in output
- `tests/test_handlers/test_system_handler.py` — various tests that check hardcoded text
- Add new tests for error paths that weren't previously tested

## Verification

1. `pytest --tb=short -q` — all tests pass
2. `python -m flake8 .` — no lint errors
3. `PYTHONIOENCODING=utf-8 python run.py --validate-i18n` — translations valid
4. Coverage check on changed source modules

# Add mypy Type Checking to CI — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add mypy as a blocking CI job that catches type errors before merge, starting with lenient config that passes clean.

**Architecture:** Create `mypy.ini` at repo root with lenient global defaults and per-module overrides. Handler layer gets union-attr/index suppressed (Telegram's Optional types are noisy, not buggy). Services/API/utils get full checking. All genuine type errors are fixed so CI passes clean from day one.

**Tech Stack:** mypy, types-PyYAML, GitHub Actions

---

## Current State

- **494 mypy errors** across 42 of 67 source files
- Error breakdown by code:
  - `union-attr` (326) — handlers accessing `update.effective_message`, `context.user_data`, etc. (Optional types)
  - `index` (58) — handlers indexing `context.user_data` (Optional dict)
  - `attr-defined` (42) — singleton services missing class-level annotations
  - `assignment` (31) — implicit Optional (`param: str = None` without `Optional`)
  - `arg-type` (14) — wrong argument types passed
  - `import-untyped` (6) — missing PyYAML stubs
  - Other (17) — var-annotated, return, str, etc.
- Top offending files: `settings.py` handler (108), `media/handler.py` (76), `album_picker.py` (40), `delete.py` (37)

## Strategy

1. **Suppress handler noise via per-module config** — `union-attr` and `index` errors in `src/bot/handlers/` are from Telegram's Optional types (effective_message, callback_query, user_data). These are guaranteed non-None in handler context. Suppress at module level rather than littering code with 380+ `assert` statements or `# type: ignore` comments.

2. **Fix genuine errors everywhere else** — implicit Optional, attr-defined on singletons, missing returns, wrong arg types. These catch real bugs.

3. **Install type stubs** — `types-PyYAML` eliminates import-untyped errors.

4. **Make CI blocking from day one** — no `continue-on-error`. The config is tuned to pass clean.

## Phases

### Phase 1: Infrastructure (mypy config + CI job + deps)

Create `mypy.ini` with:
- `ignore_missing_imports = True` (third-party libs without stubs)
- `no_implicit_optional = True` (modern default, we'll fix the code)
- `warn_unused_ignores = True`
- `show_error_codes = True`
- `check_untyped_defs = False` (don't require annotations on all functions)
- Per-module: `[mypy-src.bot.handlers.*]` disables `union-attr`, `index`
- Per-module: `[mypy-src.setup.*]` disables checking (interactive wizard, not business logic)

Add to `requirements-test.txt`:
- `mypy>=1.8.0`
- `types-PyYAML>=6.0.12`

Add CI job to `.github/workflows/ci.yml`:
- New `type-check` job between `lint` and `unit-test`
- Runs `mypy src/`
- Blocking (no `continue-on-error`)

### Phase 2: Fix implicit Optional errors (~15 occurrences across 7 files)

Mechanical fix: `param: str = None` → `param: Optional[str] = None`

Files:
- `src/utils/validate_translations.py` — `required_sections`
- `src/setup/validators.py` — `apikey` (2 functions)
- `src/setup/prompts.py` — `default_config`
- `src/utils/logger.py` — `context`, `input_data`
- `src/services/translation.py` — `subject`, `title`
- `src/services/sabnzbd.py` — `name`, `category`
- `src/api/sabnzbd.py` — `nzbname`, `category`
- `src/api/base.py` — `title` (3 methods), `timeout`, `max_retries`

### Phase 3: Fix attr-defined errors on singleton services

The singleton `__new__` pattern creates instance attributes that mypy can't see from the class definition. Fix by adding class-level type annotations.

Files:
- `src/services/sabnzbd.py` — `_enabled`, `api_key`, `base_url`
- `src/services/scheduler.py` — `jobs`
- `src/services/media.py` — client attributes
- `src/services/rate_limit.py` — `_records` needs type annotation

### Phase 4: Fix remaining non-handler errors

- `src/api/base.py:131` — missing return statement
- `src/utils/helpers.py:90` — float assigned to int variable
- `src/utils/validation.py:91` — `ValidationError.message` attr
- `src/bot/keyboards.py` — union-attr on Telegram types (may need per-module config or targeted fixes)
- Various `arg-type` errors in non-handler code

### Phase 5: Verification

- Run `mypy src/` — must pass clean (0 errors)
- Run full test suite — no regressions
- Run flake8 — no lint failures

### Phase 6: Create follow-up issues for suppressed errors

Create GitHub issues to track fixing the suppressed handler/setup type errors in batches:

1. **Handlers union-attr/index errors** — Fix Telegram Optional type narrowing in handler layer (`src/bot/handlers/`). ~384 suppressed errors. Split by handler file or group (media handlers, download handlers, management handlers).
2. **Setup module type errors** — Fix type errors in `src/setup/` (interactive wizard). Lower priority since it's not business logic.

Each issue should reference #118 as the parent, include the specific error codes to address, and list affected files. Once all follow-up issues are resolved, the per-module suppressions in `mypy.ini` can be removed.

## Verification Commands

```bash
# Type checking (must pass clean)
python -m mypy src/

# Full test suite (no regressions)
python -m pytest --tb=short -q

# Lint (no new issues)
python -m flake8 .
```

## Files Changed

### New files:
- `mypy.ini`

### Modified files:
- `requirements-test.txt` — add mypy, types-PyYAML
- `.github/workflows/ci.yml` — add type-check job
- `src/utils/validate_translations.py` — Optional fix
- `src/setup/validators.py` — Optional fix
- `src/setup/prompts.py` — Optional fix
- `src/utils/logger.py` — Optional fix
- `src/services/translation.py` — Optional fix
- `src/services/sabnzbd.py` — Optional fix + class annotations
- `src/api/sabnzbd.py` — Optional fix
- `src/api/base.py` — Optional fix + missing return
- `src/services/scheduler.py` — class annotations
- `src/services/media.py` — class annotations
- `src/services/rate_limit.py` — type annotation
- `src/utils/helpers.py` — type fix
- `src/utils/validation.py` — attr fix
- `src/bot/keyboards.py` — targeted fixes or per-module config

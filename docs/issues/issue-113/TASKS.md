# Issue #113: Help Command Translation & Dynamic Content

**Goal:** Replace hardcoded English help text with translated, service-aware dynamic help output.

**Plan:** See `plan.md` for full context, design decisions, and translation key definitions.

---

### Phase 1: Translation Keys & Dynamic Handler (2 tasks)

**Goal:** Add section-based help translation keys and rewrite the handler to use them dynamically.

- [x] **1.1** Add help section translation keys to all locale files
    - **Context:** See plan.md Phase 1. The template has a monolithic `HelpText` key (lines 128-153) that must be replaced with section keys (`HelpHeader`, `HelpBasicCommands`, `HelpMediaMovies`, `HelpMediaSeries`, `HelpMediaMusic`, `HelpDownloadTransmission`, `HelpDownloadSabnzbd`, `HelpVersion`, `HelpFooter`). See plan.md for exact YAML content.
    - **Watch out:** Remove the old `HelpText` block. YAML multiline `|` blocks need consistent indentation. All 9 locale files + template need identical keys (English defaults for non-English locales).
    - **Scope:** Replace `HelpText` in template, add section keys to all 10 translation files
    - **Touches:** `translations/addarr.template.yml`, `translations/addarr.en-us.yml`, 8 other locale files
    - **Action items:**
        - [GREEN] Replace `HelpText` block in template with section keys from plan.md
        - [GREEN] Add same keys to `addarr.en-us.yml`
        - [GREEN] Add same keys to remaining 8 locale files
    - **Success:** `PYTHONIOENCODING=utf-8 python run.py --validate-i18n` passes
    - **Completed:** 2026-03-10
    - **Learnings:** All 9 locale files had identical HelpText blocks that needed replacing
    - **Key Changes:** Replaced monolithic `HelpText` key with 9 section keys (`HelpHeader`, `HelpBasicCommands`, `HelpMediaMovies`, `HelpMediaSeries`, `HelpMediaMusic`, `HelpDownloadTransmission`, `HelpDownloadSabnzbd`, `HelpVersion`, `HelpFooter`) in template + all 9 locale files
    - **Notes:** Non-English locales have English defaults; native speakers can translate later

- [x] **1.2** Rewrite help handler with dynamic translated text + tests
    - **Context:** See plan.md Phase 2-3. `src/bot/handlers/help.py` currently has hardcoded English text (lines 42-66) with wrong version ("0.1.0") and wrong repo URLs. Rewrite to use `_build_help_text()` that assembles sections from translations, filtered by enabled services via `config.get("radarr", {}).get("enable")` (same pattern as `src/bot/commands.py:45`). Version from `src.__version__` ("0.8").
    - **Watch out:** Patch config at `src.bot.handlers.help.config` (module-level import binding). Existing tests in `test_help_handler.py` assert `/movie` and `/series` in output — update them to mock config with those services enabled. `get_text()` uses `%(key)s` formatting for version substitution.
    - **Scope:** Handler rewrite + test updates + new test cases
    - **Touches:** `src/bot/handlers/help.py`, `tests/test_handlers/test_help_handler.py`
    - **Action items:**
        - [RED] Write `test_show_help_hides_disabled_services` — config with radarr disabled, verify `/movie` absent
        - [RED] Write `test_show_help_shows_version` — verify `__version__` appears in output
        - [RED] Write `test_show_help_shows_download_clients` — enable transmission+sabnzbd, verify they appear
        - [RED] Write `test_show_help_hides_download_clients` — disable both, verify absent
        - [GREEN] Add `_build_help_text()` method and rewrite `show_help` to use it (see plan.md for implementation)
        - [GREEN] Update existing `test_show_help_command` to mock config with services enabled
    - **Success:** `pytest tests/test_handlers/test_help_handler.py -v` all pass, `pytest --cov=src.bot.handlers.help --cov-report=term-missing` shows 100% on changed code
    - **Completed:** 2026-03-10
    - **Learnings:** The conftest fake `src` module didn't have `__version__`, causing `from src import __version__` to fail and preventing `help.py` from loading in tests. Fixed by adding `__version__` to the fake module. Used `with patch(...)` context managers instead of `@patch` decorators for config mocking to avoid module resolution issues with `help` (Python builtin name collision).
    - **Key Changes:** Rewrote `help.py` with `_build_help_text()` method using config checks and translations. Added 5 new test cases (disabled services, version, download clients show/hide). Updated `conftest.py` to set `__version__` on fake src module.
    - **Notes:** 100% coverage on help.py, 1861 tests pass, no lint errors

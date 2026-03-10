# Help Command Translation & Dynamic Content — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace hardcoded English help text with translated, service-aware dynamic help output.

**Architecture:** Split the monolithic `HelpText` translation key into section-based keys so download client commands (Transmission/SABnzbd) can be conditionally included. The help handler builds the text by checking config for enabled services and assembling only relevant translation sections. Version is pulled from `src.__version__`.

**Tech Stack:** python-telegram-bot v20+, TranslationService (python-i18n wrapper), pytest + unittest.mock

---

## Context

### Current State
- `src/bot/handlers/help.py` has fully hardcoded English help text (lines 42-66)
- Hardcoded version "0.1.0" — actual version is `src.__version__` = "0.8"
- Hardcoded repo URLs point to `Cyneric/addarr` — should be `Krypt0nBull3t/Addarr`
- Shows ALL commands regardless of which services are enabled
- `TranslationService` is imported but only used in `handle_back`, not in `show_help`

### Translation Template
The template (`translations/addarr.template.yml`) already has a `HelpText` key (lines 129-153) but it's a single block including Transmission/SABnzbd unconditionally. We'll replace it with section keys.

### Existing Patterns
- `src/bot/commands.py` already checks `config.get("radarr", {}).get("enable")` etc. to build dynamic command lists — we follow this exact pattern
- Translation keys use flat top-level names: `HelpButton`, `CommandHelp`, `CommandStart`, etc.
- `get_text()` supports `%(key)s` formatting: `translation.get_text("key", param=value)`

### Files to Touch
| File | Action |
|------|--------|
| `src/bot/handlers/help.py` | Rewrite `show_help` to build dynamic translated text |
| `translations/addarr.template.yml` | Replace `HelpText` with section keys |
| `translations/addarr.en-us.yml` | Add English section keys |
| `translations/addarr.{8 other locales}.yml` | Add section keys (English defaults) |
| `tests/test_handlers/test_help_handler.py` | Update tests for new behavior |

---

## Design Decisions

1. **Section-based translation keys** rather than one monolithic `HelpText`:
   - `HelpHeader` — title line
   - `HelpBasicCommands` — always-shown commands (start, auth, help, status, settings, delete, library)
   - `HelpMediaMovies` — movie commands (when radarr enabled)
   - `HelpMediaSeries` — series commands (when sonarr enabled)
   - `HelpMediaMusic` — music commands (when lidarr enabled)
   - `HelpDownloadTransmission` — transmission command (when enabled)
   - `HelpDownloadSabnzbd` — sabnzbd command (when enabled)
   - `HelpFooter` — version + repo links

2. **Config access** follows `commands.py` pattern: `config.get("radarr", {}).get("enable")`.

3. **Version** imported from `src.__version__` — no hardcoding.

4. **Repo URLs** updated to `Krypt0nBull3t/Addarr`.

5. **Remove old `HelpText` key** from template and all locale files (replaced by section keys).

---

## Phase 1: Translation Keys

### Task 1.1: Add help section keys to template

**Files:**
- Modify: `translations/addarr.template.yml` (lines 128-153)

Replace the existing `HelpText` block with individual section keys:

```yaml
  # Help sections
  HelpHeader: "🤖 *Available Commands:*"
  HelpBasicCommands: |
    🚀 /start - Start the bot
    🔐 /auth - Authenticate with password
    ❓ /help - Show this help message
    📊 /status - Check system status
    ⚙️ /settings - Manage settings
    🗑️ /delete - Delete media
    📚 /library - Browse your library
  HelpMediaMovies: |
    🎬 /movie - Search and add movies
    🎬 /allmovies - Show all movies
  HelpMediaSeries: |
    📺 /series - Search and add TV shows
    📺 /allseries - Show all series
  HelpMediaMusic: |
    🎵 /music - Search and add music
    🎵 /allmusic - Show all music
  HelpDownloadTransmission: "📡 /transmission - Manage Transmission"
  HelpDownloadSabnzbd: "📥 /sabnzbd - Manage SABnzbd"
  HelpVersion: "🔄 Version: %(version)s"
  HelpFooter: |
    📖 Wiki: https://github.com/Krypt0nBull3t/Addarr/wiki
    🐞 Issues: https://github.com/Krypt0nBull3t/Addarr/issues
```

### Task 1.2: Add help section keys to en-us locale

**Files:**
- Modify: `translations/addarr.en-us.yml`

Add the same keys with English text (identical to template).

### Task 1.3: Add help section keys to remaining 8 locale files

**Files:**
- Modify: All 8 non-English locale files

Add the same English keys as defaults. Native speakers can translate later.

---

## Phase 2: Dynamic Help Handler

### Task 2.1: Rewrite `show_help` to build dynamic translated text

**Files:**
- Modify: `src/bot/handlers/help.py`
- Test: `tests/test_handlers/test_help_handler.py`

**Implementation approach:**

```python
from src.config.settings import config
from src import __version__

# In show_help:
def _build_help_text(self):
    """Build help text from translations, filtered by enabled services."""
    t = self.translation
    sections = [t.get_text("HelpHeader"), "", t.get_text("HelpBasicCommands")]

    # Media commands — only show enabled services
    if config.get("radarr", {}).get("enable"):
        sections.append(t.get_text("HelpMediaMovies"))
    if config.get("sonarr", {}).get("enable"):
        sections.append(t.get_text("HelpMediaSeries"))
    if config.get("lidarr", {}).get("enable"):
        sections.append(t.get_text("HelpMediaMusic"))

    # Download clients
    if config.get("transmission", {}).get("enable", False):
        sections.append(t.get_text("HelpDownloadTransmission"))
    if config.get("sabnzbd", {}).get("enable", False):
        sections.append(t.get_text("HelpDownloadSabnzbd"))

    # Footer
    sections.append("")
    sections.append(t.get_text("HelpVersion", version=__version__))
    sections.append(t.get_text("HelpFooter"))

    return "\n".join(sections)
```

The `show_help` method calls `_build_help_text()` instead of using the hardcoded string.

---

## Phase 3: Tests

### Task 3.1: Test help text includes only enabled service commands

**Files:**
- Modify: `tests/test_handlers/test_help_handler.py`

Update existing tests and add new ones:

1. **Update `test_show_help_command`** — mock config to enable radarr+sonarr, verify those commands appear in output
2. **Add `test_show_help_hides_disabled_services`** — mock config with radarr disabled, verify `/movie` and `/allmovies` do NOT appear
3. **Add `test_show_help_shows_version`** — verify `__version__` value appears in output
4. **Add `test_show_help_shows_download_clients`** — enable transmission+sabnzbd in config, verify they appear
5. **Add `test_show_help_hides_download_clients`** — disable both, verify they don't appear

Config mocking pattern (from `commands.py` tests):
```python
@patch("src.bot.handlers.help.config")
```
Since `help.py` will import `from src.config.settings import config`, patch at the import site.

---

## Verification

After all tasks:
1. `pytest tests/test_handlers/test_help_handler.py -v` — all tests pass
2. `pytest --tb=short -q` — full suite passes
3. `python -m flake8 .` — no lint errors
4. `pytest --cov=src.bot.handlers.help --cov-report=term-missing` — 100% on new/changed code
5. `PYTHONIOENCODING=utf-8 python run.py --validate-i18n` — translation validation passes

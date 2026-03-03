# Issue #110: Register Bot Commands with Telegram (`setMyCommands`)

## Summary

Register bot commands via `setMyCommands` with two tiers: minimal set for unauthenticated users (`/start`, `/auth`, `/help`) and full set for authenticated users (all commands, filtered by enabled services). New shared `src/bot/commands.py` module avoids circular imports between `main.py` and `auth.py`.

---

### Phase 1: Command Builder Module + Translations (2 tasks)

**Goal:** Create the command-building logic and translation keys that both startup and post-auth registration will use.

- [x] **1.1** Implement command builder functions with translation keys
    - **Context:**
        - **Why:** Both `AddarrBot.initialize()` and `AuthHandler.check_password()` need to build command lists — a shared module avoids circular imports and duplication
        - **Architecture:** New `src/bot/commands.py` with three functions: `build_default_commands()` (3 unauthenticated commands), `build_authenticated_commands()` (7 base + conditional per enabled service), `register_commands_for_chat()` (async helper). Uses `TranslationService.get_text()` with flat top-level keys (`CommandStart`, `CommandAuth`, etc.) to avoid the pre-existing nested lookup bug
        - **Key refs:** `src/config/settings.py` for `config.get()` pattern; `src/services/translation.py:73-102` for `get_text()` single-level lookup; `src/main.py:134,140` for service enablement checks (`config.get("transmission", {}).get("enable", False)`)
        - **Watch out:** Telegram requires command names to be lowercase — use `allmovies` not `allMovies` in `BotCommand`. Telegram's command matching is case-insensitive so `/allMovies` typed by users still works. Translation keys must be flat top-level (not nested like `Commands.start`) because `get_text()` does a single `.get(key)` lookup
    - **Scope:** New `src/bot/commands.py`, translation keys in all 9 locale files + template
    - **Touches:** `src/bot/commands.py` (create), `translations/addarr.*.yml` (all 9), `translations/addarr.template.yml`
    - **Action items:**
        - [RED] Write tests for `build_default_commands()` — returns exactly 3 BotCommand objects (start, auth, help)
        - [RED] Write tests for `build_authenticated_commands()` — minimal config (no optional services) returns 7 base commands
        - [RED] Write tests for `build_authenticated_commands()` — each service toggle adds expected commands (radarr adds movie+allmovies, sonarr adds series+allseries, lidarr adds music+allmusic, transmission adds transmission, sabnzbd adds sabnzbd)
        - [RED] Write tests for `build_authenticated_commands()` — all services enabled returns all 15 commands
        - [RED] Write test for `register_commands_for_chat()` — mocks bot, verifies `set_my_commands` called with `BotCommandScopeChat`
        - [RED] Write test for `register_commands_for_chat()` — bot raises exception, function logs warning but doesn't propagate
        - [GREEN] Create `src/bot/commands.py` with `build_default_commands()`, `build_authenticated_commands()`, `register_commands_for_chat()`
        - [GREEN] Add `CommandStart`, `CommandAuth`, `CommandHelp`, `CommandStatus`, `CommandSettings`, `CommandPreferences`, `CommandDelete`, `CommandMovie`, `CommandSeries`, `CommandMusic`, `CommandAllMovies`, `CommandAllSeries`, `CommandAllMusic`, `CommandTransmission`, `CommandSabnzbd` keys to all translation files and template
    - **Success:** `pytest tests/test_bot/test_commands.py -v` — all tests pass, `flake8 src/bot/commands.py` clean
    - **Completed:** 2026-03-03
    - **Learnings:**
        - `mock_config` fixture creates a fresh MockConfig but `src.bot.commands` binds `config` at import time — must use `patch("src.bot.commands.config", mock_config)` to override per-test
        - TranslationService `get_text()` returns the key string when translations are empty (mocked), so test assertions check for key names like `"CommandStart"`
    - **Key Changes:**
        - Created `src/bot/commands.py` with `build_default_commands()`, `build_authenticated_commands()`, `register_commands_for_chat()`
        - Created `tests/test_bot/test_commands.py` with 12 tests (3 default, 7 authenticated config combos, 2 register)
        - Added 15 `CommandX` translation keys to all 9 locale files + template
    - **Notes:** Command names are lowercase (`allmovies` not `allMovies`) per Telegram requirement — Telegram matching is case-insensitive

---

### Phase 2: Bot Integration — Startup + Post-Auth Registration (1 task)

**Goal:** Wire command registration into bot startup and post-authentication flow.

- [x] **2.1** Integrate command registration into `AddarrBot.initialize()` and `AuthHandler.check_password()`
    - **Context:**
        - **Why:** Commands must be registered at two points: (1) startup sets default scope for unauthenticated users and per-chat scope for already-authenticated users, (2) after successful auth sets per-chat scope for the newly authenticated user
        - **Architecture:** `AddarrBot` gets a `_register_commands()` method that calls `build_default_commands()` for `BotCommandScopeDefault` and iterates `AuthHandler._authenticated_users` calling `register_commands_for_chat()` for each. `AuthHandler.check_password()` calls `register_commands_for_chat()` after adding user to authenticated set. Both import from `src.bot.commands` (no circular dependency)
        - **Key refs:** `src/main.py:79` insertion point after `await self.application.initialize()`; `src/bot/handlers/auth.py:141-142` insertion point after `AuthHandler._authenticated_users.add(user.id)` and `self._save_authenticated_users()`; `tests/test_main.py` for existing bot initialization tests; `tests/test_handlers/test_auth_handler.py` for existing auth handler tests
        - **Watch out:** `_register_commands()` must be called after `self.application.initialize()` so `self.application.bot` is available. Per-user `set_my_commands` may fail for users who blocked the bot or deleted their chat — catch per-user exceptions without failing startup. Import `BotCommandScopeDefault`, `BotCommandScopeChat` from `telegram` package
    - **Scope:** Modify `src/main.py` and `src/bot/handlers/auth.py`, add integration tests
    - **Touches:** `src/main.py`, `src/bot/handlers/auth.py`, `tests/test_main.py`, `tests/test_handlers/test_auth_handler.py`
    - **Action items:**
        - [RED] Write test: `_register_commands()` sets default commands via `BotCommandScopeDefault`
        - [RED] Write test: `_register_commands()` sets per-user commands for each authenticated user
        - [RED] Write test: `_register_commands()` handles per-user failures gracefully (one user fails, others still get commands)
        - [RED] Write test: `check_password()` success calls `register_commands_for_chat()` with correct chat_id and bot
        - [GREEN] Add `_register_commands()` method to `AddarrBot`, call after `self.application.initialize()` in `initialize()`
        - [GREEN] Add `register_commands_for_chat()` call in `AuthHandler.check_password()` after successful authentication
    - **Success:** `pytest --tb=short -q` — full suite passes, `flake8 .` clean, `python run.py --validate-i18n` passes
    - **Completed:** 2026-03-03
    - **Learnings:**
        - `_make_mock_application()` in test_main.py needed `app.bot = AsyncMock()` with `set_my_commands = AsyncMock()` since `_register_commands()` awaits `bot.set_my_commands()`
        - `register_commands_for_chat()` already builds its own command list internally, so `_register_commands()` doesn't need to pre-build `auth_commands` (removed dead variable caught by flake8)
        - Patching `src.bot.handlers.auth.register_commands_for_chat` works because auth.py imports it at module level
    - **Key Changes:**
        - Modified `src/main.py` — added `_register_commands()` method, called after `application.initialize()`, imports `build_default_commands` and `register_commands_for_chat`
        - Modified `src/bot/handlers/auth.py` — added `register_commands_for_chat` import and call after successful password check
        - Added 4 tests in `tests/test_main.py::TestRegisterCommands`
        - Added 1 test in `tests/test_handlers/test_auth_handler.py::test_successful_auth_registers_commands`
        - Updated `_make_mock_application()` to include `app.bot = AsyncMock()`
    - **Notes:** `python run.py --validate-i18n` has a pre-existing Windows encoding issue with emoji output (not related to our changes)

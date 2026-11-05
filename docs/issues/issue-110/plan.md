# Register Bot Commands with Telegram (`setMyCommands`) — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Register bot commands with Telegram's `setMyCommands` API so users see available commands in the "/" menu, with two tiers: a minimal set for unauthenticated users and the full set for authenticated users.

**Architecture:** A new `_register_commands()` method on `AddarrBot` builds command lists based on config-enabled services and calls `bot.set_my_commands()` with scope-based registration. Default scope gets the unauthenticated subset (`/start`, `/auth`, `/help`). Each already-authenticated user gets the full command list via `BotCommandScopeChatMember`. After successful authentication, `AuthHandler` also registers the full command set for the newly authenticated user.

**Tech Stack:** `telegram.BotCommand`, `telegram.BotCommandScopeDefault`, `telegram.BotCommandScopeChat` from python-telegram-bot v20+. Translation keys use flat top-level names (e.g., `CommandStart`) to work with the existing `TranslationService.get_text()` single-level lookup.

---

## Context

### Translation Key Convention

`TranslationService.get_text(key)` performs a single-level dict lookup: `translations[lang].get(key)`. Nested YAML keys (like `Sabnzbd.NotEnabled`) are NOT resolved by the current implementation — it returns the raw key string as fallback. To avoid this pre-existing issue, all new keys use flat top-level names: `CommandStart`, `CommandAuth`, etc.

### Service Enablement Checks

The established config patterns for checking if services are enabled:

```python
config.get("radarr", {}).get("enable")       # Radarr
config.get("sonarr", {}).get("enable")       # Sonarr
config.get("lidarr", {}).get("enable")       # Lidarr
config.get("transmission", {}).get("enable", False)  # Transmission
config.get("sabnzbd", {}).get("enable", False)       # SABnzbd
```

### Two-Tier Command Registration

| Tier | Scope | Commands |
|------|-------|----------|
| **Unauthenticated** | `BotCommandScopeDefault` | `/start`, `/auth`, `/help` |
| **Authenticated** | `BotCommandScopeChat(chat_id)` | All commands, filtered by enabled services |

**Authenticated commands (always):** `/start`, `/auth`, `/help`, `/status`, `/settings`, `/preferences`, `/delete`

**Authenticated commands (conditional):**
| Command | Condition |
|---------|-----------|
| `/movie` | `config.get("radarr", {}).get("enable")` |
| `/series` | `config.get("sonarr", {}).get("enable")` |
| `/music` | `config.get("lidarr", {}).get("enable")` |
| `/allMovies` | `config.get("radarr", {}).get("enable")` |
| `/allSeries` | `config.get("sonarr", {}).get("enable")` |
| `/allMusic` | `config.get("lidarr", {}).get("enable")` |
| `/transmission` | `config.get("transmission", {}).get("enable", False)` |
| `/sabnzbd` | `config.get("sabnzbd", {}).get("enable", False)` |

### Files to Modify

| File | Change |
|------|--------|
| `src/main.py` | Add `_build_authenticated_commands()`, `_register_commands()`, call in `initialize()` |
| `src/bot/handlers/auth.py` | After successful auth, call `set_my_commands` for the newly authenticated user's chat |
| `translations/addarr.en-us.yml` | Add `CommandStart`, `CommandAuth`, etc. keys |
| `translations/addarr.template.yml` | Add same keys as template |
| Other 8 locale files | Add same keys (English defaults; translators update later) |
| `tests/test_main.py` | Test `_build_authenticated_commands()` and `_register_commands()` |
| `tests/test_handlers/test_auth_handler.py` | Test that auth success triggers `set_my_commands` |

### Insertion Points

**`src/main.py`** — After `await self.application.initialize()` (line 79), before the success log:
```python
await self.application.initialize()
await self._register_commands()  # <-- INSERT
logger.info("🚀 Bot initialized successfully")
```

**`src/bot/handlers/auth.py`** — Inside `check_password()`, after adding user to authenticated set and saving (line 141-142), before the success log:
```python
AuthHandler._authenticated_users.add(user.id)
self._save_authenticated_users()
# Register full commands for this user's chat
await self._register_user_commands(chat.id, context.bot)  # <-- INSERT
```

---

## Phase 1: Translation Keys

Add command description translation keys to all locale files and template.

### New Translation Keys

```yaml
# Bot command descriptions (for Telegram /menu)
CommandStart: "Start the bot"
CommandAuth: "Authenticate with password"
CommandHelp: "Show available commands"
CommandStatus: "Check system status"
CommandSettings: "Manage bot settings"
CommandPreferences: "Manage preferences"
CommandDelete: "Delete media from library"
CommandMovie: "Search and add movies"
CommandSeries: "Search and add TV shows"
CommandMusic: "Search and add music"
CommandAllMovies: "List all movies"
CommandAllSeries: "List all series"
CommandAllMusic: "List all music"
CommandTransmission: "Manage Transmission"
CommandSabnzbd: "Manage SABnzbd"
```

---

## Phase 2: Command Registration in AddarrBot

### New Method: `_build_authenticated_commands()`

Returns the full `list[BotCommand]` for authenticated users, filtered by enabled services. Pure logic, no I/O — easy to test.

```python
def _build_authenticated_commands(self) -> list:
    from telegram import BotCommand
    translation = TranslationService()

    commands = [
        BotCommand("start", translation.get_text("CommandStart")),
        BotCommand("auth", translation.get_text("CommandAuth")),
        BotCommand("help", translation.get_text("CommandHelp")),
        BotCommand("status", translation.get_text("CommandStatus")),
        BotCommand("settings", translation.get_text("CommandSettings")),
        BotCommand("preferences", translation.get_text("CommandPreferences")),
        BotCommand("delete", translation.get_text("CommandDelete")),
    ]

    if config.get("radarr", {}).get("enable"):
        commands.append(BotCommand("movie", translation.get_text("CommandMovie")))
        commands.append(BotCommand("allmovies", translation.get_text("CommandAllMovies")))

    if config.get("sonarr", {}).get("enable"):
        commands.append(BotCommand("series", translation.get_text("CommandSeries")))
        commands.append(BotCommand("allseries", translation.get_text("CommandAllSeries")))

    if config.get("lidarr", {}).get("enable"):
        commands.append(BotCommand("music", translation.get_text("CommandMusic")))
        commands.append(BotCommand("allmusic", translation.get_text("CommandAllMusic")))

    if config.get("transmission", {}).get("enable", False):
        commands.append(BotCommand("transmission", translation.get_text("CommandTransmission")))

    if config.get("sabnzbd", {}).get("enable", False):
        commands.append(BotCommand("sabnzbd", translation.get_text("CommandSabnzbd")))

    return commands
```

**Note on command names:** Telegram requires command names to be lowercase. `/allMovies` is registered as a handler with mixed case, but for `setMyCommands` we use lowercase `allmovies`. Telegram's command matching is case-insensitive, so `/allMovies` typed by the user still works.

### New Method: `_register_commands()`

Sets default (unauthenticated) commands and per-user authenticated commands at startup.

```python
async def _register_commands(self) -> None:
    from telegram import BotCommand, BotCommandScopeDefault, BotCommandScopeChat

    translation = TranslationService()
    bot = self.application.bot

    # Default scope: unauthenticated users see minimal commands
    default_commands = [
        BotCommand("start", translation.get_text("CommandStart")),
        BotCommand("auth", translation.get_text("CommandAuth")),
        BotCommand("help", translation.get_text("CommandHelp")),
    ]
    await bot.set_my_commands(default_commands, scope=BotCommandScopeDefault())

    # Set full commands for already-authenticated users
    auth_commands = self._build_authenticated_commands()
    for user_id in AuthHandler._authenticated_users:
        try:
            await bot.set_my_commands(
                auth_commands, scope=BotCommandScopeChat(chat_id=user_id)
            )
        except Exception as e:
            logger.warning(f"Could not set commands for user {user_id}: {e}")
```

---

## Phase 3: Post-Auth Command Registration

### New Method on AuthHandler: `_register_user_commands()`

After successful password check, register the full command list for the newly authenticated user.

```python
@staticmethod
async def _register_user_commands(chat_id: int, bot) -> None:
    from telegram import BotCommand, BotCommandScopeChat
    from src.main import AddarrBot

    # Reuse the same command-building logic
    addarr_bot = AddarrBot.__new__(AddarrBot)
    commands = addarr_bot._build_authenticated_commands()
    try:
        await bot.set_my_commands(commands, scope=BotCommandScopeChat(chat_id=chat_id))
    except Exception as e:
        logger.warning(f"Could not register commands for chat {chat_id}: {e}")
```

**Circular import concern:** `AuthHandler` importing from `src.main` creates a circular dependency since `src/main.py` imports `AuthHandler`. Solution: use a lazy import inside the method body, or extract `_build_authenticated_commands` into a shared module.

**Better approach — extract to a shared function:** Create a module-level function `build_authenticated_commands()` in a new file `src/bot/commands.py` (or in `src/main.py` as a standalone function). Both `AddarrBot._register_commands()` and `AuthHandler._register_user_commands()` call it.

### Revised Architecture

**New file: `src/bot/commands.py`**

```python
from telegram import BotCommand
from src.config.settings import config
from src.services.translation import TranslationService


def build_default_commands() -> list:
    """Build command list for unauthenticated users."""
    translation = TranslationService()
    return [
        BotCommand("start", translation.get_text("CommandStart")),
        BotCommand("auth", translation.get_text("CommandAuth")),
        BotCommand("help", translation.get_text("CommandHelp")),
    ]


def build_authenticated_commands() -> list:
    """Build full command list for authenticated users, filtered by enabled services."""
    translation = TranslationService()

    commands = [
        BotCommand("start", translation.get_text("CommandStart")),
        BotCommand("auth", translation.get_text("CommandAuth")),
        BotCommand("help", translation.get_text("CommandHelp")),
        BotCommand("status", translation.get_text("CommandStatus")),
        BotCommand("settings", translation.get_text("CommandSettings")),
        BotCommand("preferences", translation.get_text("CommandPreferences")),
        BotCommand("delete", translation.get_text("CommandDelete")),
    ]

    if config.get("radarr", {}).get("enable"):
        commands.append(BotCommand("movie", translation.get_text("CommandMovie")))
        commands.append(BotCommand("allmovies", translation.get_text("CommandAllMovies")))

    if config.get("sonarr", {}).get("enable"):
        commands.append(BotCommand("series", translation.get_text("CommandSeries")))
        commands.append(BotCommand("allseries", translation.get_text("CommandAllSeries")))

    if config.get("lidarr", {}).get("enable"):
        commands.append(BotCommand("music", translation.get_text("CommandMusic")))
        commands.append(BotCommand("allmusic", translation.get_text("CommandAllMusic")))

    if config.get("transmission", {}).get("enable", False):
        commands.append(BotCommand("transmission", translation.get_text("CommandTransmission")))

    if config.get("sabnzbd", {}).get("enable", False):
        commands.append(BotCommand("sabnzbd", translation.get_text("CommandSabnzbd")))

    return commands


async def register_commands_for_chat(bot, chat_id: int) -> None:
    """Register authenticated commands for a specific chat."""
    from telegram import BotCommandScopeChat
    from src.utils.logger import get_logger

    logger = get_logger("addarr.commands")
    commands = build_authenticated_commands()
    try:
        await bot.set_my_commands(commands, scope=BotCommandScopeChat(chat_id=chat_id))
    except Exception as e:
        logger.warning(f"Could not set commands for chat {chat_id}: {e}")
```

This avoids circular imports entirely. Both `AddarrBot` and `AuthHandler` import from `src.bot.commands`.

---

## Phase 4: Tests

### Test file: `tests/test_bot/test_commands.py`

Tests for `build_default_commands()` and `build_authenticated_commands()`:

- `test_build_default_commands` — returns 3 commands: start, auth, help
- `test_build_authenticated_commands_all_enabled` — with all services enabled, returns all 15 commands
- `test_build_authenticated_commands_minimal` — with no optional services, returns 7 base commands
- `test_build_authenticated_commands_radarr_only` — enables only radarr, gets base + movie + allmovies
- `test_build_authenticated_commands_sonarr_only` — enables only sonarr, gets base + series + allseries
- `test_build_authenticated_commands_lidarr_only` — enables only lidarr, gets base + music + allmusic
- `test_build_authenticated_commands_transmission_only` — enables only transmission, gets base + transmission
- `test_build_authenticated_commands_sabnzbd_only` — enables only sabnzbd, gets base + sabnzbd
- `test_register_commands_for_chat` — mocks bot, verifies `set_my_commands` called with correct scope
- `test_register_commands_for_chat_error_handling` — bot raises exception, function doesn't propagate

### Test file: `tests/test_main.py` (additions)

- `test_register_commands_called_during_initialize` — verify `_register_commands` is called after `application.initialize()`
- `test_register_commands_sets_default_and_per_user` — mock `AuthHandler._authenticated_users` with 2 users, verify `set_my_commands` called 3 times (1 default + 2 per-user)

### Test file: `tests/test_handlers/test_auth_handler.py` (additions)

- `test_successful_auth_registers_commands` — after password check succeeds, verify `register_commands_for_chat` was called with the chat ID and bot

---

## Verification

1. `pytest --tb=short -q` — all tests pass
2. `flake8 .` — no lint errors
3. `python run.py --validate-i18n` — translation validation passes
4. Manual: start the bot, check "/" menu shows only start/auth/help before authenticating, then full commands after auth

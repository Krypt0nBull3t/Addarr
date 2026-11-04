# Wiring a New Handler

## Step 1: Define States

Add new states to `src/bot/states.py`:

```python
class States:
    # Existing states...
    SEARCHING = 1
    SELECTING = 2

    # New states (use unique values)
    <FEATURE>_MENU = "<feature>_menu"
    <FEATURE>_ACTION = "<feature>_action"
```

**Convention:**
- Media flow states: integers `1` to `5` (`SEARCHING` to `ALBUM_SELECT`); auth uses `PASSWORD = 0`
- Other flow states: descriptive strings (`"settings_menu"`, `"<feature>_menu"`)
- Never reuse state values across different ConversationHandlers

## Step 2: Add Translation Keys

Add keys with `@i18n-key` (template plus all 9 locales). It covers key naming, `%{name}` placeholders and validation.

## Step 3: Register in main.py

Add to `src/main.py:AddarrBot._add_handlers()`:

```python
def _add_handlers(self):
    # ... existing handlers in order ...

    # Add new handler (respect registration order)
    <feature>_handler = <Feature>Handler()
    for handler in <feature>_handler.get_handler():
        self.application.add_handler(handler)
```

**Registration order matters.** PTB matches the first matching handler. Current order (from `src/main.py:_add_handlers()`):

1. AuthHandler
2. MediaHandler
3. SettingsHandler
4. WebhooksHandler
5. DeleteHandler
6. LibraryHandler
7. CalendarHandler
8. MissingHandler
9. QueueHandler
10. HistoryHandler
11. TransmissionHandler *(conditional on transmission.enable)*
12. SabnzbdHandler *(conditional on sabnzbd.enable)*
13. BazarrHandler *(conditional on bazarr.enable)*
14. DownloadsHandler
15. HelpHandler
16. PreferencesHandler
17. SystemHandler
18. StartHandler *(last: its `menu_cancel` must not take Cancel taps from an open conversation)*

**Placement rules:**
- Handlers with unique command names (`/<feature>`) can go anywhere
- Handlers that share callback prefixes with existing handlers must go after the handler that should take priority
- Conditional handlers (config-gated) follow this pattern:

```python
if config.get("<service>", {}).get("enable", False):
    <feature>_handler = <Feature>Handler()
    for handler in <feature>_handler.get_handler():
        self.application.add_handler(handler)
```

## Step 4: Import in main.py

Add the import at the top of `src/main.py`. It imports every handler from its own module, not from `src/bot/handlers/__init__.py`:

```python
from src.bot.handlers.<feature> import <Feature>Handler
```

## Conversation Flow Design

```
Entry: /command or callback_data match
       ↓
State 1: Show prompt, wait for input
       ↓
State 2: Process input, show results
       ↓
State 3: Confirm action
       ↓
ConversationHandler.END
```

Each state transition returns the next state constant. Every path must eventually reach `ConversationHandler.END` (including error paths).

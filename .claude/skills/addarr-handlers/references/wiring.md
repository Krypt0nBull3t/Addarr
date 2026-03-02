# Wiring a New Handler

## Step 1: Define States

Add new states to `src/bot/states.py`:

```python
class States:
    # Existing states...
    SEARCHING = 1
    SELECTING = 2

    # New states (use unique values)
    MY_FEATURE_MENU = "my_feature_menu"
    MY_FEATURE_ACTION = "my_feature_action"
```

**Convention:**
- Media flow states: integers (`1, 2, 3, 4`)
- Other flow states: descriptive strings (`"settings_menu"`, `"my_feature_menu"`)
- Never reuse state values across different ConversationHandlers

## Step 2: Add Translation Keys

Add to all `translations/addarr.*.yml` files. At minimum, `addarr.en-us.yml`:

```yaml
en-us:
  # PascalCase for simple terms
  MyFeature: "My Feature"
  MyFeaturePrompt: "🔍 Choose an option:"

  # Dotted path for nested context
  MyFeature.Success: "✅ Done!"
  MyFeature.Error: "❌ Something went wrong"

  # Variable interpolation with %{name}
  MyFeature.Added: "Added %{title} successfully"
```

**Naming rules:**
- PascalCase for keys: `MyFeature`, `SearchResults`
- Dotted paths for grouping: `Settings.LanguageChanged`
- Variables: `%{variable_name}`
- Emojis in the value, not the key

## Step 3: Export Handler

Add to `src/bot/handlers/__init__.py`:

```python
from .my_feature import MyFeatureHandler

__all__ = [
    # existing...
    "MyFeatureHandler",
]
```

## Step 4: Register in main.py

Add to `src/main.py:AddarrBot._add_handlers()`:

```python
def _add_handlers(self):
    # ... existing handlers in order ...

    # Add new handler (respect registration order)
    my_feature = MyFeatureHandler()
    for handler in my_feature.get_handler():
        self.application.add_handler(handler)
```

**Registration order matters.** PTB matches the first matching handler. Current order:

1. StartHandler
2. AuthHandler
3. MediaHandler
4. SettingsHandler
5. DeleteHandler
6. LibraryHandler
7. TransmissionHandler *(conditional)*
8. SabnzbdHandler *(conditional)*
9. HelpHandler
10. PreferencesHandler
11. SystemHandler

**Placement rules:**
- Handlers with unique command names (`/myfeature`) can go anywhere
- Handlers that share callback prefixes with existing handlers must go after the handler that should take priority
- Conditional handlers (config-gated) follow this pattern:

```python
if config.get("my_service", {}).get("enable", False):
    my_feature = MyFeatureHandler()
    for handler in my_feature.get_handler():
        self.application.add_handler(handler)
```

## Step 5: Import in main.py

Add the import at the top of `src/main.py`:

```python
from src.bot.handlers.my_feature import MyFeatureHandler
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

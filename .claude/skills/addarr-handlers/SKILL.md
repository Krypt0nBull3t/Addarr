---
name: addarr-handlers
description: Use when adding new Telegram bot handlers, conversation flows, callback routing, keyboards, or command handlers in Addarr. Covers handler class structure, ConversationHandler states, callback_data conventions, and keyboard construction.
---

# Addarr Handlers

Reference for building new Telegram bot handlers in Addarr. For testing handler code, see @addarr-testing.

## Quick Start Checklist

When adding a new handler:

1. Create handler class in `src/bot/handlers/<name>.py`
2. Define any new states in `src/bot/states.py`
3. Add keyboard functions to `src/bot/keyboards.py`
4. Add keys with `@i18n-key` (template plus all 9 locales)
5. Import it from its own module in `src/main.py` and register it in `AddarrBot._add_handlers()`

## Handler Class Template

```python
from telegram.ext import (
    CommandHandler, CallbackQueryHandler, ConversationHandler
)

from src.utils.logger import get_logger
from src.services.<service> import <Service>Service
from src.services.translation import TranslationService
from src.bot.states import States

logger = get_logger("addarr.<name>")


class <Name>Handler:
    """Handler for <description>"""

    def __init__(self):
        self.translation = TranslationService()
        self.<service> = <Service>Service()

    def get_handler(self):
        """Return list of handlers to register"""
        return [
            ConversationHandler(
                entry_points=[
                    CommandHandler("<cmd>", self.handle_<cmd>),
                    CallbackQueryHandler(self.handle_<action>, pattern="^<prefix>_"),
                ],
                states={
                    States.<STATE>: [
                        CallbackQueryHandler(
                            self.handle_<action>,
                            pattern="^<prefix>_"
                        ),
                    ],
                },
                fallbacks=[
                    CommandHandler("cancel", self.handle_cancel),
                    CallbackQueryHandler(self.handle_cancel, pattern="^menu_cancel$"),
                ],
                name="<name>_conversation",
                persistent=False,
                per_message=False,
            ),
        ]
```

**Critical:**
- `get_handler()` returns a **list** (even for a single handler)
- `persistent=False` and `per_message=False` are the PTB defaults. Most handlers spell them out; `AuthHandler` omits `persistent` and `BazarrHandler` omits both
- Fallbacks route the cancel callback your keyboards send (`menu_cancel` here; see [references/keyboards.md](references/keyboards.md))
- Services injected as singletons in `__init__`
- Add `Update`, `ContextTypes`, `require_auth` and the other imports with the methods that use them ([references/methods.md](references/methods.md))

## Method Signatures

See [references/methods.md](references/methods.md) for entry point, callback, message, and cancel handler patterns with `@require_auth`, `await query.answer()`, and state return conventions.

## Callback Data Conventions

See [references/callbacks.md](references/callbacks.md) for naming format, extraction patterns, and the complete prefix registry.

## Keyboard Construction

See [references/keyboards.md](references/keyboards.md) for keyboard function patterns, button layout, translation integration, and photo-aware message editing.

## Wiring a New Handler

See [references/wiring.md](references/wiring.md) for state definitions, translation keys, handler registration order, and the import in `src/main.py`.

## Common Mistakes

See [references/anti-patterns.md](references/anti-patterns.md) for detailed examples with bad/good code.

1. Forgetting `await query.answer()` — Telegram shows loading spinner indefinitely.
2. Using `reply_text` on callback queries — Use `edit_text` or `edit_caption` instead.
3. Forgetting photo-aware editing — `edit_text` crashes on photo messages, use `edit_caption`.
4. Missing state return — Every handler method must return a state or `ConversationHandler.END`.
5. Not clearing `context.user_data` on cancel — Stale data leaks into next conversation.
6. Wrong pattern anchor — `^prefix_$` won't match `prefix_42`; `^exact` matches `exact_extra`.
7. Registering handlers in wrong order — PTB matches first match. Specific patterns before general.
8. Forgetting `@require_auth` on entry points. All entry points need the auth decorator, including standalone callback handlers.
9. Ignoring `per_message=False` warning — It's informational, not an error. Safe to ignore.

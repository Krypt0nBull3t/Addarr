# Handler Method Patterns

## Entry Point (Command Handler)

```python
@require_auth
async def handle_<command>(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the <feature> flow"""
    if not update.effective_message or not update.effective_user:
        return ConversationHandler.END

    log_user_interaction(logger, update.effective_user, "/<command>")

    # Initialize conversation state
    context.user_data["<key>"] = value

    await update.effective_message.reply_text(
        text=self.translation.get_text("PromptKey"),
        reply_markup=get_<name>_keyboard()
    )
    return States.<NEXT_STATE>
```

**Rules:**
- Always decorate with `@require_auth`
- Guard with `if not update.effective_message or not update.effective_user`
- Log via `log_user_interaction(logger, update.effective_user, "/<cmd>")`
- Return next state constant

## Callback Handler

```python
@require_auth  # needed when registered outside a conversation's states
async def handle_<action>(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle <action> callback"""
    if not update.callback_query:
        return ConversationHandler.END

    query = update.callback_query
    await query.answer()  # ALWAYS acknowledge first

    # Extract data from callback
    value = query.data.replace("<prefix>_", "")

    # Business logic...
    result = await self.<service>.<action>(value)

    # Update message
    await query.edit_message_text(
        text=f"Result: {result}",
        reply_markup=get_<feature>_keyboard()
    )
    return States.<NEXT_STATE>
```

**Rules:**
- Decorate with `@require_auth` when the callback is registered outside a conversation's `states`: a standalone `CallbackQueryHandler` or a `ConversationHandler` entry point. Callbacks inside `states` are reached only after an authenticated entry point
- Always `await query.answer()` before any other logic
- Edit with `query.edit_message_text`, not `query.message.edit_text`: PTB types `CallbackQuery.message` as `MaybeInaccessibleMessage`
- Extract data by stripping prefix: `query.data.replace("prefix_", "")`
- For multi-part data: `parts = query.data.split("_")`
- Edit existing message, don't send new one

## Photo-Aware Message Editing

When a message might have an image (e.g., media cards), use `send_response` from `src/bot/handlers/media/formatters.py`:

```python
from src.bot.handlers.media.formatters import send_response

await send_response(query.message, text, reply_markup)
```

It edits the caption of a photo message and the text of any other message. If the edit fails, it logs the error and sends the text as a new reply.

## Message Handler (Text Input)

```python
async def handle_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text search input"""
    if not update.effective_message:
        return ConversationHandler.END

    query_text = update.message.text
    search_type = context.user_data.get("search_type")

    # Perform search
    results = await self.media_service.search(search_type, query_text)

    if not results:
        await update.effective_message.reply_text(
            self.translation.get_text(
                "SearchNoResults", search_type=search_type, query=query_text
            )
        )
        return ConversationHandler.END

    # Store results and show first
    context.user_data["search_results"] = results
    context.user_data["current_index"] = 0
    # ... show results
    return States.SELECTING
```

## Cancel Handler

```python
async def handle_cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel current conversation"""
    context.user_data.clear()

    if update.callback_query:
        await update.callback_query.answer()
        await send_response(
            update.callback_query.message, self.translation.get_text("Cancel")
        )
    elif update.effective_message:
        await update.effective_message.reply_text(
            self.translation.get_text("Cancel")
        )
    return ConversationHandler.END
```

**Rules:**
- Always clear `context.user_data`
- Handle both callback and text message cancellation
- Return `ConversationHandler.END`

## Decorator Stack

Stack the access decorators in this order, as `DeleteHandler.handle_delete` in `src/bot/handlers/delete.py` does:

```python
from src.bot.handlers.auth import require_admin, require_auth
from src.services.rate_limit import rate_limit


@require_auth
@require_admin()
@rate_limit("modify")
async def handle_<command>(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    ...
```

1. `@require_auth` refuses users who are not authenticated or not on the allowlist, and group chats when `security.chatMode` is `private_only`.
2. `@require_admin(...)` (in `src/bot/handlers/auth.py`) refuses non-admins when `security.enableAdmin` is on. With a service name, such as `@require_admin("transmission")`, it refuses them only when that service's `onlyAdmin` is also set.
3. `@rate_limit("<category>")` (in `src/services/rate_limit.py`) limits each user per category: `search`, `modify` or `auth`. It applies only when `rateLimit.enable` is set, except `auth`, which always applies.

Rate limiting goes last, so a call that auth or admin refuses does not count against the user's limit.

## Admin-Only Checks

Use `@require_admin(...)` from the decorator stack above. Do not check `security.enableAdmin` by hand.

## Context User Data

```python
# Store during conversation
context.user_data["search_type"] = "movie"
context.user_data["search_results"] = results
context.user_data["current_index"] = 0
context.user_data["selected_media"] = item

# Retrieve with defaults
results = context.user_data.get("search_results", [])
index = context.user_data.get("current_index", 0)

# Clear on cancel/end
context.user_data.clear()
```

## Translation Access

```python
# Simple key lookup
text = self.translation.get_text("Title")

# With default fallback
text = self.translation.get_text("Settings.LanguageChanged",
    default=f"Language changed to {lang}", language=lang)

# With template variables
text = self.translation.get_text("LibraryEmpty", subject="movies")
```

## Logging

```python
from src.utils.logger import get_logger, log_user_interaction

logger = get_logger("addarr.<module_name>")

# In handler methods
log_user_interaction(logger, update.effective_user, "/movie")
log_user_interaction(logger, update.effective_user, "search_movie", query)

# Standard
logger.info("Message")
logger.error(f"Error: {e}")
logger.warning("Warning")
```

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
async def handle_<action>(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle <action> callback"""
    if not update.callback_query:
        return ConversationHandler.END

    query = update.callback_query
    await query.answer()  # ALWAYS acknowledge first

    # Extract data from callback
    action = query.data.replace("<prefix>_", "")

    # Business logic...
    result = await self.<service>.do_something(action)

    # Update message
    await query.message.edit_text(
        text=f"Result: {result}",
        reply_markup=get_next_keyboard()
    )
    return States.<NEXT_STATE>
```

**Rules:**
- Always `await query.answer()` before any other logic
- Extract data by stripping prefix: `query.data.replace("prefix_", "")`
- For multi-part data: `parts = query.data.split("_")`
- Edit existing message, don't send new one

## Photo-Aware Message Editing

When a message might have an image (e.g., media cards):

```python
if query.message.photo:
    await query.message.edit_caption(
        caption=text,
        reply_markup=reply_markup
    )
else:
    await query.message.edit_text(
        text=text,
        reply_markup=reply_markup
    )
```

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
            self.translation.get_text("NoResults")
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
        await update.callback_query.message.edit_text(
            self.translation.get_text("Cancel")
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

## Admin-Only Checks

```python
if config.get("security", {}).get("enableAdmin", False):
    if update.effective_user.id not in config.get("admins", []):
        await update.effective_message.reply_text("Access restricted.")
        return ConversationHandler.END
```

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
    default=f"Language changed to {lang}")

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

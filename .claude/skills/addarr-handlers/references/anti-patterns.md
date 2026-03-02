# Handler Anti-Patterns

Common mistakes when building Telegram bot handlers in Addarr.

---

## Missing `await query.answer()`

**Don't** process a callback query without acknowledging it:

```python
# BAD - Telegram shows loading spinner indefinitely
async def handle_action(self, update, context):
    query = update.callback_query
    action = query.data.replace("prefix_", "")
    await query.message.edit_text("Done!")
```

**Instead**, always acknowledge first:

```python
# GOOD
async def handle_action(self, update, context):
    query = update.callback_query
    await query.answer()  # Always first
    action = query.data.replace("prefix_", "")
    await query.message.edit_text("Done!")
```

**Why**: Telegram requires callback queries to be answered within a timeout. Without `answer()`, users see a perpetual loading spinner on the button.

---

## Using reply_text on Callback Updates

**Don't** call `reply_text` when handling callback queries:

```python
# BAD - sends a new message instead of updating the existing one
async def handle_callback(self, update, context):
    query = update.callback_query
    await query.answer()
    await update.effective_message.reply_text("Result")
```

**Instead**, edit the existing message:

```python
# GOOD - updates the message in-place
async def handle_callback(self, update, context):
    query = update.callback_query
    await query.answer()
    await query.message.edit_text("Result", reply_markup=keyboard)
```

**Why**: Callback queries come from inline keyboard button presses. The user expects the message to update, not a new message to appear. Use `edit_text` or `edit_caption` (for photo messages).

---

## Forgetting Photo-Aware Editing

**Don't** always use `edit_text` when editing messages that might have photos:

```python
# BAD - crashes with BadRequest if message has a photo
await query.message.edit_text(text=new_text, reply_markup=keyboard)
```

**Instead**, check for photos:

```python
# GOOD
if query.message.photo:
    await query.message.edit_caption(caption=new_text, reply_markup=keyboard)
else:
    await query.message.edit_text(text=new_text, reply_markup=keyboard)
```

**Why**: Messages with images use `caption` not `text`. Calling `edit_text` on a photo message raises `telegram.error.BadRequest`. The media handler's card view sends photos, so any handler that edits those messages must handle both cases.

---

## Missing State Return

**Don't** let handler methods fall through without returning a state:

```python
# BAD - returns None implicitly, breaks ConversationHandler
async def handle_search(self, update, context):
    results = await self.service.search(query)
    if results:
        await update.message.reply_text("Found!")
        # Forgot to return next state!
```

**Instead**, always return explicitly on every path:

```python
# GOOD
async def handle_search(self, update, context):
    results = await self.service.search(query)
    if results:
        context.user_data["results"] = results
        await update.message.reply_text("Found!")
        return States.SELECTING
    await update.message.reply_text("Nothing found.")
    return ConversationHandler.END
```

**Why**: ConversationHandler uses the return value to determine the next state. Returning `None` keeps the conversation in the current state, which can cause handlers to fire on unexpected input.

---

## Not Clearing user_data on Cancel

**Don't** end a conversation without cleaning up:

```python
# BAD - stale data from previous conversation leaks into next one
async def handle_cancel(self, update, context):
    await update.effective_message.reply_text("Cancelled.")
    return ConversationHandler.END
```

**Instead**, clear user_data:

```python
# GOOD
async def handle_cancel(self, update, context):
    context.user_data.clear()
    await update.effective_message.reply_text("Cancelled.")
    return ConversationHandler.END
```

**Why**: `context.user_data` persists across conversations for the same user. If the user starts a movie search, cancels, then starts a series search, stale `search_type`, `search_results`, etc. from the movie flow will be present unless cleared.

---

## Wrong Pattern Anchor

**Don't** use exact-match anchors on prefix patterns or forget them on exact matches:

```python
# BAD - won't match "select_42" because $ requires exact "select_"
CallbackQueryHandler(handler, pattern="^select_$")

# BAD - matches "menu_cancel_extra" when you only want "menu_cancel"
CallbackQueryHandler(handler, pattern="^menu_cancel")
```

**Instead**, use anchors intentionally:

```python
# GOOD - prefix match (captures select_0, select_42, etc.)
CallbackQueryHandler(handler, pattern="^select_")

# GOOD - exact match
CallbackQueryHandler(handler, pattern="^menu_cancel$")
```

**Why**: PTB uses regex matching. `^prefix_` matches anything starting with `prefix_`. `^exact_value$` matches only that exact string. Mixing these up causes handlers to either miss valid callbacks or fire on unintended ones.

---

## Registering Handlers in Wrong Order

**Don't** register a general pattern before a specific one:

```python
# BAD - "^dl_" matches "dl_sab_speed" before the specific handler sees it
states={
    STATE: [
        CallbackQueryHandler(handle_downloads, pattern="^dl_"),
        CallbackQueryHandler(handle_sab_speed, pattern="^dl_sab_speed"),
    ]
}
```

**Instead**, put specific patterns first:

```python
# GOOD - specific pattern checked first
states={
    STATE: [
        CallbackQueryHandler(handle_sab_speed, pattern="^dl_sab_speed"),
        CallbackQueryHandler(handle_downloads, pattern="^dl_"),
    ]
}
```

**Why**: PTB tries handlers top-to-bottom within a state dict. The first matching handler wins. This also applies to handler registration order in `_add_handlers()` — more specific handlers must come before general ones. Issue #67 learned this with settings sub-menus.

---

## Forgetting @require_auth on Entry Points

**Don't** create unprotected entry points:

```python
# BAD - anyone can trigger this, bypassing authentication
async def handle_command(self, update, context):
    await update.message.reply_text("Welcome!")
```

**Instead**, decorate all entry points:

```python
# GOOD
@require_auth
async def handle_command(self, update, context):
    await update.message.reply_text("Welcome!")
```

**Why**: `@require_auth` checks if the user's ID is in the authenticated users set. Without it, unauthenticated users can access bot features. Note: `@require_auth` accesses `update.message.reply_text()` which only works for command handlers and message handlers, not bare callback queries from unauthenticated sessions.

---

## per_message=False Warning

**Don't** worry about the `PTBUserWarning` when using `per_message=False` with `CallbackQueryHandler`:

```python
# This emits a PTBUserWarning - it's informational, NOT an error
ConversationHandler(
    ...,
    per_message=False,  # Correct setting
)
```

**Why**: PTB warns because `per_message=False` means callback queries from different messages can be handled by the same conversation. This is the intended behavior in Addarr — the warning confirms the setting is active. Issue #67 confirmed this is safe to ignore.

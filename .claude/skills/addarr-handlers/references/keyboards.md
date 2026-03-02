# Keyboard Patterns

## Keyboard Function Convention

All keyboard functions live in `src/bot/keyboards.py`. Named `get_<feature>_keyboard()`.

```python
def get_<feature>_keyboard(<params>) -> InlineKeyboardMarkup:
    """Get keyboard for <feature>"""
    translation = TranslationService()
    keyboard = [
        [  # Row 1
            InlineKeyboardButton(
                f"🎬 {translation.get_text('Movie')}",
                callback_data="prefix_value"
            ),
            InlineKeyboardButton(
                f"📺 {translation.get_text('Series')}",
                callback_data="prefix_value2"
            ),
        ],
        [  # Row 2 (cancel)
            InlineKeyboardButton(
                f"❌ {translation.get_text('Cancel')}",
                callback_data="menu_cancel"
            ),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)
```

**Rules:**
- Each function creates its own `TranslationService()` instance
- Emojis go in the button text, NOT in translation keys
- Format: `f"<emoji> {translation.get_text('Key')}"`
- Cancel button always uses `callback_data="menu_cancel"`
- Return `InlineKeyboardMarkup(keyboard)`

## Dynamic Keyboard (From Data)

```python
def get_quality_keyboard(profiles: List[Dict]) -> InlineKeyboardMarkup:
    """Build keyboard from quality profiles"""
    translation = TranslationService()
    keyboard = []

    for profile in profiles:
        keyboard.append([
            InlineKeyboardButton(
                profile["name"],
                callback_data=f"quality_{profile['id']}"
            )
        ])

    # Always add cancel row
    keyboard.append([
        InlineKeyboardButton(
            f"❌ {translation.get_text('Cancel')}",
            callback_data="menu_cancel"
        )
    ])
    return InlineKeyboardMarkup(keyboard)
```

## Navigation Keyboard (Prev/Next)

```python
def get_navigation_keyboard(current_index: int, total: int) -> InlineKeyboardMarkup:
    """Keyboard with prev/next and action buttons"""
    translation = TranslationService()
    nav_row = []

    if current_index > 0:
        nav_row.append(InlineKeyboardButton(
            "⬅️", callback_data=f"nav_prev_{current_index - 1}"
        ))
    nav_row.append(InlineKeyboardButton(
        f"{current_index + 1}/{total}", callback_data="nav_noop"
    ))
    if current_index < total - 1:
        nav_row.append(InlineKeyboardButton(
            "➡️", callback_data=f"nav_next_{current_index + 1}"
        ))

    keyboard = [
        nav_row,
        [InlineKeyboardButton(
            f"✅ {translation.get_text('Add')}",
            callback_data=f"select_{current_index}"
        )],
        [InlineKeyboardButton(
            f"❌ {translation.get_text('Cancel')}",
            callback_data="menu_cancel"
        )],
    ]
    return InlineKeyboardMarkup(keyboard)
```

## Inline Handler Keyboard (No keyboards.py Function)

For simple one-off keyboards, build inline in the handler:

```python
async def handle_confirm(self, update, context):
    keyboard = [
        [
            InlineKeyboardButton("✅ Yes", callback_data="confirm_yes"),
            InlineKeyboardButton("❌ No", callback_data="confirm_no"),
        ]
    ]
    await query.message.edit_text(
        text="Are you sure?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
```

Use this only for simple yes/no or one-time keyboards. Reusable keyboards go in `keyboards.py`.

## Button Layout Guidelines

- **1 button per row**: Primary actions, selections from lists
- **2 buttons per row**: Binary choices (yes/no, confirm/cancel)
- **2-3 buttons per row**: Menu options with short labels
- **Navigation row**: Always `[⬅️] [N/M] [➡️]` format
- **Cancel button**: Always last row, always alone

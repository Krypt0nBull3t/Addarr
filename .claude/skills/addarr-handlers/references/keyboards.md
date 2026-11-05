# Keyboard Patterns

## Keyboard Function Convention

Reusable keyboard functions live in `src/bot/keyboards.py`, named `get_<feature>_keyboard()`. Some keyboards are built next to their handler instead:

- Card navigation and select buttons: `show_result` in `src/bot/handlers/media/formatters.py`
- Season buttons: `handle_season_selection` in `src/bot/handlers/media/season_picker.py`
- Delete buttons: `DeleteHandler.get_delete_keyboard` in `src/bot/handlers/delete.py`

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
- Cancel button: `callback_data="menu_cancel"` only inside a conversation whose states or fallbacks route `menu_cancel`. Otherwise give the flow its own `<prefix>_cancel` and route it (`select_cancel` in the media result views, `bazarr_cancel` in `BazarrHandler`)
- Return `InlineKeyboardMarkup(keyboard)`

## Dynamic Keyboard (From Data)

Build one row per item. `get_quality_profile_keyboard` in `src/bot/keyboards.py`:

```python
def get_quality_profile_keyboard(
    profiles: list, service: str,
    current_profile_id: Optional[int] = None,
) -> InlineKeyboardMarkup:
    """Get quality profile selection keyboard"""
    keyboard = []
    for profile in profiles:
        prefix = "✅ " if profile["id"] == current_profile_id else ""
        keyboard.append([
            InlineKeyboardButton(
                f"{prefix}{profile['name']}",
                callback_data=f"setquality_{service}_{profile['id']}"
            )
        ])
    translation = TranslationService()
    keyboard.append([
        InlineKeyboardButton(
            f"◀️ {translation.get_text('Back')}",
            callback_data="settings_back"
        )
    ])
    return InlineKeyboardMarkup(keyboard)
```

## Navigation Keyboards

Copy one of the two existing shapes:

- **Card navigation**: `show_result` in `src/bot/handlers/media/formatters.py`. Previous sends `nav_prev_{index}` and Next sends `nav_next_{index}`, each shown only when there is a result in that direction. Below them, Add to Library sends `select_{result['id']}` and Cancel sends `select_cancel`. There is no counter button.
- **Paginator**: `get_calendar_items_keyboard` in `src/bot/keyboards.py` (the missing, queue, history and downloads keyboards follow it). Its page row is prev, `N/M`, next. The `N/M` button sends `cal_noop`, which the handler only answers.

## Yes/No Keyboard

Use `get_yes_no_keyboard(callback_prefix, yes_text, no_text)` from `src/bot/keyboards.py`. It sends `<prefix>_yes` and `<prefix>_no`:

```python
from src.bot.keyboards import get_yes_no_keyboard


async def handle_confirm(self, update, context):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        text="Are you sure?",
        reply_markup=get_yes_no_keyboard("<prefix>", "✅ Yes", "❌ No"),
    )
```

Other one-off keyboards can stay in the handler module, as `DeleteHandler.get_delete_keyboard` does. Reusable keyboards go in `keyboards.py`.

## Button Layout Guidelines

- **1 button per row**: Primary actions, selections from lists
- **2 buttons per row**: Binary choices (yes/no, confirm/cancel)
- **2-3 buttons per row**: Menu options with short labels
- **Paginator row**: prev, `N/M`, next (card navigation has no `N/M` button)
- **Cancel button**: Always last row, always alone

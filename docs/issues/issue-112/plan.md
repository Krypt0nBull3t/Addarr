# Library Shortcut in Main Menu — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a "Library" button to the main menu that opens a sub-menu for browsing Movies, Series, or Music libraries, routing to the existing `LibraryHandler`.

**Architecture:** The main menu keyboard gets a new "Library" button. When pressed, `StartHandler` shows a library sub-menu keyboard with options for each enabled media type plus a Back button. Each sub-menu option dispatches to the existing `LibraryHandler._fetch_and_show()` method. The sub-menu ends the start conversation so LibraryHandler's own `CallbackQueryHandler` can handle pagination.

**Tech Stack:** python-telegram-bot v20+, async Python, existing keyboards/handler patterns.

---

## Task 1: Add translation keys to all locale files

**Files:**
- Modify: `translations/addarr.en-us.yml:37` (after Library listing section)
- Modify: `translations/addarr.de-de.yml` (same location)
- Modify: `translations/addarr.es-es.yml`
- Modify: `translations/addarr.fr-fr.yml`
- Modify: `translations/addarr.it-it.yml`
- Modify: `translations/addarr.nl-be.yml`
- Modify: `translations/addarr.pl-pl.yml`
- Modify: `translations/addarr.pt-pt.yml`
- Modify: `translations/addarr.ru-ru.yml`
- Modify: `translations/addarr.template.yml`

**What to add (2 new keys, insert after `LibraryExpired` line in each file):**

```yaml
  Library: "Library"
  LibraryPrompt: "Select a library to browse:"
```

Translate the values for each locale. Keep keys identical across all files.

**Verification:** Run `PYTHONIOENCODING=utf-8 python run.py --validate-i18n` — should pass with no missing keys.

---

## Task 2: Add `get_library_menu_keyboard()` to keyboards.py

**Files:**
- Modify: `src/bot/keyboards.py:20-71` (add new function after `get_main_menu_keyboard`)
- Test: `tests/test_bot/test_keyboards.py`

### Step 1: Write failing test

Add to `tests/test_bot/test_keyboards.py`:

```python
from src.bot.keyboards import get_library_menu_keyboard

class TestLibraryMenuKeyboard:
    """Tests for get_library_menu_keyboard"""

    @patch("src.bot.keyboards.TranslationService")
    def test_library_menu_returns_markup(self, mock_ts):
        """Returns InlineKeyboardMarkup"""
        _mock_translation(mock_ts)
        result = get_library_menu_keyboard()
        assert isinstance(result, InlineKeyboardMarkup)

    @patch("src.bot.keyboards.TranslationService")
    def test_library_menu_has_media_buttons(self, mock_ts):
        """Contains movie, series, music library buttons"""
        _mock_translation(mock_ts)
        result = get_library_menu_keyboard()
        callbacks = [
            btn.callback_data
            for row in result.inline_keyboard for btn in row
        ]
        assert "library_movie" in callbacks
        assert "library_series" in callbacks
        assert "library_music" in callbacks

    @patch("src.bot.keyboards.TranslationService")
    def test_library_menu_has_back_button(self, mock_ts):
        """Contains back button to return to main menu"""
        _mock_translation(mock_ts)
        result = get_library_menu_keyboard()
        callbacks = [
            btn.callback_data
            for row in result.inline_keyboard for btn in row
        ]
        assert "menu_back" in callbacks
```

### Step 2: Run test to verify it fails

Run: `python -m pytest tests/test_bot/test_keyboards.py::TestLibraryMenuKeyboard -v`
Expected: FAIL with ImportError (function doesn't exist yet)

### Step 3: Write implementation

Add to `src/bot/keyboards.py` after `get_main_menu_keyboard()`:

```python
def get_library_menu_keyboard() -> InlineKeyboardMarkup:
    """Get the library sub-menu keyboard"""
    translation = TranslationService()
    keyboard = [
        [
            InlineKeyboardButton(
                f"\U0001f3ac {translation.get_text('Movie')}",
                callback_data="library_movie"
            ),
            InlineKeyboardButton(
                f"\U0001f4fa {translation.get_text('Series')}",
                callback_data="library_series"
            ),
        ],
        [
            InlineKeyboardButton(
                f"\U0001f3b5 {translation.get_text('Music')}",
                callback_data="library_music"
            ),
        ],
        [
            InlineKeyboardButton(
                f"\u25c0\ufe0f {translation.get_text('Back')}",
                callback_data="menu_back"
            ),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)
```

### Step 4: Run test to verify it passes

Run: `python -m pytest tests/test_bot/test_keyboards.py::TestLibraryMenuKeyboard -v`
Expected: PASS

---

## Task 3: Add "Library" button to main menu keyboard

**Files:**
- Modify: `src/bot/keyboards.py:20-71` (add Library row)
- Modify: `tests/test_bot/test_keyboards.py` (update existing test)

### Step 1: Update existing test

In `tests/test_bot/test_keyboards.py`, class `TestMainMenuKeyboard`, method `test_main_menu_keyboard_structure`, add `"menu_library"` to the `expected` list:

```python
        expected = [
            "menu_movie",
            "menu_series",
            "menu_music",
            "menu_status",
            "menu_upcoming",
            "menu_delete",
            "menu_library",   # <-- ADD THIS
            "menu_help",
            "menu_cancel",
        ]
```

### Step 2: Run test to verify it fails

Run: `python -m pytest tests/test_bot/test_keyboards.py::TestMainMenuKeyboard -v`
Expected: FAIL — `menu_library` not found

### Step 3: Add Library button to main menu

In `src/bot/keyboards.py`, in `get_main_menu_keyboard()`, add a new row after the Delete row (before Settings):

```python
        [
            InlineKeyboardButton(
                f"\U0001f4da {translation.get_text('Library')}",
                callback_data="menu_library"
            ),
        ],
```

The resulting layout:
- Row 1: Movie, Series
- Row 2: Music, Status
- Row 3: Upcoming, Delete
- Row 4: **Library** (NEW)
- Row 5: Settings
- Row 6: Help, Cancel

### Step 4: Run test to verify it passes

Run: `python -m pytest tests/test_bot/test_keyboards.py::TestMainMenuKeyboard -v`
Expected: PASS

---

## Task 4: Handle `menu_library` in StartHandler + wire library sub-menu

**Files:**
- Modify: `src/bot/handlers/start.py:10,22-25,35-39,125-207`
- Modify: `tests/test_handlers/test_start_handler.py`
- Modify: `tests/test_handlers/conftest.py:122-165` (start_handler fixture)

### Step 1: Write failing tests

Add to `tests/test_handlers/test_start_handler.py`:

```python
@pytest.mark.asyncio
async def test_handle_menu_selection_library(
    start_handler, make_update, make_context
):
    """menu_library shows library sub-menu and ends conversation."""
    update = make_update(callback_data="menu_library")
    context = make_context()

    result = await start_handler.handle_menu_selection(update, context)

    assert result == ConversationHandler.END
    update.callback_query.message.edit_text.assert_called_once()
    # Verify it was called with the library menu keyboard
    start_handler._mock_lib_kbd.assert_called_once()
```

### Step 2: Run test to verify it fails

Run: `python -m pytest tests/test_handlers/test_start_handler.py::test_handle_menu_selection_library -v`
Expected: FAIL — `menu_library` falls through to unknown action

### Step 3: Update start_handler fixture

In `tests/test_handlers/conftest.py`, update the `start_handler` fixture to also patch `get_library_menu_keyboard`:

```python
@pytest.fixture
def start_handler(mock_media_service, mock_translation_service):
    """Create a StartHandler with patched services."""
    with (
        patch("src.bot.handlers.start.MediaHandler") as mock_mh_class,
        patch("src.bot.handlers.start.CalendarHandler") as mock_ch_class,
        patch("src.bot.handlers.start.HelpHandler") as mock_hh_class,
        patch("src.bot.handlers.start.SystemHandler") as mock_sh_class,
        patch("src.bot.handlers.start.TranslationService") as mock_ts_class,
        patch("src.bot.handlers.start.get_main_menu_keyboard") as mock_kbd,
        patch("src.bot.handlers.start.get_library_menu_keyboard") as mock_lib_kbd,
    ):
        # ... (existing mock setup stays the same) ...
        mock_lib_kbd.return_value = MagicMock()

        # ... (existing handler creation stays the same) ...
        handler._mock_lib_kbd = mock_lib_kbd
        yield handler
```

### Step 4: Implement the handler change

In `src/bot/handlers/start.py`:

1. **Add import** (line ~25): Add `get_library_menu_keyboard` to the import from `src.bot.keyboards`:
   ```python
   from src.bot.keyboards import get_main_menu_keyboard, get_library_menu_keyboard
   ```

2. **Add library handler** in `handle_menu_selection()`, after the `action == "upcoming"` block (~line 188), before the status/help/delete block:

   ```python
        if action == "library":
            await query.message.edit_text(
                self.translation.get_text("LibraryPrompt"),
                reply_markup=get_library_menu_keyboard()
            )
            return ConversationHandler.END
   ```

   We return `ConversationHandler.END` because:
   - The library sub-menu buttons (`library_movie`, etc.) need to be handled by `LibraryHandler`
   - `LibraryHandler` already has its own `CallbackQueryHandler`s registered globally
   - Ending the start conversation allows those handlers to pick up the callbacks

### Step 5: Run test to verify it passes

Run: `python -m pytest tests/test_handlers/test_start_handler.py -v`
Expected: ALL PASS

---

## Task 5: Add callback routing in LibraryHandler for sub-menu buttons

**Files:**
- Modify: `src/bot/handlers/library.py:38-47,67-96`
- Modify: `tests/test_handlers/test_library_handler.py`

### Step 1: Write failing tests

Add to `tests/test_handlers/test_library_handler.py`:

```python
# ---------------------------------------------------------------------------
# Library sub-menu callback (handle_library_selection)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("callback_data,service_method", [
    ("library_movie", "get_movies"),
    ("library_series", "get_series"),
    ("library_music", "get_music"),
])
@pytest.mark.asyncio
async def test_library_selection_callback(
    library_handler, make_update, make_context,
    callback_data, service_method
):
    """library_{type} callback fetches items and replies with paginated text."""
    items = [
        {"id": "1", "title": "Alpha"},
        {"id": "2", "title": "Beta"},
    ]
    setattr(
        library_handler._mock_service, service_method,
        AsyncMock(return_value=items)
    )

    update = make_update(callback_data=callback_data)
    context = make_context()

    await library_handler.handle_library_selection(update, context)

    update.callback_query.answer.assert_called_once()
    update.callback_query.message.edit_text.assert_called_once()
    call_args = update.callback_query.message.edit_text.call_args
    text = call_args[0][0] if call_args[0] else call_args[1].get("text", "")
    assert "Alpha" in text
    assert "Beta" in text


@pytest.mark.asyncio
async def test_library_selection_no_callback(
    library_handler, make_update, make_context
):
    """handle_library_selection returns when no callback_query."""
    update = make_update(text="/test")
    update.callback_query = None
    context = make_context()

    result = await library_handler.handle_library_selection(update, context)

    assert result is None


@pytest.mark.asyncio
async def test_library_selection_unknown_type(
    library_handler, make_update, make_context
):
    """Unknown library type returns early after answering."""
    update = make_update(callback_data="library_unknown")
    context = make_context()

    await library_handler.handle_library_selection(update, context)

    update.callback_query.answer.assert_called_once()


@pytest.mark.asyncio
async def test_library_selection_service_error(
    library_handler, make_update, make_context
):
    """Service ValueError shows not-enabled message."""
    library_handler._mock_service.get_movies = AsyncMock(
        side_effect=ValueError("not enabled")
    )

    update = make_update(callback_data="library_movie")
    context = make_context()

    await library_handler.handle_library_selection(update, context)

    update.callback_query.message.edit_text.assert_called_once()
    call_args = update.callback_query.message.edit_text.call_args
    assert "LibraryNotEnabled" in str(call_args)


@pytest.mark.asyncio
async def test_library_selection_empty_library(
    library_handler, make_update, make_context
):
    """Empty library shows empty message."""
    library_handler._mock_service.get_movies = AsyncMock(return_value=[])

    update = make_update(callback_data="library_movie")
    context = make_context()

    await library_handler.handle_library_selection(update, context)

    update.callback_query.message.edit_text.assert_called_once()
    call_args = update.callback_query.message.edit_text.call_args
    assert "LibraryEmpty" in str(call_args)
```

### Step 2: Run tests to verify they fail

Run: `python -m pytest tests/test_handlers/test_library_handler.py::test_library_selection_callback -v`
Expected: FAIL — `handle_library_selection` doesn't exist

### Step 3: Implement handle_library_selection

In `src/bot/handlers/library.py`:

1. **Add `handle_library_selection` method** to `LibraryHandler`:

```python
    @require_auth
    @rate_limit("search")
    async def handle_library_selection(self, update, context):
        """Handle library sub-menu callback (library_{type})."""
        if not update.callback_query:
            return

        query = update.callback_query
        await query.answer()

        # Map callback suffixes to MEDIA_TYPES short codes
        type_map = {"movie": "m", "series": "s", "music": "a"}
        action = query.data.replace("library_", "")
        media_type = type_map.get(action)

        if not media_type:
            return

        type_info = MEDIA_TYPES[media_type]
        log_user_interaction(
            logger, query.from_user,
            f"library_{type_info['label']}"
        )

        try:
            method = getattr(self.media_service, type_info["service_method"])
            items = await method()
        except ValueError:
            await query.message.edit_text(
                self.translation.get_text(
                    "LibraryNotEnabled", subject=type_info["label"]
                )
            )
            return
        except Exception:
            logger.error(
                f"Error fetching {type_info['label']} library",
                exc_info=True,
            )
            await query.message.edit_text(
                self.translation.get_text("LibraryError")
            )
            return

        if not items:
            await query.message.edit_text(
                self.translation.get_text(
                    "LibraryEmpty", subject=type_info["label"]
                )
            )
            return

        items = sorted(items, key=lambda x: x.get("title", "").lower())
        context.user_data[f"library_{media_type}"] = items

        text, reply_markup = self._build_page_message(items, 0, media_type)
        await query.message.edit_text(text, reply_markup=reply_markup)
```

2. **Register the callback handler** in `get_handler()`:

```python
    def get_handler(self):
        """Get library command handlers."""
        return [
            CommandHandler("allMovies", self.handle_all_movies),
            CommandHandler("allSeries", self.handle_all_series),
            CommandHandler("allMusic", self.handle_all_music),
            CallbackQueryHandler(
                self.handle_library_selection, pattern="^library_"
            ),
            CallbackQueryHandler(
                self.handle_page_navigation, pattern="^lib_"
            ),
        ]
```

### Step 4: Run all library tests

Run: `python -m pytest tests/test_handlers/test_library_handler.py -v`
Expected: ALL PASS

---

## Task 6: Full suite + coverage check

### Step 1: Run full test suite

Run: `python -m pytest --tb=short -q`
Expected: All tests pass

### Step 2: Run scoped coverage

Run: `python -m pytest tests/test_handlers/test_library_handler.py tests/test_handlers/test_start_handler.py tests/test_bot/test_keyboards.py --cov=src.bot.handlers.library --cov=src.bot.handlers.start --cov=src.bot.keyboards --cov-report=term-missing`
Expected: 100% coverage on changed lines

### Step 3: Run lint

Run: `python -m flake8 src/bot/keyboards.py src/bot/handlers/start.py src/bot/handlers/library.py`
Expected: No errors

### Step 4: Validate translations

Run: `PYTHONIOENCODING=utf-8 python run.py --validate-i18n`
Expected: Pass

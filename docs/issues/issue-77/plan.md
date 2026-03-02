# Fix #77: Deprecated CallbackContext and Mixed Imports

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Align `transmission.py` with the rest of the codebase by replacing deprecated `CallbackContext` with `ContextTypes.DEFAULT_TYPE` and converting relative imports to absolute.

**Architecture:** Pure cleanup — no behavior changes. All 8 other handlers already use `ContextTypes.DEFAULT_TYPE` and absolute `from src.xxx` imports. This brings the 9th handler into consistency.

**Tech Stack:** python-telegram-bot v20+, Python 3.11

---

### Task 1: Verify existing tests pass (baseline)

**Files:**
- Read: `tests/test_handlers/test_transmission_handler.py`

**Step 1: Run transmission tests**

Run: `pytest tests/test_handlers/test_transmission_handler.py -v`
Expected: All 7 tests PASS

**Step 2: Confirm no `CallbackContext` references in tests**

Run: `grep -r "CallbackContext" tests/`
Expected: No matches (tests use `make_context` fixture)

---

### Task 2: Fix imports in transmission handler

**Files:**
- Modify: `src/bot/handlers/transmission.py:9` (telegram.ext import)
- Modify: `src/bot/handlers/transmission.py:14-16` (relative imports)

**Step 1: Replace `CallbackContext` import with `ContextTypes`**

```python
# Line 9 — BEFORE:
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler

# AFTER:
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes
```

**Step 2: Convert relative imports to absolute**

```python
# Lines 14-16 — BEFORE:
from ...services.transmission import transmission_service
from ...utils.logger import get_logger
from src.bot.keyboards import get_yes_no_keyboard

# AFTER:
from src.services.transmission import transmission_service
from src.utils.logger import get_logger
from src.bot.keyboards import get_yes_no_keyboard
```

---

### Task 3: Update method signatures

**Files:**
- Modify: `src/bot/handlers/transmission.py:39` (`transmission_command`)
- Modify: `src/bot/handlers/transmission.py:81` (`handle_callback`)

**Step 1: Update `transmission_command` signature**

```python
# Line 39 — BEFORE:
async def transmission_command(self, update: Update, context: CallbackContext) -> None:

# AFTER:
async def transmission_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
```

**Step 2: Update `handle_callback` signature**

```python
# Line 81 — BEFORE:
async def handle_callback(self, update: Update, context: CallbackContext) -> None:

# AFTER:
async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
```

---

### Task 4: Verify and commit

**Step 1: Run transmission tests**

Run: `pytest tests/test_handlers/test_transmission_handler.py -v`
Expected: All 7 tests PASS

**Step 2: Run full test suite**

Run: `pytest --tb=short -q`
Expected: All tests PASS, no regressions

**Step 3: Lint the changed file**

Run: `flake8 src/bot/handlers/transmission.py`
Expected: Clean (no output)

**Step 4: Commit**

```bash
git add src/bot/handlers/transmission.py
git commit -m "fix: replace deprecated CallbackContext with ContextTypes.DEFAULT_TYPE (#77)

Convert relative imports to absolute imports matching project convention.
No behavior changes."
```

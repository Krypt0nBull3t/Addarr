---
name: code-simplifier
description: Use when asked to simplify, clean up, or refactor code for clarity. Focuses on reducing complexity, eliminating redundant abstractions, and improving readability while preserving functionality. Complements the quick-pass simplify superpowers skill with deeper, focused refactoring.
---

# Code Simplifier

Simplify and refine code for clarity, consistency, and maintainability while preserving exact functionality. Adapted from [Sentry's code-simplifier skill](https://github.com/getsentry/sentry-skills).

**Relationship to `superpowers:simplify`:** The `simplify` skill is a quick post-change review pass (reuse, quality, efficiency). This skill is for deeper, focused refactoring sessions where you methodically simplify a file or feature area.

## Refinement Principles

### 1. Preserve Functionality

Never change what the code does — only how it does it. All original features, outputs, and behaviors must remain intact.

### 2. Apply Project Standards

Follow Addarr conventions from CLAUDE.md:

- Async throughout (`async/await`, `aiohttp`)
- Singleton services (`__new__` + `_initialize`, not `__init__`)
- Safe config access (`.get()` with defaults, not direct indexing)
- `is_enabled()` checks before service method calls
- `@require_auth` on all handler entry points
- Centralized keyboards in `src/bot/keyboards.py`
- Translation via `TranslationService().get_text(key, default=...)`
- Flake8 with max line length 88

### 3. Enhance Clarity

Simplify code structure by:

- Reducing unnecessary nesting (early returns, guard clauses)
- Eliminating redundant abstractions used only once
- Improving variable and function names for readability
- Consolidating related logic
- Removing comments that describe obvious code
- Preferring explicit `if/elif/else` over nested ternaries
- Choosing clarity over brevity — explicit code is better than dense one-liners

### 4. Python-Specific Simplifications

Common patterns to simplify in this codebase:

```python
# BEFORE: Verbose conditional assignment
if condition:
    value = "a"
else:
    value = "b"

# AFTER: Inline conditional (when simple)
value = "a" if condition else "b"
```

```python
# BEFORE: Manual dict building
result = {}
for item in items:
    result[item.id] = item.name

# AFTER: Dict comprehension
result = {item.id: item.name for item in items}
```

```python
# BEFORE: Nested config access with repeated .get()
server = config.get("radarr", {}).get("server", {})
addr = server.get("addr", "")
port = server.get("port", "")
path = server.get("path", "")

# AFTER: Unpack once
server = config.get("radarr", {}).get("server", {})
addr, port, path = server.get("addr", ""), server.get("port", ""), server.get("path", "")
```

```python
# BEFORE: Redundant wrapper
def is_not_empty(lst):
    return len(lst) > 0

if is_not_empty(results):
    ...

# AFTER: Direct check
if results:
    ...
```

### 5. Maintain Balance

Avoid over-simplification that could:

- Reduce code clarity or maintainability
- Create overly clever solutions hard to understand
- Combine too many concerns into single functions
- Remove helpful abstractions that improve organization
- Prioritize fewer lines over readability
- Make the code harder to debug or extend

### 6. Focus Scope

Only refine code that has been recently modified or explicitly targeted, unless instructed to review broader scope.

## Refinement Process

1. **Identify** the target code sections (changed files or specified scope)
2. **Analyze** for complexity reduction opportunities
3. **Apply** project standards from CLAUDE.md and skill conventions
4. **Ensure** all functionality remains unchanged
5. **Verify** the refined code is simpler and more maintainable
6. **Run tests** to confirm nothing broke: `pytest -x --tb=short`

## Common Simplification Targets in Addarr

| Pattern | Simplification |
|---------|---------------|
| Repeated `if photo: edit_caption else: edit_text` | Extract to helper or use existing utility |
| Manual keyboard construction inline | Move to `src/bot/keyboards.py` function |
| Duplicate error handling in handlers | Extract common error response pattern |
| Verbose config access chains | Unpack config section once at top |
| Repeated `is_enabled()` + error reply | Consider decorator or shared guard |
| Multiple similar `CallbackQueryHandler` registrations | Look for pattern consolidation |

## What NOT to Simplify

- Singleton `__new__` + `_initialize` pattern (it's intentional, not redundant)
- `is_enabled()` guard checks (safety-critical, must remain explicit)
- `await query.answer()` calls (Telegram requirement)
- `context.user_data.clear()` in cancel handlers (prevents state leaks)
- State return values from handler methods (ConversationHandler requires them)

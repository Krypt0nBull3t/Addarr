---
name: telegram-ux-review
description: Use when reviewing Telegram bot interaction quality, keyboard consistency, flow efficiency, or message formatting. Covers Telegram-specific constraints (64-byte callback_data, 1024-char caption limit, 4096-char text limit) and bot UX patterns.
---

# Telegram UX Review

On-demand review of bot interaction quality. Fills the gap left by traditional UI/UX tools that don't apply to Telegram's constrained interaction model.

**Key files to audit:** `src/bot/keyboards.py`, `src/bot/handlers/media/formatters.py`, `src/bot/handlers/media/handler.py`, all handler files that build inline keyboards.

## Telegram Limits

Limits from the Bot API (values as in python-telegram-bot 22.8 `telegram.constants`). Nothing in the code guards them.

| Constraint | Limit | Consequence |
|-|-|-|
| `callback_data` | 64 bytes | The Bot API rejects the whole send or edit with HTTP 400 (`BUTTON_DATA_INVALID`); the user sees nothing |
| Photo caption | 1024 characters | The send fails with HTTP 400 (caption too long); the user sees nothing |
| Text message | 4096 characters | The send fails with HTTP 400 |
| Buttons in one inline keyboard | 100 | The send fails |
| Buttons per row | 8 | Undocumented by Telegram (PTB `InlineKeyboardMarkupLimit.BUTTONS_PER_ROW`); may change |

Heuristic, not an API limit: button text longer than about 30 characters gets cut off on small phone screens.

## Phase 1: Keyboard Consistency

* [ ] **Back/cancel placement** — Every keyboard has back/cancel in the last row
* [ ] **Pagination pattern** — All paginated views use same format (e.g., arrows + page indicator)
* [ ] **Filter checkmark convention**: Consistent symbol for active/inactive filters across all keyboards
* [ ] **Mobile fit** — Button text fits typical phone screen widths without truncation
* [ ] **Callback data size**: Every `callback_data=` under `src/bot/` (keyboards.py and the handlers that build buttons, including f-strings with IDs) stays within 64 bytes. This skill owns the check; security-audit points here.
* [ ] **No duplicate callback_data** — No identical callback_data values across unrelated keyboards (would cause wrong handler to fire)

## Phase 2: Flow Efficiency

* [ ] **Tap count** — Common actions (search -> select -> add) require <= 5 taps. Count and flag if more.
* [ ] **Dead-end detection** — Every conversation state has a clear exit path (back, cancel, or timeout)
* [ ] **Actionable errors** — Error states offer next steps, not just "something went wrong"
* [ ] **Cancel from anywhere** — `/cancel` command works from every conversation state (check `fallbacks` in each ConversationHandler)

## Phase 3: Information Density

* [ ] **Caption length** — Photo captions stay within 1024-character Telegram limit. Check `formatters.py` caption builders.
* [ ] **Text length** — Text messages stay within 4096-character limit. Check error messages, help text, status output.
* [ ] **Truncation strategy** — Consistent approach when content exceeds limits (ellipsis, "and N more", pagination)
* [ ] **Format consistency** — Search result formatting consistent between list view and card view
* [ ] **Metadata order** — Rating, genre, year, links display follows same order across all media types (movie, series, music)

## Phase 4: Accessibility

* [ ] **Emoji + text pairing** — Emoji used as visual markers, always paired with text labels (e.g., `Added` not just the checkmark emoji)
* [ ] **Image fallback** — Text-only fallback exists when poster images fail to load
* [ ] **Plain text degradation** — Messages remain readable without Markdown/HTML formatting
* [ ] **Status clarity** — Status indicators use both symbol and word (e.g., `Success: Added` not just a symbol)

## Output

**Only report actionable findings.** Skip:
- Stylistic preferences without UX impact
- Platform limitations that can't be worked around
- Pre-existing patterns consistent with the codebase

For each issue:

* **File:Line** — Brief description
* **Severity**: Critical / High / Medium / Low
* **Problem**: What's wrong from a user perspective
* **Fix**: Concrete suggestion

If nothing significant found, say so in one line.

Do not make changes — just report findings.

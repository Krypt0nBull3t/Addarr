# Issue #210 design: harden auth

Source: issue #210 (F090, F091, F092 of audit 2026-10-28). Decisions confirmed by the developer on 2026-11-05.

## Root causes

- **F092**: `message.delete()` is awaited with no guard in `AuthHandler.check_password` (`src/bot/handlers/auth.py`) and eight times in `src/bot/handlers/media/formatters.py` (`show_result`, `show_list`, `show_list_detail`). Telegram raises `TelegramError` when the bot has no delete rights in a group. In `check_password` that skips the password check. In `show_result` it jumps to the outer `except`, which sends a second card.
- **F090**: two prompts take any password: `configure_telegram` and the telegram branch of `configure_required_value` (`src/setup/prompts.py`). `Config.__init__` has no password prompt.
- **F091**: `AuthHandler.__init__` loads `authenticated_users` from config and never compares it with the current password.

## Decisions

1. One helper `_delete_quietly(message)` in `formatters.py`. It catches `TelegramError`, logs a warning and returns. `auth.py` gets the same guard inline (a handler must not import from `media`).
2. One helper `_prompt_chat_password()` in `prompts.py`, used by both prompt sites. It shows a `questionary.text` prompt pre-filled with `secrets.token_urlsafe(16)`. Enter accepts it. A typed value under 12 characters is refused and asked again.
3. `authenticated_users_hash` in `config.yaml` holds the sha256 hex digest of the password. `config.yaml` already holds the password in plain text, so a salt adds no protection.
4. At start-up, when the list has users and the stored hash differs from the current hash, the list is cleared and saved with the current hash.
5. A list with no stored hash counts as a mismatch. Every existing user sends `/auth` once after the upgrade. The PR body says so.

## Out of scope

- A start-up refusal of an existing short password. Only new passwords typed in the wizard are checked.
- Per-user group-aware auth (#151) and the rate-limit reset on restart.
- Changes to `_save_authenticated_users` beyond writing the hash. Issue #209 (F032) also edits it; the PR that merges second merges `origin/development`.

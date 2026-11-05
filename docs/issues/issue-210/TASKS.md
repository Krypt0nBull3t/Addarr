# Issue #210 Tasks: Harden auth

Plan: `docs/issues/issue-210/plan.md`. Design: `docs/issues/issue-210/design.md`.

### Phase 1: Failed deletes (F092) (2 tasks)

**Goal:** A failed `message.delete()` never stops the password check or a search.

- [x] **1.1** Guard the deletes in the media result cards
    - **Context:**
        - **Why:** In a group where the bot cannot delete, `message.delete()` raises `TelegramError`. In `show_result` it lands in the outer `except` and sends a second card (or a SearchError).
        - **Architecture:** One module-level helper in `formatters.py`; all 8 `await message.delete()` calls use it.
        - **Key refs:** `src/bot/handlers/media/formatters.py` lines 211, 220, 228, 240 (`show_result`), 264 (`show_list`), 287, 296, 304 (`show_list_detail`); `tests/test_handlers/test_media_formatters.py` (`make_message` fixture).
        - **Watch out:** Catch only `telegram.error.TelegramError`; a `RuntimeError` must still propagate. Keep the module's 100% coverage.
    - **Scope:** `_delete_quietly(message)` helper and its 8 call sites.
    - **Touches:** `src/bot/handlers/media/formatters.py`, `tests/test_handlers/test_media_formatters.py`
    - **Action items:**
        - [RED] `test_show_result_sends_card_once_when_delete_fails` (BadRequest on delete: `reply_text` awaited once, new message returned)
        - [RED] Parametrized test: `show_list`, `show_list_detail` with and without poster survive a failed delete
        - [RED] `test_delete_quietly_lets_other_errors_through`
        - [GREEN] Add `_delete_quietly`, replace the 8 calls
    - **Success:** the new tests fail before the fix and pass after; handlers scoped run keeps 100%; flake8 and mypy clean.
    - **Completed:** 2026-11-05
    - **Learnings:**
        - Adding the helper with a bare `await message.delete()` first turned the 5 behavior tests red for the right reason (BadRequest escaping) before the catch went in.
        - `show_result` had 4 delete calls, not the 3 the issue listed; all 8 flow call sites now go through the helper.
    - **Key Changes:**
        - `src/bot/handlers/media/formatters.py`: `_delete_quietly(message)` catches `TelegramError`, logs a warning; all deletes use it.
        - `tests/test_handlers/test_media_formatters.py`: 4 new tests (5 cases) for `show_result`, `show_list`, `show_list_detail` and the non-Telegram error path.
    - **Notes:** Only `TelegramError` is swallowed; other errors still propagate.

- [x] **1.2** Guard the password-message delete
    - **Context:**
        - **Why:** The unguarded delete in `check_password` skips the password check when it raises, so the password stays visible and unchecked.
        - **Architecture:** Inline `try/except TelegramError` in `auth.py`; a handler module must not import from `media`.
        - **Key refs:** `src/bot/handlers/auth.py` `check_password` (`await message.delete()`), `tests/test_handlers/test_auth_handler.py` (`mock_config`, `make_update`, `make_context`).
        - **Watch out:** Never log the message text (it holds the password).
    - **Scope:** Guard plus warning log.
    - **Touches:** `src/bot/handlers/auth.py`, `tests/test_handlers/test_auth_handler.py`
    - **Action items:**
        - [RED] `test_check_password_authenticates_when_delete_fails`
        - [RED] `test_check_password_rejects_wrong_password_when_delete_fails`
        - [GREEN] Wrap the delete
    - **Success:** tests fail before and pass after; handlers scoped run keeps 100%.
    - **Completed:** 2026-11-05
    - **Learnings:**
        - `make_update` exposes the message as `update.effective_message`; setting `delete.side_effect` there reaches the handler.
    - **Key Changes:**
        - `src/bot/handlers/auth.py`: `check_password` catches `TelegramError` from the delete and logs a warning without the message text.
        - `tests/test_handlers/test_auth_handler.py`: 2 tests (correct and wrong password with a failing delete).
    - **Notes:** The guard stays inline; `auth.py` must not import from `media`.

### Phase 2: Password rules (F090) (1 task)

**Goal:** The wizard proposes a random password; a typed password needs 12+ characters.

- [x] **2.1** Shared password prompt in the wizard
    - **Context:**
        - **Why:** Any non-empty password is accepted today, at two prompt sites.
        - **Architecture:** `_prompt_chat_password()` in `prompts.py`, used by `configure_telegram` and the telegram branch of `configure_required_value`. `src/setup/` never imports `src.config.settings` (ADR 0005).
        - **Key refs:** `src/setup/prompts.py` (`configure_telegram`, `configure_required_value`), `tests/test_setup/test_prompts.py` (`test_returns_dict_with_token_and_password`, `test_telegram_token`).
        - **Watch out:** Existing tests mock `questionary.password` for the password prompt; the password prompt becomes `questionary.text` (pre-filled), so update them. `ask_async` returns `None` on Ctrl-C: return it as-is. Refuse in a loop in our code, not via questionary `validate`, so a test can see the refusal.
    - **Scope:** `MIN_PASSWORD_LENGTH = 12`, helper, two call sites.
    - **Touches:** `src/setup/prompts.py`, `tests/test_setup/test_prompts.py`
    - **Action items:**
        - [RED] `test_proposes_token_urlsafe_value` (patch `secrets.token_urlsafe`; called with 16; prompt default equals it)
        - [RED] `test_rejects_11_characters`, `test_accepts_12_characters`, `test_none_returned_as_is`
        - [RED] Update the two existing tests to mock `questionary.text`
        - [GREEN] Implement the helper and use it at both sites
    - **Success:** new tests fail before and pass after; `scripts/test_runner.py setup --coverage` keeps 100%.
    - **Completed:** 2026-11-05
    - **Learnings:**
        - A mutation (`MIN_PASSWORD_LENGTH = 1`) turned `test_rejects_11_characters` red, so the test can fail on the rule.
        - The existing tests mocked `questionary.password` for both prompts; the token stays a hidden prompt, only the password moved to `questionary.text`.
    - **Key Changes:**
        - `src/setup/prompts.py`: `MIN_PASSWORD_LENGTH = 12`, `_prompt_chat_password()`; both prompt sites use it.
        - `tests/test_setup/test_prompts.py`: `TestPromptChatPassword` (4 tests); two existing tests now mock `questionary.text`.
    - **Notes:** The password prompt is visible by design (the generated value must be readable). A cancelled prompt still returns `None`, as before.

### Phase 3: Revoke on password change (F091) (1 task)

**Goal:** Changing `telegram.password` clears every authenticated user.

- [ ] **3.1** Store a password hash and clear the list on mismatch
    - **Context:**
        - **Why:** `authenticated_users` never expires and survives a password change.
        - **Architecture:** `_password_hash(password)` (sha256 hex) in `auth.py`; `authenticated_users_hash` saved with the list; `AuthHandler.__init__` compares at start-up. Missing hash counts as mismatch (decided: one re-auth after upgrade).
        - **Key refs:** `src/bot/handlers/auth.py` (`__init__`, `_save_authenticated_users`); `tests/conftest.py` (`MockConfig` default config: `authenticated_users: [12345]`, `telegram.password: "test-pass"`); `tests/integration/test_auth_flow.py`.
        - **Watch out:** Hash `str(password)` (YAML can load an int). Only save at start-up when users were cleared. `src/main.py` registers commands for `_authenticated_users` after the handler is built, so a cleared list stays cleared. #209 and #225 edit the same save method and `MockConfig`; the second PR to merge keeps both.
    - **Scope:** Hash helper, start-up check, save writes the hash, conftest default hash.
    - **Touches:** `src/bot/handlers/auth.py`, `tests/conftest.py`, `tests/test_handlers/test_auth_handler.py`
    - **Action items:**
        - [RED] `test_init_clears_users_when_hash_differs`, `test_init_clears_users_when_hash_missing`, `test_init_keeps_users_when_hash_matches`
        - [RED] `test_init_empty_list_does_not_save`, `test_save_writes_hash`, `test_int_password_hash_matches_string`
        - [GREEN] Implement; add the matching hash to the `MockConfig` default so existing tests keep user 12345
    - **Success:** new tests fail before and pass after; handlers scoped run and `tests/integration` pass at 100%.

### Phase 4: Docs (1 task)

**Goal:** The docs name the hash key and the wizard rule.

- [ ] **4.1** Update docs
    - **Context:**
        - **Why:** CLAUDE.md lists the auth pattern; a new config key and a password rule are user-visible.
        - **Architecture:** Docs only.
        - **Key refs:** `CLAUDE.md` § Key Patterns (Authentication decorator); any README section on `telegram.password`.
        - **Watch out:** `tests/test_architecture/test_repo_docs.py` checks every path and name in CLAUDE.md.
    - **Scope:** One sentence in CLAUDE.md; README only if it describes the password.
    - **Touches:** `CLAUDE.md`, `README.md` (if relevant)
    - **Action items:**
        - [GREEN] Edit the docs
        - [GREEN] Run `tests/test_architecture`
    - **Success:** architecture tests pass.

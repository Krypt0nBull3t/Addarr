# Issue #210: Harden auth Implementation Plan

**Goal:** A failed delete never stops the password check or a search. A new password is random or 12+ characters. A password change revokes every authenticated user.

**Architecture:** Guard each `message.delete()` with a `TelegramError` catch. Share one password prompt helper between both wizard paths. Store the sha256 of the password beside `authenticated_users` and clear the list when it differs.

**Tech Stack:** python-telegram-bot 22.8, questionary, hashlib, secrets, pytest.

**Spec:** `docs/issues/issue-210/design.md`

## Global Constraints

- `config["key"]` access is banned in `src/`; use `config.get()`.
- `Optional[str]` syntax for optionals.
- Every test and gate runs through the suite lock; coverage stays at 100%.
- No new translation keys (the wizard prompts are English literals, as today).

## Review Focus

- Delete raises `BadRequest` ("message can't be deleted") in `show_list_detail` without a poster: card still sent once. (Task 1)
- Delete raises a non-Telegram error: still propagates (the guard is not a blanket catch). (Task 1)
- Password prompt returns `None` (Ctrl-C): returned as-is, no `TypeError` on `len(None)`. (Task 3)
- Exactly 12 typed characters accepted; the proposed value is accepted unchanged. (Task 3)
- Password stored as an int in YAML (`password: 123456`): hash uses `str(password)`, as `self.password` already does. (Task 4)
- Empty list plus changed password: no write at start-up. (Task 4)

---

### Task 1: Guard deletes in media formatters (F092)

**Files:**
- Modify: `src/bot/handlers/media/formatters.py` (8 `message.delete()` calls: `show_result` x4, `show_list`, `show_list_detail` x3)
- Test: `tests/test_handlers/test_media_formatters.py`

**Interfaces:**
- Produces: `async def _delete_quietly(message) -> None` in `formatters.py`.

- [ ] **Step 1: Write failing tests** `test_show_result_sends_card_once_when_delete_fails` (message mock `delete` raises `telegram.error.BadRequest("Message can't be deleted")`; assert `reply_text` awaited once and the returned message is the new one), a parametrized `test_show_list_and_detail_survive_failed_delete` for `show_list`, `show_list_detail` with and without poster, and `test_delete_quietly_lets_other_errors_through` (`delete` raises `RuntimeError`, expect `RuntimeError`).
- [ ] **Step 2: Run** `<lock> .venv/bin/python -m pytest tests/test_handlers/test_media_formatters.py -k "delete" -v`. Expected: FAIL.
- [ ] **Step 3: Implement** `_delete_quietly`: `try: await message.delete()`, `except TelegramError as e: logger.warning(...)`. Replace all 8 calls. Import `TelegramError` from `telegram.error`.
- [ ] **Step 4: Run** the same command. Expected: PASS. Run `<lock> .venv/bin/python scripts/test_runner.py handlers --coverage`.
- [ ] **Step 5: Commit** `fix: ignore failed deletes in result cards (#210, task 1)`.

### Task 2: Guard the password delete (F092)

**Files:**
- Modify: `src/bot/handlers/auth.py` (`check_password`, the delete near line 203)
- Test: `tests/test_handlers/test_auth_handler.py`

- [ ] **Step 1: Write failing test** `test_check_password_authenticates_when_delete_fails`: `update.message.delete` is `AsyncMock(side_effect=TelegramError("no rights"))`; correct password; assert user 12345-style new id in `AuthHandler._authenticated_users` and result `ConversationHandler.END`. Add `test_check_password_rejects_wrong_password_when_delete_fails`.
- [ ] **Step 2: Run** `-k "delete_fails"`. Expected: FAIL with `TelegramError`.
- [ ] **Step 3: Implement** `try/except TelegramError` around the delete in `check_password`; log a warning (never the message text).
- [ ] **Step 4: Run** the tests. Expected: PASS.
- [ ] **Step 5: Commit** `fix: check the password when the delete fails (#210, task 2)`.

### Task 3: Random or 12+ character password in the wizard (F090)

**Files:**
- Modify: `src/setup/prompts.py` (`configure_telegram`, `configure_required_value`)
- Test: `tests/test_setup/test_prompts.py` (update `test_returns_dict_with_token_and_password`, `test_telegram_token`; they mock `questionary.password` for the password prompt today)

**Interfaces:**
- Produces: `MIN_PASSWORD_LENGTH = 12`; `async def _prompt_chat_password() -> Optional[str]`.

- [ ] **Step 1: Write failing tests** in a new `TestPromptChatPassword`: `test_proposes_token_urlsafe_value` (patch `src.setup.prompts.secrets.token_urlsafe` to return `"proposed-value-xyz"`; assert `questionary.text` called with `default="proposed-value-xyz"` and `token_urlsafe` called with `16`); `test_rejects_11_characters` (`ask_async` side_effect `["a"*11, "b"*12]`; result `"b"*12`, 2 asks); `test_accepts_12_characters` (`"a"*12`, 1 ask); `test_none_returned_as_is`. Update the two existing tests to mock `questionary.text` for the password.
- [ ] **Step 2: Run** `<lock> .venv/bin/python -m pytest tests/test_setup/test_prompts.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement** the helper: generate once, loop `ask_async` while the answer is not `None` and `len < MIN_PASSWORD_LENGTH`, printing a red message on each refusal. Use it at both prompt sites.
- [ ] **Step 4: Run** the file plus `scripts/test_runner.py setup --coverage`. Expected: PASS.
- [ ] **Step 5: Commit** `fix: propose a random chat password in setup (#210, task 3)`.

### Task 4: Revoke users when the password changes (F091)

**Files:**
- Modify: `src/bot/handlers/auth.py` (`AuthHandler.__init__`, `_save_authenticated_users`; new module function `_password_hash(password: str) -> str`)
- Modify: `tests/conftest.py` (default `MockConfig` gets `authenticated_users_hash` = sha256 of `"test-pass"` so existing tests keep their user)
- Test: `tests/test_handlers/test_auth_handler.py`

**Interfaces:**
- Produces: `_password_hash(password: str) -> str` (sha256 hex of the UTF-8 bytes); config key `authenticated_users_hash`.

- [ ] **Step 1: Write failing tests**: `test_init_clears_users_when_hash_differs` (hash of another password; expect `_authenticated_users == set()` and the saved config has `authenticated_users == []` and the new hash); `test_init_clears_users_when_hash_missing`; `test_init_keeps_users_when_hash_matches`; `test_init_empty_list_does_not_save` (`save` not called); `test_save_writes_hash` (after a successful `check_password`, saved hash equals `_password_hash("test-pass")`); `test_int_password_hash_matches_string` (config `password: 123456`).
- [ ] **Step 2: Run** `-k "hash"`. Expected: FAIL.
- [ ] **Step 3: Implement** per design decisions 3-5. Start-up: when `users` is non-empty and the stored hash differs from the current one, set the class set to empty, log a warning with the count, call `_save_authenticated_users()`.
- [ ] **Step 4: Run** `<lock> .venv/bin/python scripts/test_runner.py handlers --coverage` and `tests/integration`. Fix fixtures that now lose users.
- [ ] **Step 5: Commit** `fix: revoke authenticated users when the password changes (#210, task 4)`.

### Task 5: Docs

**Files:**
- Modify: `CLAUDE.md` (Key Patterns, authentication bullet: one sentence on `authenticated_users_hash`), the README or docs page that describes `telegram.password`, if one exists.

- [ ] **Step 1: Edit** the files. Run `<lock> .venv/bin/python -m pytest tests/test_architecture --tb=short -v`. Expected: PASS.
- [ ] **Step 2: Commit** `docs: describe the password hash and wizard rule (#210, task 5)`.

## Verification

Run the preflight (`/addarr pr` step 5). PR body carries the upgrade note: every user sends `/auth` once after upgrading.

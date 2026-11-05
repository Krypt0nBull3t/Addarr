---
title: "Harden auth: weak passwords, no revocation, failed deletes in groups"
labels: [bug, security, agent-ready, priority:high]
slice: 15
findings: [F092, F090, F091]
---
## Bug

- **F092** In a group chat, `message.delete()` raises when the bot lacks delete rights. The password stays visible and is never checked. The same raise breaks search (SearchError or a duplicate card).
- **F090** Any non-empty password is accepted. The allowlist is off by default. A guesser gets 3 tries per 5 minutes per account (864 per day), and the counters reset on restart.
- **F091** `authenticated_users` never expire. Changing the password revokes nobody (relates #151).

## Steps to reproduce

1. **F092** Add the bot to a group without delete rights, with a chatMode that lets groups in. Send /auth and the password. The message stays visible and the password is not checked. Search for a movie in the same group: SearchError or a duplicate card.
2. **F090** Run `python run.py --setup` and enter a one-character password. The wizard accepts it.
3. **F091** Authenticate a user. Change `telegram.password` and restart the bot. The user is still authenticated.

## Expected behavior

A failed delete does not stop the password check or the search. The setup wizard proposes a random password. A password the user types needs 12 or more characters. Changing the password revokes every authenticated user.

## Fix

- [ ] **F092** Wrap the deletes in `try/except TelegramError` (`src/bot/handlers/auth.py:202`; `src/bot/handlers/media/formatters.py:211`, `:228`, `:264`)
- [ ] **F090** In the setup wizard, propose a random password from `secrets.token_urlsafe(16)`. Reject a typed password shorter than 12 characters (`src/setup/prompts.py:136`, `src/bot/handlers/auth.py:204`)
- [ ] **F091** Store a password hash with the list; clear the list when the hash changes (`src/bot/handlers/auth.py:126`)

## Acceptance criteria

Each test fails before its fix and passes after:

- **F092** `tests/test_handlers/test_auth_handler.py`: when `message.delete()` raises `TelegramError`, the password is still checked and the user is authenticated. `tests/test_handlers/test_media_formatters.py`: when `delete()` raises, the result card is sent once and no error is raised.
- **F090** `tests/test_setup/test_prompts.py`: with `secrets.token_urlsafe` patched, the password prompt proposes its value. A typed password of 11 characters is rejected. A typed password of 12 characters is accepted.
- **F091** `tests/test_handlers/test_auth_handler.py`: when the stored hash does not match the current password, `authenticated_users` is cleared.
- `pytest`, `flake8` and `mypy src/` pass.

## Notes

- Source: audit 2026-10-28, docs/issues/audit-2026-10-28/FINDINGS.md (F-ids F092, F090, F091).
- Priority: max P 30, sum P 86 (high).
- Order: do slices 1-8 first. Slice 14 (F032) changes `_save_authenticated_users`, which F091 also touches.
- Related open issue: #151 (group-aware per-user auth), for F091.
- Decided 2026-10-28: F090 the wizard proposes a `secrets.token_urlsafe(16)` password; a typed password needs 12+ characters.

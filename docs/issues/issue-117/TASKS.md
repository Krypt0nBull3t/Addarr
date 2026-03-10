# Issue #117: Enforce Private Chat Mode

**Goal:** Reject bot commands in group/supergroup/channel chats by default via `security.chatMode` config.

**Plan:** See `plan.md` in this directory.

---

### Phase 1: Config, Translations & Test Fixtures (1 task)

**Goal:** Infrastructure for chat mode enforcement — config key, translation key, and test fixture support.

- [x] **1.1** Add chatMode config, PrivateChatOnly translation, and enhance make_update fixture
    - **Context:** See plan.md Phase 1 & 3. Key refs: `config_example.yaml:136` (security section), `tests/conftest.py:71` (MOCK_CONFIG_DATA), `tests/conftest.py:338` (make_update fixture)
    - **Watch out:** `make_update` currently only sets `update.effective_chat` for text message updates (line 359), not callback query updates — fix this. Translation key must be flat top-level (`PrivateChatOnly` not `Security.PrivateChatOnly`). All 9 locales + template need the key.
    - **Scope:** Config example, mock config data, translation keys across all locales, make_update `chat_type` parameter, effective_chat for callback updates
    - **Touches:** `config_example.yaml`, `tests/conftest.py`, `translations/addarr.*.yml`, `translations/addarr.template.yml`
    - **Action items:**
        - [GREEN] Add `chatMode: private_only` to `config_example.yaml` security section
        - [GREEN] Add `chatMode` to `MOCK_CONFIG_DATA` in `tests/conftest.py`
        - [GREEN] Add `PrivateChatOnly` translation key to all locale files + template
        - [GREEN] Add `chat_type` parameter to `make_update` fixture and set `effective_chat` on all update types
    - **Success:** `python run.py --validate-i18n` passes, existing tests still pass
    - **Completed:** 2026-03-10
    - **Learnings:** `make_update` was missing `effective_chat` for callback query updates — this would have caused AttributeError in the decorator for callback-based interactions.
    - **Key Changes:** `config_example.yaml` (chatMode), `tests/conftest.py` (MOCK_CONFIG_DATA + make_update chat_type param + effective_chat fix), all 10 translation files (PrivateChatOnly key)
    - **Notes:** Translated PrivateChatOnly to all 9 locales. Translations are best-effort — native speakers may want to refine.

### Phase 2: Core Enforcement (2 tasks)

**Goal:** Chat type checking in `require_auth` decorator and `AuthHandler.start_auth`.

- [ ] **2.1** Add chat type check to `require_auth` decorator
    - **Context:** See plan.md Task 2.1. Key refs: `src/bot/handlers/auth.py:37-51` (require_auth). The decorator guards 15+ handler methods — adding the check here covers all of them. Must handle both message and callback query reply paths.
    - **Watch out:** `update.message` is None for callback queries — use `update.effective_chat` for the type check, and branch reply logic. Config access: `config.get("security", {}).get("chatMode", "private_only")`. For callback rejections use `update.callback_query.answer(msg, show_alert=True)`.
    - **Scope:** Modify `require_auth` to check chat type before auth, add ~5 tests
    - **Touches:** `src/bot/handlers/auth.py`, `tests/test_handlers/test_auth_handler.py`
    - **Action items:**
        - [RED] Write tests: group chat rejected, supergroup rejected, private chat allowed, allow_all mode allows group, callback query in group answered with alert
        - [GREEN] Add chat type check to `require_auth` before the auth check
    - **Success:** All new tests pass, existing tests still pass, `flake8` clean

- [ ] **2.2** Add chat type check to `AuthHandler.start_auth`
    - **Context:** See plan.md Task 2.2. Key refs: `src/bot/handlers/auth.py:102-128` (start_auth). This method is NOT decorated with `@require_auth` — it needs its own chat type check to prevent password exposure in group chats.
    - **Watch out:** Must return `ConversationHandler.END` when rejecting, not just `None`. Check goes before the "already authenticated" check.
    - **Scope:** Modify `start_auth`, add ~3 tests
    - **Touches:** `src/bot/handlers/auth.py`, `tests/test_handlers/test_auth_handler.py`
    - **Action items:**
        - [RED] Write tests: start_auth rejects group chat (returns END), allows private, allows group with allow_all
        - [GREEN] Add chat type check at top of `start_auth`
    - **Success:** All tests pass, `flake8` clean, `pytest --cov=src.bot.handlers.auth --cov-report=term-missing` shows 100% on new lines

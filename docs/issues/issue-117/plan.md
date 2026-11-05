# Enforce Private Chat Mode — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add chat type enforcement so the bot rejects commands in group/supergroup/channel chats by default, with a config option to control behavior.

**Architecture:** Add a `chat_mode: private_only` config key under `security`. Modify the `require_auth` decorator to check `update.effective_chat.type` before proceeding. Auth handler (`/auth`) should also enforce private-only since passwords in groups are a security risk.

**Tech Stack:** python-telegram-bot v20+, pytest, aiohttp

---

## Design Decisions

1. **Where to enforce:** In the `require_auth` decorator (covers 15+ handler methods) AND in `AuthHandler.start_auth` (which isn't decorated with `require_auth`). This gives us a single enforcement point for most handlers plus explicit protection for the auth flow.

2. **Config key:** `security.chatMode` with values `private_only` (default) or `allow_all`. Using `allow_all` instead of `group_aware` because true group-aware isolation is a separate feature (#151). `allow_all` simply disables the chat type check.

3. **Translation key:** `PrivateChatOnly` — a single message explaining the bot only works in private chats.

4. **Auth handler special case:** `/auth` asks for a password. Even without `@require_auth`, it must reject group chats in `private_only` mode to prevent password exposure.

5. **What about callback queries?** The `require_auth` decorator currently accesses `update.message.reply_text`. For callback queries, `update.message` is None but `update.effective_chat` is always available. The chat type check happens before the auth check, so we use `update.effective_chat` which works for both message and callback contexts. If the chat type is rejected, we need to handle the reply path carefully (use `update.effective_message.reply_text` or `update.callback_query.answer`).

## Scope

- Add `security.chatMode` to `config_example.yaml` and `MOCK_CONFIG_DATA`
- Add `PrivateChatOnly` translation key to all 9 locale files + template
- Modify `require_auth` decorator to check chat type
- Modify `AuthHandler.start_auth` to check chat type
- Add tests for all new behavior
- Update `--validate-i18n` (automatic — it validates against template)

## Out of Scope

- Group-aware per-user session isolation (tracked in #151)
- Admin override for group chats (future enhancement)

---

## Phase 1: Config & Translation Infrastructure

### Task 1.1: Add `chatMode` config key

**Files:**
- Modify: `config_example.yaml:136-138` (security section)
- Modify: `tests/conftest.py:71` (MOCK_CONFIG_DATA security section)

Add `chatMode: private_only` under the existing `security` section in config_example.yaml. Add the same key to MOCK_CONFIG_DATA so tests have it available.

**Config example change:**
```yaml
security:
  enableAdmin: false
  enableAllowlist: false
  chatMode: private_only  # Options: private_only, allow_all
```

**MOCK_CONFIG_DATA change:**
```python
"security": {"enableAdmin": False, "enableAllowlist": False, "chatMode": "private_only"},
```

### Task 1.2: Add `PrivateChatOnly` translation key

**Files:**
- Modify: `translations/addarr.en-us.yml` (and all 8 other locales + template)

Add a flat top-level key `PrivateChatOnly` near the other auth-related keys. The message should explain that the bot only works in private/direct chats.

**English:**
```yaml
PrivateChatOnly: "🔒 This bot only works in private chats. Please message me directly."
```

Other locales get the same English text (maintainers can translate later). Template gets an empty value.

---

## Phase 2: Core Enforcement

### Task 2.1: Add chat type check to `require_auth` decorator

**Files:**
- Modify: `src/bot/handlers/auth.py:37-51` (require_auth function)
- Test: `tests/test_handlers/test_auth_handler.py`

Add a chat type check at the top of `require_auth`, before the authentication check. Read `security.chatMode` from config. If `private_only` and chat type is not `"private"`, reply with `PrivateChatOnly` and return.

**Key implementation detail:** `update.effective_chat` works for both message updates and callback queries. Use it instead of `update.message.chat`. For the rejection reply, handle both paths:
- If `update.message` exists: `update.message.reply_text()`
- If `update.callback_query` exists: `update.callback_query.answer(text, show_alert=True)`

**Updated decorator logic:**
```python
def require_auth(func):
    @wraps(func)
    async def wrapped(self, update, context, *args, **kwargs):
        if not update.effective_user:
            return

        # Chat type enforcement
        chat_mode = config.get("security", {}).get("chatMode", "private_only")
        if chat_mode == "private_only" and update.effective_chat:
            if update.effective_chat.type != "private":
                translation = TranslationService()
                msg = translation.get_text(
                    "PrivateChatOnly",
                    default="🔒 This bot only works in private chats."
                )
                if update.callback_query:
                    await update.callback_query.answer(msg, show_alert=True)
                elif update.message:
                    await update.message.reply_text(msg)
                return

        # Existing auth check
        if not AuthHandler.is_authenticated(update.effective_user.id):
            ...
        return await func(self, update, context, *args, **kwargs)
    return wrapped
```

**Tests to add:**
1. `test_require_auth_rejects_group_chat` — group chat type with private_only mode → rejected
2. `test_require_auth_rejects_supergroup_chat` — supergroup → rejected
3. `test_require_auth_allows_private_chat` — private chat → proceeds to auth check
4. `test_require_auth_allows_group_when_allow_all` — group chat with allow_all mode → proceeds
5. `test_require_auth_rejects_group_via_callback` — callback query in group → answered with alert

### Task 2.2: Add chat type check to `AuthHandler.start_auth`

**Files:**
- Modify: `src/bot/handlers/auth.py:102-128` (start_auth method)
- Test: `tests/test_handlers/test_auth_handler.py`

Add the same chat type check at the start of `start_auth`, before the "already authenticated" check. This protects the password flow from group exposure.

**Tests to add:**
1. `test_start_auth_rejects_group_chat` — group chat → replies with PrivateChatOnly, returns END
2. `test_start_auth_allows_private_chat` — private chat → normal flow continues
3. `test_start_auth_allows_group_when_allow_all` — allow_all mode → normal flow

---

## Phase 3: Test Fixture Updates

### Task 3.1: Enhance `make_update` fixture for chat type testing

**Files:**
- Modify: `tests/conftest.py:338-362` (make_update fixture)

Add a `chat_type` parameter to `make_update` so tests can easily create group/supergroup updates. Currently `make_message` already sets `chat.type` based on `chat_title`, but `make_update` doesn't expose this.

**Updated fixture:**
```python
def _make_update(text=None, callback_data=None, user=None, chat_type=None):
    ...
    if callback_data is not None:
        msg = make_message(user=_user, chat_title="Group" if chat_type == "group" else None)
        if chat_type:
            msg.chat.type = chat_type
        ...
    else:
        msg = make_message(text=text or "test", user=_user, chat_title="Group" if chat_type and chat_type != "private" else None)
        if chat_type:
            msg.chat.type = chat_type
        ...
    update.effective_chat = msg.chat
    ...
```

**Note:** `update.effective_chat` must be set for ALL update types (currently only set for text message updates at line 359, not callback query updates). Fix this.

---

## Verification

1. `pytest --tb=short -q` — all tests pass
2. `python -m flake8 .` — no lint errors
3. `PYTHONIOENCODING=utf-8 python run.py --validate-i18n` — translations valid
4. `pytest --cov=src.bot.handlers.auth --cov-report=term-missing` — 100% coverage on new lines

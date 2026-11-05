---
title: "Delete dead code and its tests"
labels: [tech-debt, python, priority:low, agent-ready]
slice: 31
findings: [F260]
---

## Problem

**F260** This code has no live caller:

- `src/utils/helpers.py`: `check_auth`, `get_authorized_chats`, `save_chat_id` (`:18-51`) and `is_authenticated` (`:87-89`)
- `src/definitions.py`: `load_config` to `is_allowed_chat` (`:39-67`), once F070 is fixed
- `src/models/media.py` and `src/models/notification.py`
- `get_metadata_profiles` in `src/api/lidarr.py:253`
- `log_exception` in `src/utils/logger.py:136`
- `show_token_help` in `src/utils/splash.py:118`
- the `"message"` key in `src/services/media.py:303`, `:372`, `:441`, which nothing reads
- the unused `States` constants in `src/bot/states.py` (the real ones are in `src/bot/handlers/media/dispatch.py`)

## Expected behavior

`src/` has no function, module or key without a live reader.

## Fix

- [ ] **F260** Delete the listed code with its tests (`src/utils/helpers.py:18-51`, `:87-89`; `src/definitions.py:39-67`; `src/models/media.py`; `src/models/notification.py`; `src/api/lidarr.py:253`; `src/utils/logger.py:136`; `src/utils/splash.py:118`; `src/services/media.py:303`, `:372`, `:441`; `src/bot/states.py`)

## Acceptance criteria

- [ ] `grep -n "^def " src/definitions.py` returns nothing.
- [ ] `src/models/media.py`, `src/models/notification.py` and `src/bot/states.py` are gone, and so are their tests (for example `tests/test_bot/test_states.py`).
- [ ] `grep -rn "def check_auth\|def get_authorized_chats\|def save_chat_id\|def is_authenticated\|def get_metadata_profiles\|def log_exception\|def show_token_help" src` returns nothing.
- [ ] `grep -n '"message": profile_text' src/services/media.py` returns nothing.
- [ ] `pytest` (coverage stays at 100%, architecture tests included), `flake8` and `mypy src/` pass.

## Notes

- Source: audit 2026-10-28, docs/issues/audit-2026-10-28/FINDINGS.md (F-ids F260).
- Priority: max P 12, sum P 12, `priority:low`.
- Depends on slice 7 (F070): `/settings` and `/webhooks` import `src.definitions.is_admin` until F070 is fixed. Delete the `definitions.py` functions only after F070 lands.
- Slice 30 (F251) deletes `tests/test_models/test_media.py` and `test_notification.py`. Do that in the same PR as the model deletion.
- CLAUDE.md names `src/bot/states.py` as the home of the conversation states. Update those lines when the file goes.
- Related open issues: none.

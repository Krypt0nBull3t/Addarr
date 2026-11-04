# 0003. Handler registration order, with Start last

**Status:** Accepted. Recorded 2026-11-04; Start moved last on 2026-10-27 (commit 3d03ea6).

## Context

`python-telegram-bot` gives an update to the first registered handler that matches it. `StartHandler` has a `menu_cancel` callback. Registered before the conversations, it would take a Cancel tap meant for an open media or settings conversation, and that conversation would stay open.

## Decision

`AddarrBot._add_handlers()` in `src/main.py` registers handlers in this order: Auth, Media, Settings, the other feature handlers, Help, Preferences, System, and Start last. The Transmission, SABnzbd and Bazarr handlers are registered only when their service is enabled.

Pinned by `test_menu_cancel_still_ends_media_search` in `tests/integration/test_start_flow.py`.

## Consequences

- A new handler goes before `StartHandler`.
- A new handler whose pattern overlaps an existing one must be placed after the conversation it could steal from. Check it with an integration test.

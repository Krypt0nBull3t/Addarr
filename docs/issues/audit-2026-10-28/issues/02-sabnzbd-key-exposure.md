---
title: "SABnzbd API key leaks into logs and /status"
labels: [bug, security, agent-ready, priority:critical]
slice: 2
findings: [F011, F010]
---

## Bug

The SABnzbd API key travels in the query string (`apikey=`). aiohttp error text can contain the full request URL. The bot shows that text to users and writes it to the logs.

- **F011** /status Details shows the SABnzbd key. The health check returns `f"Error: {str(e)}"`. aiohttp errors such as `TooManyRedirects` contain the URL with `apikey=`. The Details view prints that status as is.
- **F010** aiohttp `ContentTypeError` text contains the URL with `apikey=` (reproduced). Every `except` block in the SABnzbd service logs `{e}`.

## Steps to reproduce

F011:

1. Point `sabnzbd.server` at a host that answers the API with a redirect loop.
2. Send /status and open Details.
3. The SABnzbd line shows `Error: ...apikey=<key>...`.

F010:

1. Point `sabnzbd.server` at a host that answers 200 with HTML, for example a proxy login page.
2. Set a SABnzbd speed limit from the bot.
3. `response.json()` raises `ContentTypeError`. The log line `Error setting SABnzbd speed limit: ...` contains `apikey=<key>`.

## Expected behavior

No user-facing text and no log line contains the SABnzbd API key. Errors show only the exception type.

## Fix

- [ ] **F011** Return `f"Error: {type(e).__name__}"` from the SABnzbd health check (`src/services/health.py:308-309`; shown by `src/bot/handlers/system.py:240`)
- [ ] **F010** Log `type(e).__name__`, not `{e}`, in every `except` block (`src/services/sabnzbd.py:90`; all blocks: `:58`, `:90`, `:112`, `:134`, `:158`, `:182`, `:236`, `:263`)

## Acceptance criteria

Each test below fails before the fix and passes after it.

- **F011** `tests/test_services/test_health_service.py`: the SABnzbd request raises `aiohttp.TooManyRedirects` whose text contains `apikey=secret`. The returned status is `Error: TooManyRedirects` and does not contain `secret`.
- **F010** `tests/test_services/test_sabnzbd_service.py`: parametrize over every method with an `except` block. The mocked response is 200 with `content_type="text/html"`, or raises an error whose text holds the key. No captured log message contains the API key.
- `pytest`, `flake8` and `mypy src/` pass.

## Notes

- Source: audit 2026-10-28, docs/issues/audit-2026-10-28/FINDINGS.md (F-ids F011, F010).
- Priority: max P 45, sum P 85 (critical).
- Dependencies: slices 1-8 go first. No other slice blocks this one.
- No owner decision needed.

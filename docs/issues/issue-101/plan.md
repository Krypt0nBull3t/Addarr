# Issue #101: SABnzbd Queue Dashboard

## Context

Users have no visibility into SABnzbd download status from Telegram. The API client (`SabnzbdClient`) and service (`SABnzbdService`) already provide `get_queue()`, `get_history()`, `pause_queue()`, `resume_queue()`, and `get_status()`, but no handler exposes this data. The current `/sabnzbd` handler only offers speed limit controls.

## Goal

Add a `/downloads` command that displays a SABnzbd queue dashboard with:
- Active downloads showing title, progress %, speed, ETA, and queue size
- Recent download history
- Per-item pause/resume inline buttons
- Pagination for large queues
- Refresh button to update the display

## Design Decisions

### 1. New `/downloads` command (not extending `/sabnzbd`)

**Rationale:** `/sabnzbd` is for speed control (settings-oriented). `/downloads` is for monitoring (dashboard-oriented). Different concerns, different handlers.

### 2. No ConversationHandler needed

The dashboard is a single-message display with inline buttons for actions (refresh, pagination, tab switching, per-item controls). All interactions are callback queries that edit the same message. A `CommandHandler` + `CallbackQueryHandler` pattern (like `TransmissionHandler`) is sufficient.

### 3. Tab-based view: Queue vs History

Two views switchable via inline buttons:
- **Queue tab** (default): Active/queued downloads with progress, speed, ETA
- **History tab**: Recently completed downloads with status and size

### 4. Per-item pause/resume

SABnzbd API supports per-item control via:
- `mode=queue&name=pause&value=<nzo_id>` — pause individual item
- `mode=queue&name=resume&value=<nzo_id>` — resume individual item

Need to add these methods to both `SabnzbdClient` and `SABnzbdService`.

### 5. Callback data conventions

Following existing patterns (`sabnzbd_speed_`, `queue_page_`, etc.):
- `dl_tab_queue` / `dl_tab_history` — tab switching
- `dl_page_{n}` — pagination
- `dl_pause_{nzo_id}` — pause individual item
- `dl_resume_{nzo_id}` — resume individual item
- `dl_pause_all` / `dl_resume_all` — pause/resume entire queue
- `dl_refresh` — refresh current view

### 6. Queue slot fields (from SABnzbd API)

Queue slots contain: `nzo_id`, `filename`, `status` (Downloading/Queued/Paused), `percentage`, `mb`/`mbleft`, `timeleft`, `avg_age`, `size`.

History slots contain: `nzo_id`, `name`, `status` (Completed/Failed), `size`, `download_time`, `completed_stamps`.

## Target Structure

### Files to modify
- `src/api/sabnzbd.py` — Add `pause_item()`, `resume_item()` methods
- `src/services/sabnzbd.py` — Add `pause_item()`, `resume_item()`, `get_queue_details()` methods
- `src/bot/handlers/sabnzbd.py` — Extend with `/downloads` command and callback handlers
- `src/bot/keyboards.py` — Add `get_downloads_dashboard_keyboard()`, `get_downloads_history_keyboard()`
- `src/bot/commands.py` — Register `/downloads` command
- `translations/addarr.en-us.yml` — Add translation keys

### Files to create
- `tests/bot/handlers/test_downloads_handler.py` — Handler tests
- `tests/api/test_sabnzbd_downloads.py` — API client tests for new methods
- `tests/services/test_sabnzbd_downloads.py` — Service tests for new methods
- `tests/bot/test_keyboards_downloads.py` — Keyboard builder tests

### No new files in src/
The feature extends existing modules. No new handler class needed — extend `SabnzbdHandler` with the downloads dashboard functionality.

## Phased Approach

### Phase 1: API + Service Layer (per-item control + queue details)
Add `pause_item()` and `resume_item()` to API client and service. Add `get_queue_details()` to service that returns normalized queue data with all fields needed for display.

### Phase 2: Keyboard Builders
Add keyboard functions for the downloads dashboard (queue view, history view, pagination, per-item controls).

### Phase 3: Handler + Command Registration
Extend `SabnzbdHandler` with `/downloads` command, tab switching, pagination, per-item pause/resume, and refresh callbacks. Register the command in `commands.py`.

### Phase 4: Translations
Add all user-facing strings as translation keys.

## Message Format (Queue Tab)

```
📥 SABnzbd Downloads

⚡ Speed: 5.2 MB/s | 📦 Queue: 3 items | 💾 Remaining: 1.2 GB

1. Movie.Name.2024.1080p
   ▓▓▓▓▓▓▓░░░ 72% | 15m left | ⏸ Pause

2. TV.Show.S03E05
   ▓▓▓░░░░░░░ 30% | 45m left | ⏸ Pause

3. Another.Movie [Paused]
   ▓░░░░░░░░░ 12% | — | ▶️ Resume

[◀️ Prev] [1/2] [Next ▶️]
[📋 Queue ✓] [📜 History]
[⏸ Pause All] [🔄 Refresh]
```

## Message Format (History Tab)

```
📜 SABnzbd History

1. ✅ Movie.Name.2024 — 4.2 GB — 2h 15m
2. ✅ TV.Show.S03E04 — 1.1 GB — 35m
3. ❌ Failed.Download — 0 B — Failed

[◀️ Prev] [1/2] [Next ▶️]
[📋 Queue] [📜 History ✓]
[🔄 Refresh]
```

## Verification

1. `python -m pytest tests/api/test_sabnzbd_downloads.py -v` — API client tests pass
2. `python -m pytest tests/services/test_sabnzbd_downloads.py -v` — Service tests pass
3. `python -m pytest tests/bot/handlers/test_downloads_handler.py -v` — Handler tests pass
4. `python -m pytest tests/bot/test_keyboards_downloads.py -v` — Keyboard tests pass
5. `python -m pytest --tb=short -q` — Full suite green
6. `python -m flake8 .` — No lint errors
7. `PYTHONIOENCODING=utf-8 python run.py --validate-i18n` — Translations valid

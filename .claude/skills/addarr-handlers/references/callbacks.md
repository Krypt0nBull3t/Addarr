# Callback Data Conventions

## Naming Format

```
<prefix>_<value>[_<value2>...]
```

All callback data is a flat string with underscore-delimited segments. Max 64 bytes (Telegram limit).

## Prefix Registry

Built from the `CallbackQueryHandler(..., pattern=...)` calls in `src/bot/handlers/`. Handlers are listed in `_add_handlers()` order (see [wiring.md](wiring.md)). AuthHandler registers no callbacks. Placeholders in `<angle brackets>` are filled at runtime.

| Prefix / data | Handler | Example | Description |
|-|-|-|-|
| `menu_movie` / `menu_series` / `menu_music` | MediaHandler | `menu_movie` | Start a media search (conversation entry) |
| `menu_cancel` | MediaHandler | `menu_cancel` | Cancel the media conversation (every state) |
| `select_` | MediaHandler | `select_<result id>`, `select_cancel` | Pick a search result; `select_cancel` also ends season selection |
| `nav_` | MediaHandler | `nav_next_<index>`, `nav_prev_<index>` | Card view navigation |
| `listsel_` | MediaHandler | `listsel_3` | List view item selection |
| `listback` | MediaHandler | `listback` | Back from the detail view to the list |
| `listpage_` | MediaHandler | `listpage_2`, `listpage_noop` | List view pagination |
| `viewtoggle` | MediaHandler | `viewtoggle` | Toggle card/list view |
| `quality_` | MediaHandler | `quality_<profile id>`, `quality_cancel` | Quality profile selection |
| `season_` | MediaHandler | `season_5`, `season_all`, `season_confirm`, `season_future_seasons`, `season_future_episodes`, `season_monitor_all` | Season selection (buttons built in `src/bot/handlers/media/season_picker.py`) |
| `album_monitor_mode_` | MediaHandler | `album_monitor_mode_all`, `album_monitor_mode_pick` | Lidarr: monitor all albums or pick |
| `albumsel_` | MediaHandler | `albumsel_<album id>`, `albumsel_all`, `albumsel_confirm`, `albumsel_future`, `albumsel_monitor_all` | Lidarr album selection (`get_album_selection_keyboard` in `src/bot/keyboards.py`) |
| `menu_settings` | SettingsHandler | `menu_settings` | Open settings (conversation entry) |
| `settings_` | SettingsHandler | `settings_language`, `settings_radarr`, `settings_downloads`, `settings_users`, `settings_back` | Settings sub-menus and back |
| `lang_` | SettingsHandler | `lang_en-us` | Language selection |
| `svc_toggle_` | SettingsHandler | `svc_toggle_radarr` | Enable/disable a service |
| `svc_quality_` | SettingsHandler | `svc_quality_radarr` | Open the default quality menu of a service |
| `setquality_` | SettingsHandler | `setquality_radarr_42` | Default quality setting |
| `dl_transmission` / `dl_sabnzbd` | SettingsHandler | `dl_transmission` | Open Transmission or SABnzbd settings |
| `dl_trans_` | SettingsHandler | `dl_trans_toggle`, `dl_trans_turtle` | Transmission enable and turtle mode |
| `dl_sab_` | SettingsHandler | `dl_sab_toggle`, `dl_sab_speed`, `dl_sab_speed_25`, `dl_sab_pause`, `dl_sab_resume` | SABnzbd settings |
| `dl_back` | SettingsHandler | `dl_back` | Back from download client settings |
| `usr_` | SettingsHandler | `usr_toggle_admin`, `usr_toggle_allowlist`, `usr_back` | User access settings |
| `menu_cancel` | SettingsHandler | `menu_cancel` | Cancel settings (fallback) |
| `wh_` | WebhooksHandler | `wh_setup_radarr`, `wh_regen_radarr`, `wh_events`, `wh_toggle_<event>`, `wh_port`, `wh_back`, `wh_close` | Webhook management |
| `delete_` | DeleteHandler | `delete_type_movie`, `delete_page_<type>_<n>`, `delete_item_<type>_<id>`, `delete_confirm_<type>_<id>`, `delete_cancel` | Delete media; the type and id travel in the callback, never in `user_data` |
| `library_` | LibraryHandler | `library_movie`, `library_series`, `library_music` | Library type selection |
| `lib_` | LibraryHandler | `lib_m_2` (`m`/`s`/`a` = movie/series/music) | Library pagination |
| `cal_` | CalendarHandler | `cal_period_7`, `cal_page_2`, `cal_add_movie_<id>`, `cal_refresh`, `cal_back`, `cal_noop` | Calendar browsing and adding |
| `missing_` | MissingHandler | `missing_filter_movie`, `missing_page_2`, `missing_search_<service>_<id>`, `missing_refresh`, `missing_back`, `missing_noop` | Missing/wanted media |
| `queue_` | QueueHandler | `queue_filter_movie`, `queue_page_2`, `queue_refresh`, `queue_back`, `queue_noop` | Queue browsing |
| `hist_` | HistoryHandler | `hist_filter_all`, `hist_page_2`, `hist_refresh`, `hist_back`, `hist_noop` | History browsing |
| `transmission_` | TransmissionHandler | `transmission_toggle_yes`, `transmission_toggle_no` | Confirm the `/transmission` turtle mode toggle |
| `sabnzbd_speed_` | SabnzbdHandler | `sabnzbd_speed_25`, `sabnzbd_speed_50`, `sabnzbd_speed_100` | `/sabnzbd` speed limit |
| `bazarr_` | BazarrHandler | `bazarr_menu`, `bazarr_search`, `bazarr_wanted_movies`, `bazarr_wanted_episodes`, `bazarr_cancel` | Bazarr subtitles |
| `dl_client_` | DownloadsHandler | `dl_client_tx`, `dl_client_sab` | Switch download client |
| `dl_tab_` | DownloadsHandler | `dl_tab_queue`, `dl_tab_history` | Queue/history tab |
| `dl_page_` | DownloadsHandler | `dl_page_2` | Downloads pagination |
| `dl_pause_` / `dl_resume_` | DownloadsHandler | `dl_pause_<nzo_id>`, `dl_resume_<nzo_id>` | Pause/resume one item (pattern `(?!all)` excludes the next row) |
| `dl_pauseall` / `dl_resumeall` | DownloadsHandler | `dl_pauseall` | Pause/resume everything |
| `dl_refresh` / `dl_noop` | DownloadsHandler | `dl_refresh` | Refresh; `dl_noop` is a disabled button |
| `menu_back` | HelpHandler | `menu_back` | Back from help to the main menu |
| `pref_toggle_view` | PreferencesHandler | `pref_toggle_view` | Toggle the card/list view preference |
| `system_` | SystemHandler | `system_details`, `system_diskspace`, `system_refresh`, `system_back` | System status |
| `menu_cancel` / `menu_status` / `menu_upcoming` / `menu_library` / `menu_help` / `menu_delete` | StartHandler | `menu_status` | Main menu buttons that start no conversation (registered last) |

## Pattern Matching in ConversationHandler

```python
# Exact match (use $ anchor)
CallbackQueryHandler(self.handle_cancel, pattern="^menu_cancel$")

# Prefix match (captures all with prefix)
CallbackQueryHandler(self.handle_selection, pattern="^select_")

# Multi-prefix match (regex OR)
CallbackQueryHandler(self.handle_nav, pattern="^(nav_|listpage_)")
```

**Rules:**
- Use `$` anchor for exact matches only
- Prefix-only patterns (no `$`) match any suffix
- More specific patterns must be registered before general ones
- Within a state dict, PTB tries handlers top-to-bottom

## Data Extraction Patterns

### Single value
```python
# callback_data = "select_603" or "select_cancel"
selection = query.data.replace("select_", "")  # "603": result ids are strings
if selection == "cancel":
    await send_response(query.message, "🚫 Search cancelled.")
    return ConversationHandler.END
results = context.user_data.get("search_results", [])
selected = next((r for r in results if r["id"] == selection), None)
```

Search result ids are strings (`str(tmdbId)`, `str(tvdbId)`, `album:<id>`), built in `src/services/media.py`. Do not cast them to `int`.

### Multi-part value
```python
# callback_data = "setquality_radarr_42"
parts = query.data.split("_")
# parts[0] = "setquality", parts[1] = "radarr", parts[2] = "42"
service = parts[1]
profile_id = int(parts[2])
```

### Boolean/toggle
```python
# callback_data = "svc_toggle_radarr"
service_name = query.data.replace("svc_toggle_", "")
current = config.get(service_name, {}).get("enable", False)
config.update_nested(f"{service_name}.enable", not current)
config.save()
```

### Noop pattern
```python
# callback_data = "listpage_noop" (disabled pagination button)
suffix = query.data.replace("listpage_", "")
if suffix == "noop":
    await query.answer()  # Acknowledge but do nothing
    return current_state
page = int(suffix)
```

## Adding a New Prefix

1. Choose a unique prefix not in the registry above
2. Keep it short (callback_data max 64 bytes)
3. Add the handler to the appropriate state in your ConversationHandler
4. Document the prefix in this registry

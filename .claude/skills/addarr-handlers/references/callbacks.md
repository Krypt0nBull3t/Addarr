# Callback Data Conventions

## Naming Format

```
<prefix>_<value>[_<value2>...]
```

All callback data is a flat string with underscore-delimited segments. Max 64 bytes (Telegram limit).

## Prefix Registry

| Prefix | Handler | Example | Description |
|--------|---------|---------|-------------|
| `menu_` | MediaHandler | `menu_movie`, `menu_series`, `menu_cancel` | Main menu actions |
| `select_` | MediaHandler | `select_123` | Media selection by index |
| `nav_` | MediaHandler | `nav_next_5`, `nav_prev_3` | Card view navigation |
| `quality_` | MediaHandler | `quality_42` | Quality profile selection |
| `season_` | MediaHandler | `season_5`, `season_confirm` | Season selection |
| `listsel_` | MediaHandler | `listsel_3` | List view item selection |
| `listpage_` | MediaHandler | `listpage_2`, `listpage_noop` | List view pagination |
| `viewtoggle` | MediaHandler | `viewtoggle` | Toggle card/list view |
| `lang_` | SettingsHandler | `lang_en-us` | Language selection |
| `setquality_` | SettingsHandler | `setquality_radarr_42` | Default quality setting |
| `svc_toggle_` | SettingsHandler | `svc_toggle_radarr` | Enable/disable service |
| `dl_trans_` | SettingsHandler | `dl_trans_turtle` | Transmission settings |
| `dl_sab_` | SettingsHandler | `dl_sab_speed`, `dl_sab_speed_25` | SABnzbd settings |
| `settings_` | SettingsHandler | `settings_back` | Settings navigation |
| `delete_` | DeleteHandler | `delete_movie_123` | Delete media |
| `lib_` | LibraryHandler | `lib_movies`, `lib_page_2` | Library browsing |
| `pref_` | PreferencesHandler | `pref_view_list` | Preference changes |

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
# callback_data = "select_42"
index = int(query.data.replace("select_", ""))  # 42
```

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

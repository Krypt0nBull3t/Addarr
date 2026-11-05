# Issue 217: stuck spinners and dead ends in Telegram navigation

Line numbers are from `cf51f57`. Each root cause was read in the code.

## Root causes

| Finding | Root cause | Fix |
|-|-|-|
| F110 | `_handle_filter` in `queue.py:104`, `missing.py:110`, `history.py:105`, `_refresh_current_view` in `downloads.py:323`, SAB pause in `settings.py:648`, and `_handle_details` and `_handle_diskspace` in `system.py:150`, `:170` call `edit_text`. On a re-tap Telegram raises "Message is not modified". In `queue.py`, `missing.py`, `history.py` and `system.py` `query.answer()` runs after the edit, so the spinner stays. | Use `edit_text_ignoring_unmodified` (`src/utils/chat.py`). Call `query.answer()` before the edit. |
| F115 | `show_queue` and `show_missing` use `setdefault`, so an old filter survives. `_build_response` in queue, missing and history returns the `*_empty_keyboard` (no filter row) when the filtered list is empty. `missing._handle_filter` never refetches for movie or series, so it filters the cached cutoff list. | Assign `"all"` on entry. Use the items keyboard when items exist or a filter other than all is active. Refetch `get_missing_media` on movie and series. |
| F113 | Help, the library list and both Bazarr wanted replies have no keyboard. No keyboard has a `bazarr_menu` button. | Add Back: Help `menu_back`, library list `menu_library`, Bazarr wanted `bazarr_menu`. The three handlers already exist. |
| F114 | `start.py:92` calls `edit_text` on a message that can be a photo. | Use `formatters.send_response`. |
| F112 | SAB speed Back is `dl_back` and quality Back is `settings_back`: both go to the settings root. `handle_back` ends with the "End" text and no keyboard. | SAB speed Back `dl_sabnzbd`. Quality Back `settings_<service>`, and route it in the `SETTINGS_QUALITY` state. `handle_back` edits to the main menu text and keyboard before END. |
| F111 | `handle_menu_callback` calls `query.answer()` only on the cancel path. | Call `query.answer()` at the top. |

## Scope

- F115 needs no new pagination row, so `_build_pagination_row` is not used. The other pagination copies stay for #223.
- `_handle_page` in queue, missing and history keeps `edit_text`. A page button always changes the page, so a re-tap cannot hit it.
- No new translation keys. The `Back` key exists.

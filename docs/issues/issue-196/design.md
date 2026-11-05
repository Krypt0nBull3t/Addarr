# Issue 196 design: /delete acts on the wrong item and hides file deletion

Issue: https://github.com/Krypt0nBull3t/Addarr/issues/196 (F003, F001, F002, F004).

## Root cause

`src/bot/handlers/delete.py` keeps the media type (`user_data["delete_type"]`) and the
chosen item (`user_data["delete_item"]`) in `context.user_data`. The buttons carry only an
id (`delete_item_<id>`, `delete_confirm`). The type and item are read when the user taps,
not when the button was drawn. Radarr and Sonarr ids collide, so a tap on an old list acts
on a different item of the newest type. `ThisDelete` has no `%{title}` placeholder and no
mention of files, while every delete sends `deleteFiles=true`. The item list builds one
button per library item, so a library of about 100 items or more hits Telegram's keyboard cap.

## Decisions (decided 2026-10-28 and in the step 3 review)

- Prompt only for F001: the confirm text shows the title and says the files on disk are deleted too.
  Keep `deleteFiles=true`, the config and the `enableAdmin` default. No keep-files option.
- Callback data carries the type and id: `delete_item_<type>_<id>`,
  `delete_confirm_<type>_<id>`, `delete_page_<type>_<page>`. `delete_type_<type>` and
  `delete_cancel` stay. The longest value, `delete_confirm_series_<id>`, stays far under 64 bytes.
- The handler stores nothing in `user_data` for this flow. Page taps refetch the list.
  The confirm step refetches the item by type and id, for the title in the result message.
  A missing item shows `NoExist`.
- An unknown type shows `InvalidMediaType`. A non-digit id, or a callback that does not split
  into type and id, shows `ItemDataNotFound`.
- Pagination: one new helper `_build_pagination_row(prefix, page, total_pages)` in
  `src/bot/keyboards.py`, as issue #223 (F265) specifies. It clamps the page. Only /delete
  uses it here. Replacing the other copies is #223 work. Page size is 10, as in `library.py`.
- Locales: the 8 non-English files and the template get the new `ThisDelete` text.
  The fr, it, pt and de texts stay plain, because #224 (F211) rewrites them.

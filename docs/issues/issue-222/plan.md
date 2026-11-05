# Issue 222: Fix /help command list, post-auth menu and History labels

Issue: https://github.com/Krypt0nBull3t/Addarr/issues/222 (audit findings F120, F093, F121, F122).
Branch: `fix/222-fix-help-list-auth-menu-history-labels`, from `development` at `cf51f57`.
No design.md: the four fixes are small, independent and prescribed by the issue.

## Context and root causes

Line numbers in the issue moved after the six critical fixes. These are current.

- **F093** `src/bot/handlers/auth.py:224-227` (`check_password`) sends the text `/start` with `context.bot.send_message`. A bot never receives its own messages, so no menu opens.
- **F121** `src/bot/handlers/system.py`: `show_status` (`:84-92`), the unknown-action fallback (`:117`), `_handle_refresh` (`:130`) and `_handle_details` (`:150`) send `*bold*` text with no `parse_mode`. `_build_status_text` and `_build_details_text` (`:194-242`) put service names and the health `status` string in that text. They can hold `_` or `*`, which break Markdown parsing once `parse_mode` is set.
- **F122** `src/bot/keyboards.py`: `get_history_items_keyboard` marks the active filter with a bullet (`:1173`). The `hist_refresh` button uses the `Search` key (`:1220`, and in `get_history_empty_keyboard` `:1237`). Other screens hardcode `"\U0001f504 Refresh"` (`:117`, `:542`, `:624`, `:736`), and the downloads tabs mark the active tab with `"✓ "` (`:1103`).
- **F120** `HelpHandler._build_help_text` (`src/bot/handlers/help.py:35-59`) has no entries for `/preferences`, `/webhooks`, `/upcoming`, `/missing`, `/queue`, `/history`, `/downloads`. `HelpBasicCommands` (all 10 translation files) lists `/library`, which has no `CommandHandler` (only a `menu_library` callback in `start.py`). The gating to follow is `build_authenticated_commands()` in `src/bot/commands.py:31-83`.

## Decisions

- F093: send `translation.get_text("mainMenu")` with `reply_markup=get_main_menu_keyboard()` through `chat.send_message`, as `StartHandler.show_menu` does. No cycle: `keyboards.py` imports only `TranslationService`.
- F121: keep Markdown (as Disk Space does). Pass `parse_mode="Markdown"` on every status and details send. Escape dynamic text (service names, health status strings) with `telegram.helpers.escape_markdown(text, version=1)`. Confirmed by the orchestrator.
- F122: hardcode `"\U0001f504 Refresh"` like the other screens. Active filter prefix is `"✓ "`.
- F120: remove `/library`. Add `/preferences` and `/webhooks` to `HelpBasicCommands` (ungated, as in `build_authenticated_commands`). Add four gated keys, in all 10 files, after `HelpMediaMusic`:
  - `HelpCalendar` (`/upcoming`, `/missing`): radarr or sonarr
  - `HelpQueue` (`/queue`): radarr, sonarr or lidarr
  - `HelpHistory` (`/history`): radarr or sonarr
  - `HelpDownloads` (`/downloads`): sabnzbd or transmission
- Locale values of the new keys and the changed `HelpBasicCommands` lines are English in the 8 non-template locales, as the existing `Help*` block already is. #224 (F210) translates the `Help*` keys; the PR body says so. The i18n-key rule 5 (translate) is deferred to #224 by the orchestrator.

## Tasks (TDD, each ends with a commit)

### 1. F093 post-auth menu

Files: `src/bot/handlers/auth.py`, `tests/test_handlers/test_auth_handler.py`.

- Test `test_check_password_correct_sends_main_menu`: patch `src.bot.handlers.auth.TranslationService` (key-echo) and `src.bot.handlers.auth.get_main_menu_keyboard`. After a correct password assert `chat.send_message` got a call with `"mainMenu"` and `reply_markup=<the patched keyboard return>`, and that no `chat.send_message` or `context.bot.send_message` call has text `"/start"`. Fails before the fix.
- Fix: import `get_main_menu_keyboard` from `src.bot.keyboards`. Replace the `context.bot.send_message(chat.id, "/start")` block with `chat.send_message(self.translation.get_text("mainMenu"), reply_markup=get_main_menu_keyboard())`.

### 2. F121 status and details parse mode

Files: `src/bot/handlers/system.py`, `tests/test_handlers/test_system_handler.py`.

- Tests (fail before the fix): assert `parse_mode == "Markdown"` on `show_status` (command `reply_text` and callback `edit_text`), `_handle_refresh` (`edit_text_ignoring_unmodified` call), `_handle_details`, and the unknown-action fallback. Add `test_handle_details_escapes_markdown_in_error`: health result with `{"name": "Radarr_v3", "healthy": False, "status": "Error: a_b *x*"}`; assert the sent text contains `Radarr\_v3` and `a\_b \*x\*`. Add the same for `unhealthy_services=["my_service"]` in the status text.
- Fix: add `_md(text) -> str` (`escape_markdown(str(text), version=1)`). Use it for each service name and status in `_build_status_text` and `_build_details_text`. Add `parse_mode="Markdown"` to the five calls above.

### 3. F122 History labels

Files: `src/bot/keyboards.py`, `tests/test_bot/test_keyboards.py`.

- Tests: in `TestHistoryItemsKeyboard` and `TestHistoryEmptyKeyboard`, assert the `hist_refresh` button text equals `"\U0001f504 Refresh"` and does not contain `Search`. Change `test_filter_active_highlight` to expect the `"✓ "` prefix on the active tab and none on the others. Fail before the fix.
- Fix: the three lines named in the root cause.

### 4. F120 help text

Files: `src/bot/handlers/help.py`, `translations/addarr.template.yml`, the 9 `translations/addarr.<locale>.yml`, `tests/test_handlers/test_help_handler.py`.

- Tests (fail before the fix), using the shipped `translations/addarr.en-us.yml` (root key `en-us`) through a stub `TranslationService.get_text(key, **kw)` that formats `%(version)s`:
  - `test_help_lists_new_commands_and_no_library`: all six services enabled; text contains `/preferences`, `/webhooks`, `/upcoming`, `/missing`, `/queue`, `/history`, `/downloads`, and not `/library`.
  - `test_help_hides_arr_and_download_commands_when_off`: all off; `/upcoming`, `/missing`, `/queue`, `/history`, `/downloads` absent, `/preferences` and `/webhooks` present.
  - `test_help_matches_registered_commands` (parametrized over: none, radarr, sonarr, lidarr, transmission, sabnzbd, bazarr, all): patch `config` in both `src.bot.handlers.help` and `src.bot.commands`. The set `re.findall(r"/(\w+) -", help_text)` equals `{c.command for c in build_authenticated_commands()}`. This keeps help and registration from drifting.
- Fix: in `_build_help_text`, add the four gated sections in this order: after the media sections (calendar, queue, history), and downloads after the transmission and sabnzbd lines. Edit the 10 translation files in one pass: replace the `/library` line with the `/preferences` and `/webhooks` lines, and add the four keys in the same position in every file. Values (en-us):
  - Each line starts with one emoji, like the existing `Help*` lines (the i18n validator requires an emoji in every locale).
  - `HelpCalendar`: two lines, `/upcoming - Browse upcoming releases` and `/missing - Browse missing media`
  - `HelpQueue`: `/queue - Browse download queue`
  - `HelpHistory`: `/history - Browse recent activity`
  - `HelpDownloads`: `/downloads - Download queue`
  - `HelpBasicCommands` additions: `/preferences - Manage preferences` and `/webhooks - Manage webhook notifications`
- Check: `PYTHONIOENCODING=utf-8 <lock> .venv/bin/python run.py --validate-i18n` prints `All translations are valid!`.

### 5. Verify

Run scoped checks per task, then the preflight (`references/preflight.md`) once before the PR. Update `docs/issues/issue-222/TASKS.md` completion metadata per task.

## Risks

- #224 edits the same `Help*` blocks: expect a conflict in `translations/*.yml`. Merge `origin/development` before the PR. The PR body tells #224 to translate the new keys.
- The existing test `test_filter_active_highlight` pins the old bullet: it changes in task 3.
- Integration tests send `/start` as a user command, not the bot: unaffected.

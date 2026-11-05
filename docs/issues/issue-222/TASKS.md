# Issue 222: Fix /help command list, post-auth menu and History labels

Plan: `docs/issues/issue-222/plan.md`. Issue: https://github.com/Krypt0nBull3t/Addarr/issues/222.
Run every test and gate through the suite lock (`<lock>` in the addarr-workflow skill).

### Phase 1: Four audit fixes (4 tasks)

**Goal:** /help matches the registered commands, a correct password opens the main menu, status texts parse as Markdown, and History labels match the other screens.

- [ ] **1.1** F093: open the main menu after a correct password
    - **Context:**
        - **Why:** `check_password` sends the text `/start` with `context.bot.send_message`. A bot does not receive its own messages, so no menu opens.
        - **Architecture:** Send the menu the way `StartHandler.show_menu` does: `get_text("mainMenu")` with `reply_markup=get_main_menu_keyboard()`. `src/bot/keyboards.py` imports only `TranslationService`, so there is no import cycle.
        - **Key refs:** `src/bot/handlers/auth.py:223-227`, `src/bot/handlers/start.py:55-66`, `tests/test_handlers/test_auth_handler.py` (`test_check_password_correct`, `test_successful_auth_registers_commands`)
        - **Watch out:** In tests `update.effective_message.chat.send_message` and `context.bot.send_message` are both `AsyncMock`. Assert the text `/start` is sent through neither. Patch `src.bot.handlers.auth.get_main_menu_keyboard`.
    - **Scope:** One send call in `check_password`, one import, one new test
    - **Touches:** `src/bot/handlers/auth.py`, `tests/test_handlers/test_auth_handler.py`
    - **Action items:**
        - [RED] Write `test_check_password_correct_sends_main_menu`: `chat.send_message` is called with `"mainMenu"` and `reply_markup` equal to the patched keyboard, and no send has the text `/start`
        - [GREEN] Replace the `context.bot.send_message(chat.id, "/start")` block with `chat.send_message(self.translation.get_text("mainMenu"), reply_markup=get_main_menu_keyboard())`
    - **Success:** The new test fails before and passes after; `scripts/test_runner.py handlers --coverage` passes; flake8 and mypy clean

- [ ] **1.2** F121: send status and details texts with Markdown and escape dynamic text
    - **Context:**
        - **Why:** `*System Status*` and the other titles show their asterisks, because `show_status`, the refresh, the details view and the unknown-action fallback send no `parse_mode`. Service names and health status strings can hold `_` or `*`, which break parsing once `parse_mode` is set.
        - **Architecture:** Keep Markdown, as Disk Space (`_handle_diskspace`) does. Add a module helper `_md(text) -> str` that returns `telegram.helpers.escape_markdown(str(text), version=1)` and use it for every service name and status in `_build_status_text` and `_build_details_text`.
        - **Key refs:** `src/bot/handlers/system.py:84-92`, `:117`, `:130`, `:150`, `:194-242`; `src/utils/chat.py` (`edit_text_ignoring_unmodified` passes kwargs through); `tests/test_handlers/conftest.py` (`system_handler`)
        - **Watch out:** `escape_markdown(version=1)` escapes `_ * [` and a backtick. The fixed titles (`*System Status*`) must stay unescaped. Error texts from translations (`StatusRefreshError`, `StatusDetailsError`) stay plain, with no `parse_mode`.
    - **Scope:** `parse_mode="Markdown"` on 5 calls, one helper, escaping in two builders
    - **Touches:** `src/bot/handlers/system.py`, `tests/test_handlers/test_system_handler.py`
    - **Action items:**
        - [RED] Write tests that `show_status` (command and callback), `_handle_refresh`, `_handle_details` and the unknown-action fallback pass `parse_mode="Markdown"`
        - [RED] Write `test_handle_details_escapes_markdown_in_error`: a service `Radarr_v3` with status `Error: a_b *x*` gives `Radarr\_v3` and `a\_b \*x\*` in the sent text
        - [RED] Write the same escaping test for an unhealthy service name `my_service` in the status text
        - [GREEN] Add `_md`, use it in both builders, and add `parse_mode="Markdown"` to the five calls
    - **Success:** The new tests fail before and pass after; handlers scoped run passes; flake8 and mypy clean

- [ ] **1.3** F122: History Refresh label and check mark
    - **Context:**
        - **Why:** The History refresh button reads "Search" (the `Search` key), and the active filter tab starts with a bullet. Other screens say Refresh and the downloads tabs use `✓`.
        - **Architecture:** Hardcode `"\U0001f504 Refresh"` like the other keyboards in `keyboards.py` (no new key). Active filter prefix is `"✓ "`.
        - **Key refs:** `src/bot/keyboards.py:1173`, `:1220`, `:1237`; `tests/test_bot/test_keyboards.py` (`TestHistoryItemsKeyboard`, `TestHistoryEmptyKeyboard`, `_mock_translation` returns the key as the text)
        - **Watch out:** `test_filter_active_highlight` pins the old bullet; change it, do not delete it.
    - **Scope:** Three one-line changes and their tests
    - **Touches:** `src/bot/keyboards.py`, `tests/test_bot/test_keyboards.py`
    - **Action items:**
        - [RED] Assert the `hist_refresh` button text equals `"\U0001f504 Refresh"` and has no `Search`, in both History keyboards
        - [RED] Change `test_filter_active_highlight` to expect the `"✓ "` prefix on the active tab and none on the others
        - [GREEN] Change the three lines
    - **Success:** The new tests fail before and pass after; `scripts/test_runner.py bot --coverage` passes

- [ ] **1.4** F120: /help lists the registered commands
    - **Context:**
        - **Why:** /help omits `/preferences`, `/webhooks`, `/upcoming`, `/missing`, `/queue`, `/history`, `/downloads` and lists `/library`, which has no handler.
        - **Architecture:** Gate each section as `build_authenticated_commands()` (`src/bot/commands.py:31-83`) gates it. New keys, in all 10 files after `HelpMediaMusic`: `HelpCalendar` (two lines; radarr or sonarr), `HelpQueue` (radarr, sonarr or lidarr), `HelpHistory` (radarr or sonarr), `HelpDownloads` (sabnzbd or transmission). `/preferences` and `/webhooks` go into `HelpBasicCommands` ungated; its `/library` line goes.
        - **Key refs:** `src/bot/handlers/help.py:35-59`, `translations/addarr.en-us.yml:139-163` (same lines ±10 in the other files), `tests/test_handlers/test_help_handler.py` (`_make_config`, `_help_patches`), `.claude/skills/i18n-key/SKILL.md`
        - **Watch out:** Non-template locale values are English, as the existing Help block is (orchestrator ruling; #224 translates them, and the PR body names the keys). Each line starts with one emoji or the i18n validator fails. Quote values that start with an emoji. The help parity test needs `config` patched in both `src.bot.handlers.help` and `src.bot.commands`. The registered-command regex is `r"/(\w+) -"`.
    - **Scope:** `_build_help_text` gating, 4 new keys and 2 changed lines in 10 files, 3 new tests
    - **Touches:** `src/bot/handlers/help.py`, `translations/addarr.template.yml`, the 9 `translations/addarr.<locale>.yml`, `tests/test_handlers/test_help_handler.py`
    - **Action items:**
        - [RED] `test_help_lists_new_commands_and_no_library`: real `translations/addarr.en-us.yml` (root `en-us`), all six services on; the 7 commands present, `/library` absent
        - [RED] `test_help_hides_arr_and_download_commands_when_off`: all off; `/upcoming`, `/missing`, `/queue`, `/history`, `/downloads` absent, `/preferences` and `/webhooks` present
        - [RED] `test_help_matches_registered_commands`, parametrized over none, radarr, sonarr, lidarr, transmission, sabnzbd, bazarr, all: the command set in the help text equals `{c.command for c in build_authenticated_commands()}`
        - [GREEN] Add the four gated sections to `_build_help_text` (calendar, queue, history after the media sections; downloads after the transmission and sabnzbd lines)
        - [GREEN] Edit the 10 translation files (`@i18n-key`)
    - **Success:** The new tests fail before and pass after; `PYTHONIOENCODING=utf-8 <lock> .venv/bin/python run.py --validate-i18n` prints `All translations are valid!`; handlers scoped run passes

### Phase 2: Verify (1 task)

**Goal:** All CI checks pass locally before the PR.

- [ ] **2.1** Preflight
    - **Context:**
        - **Why:** CI requires lint, mypy, i18n, the 100% coverage gate, integration and architecture tests.
        - **Architecture:** `/addarr pr` runs review, then the preflight in `references/preflight.md`.
        - **Key refs:** `.claude/skills/addarr-workflow/references/preflight.md`
        - **Watch out:** Merge `origin/development` first. #224 (F210) edits the same `Help*` keys.
    - **Scope:** Run only, no new code
    - **Touches:** none
    - **Action items:**
        - [GREEN] Run the create-pr flow
    - **Success:** Every preflight step passes

# Issue 198: Config upgrade and setup crash the bot, tasks

Plan: `docs/issues/issue-198/plan.md`. Design: `docs/issues/issue-198/design.md`. Issue: #198.
Plan task N maps to the numbers below: 1 = 1.1, 2 = 1.2, 3 = 1.3, 4 = 1.4, 5 = 1.5, 6 = 2.1, 7 = 2.2,
8 = 2.3, 9 = 2.4, 10 = 3.1, 11 = 3.2, 12 = 4.1.

Every task: run `<lock> <py> ...` for tests (see the addarr-workflow Suite Lock), keep flake8 and mypy clean,
commit once per task with the task number in the message (for example `(#198, task 1.2)`).

## Phase 1: Config loading and validation (5 tasks)

**Goal:** `src/config/settings.py` handles empty files, missing sections, bad values and unvalidated
services, and the tests exercise the real module.

**Phase Context:**

- Why NOT edit the sys.modules mock: the mock hides the real `Config`. The loader imports a second copy under
  `src.config._real_settings` and never registers it.

- [x] **1.1** Real-module settings loader (plan task 1)
    - **Context:**
        - **Why:** `tests/test_config/test_settings.py` tests copies of the code and cannot fail. Every later
          task in this phase needs the real module.
        - **Architecture:** A pytest fixture in `tests/test_config/conftest.py` that execs
          `src/config/settings.py` via `importlib.util.spec_from_file_location` with file reads patched.
        - **Key refs:** `src/config/settings.py:82-247` (`Config`, global instance at import),
          `tests/conftest.py` (sys.modules mock injection, `MockConfig`), `src/definitions.py:20-21`
          (`CONFIG_PATH`, `CONFIG_EXAMPLE_PATH`).
        - **Watch out:** `Config()` runs at import, so errors surface during `exec_module`; keep the module
          object so `ConfigurationError` stays reachable. Use the name `src.config._real_settings` so the
          relative imports (`..definitions`, `..utils.backup`) resolve. Patch `sys.stdin`/`sys.stdout`
          `isatty`, `questionary.*`, `src.utils.backup.create_backup`, `builtins.open` and
          `os.path.exists` only for the two config paths. Leave `.coveragerc` alone (issue #205).
    - **Scope:** Fixture `load_settings`, dataclass `LoadedSettings(module, config, error, written, q)`.
    - **Touches:** `tests/test_config/conftest.py` (new), `tests/test_config/test_settings.py`
    - **Action items:**
        - [RED] Write `test_loads_valid_config`, `test_missing_file_gives_error` and
          `test_module_is_not_the_mock` in class `TestRealSettingsLoader`
        - [GREEN] Implement the fixture
    - **Success:** The three tests pass, flake8 and mypy clean, the existing settings tests still pass.
    - **Completed:** 2026-11-04
    - **Learnings:**
        - The module object survives a failed `exec_module`, so `result.module.ConfigurationError` is the real
          class even when `Config()` raised at import.
        - The loader must patch `os.path.exists` and `builtins.open` only for the two config paths and delegate
          the rest, or other imports break.
    - **Key Changes:**
        - Created `tests/test_config/conftest.py` with `load_settings`, `valid_config_text` and `LoadedSettings`.
        - Added class `TestRealSettingsLoader` to `tests/test_config/test_settings.py`.
    - **Notes:** `select_answer` and `confirm` args steer the questionary mocks. `result.q` holds the mocks.

- [x] **1.2** F024: empty file or section gives a clear error (plan task 2)
    - **Context:**
        - **Why:** An empty `config.yaml`, or a section such as `health_alerts:` with nothing under it, raises
          `TypeError: argument of type 'NoneType' is not iterable` at import.
        - **Architecture:** Validation stays in `Config`; the error is a `ConfigurationError` with a shared
          hint constant `_BACKUP_HINT`.
        - **Key refs:** `src/config/settings.py:89-95` (`_load_config`), `:210-221` (`_get_missing_keys`).
        - **Watch out:** A `None` leaf is valid when the example leaf is not a dict (`apikey:`,
          `adminNotifyId:`). Only a non-dict where the example has a dict is an error. The message must
          contain `backup/`. Do not auto-heal (decision from the review of the plan).
    - **Scope:** Two raises, one constant.
    - **Touches:** `src/config/settings.py`, `tests/test_config/test_settings.py`
    - **Action items:**
        - [RED] Write `test_empty_file_raises_configuration_error`,
          `test_empty_section_raises_configuration_error`,
          `test_empty_security_section_raises_configuration_error`, `test_none_leaf_is_still_valid`
        - [GREEN] Raise in `_load_config` for a non-dict result and in `_get_missing_keys` for a non-dict
          section
    - **Success:** Tests pass; messages name `backup/` (and the section name for sections).
    - **Completed:** 2026-11-04
    - **Learnings:**
        - The empty-section check must run before recursion, or the recursive call raises TypeError on None.
        - A None leaf stays valid: only a non-dict where the example has a dict is an error.
    - **Key Changes:**
        - `src/config/settings.py`: added `_BACKUP_HINT`; `_load_config` and `_get_missing_keys` raise `ConfigurationError`.
        - Added class `TestRealSettingsEmptyConfig` (4 tests).
    - **Notes:** Messages name backup/ and python run.py --setup. No auto-heal, per the plan review.

- [x] **1.3** F020: missing sections are copied from the example (plan task 3)
    - **Context:**
        - **Why:** In an upgrade from `main`, a missing `bazarr:` is prompted as "Enter value for bazarr:"
          and saved as text, so `config.get("bazarr", {}).get` fails at every start.
        - **Architecture:** Reuse `_apply_default_key`; add a small `_example_value` lookup it shares.
        - **Key refs:** `src/config/settings.py:97-134` (`_validate_config`), `:136-155`
          (`_apply_default_key`), `:157-189` (`_configure_missing_key`).
        - **Watch out:** `_get_missing_keys` lists a missing section by its own key only (not its children).
          The prompt path must still run for leaf keys.
    - **Scope:** Branch in the interactive loop.
    - **Touches:** `src/config/settings.py`, `tests/test_config/test_settings.py`
    - **Action items:**
        - [RED] Write `test_missing_section_is_copied_not_prompted`, `test_missing_leaf_is_still_prompted`,
          `test_saved_file_has_section`
        - [GREEN] Add `_example_value`, use it in `_apply_default_key`, branch in `_validate_config`
    - **Success:** Tests pass; `questionary.text` is never called for `bazarr`.
    - **Completed:** 2026-11-04
    - **Learnings:**
        - `_get_missing_keys` lists a missing section by its own key only, so one dict check in the interactive loop is enough.
        - The leaf-prompt test passes before the fix; it guards that leaves are still prompted.
    - **Key Changes:**
        - `src/config/settings.py`: new `_example_value`; `_apply_default_key` uses it; `_validate_config` copies dict defaults instead of prompting.
        - Added class `TestRealSettingsMissingSection` (3 tests).
    - **Notes:** The saved config.yaml holds the full example section.

- [x] **1.4** F025: startup runs the validators (plan task 4)
    - **Context:**
        - **Why:** `validate_port`, `validate_service_apikey` and `validate_telegram_token` exist but are
          never called, so an enabled service with an empty key starts.
        - **Architecture:** One loop in `_validate_values` over radarr, sonarr, lidarr, sabnzbd, bazarr; the
          token check runs always.
        - **Key refs:** `src/config/settings.py:33-80` (validators), `:191-208` (`_validate_values`),
          `config_example.yaml` (`server.port`, `auth.apikey` per service).
        - **Watch out:** `validate_port` requires an int, so a quoted port now fails (PR upgrade note).
          Transmission has no apikey: do not check it. Bazarr gains the address check. Use `or {}` for
          sections that could be None.
    - **Scope:** `_validate_values` only.
    - **Touches:** `src/config/settings.py`, `tests/test_config/test_settings.py`
    - **Action items:**
        - [RED] Write parametrized tests: empty apikey, port 0, empty token, disabled service passes,
          transmission without apikey passes, bazarr empty addr raises, `test_string_port_is_rejected`
        - [GREEN] Call the validators in `_validate_values`
    - **Success:** Tests pass; each error names the service.
    - **Completed:** 2026-11-04
    - **Learnings:**
        - The existing address loop and the new checks share one loop over five services; bazarr now gets the address check too.
        - The empty-section check from 1.2 runs first, so `auth: None` cannot reach `validate_service_apikey`.
    - **Key Changes:**
        - `src/config/settings.py`: `_validate_values` calls `validate_telegram_token`, `validate_server_addr`, `validate_service_apikey`, `validate_port`.
        - Added class `TestRealSettingsStartupValidation` (41 cases).
    - **Notes:** A quoted port such as "7878" now stops startup. Put this upgrade note in the PR body.

- [x] **1.5** F023: chatMode value validation and prompt (plan task 5)
    - **Context:**
        - **Why:** Only the exact value `private_only` blocks groups, and nothing validates chatMode, so
          `""` or `"private"` lets groups in.
        - **Architecture:** `CHAT_MODES` lives in `src/definitions.py` because `src/setup/` must not import
          `src/config/settings.py`.
        - **Key refs:** `src/definitions.py`, `src/config/settings.py:168-186` (`_configure_missing_key`),
          `:191-208`, `config_example.yaml:160`.
        - **Watch out:** Non-interactive upgrade already applies the example default (`private_only`) via
          `_apply_default_key`. Case variants are invalid.
    - **Scope:** Constant, validation, select prompt for a missing `security.chatMode`.
    - **Touches:** `src/definitions.py`, `src/config/settings.py`, `tests/test_config/test_settings.py`
    - **Action items:**
        - [RED] Write `test_invalid_chat_mode_raises` (`"private"`, `""`, `"Private_Only"`),
          `test_valid_chat_modes_load`, `test_missing_chat_mode_uses_select`,
          `test_missing_chat_mode_non_interactive_gets_default`
        - [GREEN] Add `CHAT_MODES`, validate in `_validate_values`, add the select branch
    - **Success:** Tests pass; `questionary.select` gets `choices == list(CHAT_MODES)`.
    - **Completed:** 2026-11-04
    - **Learnings:**
        - A `chatMode:` set to None is not missing (the key exists), so the value check is the one that rejects it.
        - `CHAT_MODES` lives in `src/definitions.py` so `src/setup/` can use it without loading config.yaml.
    - **Key Changes:**
        - `src/definitions.py`: added `CHAT_MODES`.
        - `src/config/settings.py`: `_validate_values` rejects other values; `_configure_missing_key` asks `security.chatMode` with `questionary.select`.
        - Added class `TestRealSettingsChatMode` (8 cases).
    - **Notes:** Task 2.1 makes auth.py fail closed and task 2.2 makes the wizard use CHAT_MODES.

## Phase 2: Bot and setup wizard (4 tasks)

**Goal:** The bot fails closed on chat mode, and the wizard keeps chatMode, runs once and works without
`config.yaml`.

- [x] **2.1** F023: the bot fails closed on chatMode (plan task 6)
    - **Context:**
        - **Why:** `_enforce_private_chat` blocks groups only for the exact value `private_only`.
        - **Architecture:** Compare with the literal `"allow_all"`; every other value takes the private path.
        - **Key refs:** `src/bot/handlers/auth.py:39-53`, `tests/test_handlers/test_auth_handler.py:157,194`.
        - **Watch out:** A missing `chatMode` keeps the default `private_only`. Run the integration tests
          because this is a user-facing guard.
    - **Scope:** One condition.
    - **Touches:** `src/bot/handlers/auth.py`, `tests/test_handlers/test_auth_handler.py`
    - **Action items:**
        - [RED] Write `test_invalid_chat_mode_blocks_group` (`"private"`, `""`) and
          `test_allow_all_still_allows_group`
        - [GREEN] Change the condition
    - **Success:** Auth handler and integration tests pass.
    - **Completed:** 2026-11-04
    - **Learnings:**
        - A chatMode set to None is not replaced by the `config.get` default. The old `!= private_only` check let it through, so groups were allowed. The new check blocks it.
        - The existing allow_all test already covered the open path.
    - **Key Changes:**
        - `src/bot/handlers/auth.py`: `_enforce_private_chat` returns False only for `allow_all` or when there is no chat.
        - Added `test_require_auth_rejects_group_when_chat_mode_invalid` (4 cases).
    - **Notes:** Integration tests (95) and handler coverage (612 tests, 100%) pass.

- [x] **2.2** F023: the wizard keeps and asks chatMode (plan task 7)
    - **Context:**
        - **Why:** The wizard replaces `security` and drops `chatMode`.
        - **Architecture:** `_async_setup` merges into the existing `security` dict;
          `configure_access_control(current_chat_mode: Optional[str] = None)` asks with `questionary.select`.
        - **Key refs:** `src/setup/wizard.py:111-118`, `src/setup/prompts.py:142-208`,
          `tests/test_setup/test_wizard.py:119-200`, `tests/test_setup/test_prompts.py:162-250`.
        - **Watch out:** Import `CHAT_MODES` from `src.definitions`, never from `src.config.settings`. Existing
          wizard tests that assert the call arguments of `configure_access_control` need the new argument.
    - **Scope:** Prompt, merge.
    - **Touches:** `src/setup/prompts.py`, `src/setup/wizard.py`, `tests/test_setup/`
    - **Action items:**
        - [RED] Write `test_chat_mode_select_offers_valid_values`, `test_chat_mode_default_is_current_value`,
          `test_chat_mode_invalid_current_falls_back`, `test_existing_chat_mode_survives_wizard`,
          `test_security_merge_keeps_unrelated_keys`
        - [GREEN] Implement the prompt and the merge
    - **Success:** `scripts/test_runner.py setup --coverage` passes.
    - **Completed:** 2026-11-04
    - **Learnings:**
        - The wizard merges into `self.config.get("security") or {}` so an empty (None) section cannot break `update`.
        - Existing access-control prompt tests needed a `questionary.select` mock once the new prompt was awaited.
    - **Key Changes:**
        - `src/setup/prompts.py`: `configure_access_control(current_chat_mode)` asks chatMode with `questionary.select` over `CHAT_MODES`.
        - `src/setup/wizard.py`: `_async_setup` merges the security answers into the existing section and passes the current chatMode.
        - Tests: 5 new in `tests/test_setup/`; 4 existing prompt tests got a select mock.
    - **Notes:** `src/setup/` imports CHAT_MODES from `src.definitions`, never from `src.config.settings`.

- [x] **2.3** F022: reset runs the wizard once (plan task 8)
    - **Context:**
        - **Why:** `_reset_config` ends with `self.run()`, so `--reset` runs the wizard twice.
        - **Architecture:** `run(reset=True)` already continues to `_async_setup` after `_reset_config`.
        - **Key refs:** `src/setup/wizard.py:68-96`, `:179-227`, `run.py:59-73`,
          `tests/test_setup/test_wizard.py:531-560`.
        - **Watch out:** `run.py --setup` with an existing config calls `run(reset=True)`; it is fixed by the
          same deletion.
    - **Scope:** Delete the call and its comment.
    - **Touches:** `src/setup/wizard.py`, `tests/test_setup/test_wizard.py`
    - **Action items:**
        - [RED] Write `test_run_reset_calls_async_setup_once`; change the existing success-path test to assert
          `run` is not called
        - [GREEN] Delete `self.run()`
    - **Success:** Wizard tests pass.
    - **Completed:** 2026-11-04
    - **Learnings:**
        - The old success-path test mocked `run()` to stop recursion, which hid the double run. The new test mocks `_async_setup` instead.
        - `run.py --setup` with an existing config also goes through `run(reset=True)`, so one deletion fixes both entry points.
    - **Key Changes:**
        - `src/setup/wizard.py`: removed `self.run()` at the end of `_reset_config`.
        - `tests/test_setup/test_wizard.py`: added `test_run_reset_calls_async_setup_once`; the success-path test now asserts `run` is not called.
    - **Notes:** The wizard prints "Starting setup wizard..." before returning to `run()`, which continues to `_async_setup`.

- [x] **2.4** F021: config handler has colors (plan task 9)
    - **Context:**
        - **Why:** `config_handler = ConfigHandler(None)` crashes on `self.colors.Fore` when
          `python run.py --setup` runs without `config.yaml`, because prerun is skipped for `--setup`.
        - **Architecture:** Build the module instance with `ColorHandler()` from `src/utils/prerun.py`
          (stdlib imports only, so no cycle).
        - **Key refs:** `src/utils/config_handler.py:56-63,102`, `src/utils/prerun.py:18-40,60-62`,
          `tests/test_utils/test_config_handler.py:206-214`.
        - **Watch out:** `load_config` must return `{}` for an empty file (ruamel returns None) so `--setup`
          can repair it. `prerun.py` keeps assigning `config_handler.colors`.
    - **Scope:** One line plus `or {}`.
    - **Touches:** `src/utils/config_handler.py`, `tests/test_utils/test_config_handler.py`
    - **Action items:**
        - [RED] Write `test_global_instance_has_colors` (replaces `test_colors_is_none`),
          `test_create_from_example_without_config_returns_true`,
          `test_load_config_empty_file_returns_empty_dict`
        - [GREEN] Implement
    - **Success:** `scripts/test_runner.py utils --coverage` passes.
    - **Completed:** 2026-11-04
    - **Learnings:**
        - `prerun.py` only imports the standard library at module level, so config_handler can import `ColorHandler` without a cycle.
        - The load-error path crashed too (it prints with colors), not only `create_from_example`.
    - **Key Changes:**
        - `src/utils/config_handler.py`: global instance is `ConfigHandler(ColorHandler())`; `load_config` returns `{}` for an empty file.
        - `tests/test_utils/test_config_handler.py`: `test_colors_is_none` replaced by 4 tests.
    - **Notes:** `prerun.py` still assigns `config_handler.colors`; it is the same kind of object.

## Phase 3: Token error and logging (2 tasks)

**Goal:** A bad token in a container exits with a message, and the logger obeys the config.

- [ ] **3.1** F027: no token prompt without a terminal (plan task 10)
    - **Context:**
        - **Why:** In Docker `input()` raises `EOFError`, so the container restart-loops on a bad token.
        - **Architecture:** One shared `is_interactive()` in `src/utils/terminal.py`, imported by
          `settings.py` and `error_handler.py`. The module imports nothing from `src.config`, so there is no
          cycle and no `config.yaml` load.
        - **Key refs:** `src/utils/error_handler.py:12-67`, `src/config/settings.py:23-25,106`,
          `src/main.py:95-102`, `tests/test_utils/test_error_handler.py`.
        - **Watch out:** `main.py` needs no change: False leads to `raise`. Existing token tests need an
          autouse fixture that makes `is_interactive` True. The loader's `sys.stdin` patch still drives
          `settings`. Add a one-line comment in `terminal.py` saying why it is a separate module.
    - **Scope:** New module, one early return, import swap.
    - **Touches:** `src/utils/terminal.py` (new), `src/utils/error_handler.py`, `src/config/settings.py`,
      `tests/test_utils/test_terminal.py` (new), `tests/test_utils/test_error_handler.py`
    - **Action items:**
        - [RED] Write `test_is_interactive_checks_both_streams` and
          `test_non_interactive_returns_false_without_prompt`
        - [GREEN] Implement `is_interactive`, use it in both modules
    - **Success:** Utils and config tests pass; no `input()` call when not interactive.

- [ ] **3.2** F026: logger reads debug and toConsole (plan task 11)
    - **Context:**
        - **Why:** `logging.debug` and `logging.toConsole` are never read, yet the splash shows "Debug
          Enabled".
        - **Architecture:** `_read_logging_settings() -> Tuple[bool, bool]` reads `CONFIG_PATH` with a raw
          `yaml.safe_load` (the logger must not import `Config`: setup runs without a config).
        - **Key refs:** `src/utils/logger.py:79-116`, `src/utils/splash.py:70`,
          `tests/test_utils/test_logger.py:84-100` (`fresh_loggers`).
        - **Watch out:** Defaults are `(False, True)` on any read problem. `error.log` stays ERROR. The
          `fresh_loggers` fixture must patch `src.utils.logger.CONFIG_PATH` to a tmp path so a developer's
          real `config.yaml` cannot change test results. With `toConsole: false` and an unwritable log
          folder Python's last-resort handler prints the warning.
    - **Scope:** Helper, two conditionals.
    - **Touches:** `src/utils/logger.py`, `tests/test_utils/test_logger.py`
    - **Action items:**
        - [RED] Write tests for debug DEBUG on console and `addarr.log`, `toConsole` false and true,
          debug with `toConsole: false`, and the three fallback cases (missing file, invalid YAML,
          `logging: 5`)
        - [GREEN] Implement the helper and use it
    - **Success:** Logger tests pass; `scripts/test_runner.py utils --coverage` is 100% for `logger.py`.

## Phase 4: Docs and gate (1 task)

**Goal:** No doc contradicts the new behavior.

- [ ] **4.1** Align docs with chatMode validation (plan task 12)
    - **Context:**
        - **Why:** Skills and notes mention `chatMode` handling.
        - **Architecture:** Docs only.
        - **Key refs:** `.claude/skills/security-audit/SKILL.md:15,51`,
          `.claude/skills/addarr-handlers/references/methods.md:145`, `CLAUDE.md`.
        - **Watch out:** Edit only a line that is now wrong. Run the architecture tests after any change.
    - **Scope:** Check and fix wording.
    - **Touches:** the files above, only if needed
    - **Action items:**
        - [RED] Not applicable (docs). The architecture and docs-drift tests are the check.
        - [GREEN] Fix wording if needed, then run `tests/test_architecture`
    - **Success:** Architecture tests pass. Skip the commit if no file changed.

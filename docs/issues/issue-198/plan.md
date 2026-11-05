# Issue 198: Config upgrade and setup crash the bot, implementation plan

**Goal:** Fix F020 to F027 so an old, empty or half-written `config.yaml`, the setup wizard and a bad Telegram
token stop crashing the bot or letting group chats in.

**Architecture:** Fixes sit in the existing layers: `src/config/settings.py` (load, upgrade, validate),
`src/setup/` (wizard and prompts), `src/utils/` (config handler, error handler, logger) and
`src/bot/handlers/auth.py` (fail-closed chat mode). One shared constant `CHAT_MODES` lives in
`src/definitions.py` because `src/setup/` must not import `src/config/settings.py` (that import loads
`config.yaml`).

**Tech stack:** Python 3.11, pytest, questionary, PyYAML, ruamel.yaml.

**Spec:** `docs/issues/issue-198/design.md` and issue #198.

## Global Constraints

- `config["key"]` bracket access is banned in `src/` business logic. Use `config.get("key", default)`.
- `Optional[str]` syntax for optional parameters, not `str | None`.
- flake8 line length 88 (E203, E501, W503 ignored). `mypy src/` must pass.
- Every test, gate and `git push` runs through the suite lock (see SKILL.md).
- Tests for `src/config/settings.py` exercise the real module through the loader of Task 1.
- Commits are per task, conventional style, reference `#198` and the task number.
- No new translation keys (setup prompts and config errors are English, as today).

## Review Focus

Failure modes the issue implies but no finding names. Each has a test in the owning task.

1. `security:` empty (None) in `config.yaml`: `ConfigurationError` naming `backup/`, not `AttributeError`. (Task 2)
2. `chatMode: allow_all` still loads and still lets groups in. Case variants such as `Private_Only` are rejected. (Tasks 5, 6)
3. `python run.py --setup` on an empty `config.yaml` (ruamel returns None) starts from `{}`. (Task 9)
4. A `logging:` section that is not a dict, or an unreadable config path, leaves the logger on its defaults. (Task 11)
5. `debug: true` with `toConsole: false`: no console handler, and `addarr.log` still gets DEBUG. (Task 11)

---

### Task 1: Real-module settings loader

**Files:**
- Create: `tests/test_config/conftest.py`
- Test: `tests/test_config/test_settings.py` (new class `TestRealSettingsLoader`)

**Interfaces:**
- Produces: fixture `load_settings` returning a callable
  `load(config_text: Optional[str], *, example_text: Optional[str] = None, interactive: bool = False,
  confirm: bool = True) -> LoadedSettings`.
  `LoadedSettings` is a dataclass with `module` (the executed module), `config` (the `Config` instance or
  None), `error` (the exception raised while importing, or None), `written` (dict of path to text written)
  and `q` (dict of the patched `questionary` functions `confirm`, `text`, `select`, `password`).
  `config_text=None` means `config.yaml` does not exist. `example_text=None` reads the real
  `config_example.yaml` from disk before patching.

- [ ] **Step 1: Write the failing smoke tests** in `TestRealSettingsLoader`:
  `test_loads_valid_config` (a copy of `config_example.yaml` with `language: en-us` and a token plus
  radarr disabled loads, `result.config` is not None), `test_missing_file_gives_error` (`config_text=None`,
  `result.error` is an instance of `result.module.ConfigurationError`), `test_module_is_not_the_mock`
  (`result.module is not sys.modules["src.config.settings"]`).
- [ ] **Step 2: Run to verify it fails** (fixture not found).
  Run: `<lock> <py> -m pytest tests/test_config/test_settings.py -k RealSettingsLoader -v`
- [ ] **Step 3: Implement the fixture.** Use `importlib.util.spec_from_file_location` with the name
  `src.config._real_settings` and the path of `src/config/settings.py`; create the module with
  `module_from_spec`, then `exec_module` inside a `try/except Exception` that stores the error (the module
  object keeps `ConfigurationError` because that class is defined before `Config()` runs). Patch
  `builtins.open` (a fake that serves and records only `CONFIG_PATH` and `CONFIG_EXAMPLE_PATH`, delegating
  everything else), `os.path.exists` (CONFIG_PATH follows `config_text is not None`, other paths delegate),
  `sys.stdin` and `sys.stdout` (a `MagicMock` whose `isatty` returns `interactive`), `questionary.*` and
  `src.utils.backup.create_backup`. Never register the module in `sys.modules`.
- [ ] **Step 4: Run to verify it passes.** Same command. Expected: PASS.
- [ ] **Step 5: Commit** `test: add real-module settings loader (#198, task 1)`.

### Task 2: F024, empty file and empty section give a clear error

**Files:**
- Modify: `src/config/settings.py` (`_load_config`, `_get_missing_keys`)
- Test: `tests/test_config/test_settings.py` (class `TestRealSettingsEmptyConfig`)

**Interfaces:**
- Consumes: `load_settings` (Task 1).
- Produces: module constant `_BACKUP_HINT` (str) used by both errors. It reads
  `"Restore a copy from the backup/ folder, or run python run.py --setup."`

- [ ] **Step 1: Write failing tests:** `test_empty_file_raises_configuration_error` (`config_text=""`),
  `test_empty_section_raises_configuration_error` (a valid config where `health_alerts:` has nothing under
  it), `test_empty_security_section_raises_configuration_error` (Review Focus 1), and
  `test_none_leaf_is_still_valid` (`radarr.auth.apikey:` empty with radarr disabled loads). Each error test
  asserts `isinstance(result.error, result.module.ConfigurationError)` and `"backup/" in str(result.error)`;
  the section test also asserts the message names `health_alerts`.
- [ ] **Step 2: Run to verify they fail** (`TypeError: argument of type 'NoneType' is not iterable`).
- [ ] **Step 3: Implement.** `_load_config` raises `ConfigurationError` when `yaml.safe_load` returns a
  non-dict. `_get_missing_keys` raises `ConfigurationError(f"Section '{full_key}' is empty or not a
  mapping. {_BACKUP_HINT}")` when the example value is a dict and the config value is not a dict. A missing
  key stays "missing". A YAML syntax error is out of scope.
- [ ] **Step 4: Run to verify they pass.** Run the class with `-v`.
- [ ] **Step 5: Commit** `fix: clear error for empty config file or section (#198, task 2)`.

### Task 3: F020, missing sections are copied from the example

**Files:**
- Modify: `src/config/settings.py` (`_validate_config`, `_apply_default_key`; new `_example_value`)
- Test: `tests/test_config/test_settings.py` (class `TestRealSettingsMissingSection`)

**Interfaces:**
- Produces: `Config._example_value(example_config: Dict, key: str) -> Any` returning the example value for
  a dotted key, or None when absent. `_apply_default_key` uses it.

- [ ] **Step 1: Write failing tests:** `test_missing_section_is_copied_not_prompted` (config without
  `bazarr`, `interactive=True`, `confirm=True`: `result.config["bazarr"] == example["bazarr"]` and
  `result.q["text"]` was never called with a string containing `bazarr`),
  `test_missing_leaf_is_still_prompted` (config without `language`-adjacent leaf, for example
  `security.enableAdmin`, is prompted through `confirm` or `text`),
  `test_saved_file_has_section` (`result.written[CONFIG_PATH]` parses and holds `bazarr` as a dict).
- [ ] **Step 2: Run to verify they fail** (text prompt called, `bazarr` is a str).
- [ ] **Step 3: Implement.** In the interactive branch of `_validate_config`, for each missing key: if
  `_example_value(...)` is a dict call `_apply_default_key(key, example_config)`, else
  `_configure_missing_key(key)`.
- [ ] **Step 4: Run to verify they pass.**
- [ ] **Step 5: Commit** `fix: copy missing config sections from the example (#198, task 3)`.

### Task 4: F025, startup runs the validators

**Files:**
- Modify: `src/config/settings.py` (`_validate_values`)
- Test: `tests/test_config/test_settings.py` (class `TestRealSettingsStartupValidation`)

- [ ] **Step 1: Write failing tests** (parametrized over radarr, sonarr, lidarr, sabnzbd, bazarr where it
  fits): enabled service with empty apikey raises; enabled service with `server.port: 0` raises; empty
  `telegram.token` raises; disabled service with empty apikey and port 0 loads; transmission enabled
  without apikey loads; enabled bazarr with empty `server.addr` raises. Each asserts
  `isinstance(result.error, result.module.ConfigurationError)` and the service name is in the message.
  Add `test_string_port_is_rejected` (`port: "7878"` raises) to pin the strict rule.
- [ ] **Step 2: Run to verify they fail** (config loads).
- [ ] **Step 3: Implement.** In `_validate_values`: call `validate_telegram_token(self._config.get("telegram")
  or {})` and loop over `("radarr", "sonarr", "lidarr", "sabnzbd", "bazarr")`. For an enabled service call
  `validate_service_apikey`, `validate_port(server.get("port"), name)` and `validate_server_addr`. Replace
  the existing addr loop with this loop.
- [ ] **Step 4: Run to verify they pass.**
- [ ] **Step 5: Commit** `fix: validate token, API key and port at startup (#198, task 4)`.

### Task 5: F023, chatMode value validation and prompt

**Files:**
- Modify: `src/definitions.py` (add `CHAT_MODES = ("private_only", "allow_all")`),
  `src/config/settings.py` (`_validate_values`, `_configure_missing_key`)
- Test: `tests/test_config/test_settings.py` (class `TestRealSettingsChatMode`)

**Interfaces:**
- Produces: `src.definitions.CHAT_MODES: tuple[str, ...]`.

- [ ] **Step 1: Write failing tests:** parametrized `test_invalid_chat_mode_raises` for `"private"`, `""`,
  `"Private_Only"`; `test_valid_chat_modes_load` for both values; `test_missing_chat_mode_uses_select`
  (config without `security.chatMode`, interactive: `result.q["select"]` called with choices equal to
  `list(CHAT_MODES)`, and the chosen value is stored); `test_missing_chat_mode_non_interactive_gets_default`
  (non-interactive: value is `private_only`).
- [ ] **Step 2: Run to verify they fail.**
- [ ] **Step 3: Implement.** `_validate_values` raises `ConfigurationError` naming the allowed values when
  `security.chatMode` is not in `CHAT_MODES` (use `(self._config.get("security") or {}).get("chatMode")`).
  `_configure_missing_key` uses `questionary.select(..., choices=list(CHAT_MODES))` when
  `key == "security.chatMode"`, placed before the free-text branch.
- [ ] **Step 4: Run to verify they pass.**
- [ ] **Step 5: Commit** `fix: validate chatMode and offer a select (#198, task 5)`.

### Task 6: F023, the bot fails closed on chatMode

**Files:**
- Modify: `src/bot/handlers/auth.py:41-42` (`_enforce_private_chat`)
- Test: `tests/test_handlers/test_auth_handler.py`

- [ ] **Step 1: Write failing tests:** `test_invalid_chat_mode_blocks_group` (`chatMode: "private"` and
  `""` in a group chat: `_enforce_private_chat` returns True and replies), and a regression
  `test_allow_all_still_allows_group` next to the existing tests.
- [ ] **Step 2: Run to verify the first fails.** Run: `<lock> <py> -m pytest tests/test_handlers/test_auth_handler.py -k chat_mode -v`
- [ ] **Step 3: Implement.** Return False when `chat_mode == "allow_all"` or there is no effective chat;
  every other value takes the private-only path.
- [ ] **Step 4: Run to verify they pass**, then the integration check for the auth flow:
  `<lock> <py> -m pytest tests/integration --tb=short -v`.
- [ ] **Step 5: Commit** `fix: fail closed on unknown chatMode (#198, task 6)`.

### Task 7: F023, the wizard keeps and asks chatMode

**Files:**
- Modify: `src/setup/prompts.py` (`configure_access_control`), `src/setup/wizard.py` (`_async_setup`)
- Test: `tests/test_setup/test_prompts.py`, `tests/test_setup/test_wizard.py`

**Interfaces:**
- Produces: `configure_access_control(current_chat_mode: Optional[str] = None) -> Dict[str, Any]`. The
  returned `security` dict gains `chatMode`, chosen with `questionary.select` over `CHAT_MODES`; the select
  default is `current_chat_mode` when it is valid, else `private_only`.

- [ ] **Step 1: Write failing tests:** prompts: `test_chat_mode_select_offers_valid_values`,
  `test_chat_mode_default_is_current_value`, `test_chat_mode_invalid_current_falls_back`. Wizard:
  `test_existing_chat_mode_survives_wizard` (config has `security: {chatMode: allow_all, enableAdmin: true}`,
  mocked `configure_access_control` returns `security` without chatMode: afterwards `chatMode` is still
  `allow_all`), `test_security_merge_keeps_unrelated_keys`.
- [ ] **Step 2: Run to verify they fail.**
- [ ] **Step 3: Implement.** In `_async_setup`, replace the `security` assignment with a merge into
  `self.config.setdefault("security", {})` (use `dict.update`), and pass the existing chatMode to
  `configure_access_control`. Update the two existing wizard tests if the new argument breaks their
  `assert_*_with` calls.
- [ ] **Step 4: Run to verify they pass.** Run: `<lock> <py> scripts/test_runner.py setup --coverage`
- [ ] **Step 5: Commit** `fix: wizard keeps and asks chatMode (#198, task 7)`.

### Task 8: F022, reset runs the wizard once

**Files:**
- Modify: `src/setup/wizard.py` (`_reset_config`, delete the `self.run()` call and its comment)
- Test: `tests/test_setup/test_wizard.py`

- [ ] **Step 1: Write the failing test** `test_run_reset_calls_async_setup_once`: real `_reset_config`
  (patch `questionary`, `create_backup`, `os.path.exists`, `open`, `yaml`) and a mocked `_async_setup`
  (`AsyncMock`): `wizard.run(reset=True)` awaits `_async_setup` exactly once. Change the existing
  `test_success_loads_example_saves_and_runs` to assert `wizard.run.assert_not_called()` and rename it
  `..._saves_and_returns`.
- [ ] **Step 2: Run to verify it fails** (called twice).
- [ ] **Step 3: Implement** the deletion.
- [ ] **Step 4: Run to verify it passes.**
- [ ] **Step 5: Commit** `fix: reset runs the setup wizard once (#198, task 8)`.

### Task 9: F021, config handler has colors

**Files:**
- Modify: `src/utils/config_handler.py` (module instance line, `load_config`)
- Test: `tests/test_utils/test_config_handler.py`

- [ ] **Step 1: Write failing tests:** `test_global_instance_has_colors` (`config_handler.colors` is not
  None and has `Fore`) replacing `test_colors_is_none`; `test_create_from_example_without_config_returns_true`
  (module-level instance semantics: a `ConfigHandler(ColorHandler())` with tmp paths and no `config.yaml`
  returns True); `test_load_config_empty_file_returns_empty_dict` (Review Focus 3).
- [ ] **Step 2: Run to verify they fail.**
- [ ] **Step 3: Implement.** `from src.utils.prerun import ColorHandler` and
  `config_handler = ConfigHandler(ColorHandler())`. `load_config` returns `yaml.load(f) or {}`. Keep the
  `config_handler.colors = self.colors` line in `prerun.py` (same object type, harmless).
- [ ] **Step 4: Run to verify they pass.** Run: `<lock> <py> scripts/test_runner.py utils --coverage`
- [ ] **Step 5: Commit** `fix: give the module config handler colors (#198, task 9)`.

### Task 10: F027, no token prompt without a terminal

**Files:**
- Create: `src/utils/terminal.py` (`is_interactive`; `src.utils` is imported by `settings.py` already and the
  module imports nothing from `src.config`, so there is no circular import and no `config.yaml` load)
- Modify: `src/config/settings.py` (delete its `_is_interactive`, import `is_interactive` from
  `..utils.terminal`, update the one call), `src/utils/error_handler.py` (`handle_token_error`)
- Test: `tests/test_utils/test_terminal.py` (new), `tests/test_utils/test_error_handler.py`

**Interfaces:**
- Produces: `src.utils.terminal.is_interactive() -> bool`, True only when both `sys.stdin` and
  `sys.stdout` are terminals. Same logic as the old `settings._is_interactive`.

- [ ] **Step 1: Write the failing tests:** `test_is_interactive_checks_both_streams` (three cases: both tty,
  stdin only, stdout only) in `test_terminal.py`; `test_non_interactive_returns_false_without_prompt` in
  `test_error_handler.py` (patch `src.utils.error_handler.is_interactive` False and `builtins.input` with
  `side_effect=EOFError`: result is False, `input` not called, the "Invalid Telegram Bot Token" line is
  printed). Existing `TestHandleTokenError` tests get an autouse fixture that patches `is_interactive` to
  True.
- [ ] **Step 2: Run to verify they fail** (module missing, `EOFError`).
- [ ] **Step 3: Implement.** Move the function to `terminal.py`. In `handle_token_error`, after the two
  error prints, return False when not interactive, after printing the fix steps (share the `n` branch text
  through a small helper so it is not duplicated). Existing `test_settings.py` tests that mention
  `_is_interactive` keep working through the loader's `sys.stdin` patch.
- [ ] **Step 4: Run to verify they pass.** Run: `<lock> <py> scripts/test_runner.py utils --coverage`
- [ ] **Step 5: Commit** `fix: skip the token prompt without a terminal (#198, task 10)`.

### Task 11: F026, logger reads debug and toConsole

**Files:**
- Modify: `src/utils/logger.py` (`_setup_shared_handlers`; new `_read_logging_settings`)
- Test: `tests/test_utils/test_logger.py` (the `fresh_loggers` fixture also patches `CONFIG_PATH`)

**Interfaces:**
- Produces: `_read_logging_settings() -> Tuple[bool, bool]` returning `(debug, to_console)`. Defaults are
  `(False, True)`. Any read error, a non-dict file, or a non-dict `logging` section gives the defaults. A
  value that is not a bool counts as the default.

- [ ] **Step 1: Write failing tests** with `CONFIG_PATH` pointed at a tmp file: `debug: true` gives console
  handler level DEBUG and the `addarr.log` handler level DEBUG while `error.log` stays ERROR;
  `toConsole: false` leaves the `addarr` logger with no `StreamHandler`; `toConsole: true` has one;
  `debug: true` with `toConsole: false` has no console handler and a DEBUG file handler (Review Focus 5);
  missing file, invalid YAML and `logging: 5` all give INFO with a console handler (Review Focus 4).
- [ ] **Step 2: Run to verify they fail.**
- [ ] **Step 3: Implement.** Read once inside `_setup_shared_handlers` with `yaml.safe_load` of
  `CONFIG_PATH`. Add the console handler only when `to_console`. Use `logging.DEBUG if debug else
  logging.INFO` for the console handler and for the `addarr.log` handler.
- [ ] **Step 4: Run to verify they pass.** Run: `<lock> <py> scripts/test_runner.py utils --coverage`
- [ ] **Step 5: Commit** `fix: honor logging.debug and logging.toConsole (#198, task 11)`.

### Task 12: Docs and full gate

**Files:**
- Modify: `.claude/skills/security-audit/SKILL.md` (only if a line contradicts the fail-closed rule),
  `CLAUDE.md` (only if the test list or config rules change)
- Test: architecture and docs tests

- [ ] **Step 1: Check** that no doc names the old behavior (`!= "private_only"`, a free-text chatMode).
  Fix any line found.
- [ ] **Step 2: Run the architecture tests.** Run: `<lock> <py> -m pytest tests/test_architecture --tb=short -v`
- [ ] **Step 3: Commit** `docs: align notes with chatMode validation (#198, task 12)` only if a file changed.
- [ ] **Step 4:** `INVOKE` `superpowers:verification-before-completion`; the preflight runs in the
  create-pr flow.

## Self-review notes

- Spec coverage: F020 (3), F021 (9), F022 (8), F023 (5, 6, 7), F024 (2), F025 (4), F026 (11), F027 (10),
  loader (1). Every acceptance criterion in #198 maps to a test above.
- New cross-module names: `is_interactive` (Task 10) and `CHAT_MODES`. Tasks 5 and 7 use `CHAT_MODES` from
  `src/definitions.py`. `auth.py` compares with the literal `"allow_all"` only.

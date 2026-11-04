# Issue 198: Config upgrade and setup crash the bot

Source: issue #198 (audit findings F020 to F027). Approved decisions are in the "Decisions" section.

## Problem

Eight defects in config loading, the setup wizard, the token-error path and the logger. A broken or old
`config.yaml` can crash the bot, leave a config that fails at every start, or let group chats in.

## Decisions

Approved by the orchestrator on 2026-11-04 (all recommended options).

1. **Test loader (F221).** Build a small helper in `tests/test_config/conftest.py`. It loads the real
   `src/config/settings.py` with `importlib` under the name `src.config._real_settings` and patches the file
   reads. Only the loader is built here. `.coveragerc` and the other #205 items stay as they are.
2. **chatMode (F023).** Valid values are `private_only` and `allow_all`, held in `CHAT_MODES` in
   `src/definitions.py`. `Config._validate_values` rejects any other value. The wizard and the missing-key
   prompt use `questionary.select`. `_enforce_private_chat` in `auth.py` fails closed: only `allow_all`
   lets group chats in.
3. **Logger (F026).** `logger.py` reads `logging.debug` and `logging.toConsole` from `CONFIG_PATH` (a raw
   `yaml.safe_load`, not `Config`). If the read fails it uses INFO with the console on. `debug: true` sets
   DEBUG on the console handler and on the `addarr.log` handler. `error.log` stays at ERROR.
   `toConsole: false` adds no console handler.
4. **Validators (F025).** `_validate_values` always checks the Telegram token. For each enabled service among
   radarr, sonarr, lidarr, sabnzbd and bazarr it checks the API key, the port (`server.port`) and the
   address. Transmission has no API key and is not checked. Bazarr gains the address check because it shares
   the loop.
5. **F024 error text.** The message names `backup/` and `python run.py --setup`.

## Approach per finding

- **F020.** In the interactive branch of `_validate_config`, a missing key whose example value is a dict is
  copied with `_apply_default_key`. Only leaf keys are prompted.
- **F024.** `_load_config` raises `ConfigurationError` for an empty file or a non-dict top level.
  `_get_missing_keys` raises `ConfigurationError` when the example has a dict and the config has a
  non-dict (for example `health_alerts:` with nothing under it). Both messages name `backup/`.
  A `None` leaf is still valid when the example leaf is not a dict.
- **F023.** The wizard merges the new `security` answers into the existing `security` section. The chatMode
  prompt defaults to the existing value.
- **F022.** `_reset_config` stops calling `self.run()`. `run(reset=True)` already continues to `_async_setup`.
- **F021.** The module-level `config_handler` is built with `ColorHandler()` from `src/utils/prerun.py`.
  `load_config` returns `{}` for an empty file so `--setup` can repair it.
- **F027.** `handle_token_error` returns False without prompting when `_is_interactive()` is False.
  `main.py` needs no change: `False` already leads to `raise`, which exits with a logged error.
- **F026.** See decision 3.

## Out of scope

`.coveragerc` omit of `src/config/settings.py` (issue #205), the F030 empty-file cause (issue #209), and
splash changes (the splash reads the same `logging.debug` key and now agrees with the logger).

## Risks

- A port stored as a string (for example `"7878"`) now fails `validate_port`. This is the existing strict
  rule, now applied at startup.
- An enabled Bazarr with an empty address now fails startup.
- With `toConsole: false` and an unwritable log folder, Python's last-resort handler prints the warning to
  stderr.

---
title: "Config upgrade and setup crash the bot"
labels: [bug, security, ops, agent-ready, priority:critical]
slice: 3
findings: [F020, F021, F024, F023, F022, F025, F027, F026]
---

## Bug

Upgrading an old config, running the setup wizard, or starting with a broken config.yaml can crash the bot or leave a config that fails at every start.

- **F020** Upgrade from `main`: a missing whole section (for example `bazarr:`) is prompted as "Enter value for bazarr:" and saved as text. `config.get("bazarr", {}).get` then fails at every start.
- **F021** A fresh `python run.py --setup` with no config.yaml crashes. The module creates `config_handler = ConfigHandler(None)`, and prerun (which sets the colors) is skipped for `--setup`.
- **F024** An empty config.yaml, or an empty section such as `health_alerts:`, gives `TypeError` at import (`key not in None`).
- **F023** The wizard overwrites `security` and drops `chatMode`. chatMode is then prompted as free text, so `""` or `"private"` lets groups in. Nothing validates it.
- **F022** `--reset`, and `--setup` with an existing config, run the wizard twice: `_reset_config` calls `self.run()`.
- **F025** `validate_port`, `validate_service_apikey` and `validate_telegram_token` are never called. An enabled service with an empty key starts.
- **F027** With a bad token in Docker, `handle_token_error` calls `input()`, gets `EOFError`, and the container restart-loops.
- **F026** `logging.debug` and `logging.toConsole` are never read, yet the splash shows "Debug Enabled".

## Steps to reproduce

F020:

1. Take a config.yaml from `main` that has no `bazarr:` section.
2. Run `python run.py` in a terminal and accept "configure these settings now".
3. At "Enter value for bazarr:", type anything or press Enter.
4. config.yaml now holds `bazarr: <text>`. Every later start fails at `config.get("bazarr", {}).get`.

F021:

1. Remove config.yaml.
2. Run `python run.py --setup`.
3. It crashes on `self.colors.Fore` because `colors` is `None`.

F024:

1. Empty config.yaml, or leave `health_alerts:` with nothing under it.
2. Start the bot.
3. Importing `src.config.settings` raises `TypeError` (`key not in None`).

F023:

1. Run `python run.py --setup`. The saved `security` section has no `chatMode`.
2. Start the bot in a terminal. It asks "Enter value for security.chatMode:".
3. Type `private`, or press Enter.
4. Add the bot to a group. The group is served, because only the exact value `private_only` blocks groups.

F022:

1. Keep an existing config.yaml.
2. Run `python run.py --reset`.
3. The wizard runs to the end, then starts again from the beginning.

F025:

1. Set `radarr.enable: true` and `radarr.auth.apikey: ""`.
2. Start the bot. It starts with no config error.

F027:

1. Set a wrong `telegram.token`.
2. Run `docker compose up`.
3. `input()` raises `EOFError`. The container exits and restarts in a loop.

F026:

1. Set `logging.debug: true`.
2. Start the bot. The splash shows Debug "Enabled", but the console stays at INFO.

## Expected behavior

- A missing section is filled from `config_example.yaml`, never with a free-text answer.
- `--setup` works without a config.yaml.
- An empty file or section gives a clear error that points to `backup/`.
- The wizard keeps `chatMode`, offers only valid values, and the bot rejects invalid ones.
- `--reset` runs the wizard once.
- An enabled service without an API key, a bad port or a missing token stops startup with a clear error.
- A bad token in a non-interactive container logs an error and exits without a prompt.
- `logging.debug` sets the log level and `logging.toConsole` turns console output on or off. The splash agrees with both.

## Fix

- [ ] **F020** When the example value is a dict, copy it with `_apply_default_key` instead of prompting (`src/config/settings.py:157-186`, `:215`)
- [ ] **F021** Create the module instance as `ConfigHandler(ColorHandler())` (`src/utils/config_handler.py:49`, `:53`, `:62`, `:102`; `run.py:39`)
- [ ] **F024** Treat a `None` or non-dict value as missing. Raise a clear error that points to `backup/` (`src/config/settings.py:95`, `:215`)
- [ ] **F023** Merge the wizard result into `security` instead of replacing it. Ask chatMode with `questionary.select`. Validate chatMode in `_validate_values` (`src/setup/wizard.py:115`, `src/config/settings.py:182-185`, `src/bot/handlers/auth.py:42`)
- [ ] **F022** Delete the `self.run()` call at the end of `_reset_config` (`src/setup/wizard.py:223`)
- [ ] **F025** Call `validate_port`, `validate_service_apikey` and `validate_telegram_token` in `_validate_values` at startup (`src/config/settings.py:33-80`)
- [ ] **F027** Skip the token prompt unless `_is_interactive()` (`src/utils/error_handler.py:22`, `src/main.py:95-101`)
- [ ] **F026** Wire both keys. `logging.debug: true` sets the log level to DEBUG. `logging.toConsole` turns the console handler on or off (`src/utils/logger.py:98`, `src/utils/splash.py:70`)

## Acceptance criteria

Each test below fails before the fix and passes after it. Tests for `src/config/settings.py` must exercise the real module (load it with importlib and patch the file reads, as F221 describes). The current `tests/test_config/test_settings.py` tests copies of the code and cannot fail.

- **F020** `tests/test_config/test_settings.py`: config without `bazarr`, interactive mode. After `_validate_config`, `config["bazarr"]` equals the example dict, and `questionary.text` is never called for `bazarr`.
- **F021** `tests/test_utils/test_config_handler.py`: the module-level `config_handler.colors` is not `None`, and `create_from_example()` with no config.yaml returns True.
- **F024** `tests/test_config/test_settings.py`: an empty file and a file with `health_alerts:` both raise `ConfigurationError` whose message names `backup/`, not `TypeError`.
- **F023** `tests/test_setup/test_wizard.py`: an existing `security.chatMode` survives the wizard. `tests/test_config/test_settings.py`: `chatMode: "private"` and `chatMode: ""` raise `ConfigurationError`.
- **F022** `tests/test_setup/test_wizard.py`: `run(reset=True)` calls `_async_setup` once.
- **F025** `tests/test_config/test_settings.py`: at startup, an enabled service with an empty key, a port of 0 and an empty token each raise `ConfigurationError`.
- **F027** `tests/test_utils/test_error_handler.py`: with `_is_interactive()` False, `handle_token_error()` returns False and never calls `input()`.
- **F026** `tests/test_utils/test_logger.py`: with `logging.debug: true` the console handler level is DEBUG. With `logging.toConsole: false` the logger has no console handler. With `logging.toConsole: true` it has one.
- `pytest`, `flake8` and `mypy src/` pass.

## Notes

- Source: audit 2026-10-28, docs/issues/audit-2026-10-28/FINDINGS.md (F-ids F020, F021, F024, F023, F022, F025, F027, F026).
- Priority: max P 40, sum P 215 (critical).
- Dependencies: slices 1-8 go first. The real-module test loader is F221 in slice 10. Build it here or take it from slice 10.
- Related: F030 (slice 14) can leave config.yaml empty, which then hits F024.
- Decided 2026-10-28: F025 call the three validators in `_validate_values` at startup.
- Decided 2026-10-28: F026 wire both keys: `logging.debug` sets DEBUG, `logging.toConsole` turns the console handler on or off.

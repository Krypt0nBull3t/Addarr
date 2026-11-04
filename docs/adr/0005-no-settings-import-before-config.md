# 0005. No `src.config.settings` import before a valid config exists

**Status:** Accepted. Recorded 2026-11-04 (issue #198).

## Context

`src/config/settings.py` runs `config = Config()` at import. That reads `config.yaml`, prompts for missing keys, and raises `ConfigurationError` on a bad file. The setup wizard (`python run.py --setup`, `--reset`), the token-error path and the logger must work when `config.yaml` is missing, empty or invalid. Issue #198 found that a module-level instance built too early crashed `--setup` (F021).

## Decision

`src/setup/` and the utils that run before a valid config exists (`config_handler`, `error_handler`, `logger`, `prerun`, `backup`, `terminal`) do not import `src.config.settings` at module level. A function-level import is allowed: `show_welcome_screen` in `src/utils/splash.py` imports `config` inside the function. Shared values live where they can be imported safely:

- constants in `src/definitions.py` (`CHAT_MODES`, the path constants);
- small helpers in modules of their own (`src/utils/terminal.py` holds `is_interactive`);
- the logger reads `logging.debug` and `logging.toConsole` from `CONFIG_PATH` with a raw `yaml.safe_load` and falls back to defaults.

`src/utils/helpers.py` and `src/utils/validation.py` import `config` at module level. They run only after startup validation, so they are outside this rule.

## Consequences

- `--setup` works without a config.yaml.
- Some code reads `config.yaml` a second time (the logger). It tolerates a missing or broken file.
- No test enforces the rule yet. A reviewer checks a new module-level import in the modules named above.

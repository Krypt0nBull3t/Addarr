---
title: "Config writes can lose data, comments and authorized users"
labels: [bug, security, agent-ready, priority:high]
slice: 14
findings: [F032, F030, F013, F031]
---
## Bug

- **F032** `_save_authenticated_users` swallows save errors. The user is told "authorized" and is lost on restart (for example with a read-only config, see F170 and F190).
- **F030** `Config.save()` truncates the file, then dumps. A full disk leaves config.yaml empty, and the next start fails (F024).
- **F013** Every save writes a full backup with all secrets. Backups are never pruned. They keep config.yaml's mode (0644 when it was copied from the example). `backup/` is missing from .dockerignore.
- **F031** `yaml.dump` removes every comment in config.yaml on each /auth or settings tap. config_handler already uses a ruamel round-trip.

## Steps to reproduce

1. **F032** Make config.yaml read-only. Send /auth with the right password. The bot says you are authorized. Restart the bot: you must authenticate again.
2. **F030** Make the write fail after the file is opened (for example a full disk). Tap a settings toggle. config.yaml is empty.
3. **F013** Tap a settings toggle 20 times. `backup/` holds 20 full copies with all secrets, mode 0644 when config.yaml was copied from the example. `docker build` copies `backup/` into the image.
4. **F031** Add a comment to config.yaml. Run /auth or tap a settings toggle. The comment is gone.

## Expected behavior

A failed auth save tells the user and logs an ERROR. A failed write never leaves config.yaml empty. Only the newest 10 backups stay, only the owner can read them, and they are not in the image. Comments in config.yaml survive a save.

## Fix

- [ ] **F032** Tell the user and log ERROR when the save fails (`src/bot/handlers/auth.py:141-142`)
- [ ] **F030** Dump to a string first, then write once. Do not use `os.replace`: it breaks the compose file bind mount (`src/config/settings.py:239-243`)
- [ ] **F013** Keep the newest 10 backups, chmod them `0o600`, add `backup/` to .dockerignore (`src/utils/backup.py:36-41`, `src/utils/config_handler.py:48`, `:79`, `.dockerignore`)
- [ ] **F031** Save with the ruamel round-trip (`src/config/settings.py:243`)

## Acceptance criteria

Each test fails before its fix and passes after:

- **F032** `tests/test_handlers/test_auth_handler.py`: when `config.save()` raises, the reply is an error message, not the success text, and an ERROR is logged.
- **F030** `tests/test_config/test_settings.py`: when the dump raises, config.yaml keeps its old content.
- **F013** `tests/test_utils/test_backup.py`: after 11 backups only the newest 10 remain, each with mode `0o600`. A test checks that `.dockerignore` lists `backup/`.
- **F031** `tests/test_config/test_settings.py`: a comment in config.yaml survives `save()`.
- `pytest`, `flake8` and `mypy src/` pass. If a translation key is added for the F032 message, `PYTHONIOENCODING=utf-8 python run.py --validate-i18n` passes.

## Notes

- Source: audit 2026-10-28, docs/issues/audit-2026-10-28/FINDINGS.md (F-ids F032, F030, F013, F031).
- Priority: max P 30, sum P 98 (high).
- Order: do slices 1-8 first. Slice 3 (F024) handles the empty config.yaml that F030 can leave. Slices 6 (F170) and 23 (F190) cause the read-only config that F032 hits. The F030 and F031 tests need the real `Config.save()`, which slice 10 (F221) brings under test and coverage.

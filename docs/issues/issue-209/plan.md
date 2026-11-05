# Issue #209: Config writes can lose data, comments and authorized users

**Goal:** A failed auth save tells the user, a failed config write never empties `config.yaml`, backups are pruned and private, and comments in `config.yaml` survive a save.

**Architecture:** `Config` loads `config.yaml` with a ruamel round-trip loader, so `_config` is a `CommentedMap` (a `dict` subclass) that keeps comments. One private method dumps to a string first and then writes the file once. `create_backup` prunes and locks down its backups. `AuthHandler._save_authenticated_users` reports success as a `bool`, and `check_password` picks the reply from it.

**Tech Stack:** Python 3.10+, `ruamel.yaml==0.19.1` (already pinned), pytest.

**Spec:** GitHub issue #209 (findings F032, F030, F013, F031 in `docs/issues/audit-2026-10-28/FINDINGS.md`). Decisions from the orchestrator: F031 by loading with ruamel (option A); a failed auth save keeps the user authorized in memory and shows a warning; add translation key `AuthSaveFailed`; the follow-ups below go in the PR body, no new issues.

## Global Constraints

- Branch `fix/209-config-save-data-loss`, PR targets `development`.
- Do not use `os.replace` for the config write: it breaks the compose file bind mount.
- Keep at most 10 backups, each mode `0o600`.
- No `config["key"]` bracket access in `src/` business logic. `src/config/settings.py` may not import `src/utils/config_handler.py`.
- A new translation key goes in the template and all 9 locales (`i18n-key` skill). `nl-be` uses standard Netherlands Dutch.
- `pytest` with the 100% coverage gate, `flake8`, `mypy src/` and `PYTHONIOENCODING=utf-8 python run.py --validate-i18n` pass.
- Every test, gate and `git push` runs through the suite lock.
- #210 also edits `_save_authenticated_users` (F091). The PR that merges second merges `origin/development` and keeps both changes.

## Review Focus

- The backup folder holds other files (for example `config_example_20260101_000000.yaml`, `notes.txt`). Expected: prune deletes only `config_<date>_<time>.yaml` files.
- Fewer than 10 backups exist. Expected: nothing is deleted.
- `config.yaml` has a comment and a quoted string value (`password: "123456"`). Expected: after `save()` the comment and the quotes are still there.
- The dump raises on the startup prompt path (`_validate_config`). Expected: `config.yaml` keeps its old content (same helper as `save()`).
- The auth save fails. Expected: the user stays in `AuthHandler._authenticated_users`, gets `AuthSaveFailed`, and does not get `Chatid added`.

## Out of scope (list in the PR body as follow-ups)

- `ConfigHandler.save_config` (`src/utils/config_handler.py:67`) still truncates before it dumps.
- `src/utils/error_handler.py:60` still writes the token with PyYAML (drops comments, truncates first).
- The `config.save()` callers in `src/bot/handlers/settings.py` and `webhooks.py` do not catch a save error.
- A write that fails halfway through `f.write(text)` (full disk) can still leave a short file. Only a failure before the open is covered.

## Tasks

### Task 1: F013, prune and lock down backups

**Files:**
- Modify: `src/utils/backup.py:20-54`, `.dockerignore`
- Test: `tests/test_utils/test_backup.py`

**Interfaces:**
- Produces: constant `MAX_BACKUPS = 10`; private `_prune_backups(backup_dir: str, stem: str) -> None` in `src/utils/backup.py`. `create_backup(source_path: str = CONFIG_PATH) -> Optional[str]` keeps its signature.

- [ ] Write `test_backups_are_pruned_to_newest_ten`: patch `src.utils.backup.datetime` so `datetime.datetime.now` returns `datetime.datetime(2026, 1, 1, 0, 0, i)` for `i` in 0..10 (11 calls, `side_effect` list), call `create_backup(str(source))` 11 times. Assert exactly 10 files `config_*.yaml` remain, the second-0 file is gone and the second-10 file is there. Run it, expect FAIL.
- [ ] Write `test_backups_are_owner_only`: after one `create_backup`, `stat.S_IMODE(os.stat(result).st_mode) == 0o600` even when the source is `0o644`. Run it, expect FAIL.
- [ ] Write `test_new_backup_dir_is_owner_only`: the created `backup/` folder has mode `0o700`. Run it, expect FAIL.
- [ ] Write `test_prune_keeps_unrelated_files`: put `config_example_20260101_000000.yaml` and `notes.txt` in `backup/` with 11 real backups; after pruning both still exist. Run it, expect FAIL for the 11-backup count only (this test guards the glob, so it must also pass after the fix).
- [ ] Write `test_dockerignore_lists_backup_dir`: read `.dockerignore` (path from `Path(__file__).parents[2]`) and assert the line `backup/` is in `splitlines()`. Run it, expect FAIL.
- [ ] In `create_backup`: `Path(backup_dir).mkdir(mode=0o700, parents=True, exist_ok=True)`, `os.chmod(backup_file, 0o600)` after `shutil.copy2`, then `_prune_backups(backup_dir, stem)`. `_prune_backups` globs `f"{stem}_[0-9]*_[0-9]*.yaml"`, sorts by name (the timestamp sorts in time order), and unlinks all but the last `MAX_BACKUPS` with `unlink(missing_ok=True)`. Add `backup/` to `.dockerignore` next to `config.yaml`. Run the backup tests, expect PASS.
- [ ] Run `<lock> .venv/bin/python scripts/test_runner.py utils --coverage`. Commit: `fix: prune and lock down config backups (#209, task 1)`.

### Task 2: F030 and F031, write once and keep comments

**Files:**
- Modify: `src/config/settings.py` (imports, `_load_config`, `_validate_config` write at line 123, `save` at line 273)
- Test: `tests/test_config/test_settings.py` (replace `TestSave.test_save_writes_yaml` and `TestSave.test_save_creates_backup_first`, which test a copy of the code; keep `test_save_is_noop_in_mock`)

**Interfaces:**
- Produces: module-level `_yaml` (a `ruamel.yaml.YAML()` with `preserve_quotes = True` and `indent(mapping=2, sequence=4, offset=2)`, the same as `config_handler`); `Config._write_config(self) -> None` (dumps `self._config` to a `StringIO`, then opens `CONFIG_PATH` once and writes the text); `Config.save(self) -> None` (`create_backup()` then `_write_config()`).

Tests use the `load_settings` fixture to build a real `Config` from text, then point `module.CONFIG_PATH` at a file in `tmp_path` before they call `save()`. `create_backup` is already a mock on that module.

- [ ] Write `test_save_keeps_old_file_when_dump_fails`: write `old` text to `tmp_path/config.yaml`; load with `load_settings(valid_config_text)`; set `result.module.CONFIG_PATH`; `patch.object(result.module._yaml, "dump", side_effect=RuntimeError("boom"))`; `pytest.raises(RuntimeError)` around `config.save()`; the file text still equals `old`. Patch `module.yaml.dump` instead of `_yaml.dump` for the red run, so it fails on the old code for the right reason (the file is emptied); switch the patch to `_yaml.dump` with the implementation.
- [ ] Write `test_save_keeps_comments_and_quotes`: config text is `valid_config_text` with a line `# keep me` before `language:` and `password: "123456"` quoted; load, call `update_nested("language", "nl-be")`, `save()` to the `tmp_path` file; the saved text contains `# keep me`, `password: "123456"` and `language: nl-be`. Run it, expect FAIL.
- [ ] Write `test_startup_prompt_write_keeps_comment` in `TestRealSettingsMissingSection`: run the interactive missing-section load with a `# keep me` line in the config text; `result.written[CONFIG_PATH]` contains `# keep me`. Run it, expect FAIL.
- [ ] Implement: `from ruamel.yaml import YAML` and `from io import StringIO`; create `_yaml`; `_load_config` uses `_yaml.load(f)`; add `_write_config`; `save` calls `create_backup()` and `_write_config()`; the block at `_validate_config` line 123 becomes `self._write_config()`. PyYAML stays for `config_example.yaml` (`yaml.safe_load`). Run the config tests, expect PASS.
- [ ] Run `<lock> .venv/bin/python scripts/test_runner.py config --coverage`, then `mypy src/`. Commit: `fix: write config once and keep its comments (#209, task 2)`.

### Task 3: F032, tell the user when the auth save fails

**Files:**
- Modify: `src/bot/handlers/auth.py:134-143` and `:208-221`, the 10 files under `translations/`
- Test: `tests/test_handlers/test_auth_handler.py`

**Interfaces:**
- Produces: `AuthHandler._save_authenticated_users(self) -> bool` (`True` after `config.save()`, `False` after logging the ERROR); translation key `AuthSaveFailed`.

- [ ] Write `test_check_password_save_failure_warns_user` (async, next to `test_check_password_correct`): real `_save_authenticated_users`, `mock_config.save = MagicMock(side_effect=OSError("Read-only file system"))`, patch `src.bot.handlers.auth.logger`. After `check_password` with the right password: `chat.send_message` was awaited with `"AuthSaveFailed"` and never with `"Chatid added"`; `logger.error` was called; the user id is in `AuthHandler._authenticated_users`. Run it, expect FAIL.
- [ ] Write `test_save_authenticated_users_returns_bool`: `True` with a working `save`, `False` when `save` raises. Run it, expect FAIL.
- [ ] Implement: return `True` at the end of the `try`, `False` in the `except`. In `check_password`, `saved = self._save_authenticated_users()` and send `get_text("Chatid added" if saved else "AuthSaveFailed")`. The rest of the flow (commands, `/start`) is unchanged. Run the auth tests, expect PASS.
- [ ] Add `AuthSaveFailed` after `Chatid added` in the template and in all 9 locales, translated, with no emoji. English text: `"You are authorized for now, but the bot could not save this. You must authenticate again after a restart. Ask the admin to check that config.yaml is writable."` Run `PYTHONIOENCODING=utf-8 <lock> .venv/bin/python run.py --validate-i18n`, expect PASS.
- [ ] Commit: `fix: tell the user when the auth save fails (#209, task 3)`.

### Task 4: Docs

**Files:**
- Modify: `CLAUDE.md` (Configuration section)

- [ ] Add one sentence: `Config` loads `config.yaml` with ruamel, so comments survive a save, and `create_backup` keeps the newest 10 backups in `backup/`, mode `0o600`. Run `<lock> .venv/bin/python -m pytest tests/test_architecture --tb=short -v`, expect PASS. Commit: `docs: note comment-keeping saves and backup pruning (#209, task 4)`.

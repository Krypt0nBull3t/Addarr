# Issue #209 Tasks: Config writes can lose data, comments and authorized users

Plan: `docs/issues/issue-209/plan.md`. Branch `fix/209-config-save-data-loss`, PR targets `development`.
Every test, gate and `git push` runs through the suite lock. Use `.venv/bin/python`.

### Phase 1: Config write safety (4 tasks)

**Goal:** A failed auth save tells the user, a failed config write never empties `config.yaml`, backups are pruned and private, and comments in `config.yaml` survive a save.

**Phase Context:**

- Why NOT `os.replace`: the compose file bind-mounts the single file `config.yaml`. A replace swaps the inode and breaks the mount. The code comment must say this.
- Why NOT merge into a fresh ruamel tree (option B): the orchestrator chose option A. `Config._config` becomes a `CommentedMap`, a `dict` subclass, so every reader keeps working.

- [ ] **1.1** F013: prune and lock down backups
    - **Context:**
        - **Why:** Every save writes a full backup with all secrets. Backups are never pruned, keep the source mode (0644), and `backup/` is copied into the Docker image.
        - **Architecture:** `create_backup` in `src/utils/backup.py` is the one place all backups go through (`settings.py`, `config_handler.py:46,78`, `wizard.py:181`, `run.py:70`). Fix it there.
        - **Key refs:** `src/utils/backup.py:20-54`, `tests/test_utils/test_backup.py`, `.dockerignore`
        - **Watch out:** The timestamp has second precision, so a test that makes 11 backups must patch `src.utils.backup.datetime`. The prune glob must be `f"{stem}_[0-9]*_[0-9]*.yaml"`, or `config_*` also matches `config_example_...` files. Keep `shutil.copy2` (an existing test patches it). Do not chmod the backup dir: a dir owned by another user would break backups. Only new dirs get `mode=0o700`.
    - **Scope:** `MAX_BACKUPS = 10`, `_prune_backups(backup_dir: str, stem: str) -> None`, chmod `0o600`, dir mode, `.dockerignore` line
    - **Touches:** `src/utils/backup.py`, `.dockerignore`, `tests/test_utils/test_backup.py`
    - **Action items:**
        - [RED] `test_backups_are_pruned_to_newest_ten`: 11 backups, 10 `config_*.yaml` remain, the oldest is gone
        - [RED] `test_backups_are_owner_only`: backup mode is `0o600` for a `0o644` source
        - [RED] `test_new_backup_dir_is_owner_only`: new `backup/` has mode `0o700`
        - [RED] `test_prune_keeps_unrelated_files`: `config_example_20260101_000000.yaml` and `notes.txt` survive; fewer than 10 backups delete nothing
        - [RED] `test_dockerignore_lists_backup_dir`: `.dockerignore` has the line `backup/`
        - [GREEN] Implement in `create_backup`: `mkdir(mode=0o700, ...)`, `os.chmod(backup_file, 0o600)`, `_prune_backups(...)` with `unlink(missing_ok=True)`; add `backup/` to `.dockerignore`
    - **Success:** `scripts/test_runner.py utils --coverage` passes, flake8 and mypy clean

- [ ] **1.2** F030 and F031: write once and keep comments
    - **Context:**
        - **Why:** `Config.save()` truncates the file and then dumps with PyYAML, so a failed dump leaves an empty `config.yaml`, and PyYAML drops every comment. `_load_config` uses `yaml.safe_load`, so comments are lost at load too.
        - **Architecture:** `src/config/settings.py` gets a module-level `_yaml = YAML()` (ruamel round-trip, `preserve_quotes = True`, `indent(mapping=2, sequence=4, offset=2)`, as in `src/utils/config_handler.py:23-25`). Do not import `config_handler` (ADR 0005). `Config._write_config(self) -> None` dumps `self._config` to a `StringIO`, then opens `CONFIG_PATH` once and writes the text. `save()` is `create_backup()` then `_write_config()`. The startup prompt write at `settings.py:123-124` calls `_write_config()` too.
        - **Key refs:** `src/config/settings.py:90-102` (`_load_config`), `:123`, `:273-277` (`save`); `tests/test_config/conftest.py` (`load_settings`); `tests/test_config/test_settings.py` (`TestSave` at ~296, `TestRealSettingsMissingSection`)
        - **Watch out:** `load_settings` patches `open` only while the module loads, and `create_backup` is already a mock on the loaded module. For `save()` tests, set `result.module.CONFIG_PATH` to a file in `tmp_path`. `config_example.yaml` is still read with `yaml.safe_load` (PyYAML stays imported). Replace the two `TestSave` tests that copy the code (`test_save_writes_yaml`, `test_save_creates_backup_first`); keep `test_save_is_noop_in_mock`. The red run of the dump-fails test patches `module.yaml.dump`, so it fails on the old code for the right reason. Add a code comment: one write, no `os.replace`, because the compose file bind-mounts the single file `config.yaml` and a replace would break the mount.
    - **Scope:** ruamel load, `_write_config`, `save`, startup write, test replacement
    - **Touches:** `src/config/settings.py`, `tests/test_config/test_settings.py`
    - **Action items:**
        - [RED] `test_save_keeps_old_file_when_dump_fails`: dump raises, `config.yaml` keeps its old text
        - [RED] `test_save_keeps_comments_and_quotes`: `# keep me`, `password: "123456"` and the changed `language` value are in the saved text
        - [RED] `test_startup_prompt_write_keeps_comment`: the interactive missing-section run keeps `# keep me` in `result.written[CONFIG_PATH]`
        - [GREEN] Implement the loader, `_write_config`, `save`; point the `:123` write at `_write_config`; switch the dump-fails patch to `_yaml.dump`
        - [GREEN] Remove the two copied-code `TestSave` tests
    - **Success:** `scripts/test_runner.py config --coverage` passes, `mypy src/` clean, flake8 clean

- [ ] **1.3** F032: tell the user when the auth save fails
    - **Context:**
        - **Why:** `_save_authenticated_users` logs the error but `check_password` still sends "Chatid added", so the user thinks the login stays after a restart.
        - **Architecture:** `_save_authenticated_users(self) -> bool` returns `True` after `config.save()` and `False` after the ERROR log. `check_password` sends `get_text("Chatid added" if saved else "AuthSaveFailed")`. The user stays in `AuthHandler._authenticated_users`, and commands and `/start` follow as before.
        - **Key refs:** `src/bot/handlers/auth.py:134-143` and `:205-229`; `tests/test_handlers/test_auth_handler.py` (`test_save_authenticated_users_exception` at ~438, `test_check_password_correct` at ~616); `.claude/skills/i18n-key/SKILL.md`
        - **Watch out:** #210 (addarr-14) also edits `_save_authenticated_users` (F091); whichever PR merges second merges `origin/development` and keeps both. The translation mock returns the key as text, so assert on `"AuthSaveFailed"`. `nl-be` uses standard Netherlands Dutch. No emoji in the new key. English text: `You are authorized for now, but the bot could not save this. You must authenticate again after a restart. Ask the admin to check that config.yaml is writable.`
    - **Scope:** return value, reply choice, new key in the template and 9 locales
    - **Touches:** `src/bot/handlers/auth.py`, `translations/addarr.template.yml` and the 9 `translations/addarr.<locale>.yml` files, `tests/test_handlers/test_auth_handler.py`
    - **Action items:**
        - [RED] `test_check_password_save_failure_warns_user`: `config.save` raises `OSError`; `chat.send_message` gets `"AuthSaveFailed"`, never `"Chatid added"`; `logger.error` called; the user id is still in `_authenticated_users`
        - [RED] `test_save_authenticated_users_returns_bool`: `True` on success, `False` when `save` raises
        - [GREEN] Implement the return value and the reply choice
        - [GREEN] Add `AuthSaveFailed` after `Chatid added` in all 10 translation files (`@i18n-key`)
    - **Success:** `scripts/test_runner.py handlers --coverage` passes, `PYTHONIOENCODING=utf-8 run.py --validate-i18n` passes, flake8 and mypy clean

- [ ] **1.4** Docs note
    - **Context:**
        - **Why:** CLAUDE.md § Configuration should say how config saves behave now.
        - **Architecture:** One added sentence, no ADR (no rule in CLAUDE.md changes).
        - **Key refs:** `CLAUDE.md` § Configuration
        - **Watch out:** `tests/test_architecture/test_repo_docs.py` checks every repo path CLAUDE.md names; name only paths that exist.
    - **Scope:** one sentence
    - **Touches:** `CLAUDE.md`
    - **Action items:**
        - [GREEN] Add: `Config` loads `config.yaml` with ruamel, so comments survive a save, and `create_backup` keeps the newest 10 backups in `backup/`, mode `0o600`.
    - **Success:** `pytest tests/test_architecture --tb=short -v` passes

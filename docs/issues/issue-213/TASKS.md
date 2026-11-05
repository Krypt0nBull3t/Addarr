# Windows installer runs the bot as SYSTEM (#213) Tasks

Source: `docs/issues/issue-213/plan.md` (design: `design.md`). Branch `fix/213-windows-installer-runs-bot-as-system`. Every test and push runs through the suite lock: `~/.local/share/agent-suite/with-suite-lock.sh addarr/$AO_SESSION_ID --`.

### Phase 1: Logon task instead of the SYSTEM service (2 tasks)

**Goal:** `install.ps1` runs the bot as a logon scheduled task as the normal user, starts it only after setup wrote `config.yaml`, downloads no NSSM, and the README points to no broken script.

**Phase Context:**

- Why NOT keep the Administrator check: a user-level task needs no admin, and the git clone and pip install should not run elevated. Removing an older NSSM service needs admin, so the installer warns and prints the commands (design.md, decision 1).
- Why static text tests: neither this machine nor CI has `pwsh`. #201 set the pattern in `tests/test_install_scripts.py` (read the file, assert on its text, never run the installer).
- The Windows acceptance checks from the issue cannot run here. The PR body says so.

- [x] **1.1** Replace the NSSM service with a logon scheduled task in `install.ps1` (F180, F181, F182)
    - **Context:**
        - **Why:** The installer downloads NSSM with no hash check and runs it as admin (`install.ps1:115-125`). It installs a `LocalSystem` service whose wrapper script sits in the user-writable install dir (`:106-133`). It offers "start now" before any `config.yaml` exists (`:145-150`).
        - **Architecture:** One PowerShell script, no new files. The task runs `venv\Scripts\python.exe run.py` directly with the install dir as working directory, so no editable wrapper script remains. The principal is `[Security.Principal.WindowsIdentity]::GetCurrent().Name` with `-LogonType Interactive -RunLevel Limited`.
        - **Key refs:** `scripts/install.ps1:37-42` (Administrator check), `:101-157` (service block), `:159-168` (completion text that reads `$installService`). `run.py:58-60` (`--setup` runs the wizard). `src/definitions.py:18` (`CONFIG_PATH` is `<install dir>\config.yaml`). `tests/test_install_scripts.py` (`read`, `INSTALL_PS1`, `TestRepoUrls` as the style template).
        - **Watch out:** The tests assert the words `nssm`, `LocalSystem`, `New-Service`, `Start-Service`, `service-wrapper` and `as Administrator` are absent from the whole script, comments included. The legacy-service warning says "SYSTEM rights" and "an Administrator PowerShell". `$ErrorActionPreference = "Stop"` does not stop on a native command's exit code, so check `Test-Path` for `config.yaml` after `--setup`. A fresh clone has no `config.yaml` (git-ignored); the installer moves an existing install dir to a backup first. Keep existing comments outside the edited blocks.
    - **Scope:** Remove the Administrator check. Warn about an older `Addarr` service. Ask about starting at logon; on `y` run setup, check `config.yaml`, register the task, then offer "start now". Rework the completion text to use a `$taskInstalled` boolean.
    - **Touches:** `scripts/install.ps1`, `tests/test_install_scripts.py` (new `TestWindowsInstaller`), `docs/issues/issue-213/` (design.md, plan.md, TASKS.md go in this commit)
    - **Action items:**
        - [RED] Write `test_downloads_no_service_manager`, `test_registers_no_system_service`, `test_requires_no_administrator` and `test_warns_about_older_service` (strings in plan.md task 1)
        - [RED] Write `test_task_runs_as_current_user_with_limited_rights`, `test_task_restarts_after_failure` and `test_task_is_replaced_on_reinstall`
        - [RED] Write `test_setup_runs_before_config_check_task_and_start` (`--setup` < `Test-Path "$INSTALL_DIR\config.yaml"` < `Register-ScheduledTask` < `Start-ScheduledTask`)
        - [RED] Run `-k TestWindowsInstaller`: all 8 fail
        - [GREEN] Delete the Administrator check. Replace the service block with the flow in plan.md task 1, step 3. Update the completion text.
        - [GREEN] Run the whole `tests/test_install_scripts.py` and `tests/test_architecture`: pass
    - **Success:** 8 new tests pass, the #201 tests in the file still pass, architecture tests pass, flake8 and mypy clean.
    - **Completed:** 2026-11-05
    - **Learnings:**
        - `run.py --setup` resets an existing `config.yaml` (`reset=True`), so the installer runs it only on a fresh clone. The backup `mv` of an old install dir guarantees that.
        - `$ErrorActionPreference = "Stop"` does not stop on a native command's exit code, so a `Test-Path` on `config.yaml` is the only check that setup finished.
        - The text tests ban whole words (`LocalSystem`, `as Administrator`), so comments and messages must avoid them.
    - **Key Changes:**
        - `scripts/install.ps1`: removed the Administrator check and the NSSM block; added the older-service warning, the logon question, setup, the `config.yaml` check, `Register-ScheduledTask` (current identity, `-RunLevel Limited`, restart 3 times at 1 minute) and "start now" with `Start-ScheduledTask`; the completion text reads `$taskInstalled`.
        - `tests/test_install_scripts.py`: new `TestWindowsInstaller` (8 tests).
    - **Notes:** The PowerShell is not run here (no `pwsh`). The developer runs the Windows acceptance checks from the issue on Windows 10/11.

- [ ] **1.2** Delete `addarr.service.ps1` and its README section, add the scheduled-task note (F183)
    - **Context:**
        - **Why:** `scripts/addarr.service.ps1` registers `powershell.exe` with `New-Service`, which cannot start (error 1053). `README.md` points to it and links to the section.
        - **Architecture:** Docs and one deleted file. The new README note is the working path for Windows users.
        - **Key refs:** `README.md:77` (quick install says "as Administrator"), `:141` (TOC link `[Windows Service](#windows-service)`), `:583-604` (Service Management intro and the "Windows Service" section). `tests/test_architecture/test_repo_docs.py` (checks README paths still exist).
        - **Watch out:** Issue #215 also edits README lines; touch only the lines named here. `README.md:289-291` ("After installation") stays. The tests assert that `addarr.service.ps1`, `AddarrBot`, `Windows Service`, `Start-Service` and `as Administrator` are absent from the whole README.
    - **Scope:** `git rm` the script, fix the quick-install text, the TOC link and the Service Management section.
    - **Touches:** `scripts/addarr.service.ps1` (delete), `README.md`, `tests/test_install_scripts.py` (new `TestWindowsReadme`)
    - **Action items:**
        - [RED] Write `test_service_script_is_gone`, `test_readme_points_to_no_windows_service` and `test_readme_documents_the_scheduled_task`
        - [RED] Run `-k TestWindowsReadme`: all 3 fail
        - [GREEN] `git rm scripts/addarr.service.ps1`; edit `README.md:77`, `:141` and the Service Management section as in plan.md task 2
        - [GREEN] Run `tests/test_install_scripts.py` and `tests/test_architecture`: pass
        - [GREEN] `git grep -n -i -E "nssm|addarr\.service\.ps1|LocalSystem"` lists no match in `scripts/` or `README.md`
    - **Success:** 3 new tests pass, architecture tests pass (including `test_repo_docs.py`), no reference to the deleted script remains.

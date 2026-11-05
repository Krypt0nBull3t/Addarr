# Windows installer runs the bot as SYSTEM (#213) Implementation Plan

**Goal:** Fix F180 to F183: `install.ps1` downloads no NSSM, runs the bot as a logon scheduled task as the normal user (`RunLevel Limited`), starts it only after setup wrote `config.yaml`, and the README points to no broken script.

**Architecture:** Replace the service block of `scripts/install.ps1` (lines 101-157) and the Administrator check (lines 37-42). Delete `scripts/addarr.service.ps1` and the README "Windows Service" section. Pin the new shape with static text checks in `tests/test_install_scripts.py`, in the style of #201. The tests read the files and never run PowerShell.

**Tech Stack:** PowerShell (`ScheduledTasks` module cmdlets), pytest, `os`, `re`.

**Spec:** `docs/issues/issue-213/design.md`

## Context

Root causes (verified, line numbers match the issue on `development` at 8699324):

- **F181:** `install.ps1:115-125` downloads `nssm-2.24.zip` from `nssm.cc` and extracts it with no hash check.
- **F180:** `install.ps1:129-133` installs a `LocalSystem` service whose wrapper script, `service-wrapper.ps1` (written at `:106-112`), sits in the user-writable `%LOCALAPPDATA%\Addarr`.
- **F182:** `install.ps1:145-150` offers "start now" before `config.yaml` exists. A fresh clone has none (`config.yaml` is git-ignored).
- **F183:** `scripts/addarr.service.ps1` calls `New-Service` with `powershell.exe` as the binary (error 1053). `README.md:587-604` points to it, and `README.md:141` links to the section.
- Other README text to change: `:77` ("Open PowerShell as Administrator") and `:588` (inside the deleted section).

## Global Constraints

- Branch `fix/213-windows-installer-runs-bot-as-system`, PR targets `development`, body links `Closes #213`.
- The task runs as the installing user with `-RunLevel Limited`. Never `-RunLevel Highest`, never SYSTEM, never a stored password.
- `install.ps1` downloads nothing except the existing `git clone` and `pip install`.
- The script text must not contain the words `nssm`, `LocalSystem` or `New-Service` (the tests assert that, so comments avoid them).
- Existing `install.ps1` text outside the edited blocks stays (clone URL, venv, launcher, PATH).
- `pytest`, `flake8` and `mypy src/` pass, with the 100% coverage gate (no `src/` change is expected).
- Every test, gate and `git push` runs through the suite lock.
- Existing comments in files you edit stay unless the task removes the code they describe.

## Review Focus

- A user without Administrator rights runs the installer. Expected: no "run as Administrator" exit (test pins no `IsInRole`).
- A machine with an older `Addarr` NSSM service. Expected: a warning with `sc.exe stop Addarr` and `sc.exe delete Addarr`, and the install goes on.
- The user answers `n` to the logon question. Expected: no setup, no task, nothing started.
- `--setup` ends without `config.yaml` (user aborted). Expected: no task registered, a message with the retry steps.
- A reinstall with an existing `Addarr` task. Expected: the task is removed first, then registered again.

## Tasks

### Task 1: Installer tests (RED), then `install.ps1` (GREEN)

**Files:**
- Modify: `tests/test_install_scripts.py` (new class `TestWindowsInstaller`, after `TestRepoUrls`)
- Modify: `scripts/install.ps1:37-42` (remove the Administrator check), `:101-157` (replace the service block)

**Interfaces:**
- Produces: `install.ps1` contains `Register-ScheduledTask`, `Start-ScheduledTask`, `Get-Service -Name Addarr` and the strings the tests below pin. Task 2 relies on none of them.

- [ ] **Step 1: Write the failing tests.** Add `class TestWindowsInstaller` with a `text()` helper (`read(INSTALL_PS1)`) and these tests, each with a one-line docstring in the file's style:
  - `test_downloads_no_service_manager`: `"nssm"` not in the lowercase text; none of `Invoke-WebRequest`, `DownloadString`, `Expand-Archive` in the text.
  - `test_registers_no_system_service`: `"LocalSystem"`, `"New-Service"`, `"Start-Service"` and `"service-wrapper"` not in the text.
  - `test_requires_no_administrator`: `"IsInRole"` and `"as Administrator"` not in the text.
  - `test_warns_about_older_service`: the text contains `Get-Service -Name Addarr`, `sc.exe stop Addarr` and `sc.exe delete Addarr`.
  - `test_task_runs_as_current_user_with_limited_rights`: the text contains `Register-ScheduledTask`, `-RunLevel Limited`, `-LogonType Interactive`, `-AtLogOn` and `[Security.Principal.WindowsIdentity]::GetCurrent().Name`; `"-RunLevel Highest"` is not in it.
  - `test_task_restarts_after_failure`: the text contains `-RestartCount 3`, `-RestartInterval (New-TimeSpan -Minutes 1)` and `-ExecutionTimeLimit ([TimeSpan]::Zero)`.
  - `test_task_is_replaced_on_reinstall`: `Unregister-ScheduledTask -TaskName Addarr` appears before `Register-ScheduledTask`.
  - `test_setup_runs_before_config_check_task_and_start`: with `i = text.index`, assert `i("--setup") < i('Test-Path "$INSTALL_DIR\\config.yaml"') < i("Register-ScheduledTask") < i("Start-ScheduledTask")`.

- [ ] **Step 2: Run them to verify they fail.**
  Run: `~/.local/share/agent-suite/with-suite-lock.sh addarr/$AO_SESSION_ID -- .venv/bin/python -m pytest tests/test_install_scripts.py -k TestWindowsInstaller -v`
  Expected: all 8 FAIL (7 on a missing or present string, `test_setup_runs...` with `ValueError: substring not found`).

- [ ] **Step 3: Edit `scripts/install.ps1`.**
  - Delete the Administrator check (the `$isAdmin` line, its `if` block and the comment above them).
  - Replace the block from `# Ask about Windows service installation` to the closing `}` of the `if ($installService ...)` with the flow below. Keep the "Installation complete" block, and change its numbered steps so step 2 shows `addarr` only when no task was installed (use a `$taskInstalled` boolean instead of `$installService`).
  - Flow, in this order:
    1. `$legacyService = Get-Service -Name Addarr -ErrorAction SilentlyContinue`. If found: yellow warning that an older Addarr service exists and may run with SYSTEM rights, then print `sc.exe stop Addarr` and `sc.exe delete Addarr` with "run these in an Administrator PowerShell". No exit.
    2. Prompt `Would you like Addarr to start automatically when you log on? [y/N]`. On `y`:
       1. Run `& "$INSTALL_DIR\venv\Scripts\python.exe" "$INSTALL_DIR\run.py" --setup`.
       2. If `-not (Test-Path "$INSTALL_DIR\config.yaml")`: red message that setup wrote no `config.yaml`, no task installed, run `addarr --setup` and then this installer again. Skip the rest.
       3. Else: `$identity = [Security.Principal.WindowsIdentity]::GetCurrent().Name`. Build `New-ScheduledTaskAction -Execute "$INSTALL_DIR\venv\Scripts\python.exe" -Argument "`"$INSTALL_DIR\run.py`"" -WorkingDirectory $INSTALL_DIR`, `New-ScheduledTaskTrigger -AtLogOn -User $identity`, `New-ScheduledTaskPrincipal -UserId $identity -LogonType Interactive -RunLevel Limited`, and `New-ScheduledTaskSettingsSet -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries`.
       4. `Unregister-ScheduledTask -TaskName Addarr -Confirm:$false -ErrorAction SilentlyContinue`, then `Register-ScheduledTask -TaskName Addarr -Description "Telegram bot for media management through Radarr, Sonarr, and Lidarr" ...` with the four objects. Set `$taskInstalled = $true`. Green confirmation that Addarr starts at logon as `$identity`.
       5. Prompt `Would you like to start Addarr now? [y/N]`. On `y`: `Start-ScheduledTask -TaskName Addarr`, then print the manage commands (`Start-ScheduledTask`, `Stop-ScheduledTask`, `Get-ScheduledTask` with `-TaskName Addarr`).
  - Shortcut: the task needs a logon, so it first runs at the next logon unless "start now" is chosen. No comment needed in code; the green message says it.

- [ ] **Step 4: Run the tests to verify they pass.**
  Run: the command from step 2.
  Expected: 8 passed. Then run `~/.local/share/agent-suite/with-suite-lock.sh addarr/$AO_SESSION_ID -- .venv/bin/python -m pytest tests/test_install_scripts.py -v`. Expected: all pass, the #201 tests unchanged.

- [ ] **Step 5: Scoped architecture check, then commit.**
  Run: `~/.local/share/agent-suite/with-suite-lock.sh addarr/$AO_SESSION_ID -- .venv/bin/python -m pytest tests/test_architecture --tb=short -v`. Expected: pass.
  Commit `design.md`, `plan.md`, `TASKS.md`, the test file and `install.ps1` with `fix: run the Windows bot as a logon task as the normal user (#213, task 1.1)`. (The design and plan files go in the first commit.)

### Task 2: Delete the service script, fix the README (F183)

**Files:**
- Delete: `scripts/addarr.service.ps1`
- Modify: `README.md:77` (quick-install text), `:141` (TOC link), `:583-604` (Service Management intro and the "Windows Service" section)
- Test: `tests/test_install_scripts.py` (new class `TestWindowsReadme`)

**Interfaces:**
- Consumes: Task 1's `TestWindowsInstaller` class position only (add the new class after it).

- [ ] **Step 1: Write the failing tests.** `class TestWindowsReadme`:
  - `test_service_script_is_gone`: `os.path.exists(os.path.join(ROOT, "scripts", "addarr.service.ps1"))` is `False`.
  - `test_readme_points_to_no_windows_service`: none of `addarr.service.ps1`, `AddarrBot`, `Windows Service`, `Start-Service`, `as Administrator` is in `read(README)`.
  - `test_readme_documents_the_scheduled_task`: `Start-ScheduledTask -TaskName Addarr`, `Stop-ScheduledTask -TaskName Addarr` and `Get-ScheduledTask -TaskName Addarr` are in `read(README)`.

- [ ] **Step 2: Run them to verify they fail.**
  Run: `~/.local/share/agent-suite/with-suite-lock.sh addarr/$AO_SESSION_ID -- .venv/bin/python -m pytest tests/test_install_scripts.py -k TestWindowsReadme -v`
  Expected: 3 FAIL.

- [ ] **Step 3: Edit.**
  - `git rm scripts/addarr.service.ps1`.
  - `README.md:77`: "Open PowerShell and run:" (no Administrator).
  - `README.md:141`: replace the `[Windows Service](#windows-service)` TOC line with `[Windows Scheduled Task](#windows-scheduled-task)`.
  - `README.md:585`: "Addarr Refresh can run as a logon scheduled task on Windows or as a Linux Systemd service:".
  - Replace the `### Windows Service` section (heading, steps 1-4) with `### Windows Scheduled Task`: one sentence that the installer offers a task that starts Addarr at logon as your normal user, after setup; then a `powershell` block with `Start-ScheduledTask -TaskName Addarr`, `Stop-ScheduledTask -TaskName Addarr`, `Get-ScheduledTask -TaskName Addarr`.
  - Keep the existing "After installation" text at `:289-291`; the installer text already tells the user what to do.

- [ ] **Step 4: Run the tests to verify they pass.**
  Run: `~/.local/share/agent-suite/with-suite-lock.sh addarr/$AO_SESSION_ID -- .venv/bin/python -m pytest tests/test_install_scripts.py tests/test_architecture --tb=short -q`
  Expected: pass (`test_repo_docs.py` checks the README paths still exist).

- [ ] **Step 5: Commit.** `fix: delete the broken Windows service script and its README section (#213, task 2.1)`. Stage only the deleted script, `README.md`, the test file and `TASKS.md`.

## Verification (before the PR)

- Full preflight through `/addarr pr` (lint, mypy, translations, unit tests with the 100% gate, integration, architecture).
- `git grep -n -i -E "nssm|addarr\.service\.ps1|LocalSystem"` outside `docs/issues/audit-2026-10-28` and the tests lists no match in `scripts/` or `README.md`.
- Manual Windows 10/11 checks from the issue (`Get-ScheduledTask Addarr` shows the installing user and `Limited`; `sc qc Addarr` finds no service; a fresh install runs setup before the start prompt). They cannot run here: the PR body says so, and the developer runs them.

# Windows installer runs the bot as SYSTEM (#213) Design

Status: APPROVED by the lead on 2026-11-05 ("go with your recommendations").

## Analysis

- Layer: scripts and docs only. No change in `src/`.
- Files: `scripts/install.ps1`, `scripts/addarr.service.ps1` (delete), `README.md` (quick-install text at line 77, Service Management section, its TOC link), `tests/test_install_scripts.py` (extend; static text checks in the style of #201, never run the installer; neither this machine nor CI has `pwsh`).
- Root cause: `install.ps1:101-157` builds an NSSM `LocalSystem` service around `service-wrapper.ps1`, which sits in the user-writable install dir. "Start now" runs before any `config.yaml` exists. No other file references NSSM or `addarr.service.ps1`.
- Setup writes `config.yaml` in the install dir (`CONFIG_PATH` in `src/definitions.py`). `config.yaml` is git-ignored, so a fresh clone has none. `run.py --setup` resets an existing `config.yaml`, but the installer moves an existing install dir to a backup first, so the new dir never has one.
- Not verifiable here: the Windows acceptance checks (`Get-ScheduledTask`, `sc qc`). The PR says so.

## Decisions

1. **No Administrator check.** A user-level task needs no admin, and the git clone and pip install stop running elevated. An older `Addarr` NSSM service is detected with `Get-Service` (works without admin). The installer warns and prints the removal commands (`sc.exe stop Addarr`, `sc.exe delete Addarr`) for an admin shell, then goes on. The README quick-install text drops "as Administrator".
2. **Setup only with the task.** The installer asks "start Addarr at logon?". On `y` it runs `venv\Scripts\python.exe run.py --setup`, checks that `config.yaml` exists, and only then registers the task. On `n` it starts nothing and prints the manual steps.
3. **Task shape.** Trigger `AtLogOn` for the current identity. Action `venv\Scripts\python.exe run.py` with the install dir as working directory (no wrapper script to edit). `LogonType Interactive`, `RunLevel Limited`. Restart on failure 3 times at 1 minute. No time limit. A task named `Addarr` is removed first, so a reinstall works. `python.exe` (visible console), so the user can read the log output.
4. **README.** Delete the "Windows Service" section and its TOC link. Add a short "Windows scheduled task" note under Service Management with `Start-ScheduledTask`, `Stop-ScheduledTask` and `Get-ScheduledTask -TaskName Addarr`.

## Out of scope

- Carrying a backed-up `config.yaml` into a reinstall.
- A `-RunLevel Highest` or boot-time (pre-logon) start. A boot-time task would need a stored password or SYSTEM, which is the bug.

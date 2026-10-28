---
title: "Windows installer runs the bot as SYSTEM"
labels: [bug, security, ops, priority:high]
slice: 18
findings: [F181, F180, F182, F183]
---

## Bug

- `install.ps1` downloads NSSM without a hash check and then runs it as admin.
- The NSSM service runs as `LocalSystem` from the user-writable `%LOCALAPPDATA%\Addarr`. Any user process can edit `service-wrapper.ps1` and get SYSTEM.
- "Start now" is offered before any `config.yaml` exists, so the service crash-loops.
- `addarr.service.ps1` registers `powershell.exe` with `New-Service`. That service cannot start (error 1053). The README points to this script.

## Steps to reproduce

1. Run `scripts/install.ps1` as admin and answer `y` to the service question.
2. See that NSSM is downloaded from `https://nssm.cc/release/nssm-2.24.zip` and extracted with no hash check.
3. Run `sc qc Addarr`: the service runs as `LocalSystem`.
4. As a normal user, edit `%LOCALAPPDATA%\Addarr\service-wrapper.ps1` and restart the service: the edit runs as SYSTEM.
5. On a fresh install with no `config.yaml`, answer `y` to "start Addarr now": the service crash-loops.
6. Follow the README "Windows Service" section and run `scripts\addarr.service.ps1`, then `Start-Service AddarrBot`: error 1053.

## Expected behavior

The installer downloads no NSSM. The bot runs as a logon scheduled task as the normal user, not SYSTEM. The bot starts only after setup has written `config.yaml`. The README points to no broken script.

## Fix

- [ ] **F181** Drop NSSM and its download (`scripts/install.ps1:115-121`)
- [ ] **F180** Replace the `LocalSystem` NSSM service with a logon scheduled task that runs as the normal user (`Register-ScheduledTask -RunLevel Limited`) (`scripts/install.ps1:106-132`)
- [ ] **F182** Run setup before the first start (`scripts/install.ps1:145-150`)
- [ ] **F183** Delete `scripts/addarr.service.ps1` and the README "Windows Service" section (`scripts/addarr.service.ps1`, `README.md:591-607`)

## Acceptance criteria

Manual checks on Windows 10/11:

- [ ] F181: `install.ps1` has no NSSM step and downloads nothing from `nssm.cc`.
- [ ] F180: after install, `Get-ScheduledTask Addarr` shows the installing user and `RunLevel Limited`. `sc qc Addarr` finds no `LocalSystem` service.
- [ ] F182: on a fresh install with no `config.yaml`, setup runs before the start prompt and the bot does not crash-loop.
- [ ] F183: `scripts/addarr.service.ps1` is gone and `README.md` has no reference to it.
- [ ] `pytest`, `flake8` and `mypy src/` pass.

## Notes

- Source: audit 2026-10-28, docs/issues/audit-2026-10-28/FINDINGS.md (F-ids F181, F180, F182, F183).
- Priority: max P 25, sum P 89 (high).
- Dependencies: none in the order of work. Slice 6 (F171) also edits `scripts/install.ps1:62` (clone URL).
- Decided 2026-10-28: F180 logon scheduled task as the normal user (`Register-ScheduledTask -RunLevel Limited`).
- Decided 2026-10-28: F181 drop NSSM and its download.
- Decided 2026-10-28: F182 run setup before the first start.
- Decided 2026-10-28: F183 delete `addarr.service.ps1` and its README section.

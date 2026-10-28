---
title: "Linux install and systemd unit are broken"
labels: [bug, ops, documentation, agent-ready, priority:critical]
slice: 6
findings: [F170, F171, F173, F172, F174]
---

## Bug

The Linux install path installs the wrong repo, can lose an old install, accepts a Python that cannot run the bot, and starts a service that cannot save anything.

- **F170** `ProtectHome=read-only` makes `~/.addarr` read-only (tested: "Read-only file system"). /auth, settings, logs and preferences cannot be saved.
- **F171** install.sh, install.ps1 and the README clone `Cyneric/Addarr`, not this repo.
- **F173** The restore `trap` is set on the last lines of install.sh, so it never fires. A failed reinstall leaves the old install, with its config.yaml, in a backup folder.
- **F172** install.sh accepts Python 3.8. `tuple[bool, str]` fails to import on 3.8, and the deps need 3.10+.
- **F174** The README runs `curl ... | sudo bash`. On Ubuntu that sets HOME=/root, so Addarr installs under /root.

## Steps to reproduce

F170:

1. Install with `scripts/addarr.service` and start the service.
2. Send /auth with the right password.
3. Saving config.yaml fails with "Read-only file system". The user is lost at the next restart.

F171:

1. Run `scripts/install.sh` or `scripts/install.ps1`.
2. It clones `https://github.com/Cyneric/Addarr.git`.

F173:

1. Install Addarr once.
2. Run install.sh again. It moves the old install to `<install dir>.backup.<date>`.
3. Make a later step fail, for example with no network.
4. The script exits without restoring the backup. The old install and its config.yaml stay in the backup folder.

F172:

1. Run install.sh on a host with Python 3.8.
2. The version check passes.
3. The bot fails to import `tuple[bool, str]`, and the deps fail to install.

F174:

1. On Ubuntu, run the README command `curl -sSL .../install.sh | sudo bash`.
2. Addarr is installed under /root.

## Expected behavior

- The service can write to `~/.addarr`.
- The installers fetch this repo. README links and wiki and issue URLs point to this repo.
- A failed reinstall restores the old install.
- install.sh refuses Python older than 3.10.
- The README command installs for the current user.

## Fix

- [ ] **F170** Add `ReadWritePaths=%h/.addarr` (`scripts/addarr.service:29`)
- [ ] **F171** Point the installers, the README links and the wiki and issue URLs to `Krypt0nBull3t/Addarr` (`scripts/install.sh:406`, `scripts/install.ps1:61`, `README.md:75`, `:259`, `:304`, `:646`; the same upstream URL is also at `README.md:82`, `:264`, `:282`, `:331`)
- [ ] **F173** Set the traps at the top of the script (`scripts/install.sh:395-401`, `:638-639`)
- [ ] **F172** Set `MIN_PYTHON_VERSION="3.10"` (`scripts/install.sh:47`)
- [ ] **F174** Drop `sudo` from the README commands. The script asks for sudo only for packages (`README.md:75`, `:259`, `:264`)

## Acceptance criteria

Each test below fails before the fix and passes after it. Put them in a root-level test file such as `tests/test_install_scripts.py`, like `tests/test_dockerfile.py`.

- **F170** The test parses `scripts/addarr.service`. When it has `ProtectHome=read-only`, it also has `ReadWritePaths=%h/.addarr`.
- **F171** No clone, download, install, wiki or issue URL in `scripts/install.sh`, `scripts/install.ps1` or `README.md` points to `Cyneric/Addarr`. Author credit lines are excepted.
- **F173** In `scripts/install.sh`, the `trap 'cleanup error' ERR` line comes before the backup `mv`.
- **F172** `scripts/install.sh` sets `MIN_PYTHON_VERSION="3.10"`.
- **F174** `README.md` contains no `| sudo bash`.
- `pytest`, `flake8` and `mypy src/` pass.

## Notes

- Source: audit 2026-10-28, docs/issues/audit-2026-10-28/FINDINGS.md (F-ids F170, F171, F173, F172, F174).
- Priority: max P 40, sum P 135 (critical).
- Dependencies: slices 1-8 go first.
- Related: F170 is one cause of F032 (slice 14, lost /auth saves). Slice 20 (F280) fixes other README lines.
- Decided 2026-10-28: F171 point the installers, README links and wiki and issue URLs to `Krypt0nBull3t/Addarr`.

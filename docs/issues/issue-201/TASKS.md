# Issue #201 Tasks: Linux install and systemd unit are broken

Plan: `docs/issues/issue-201/plan.md`. Branch: `fix/201-linux-install-and-systemd-unit`.
Run every test through the suite lock. Test file for all tasks: `tests/test_install_scripts.py` (new, created in 1.1).

### Phase 1: Install scripts and service unit (6 tasks)

**Goal:** Fix F170 to F174 so the Linux install fetches this repo, restores on failure, checks Python 3.10, installs for the current user, and the service can write to `~/.addarr`.

**Phase Context:**

- Why NOT only the README for F174: `check_sudo` exits unless the user is root, so a README without `sudo` fails when a package is missing.
- Why NOT the issue's `trap 'cleanup error' ERR` for F173: install.sh has no `set -e` and fails through `exit 1`, which never fires `ERR`.
- README edits stay on the lines the issue lists plus `README.md:204` (issue #215 edits other README lines).

- [x] **1.1** F170: service can write to `~/.addarr`
    - **Context:**
        - **Why:** `ProtectHome=read-only` makes `~/.addarr` read-only, so /auth, settings, logs and preferences cannot be saved.
        - **Architecture:** Root-level test file in the style of `tests/test_dockerfile.py` (path constants from `os.path.dirname(os.path.dirname(__file__))`, a `read()` helper).
        - **Key refs:** `scripts/addarr.service:29`, `tests/test_dockerfile.py:1-15`
        - **Watch out:** `%h` is a systemd specifier and works in `ReadWritePaths`. Do not change `ProtectHome`.
    - **Scope:** New test file with constants and helper, one service line
    - **Touches:** `tests/test_install_scripts.py` (new), `scripts/addarr.service`
    - **Action items:**
        - [RED] Write `test_service_allows_writes_to_addarr_dir`: with `ProtectHome=read-only` the file also has `ReadWritePaths=%h/.addarr`
        - [GREEN] Add `ReadWritePaths=%h/.addarr` after `ProtectHome=read-only`
    - **Success:** The test fails before and passes after, flake8 clean
    - **Completed:** 2026-11-04
    - **Learnings:**
        - The test passes by design when the unit has no `ProtectHome=read-only`, as the issue's criterion says ("when it has ... it also has"). It failed on the unfixed file, so it can catch the defect.
    - **Key Changes:**
        - Created `tests/test_install_scripts.py` with the path constants, `read()` and `TestServiceUnit`.
        - Added `ReadWritePaths=%h/.addarr` to `scripts/addarr.service`.
    - **Notes:** Later tasks add tests to this file. Keep `read()` and the path constants.

- [ ] **1.2** F171: point URLs to `Krypt0nBull3t/Addarr`
    - **Context:**
        - **Why:** The installers and README fetch `Cyneric/Addarr`, not this repo.
        - **Architecture:** Plain text replacement, keep the `main` branch in raw URLs.
        - **Key refs:** `scripts/install.sh:406,612,613`, `scripts/install.ps1:61,168`, `README.md:75,82,259,264,282,304,331,646`
        - **Watch out:** Some URLs are lowercase (`cyneric/addarr`). The test matches case-insensitively. Author credit lines (`https://github.com/Cyneric)`) have no `/addarr` and stay. `install.ps1`: URL edits only. README: only the listed lines (the same edits on lines 75, 259 and 264 also come in 1.6 for `sudo`).
    - **Scope:** URL replacements in three files
    - **Touches:** `scripts/install.sh`, `scripts/install.ps1`, `README.md`, `tests/test_install_scripts.py`
    - **Action items:**
        - [RED] Write `test_no_upstream_repo_urls`: no line in install.sh, install.ps1 or README.md matches `cyneric/addarr` (ignore case)
        - [GREEN] Replace each URL with `Krypt0nBull3t/Addarr`
    - **Success:** The test fails before and passes after

- [ ] **1.3** F172: Python 3.10 minimum
    - **Context:**
        - **Why:** install.sh accepts Python 3.8, but the bot needs 3.10 (`tuple[bool, str]`, deps).
        - **Architecture:** Change the constant. The dot-stripping compare (3.10 becomes 310) already works for 3.10 and up.
        - **Key refs:** `scripts/install.sh:47,178,496,509`, `README.md:204`
        - **Watch out:** Update both "Python 3.8+" messages and the README requirement (3.9 to 3.10).
    - **Scope:** One constant, two messages, one README line
    - **Touches:** `scripts/install.sh`, `README.md`, `tests/test_install_scripts.py`
    - **Action items:**
        - [RED] Write `test_install_requires_python_310`: install.sh has `MIN_PYTHON_VERSION="3.10"` and no `3.8+`; README has `Python 3.10 or higher` and no `Python 3.9 or higher`
        - [GREEN] Make the three edits
    - **Success:** The test fails before and passes after

- [ ] **1.4** F173: failed reinstall restores the backup
    - **Context:**
        - **Why:** The restore traps are the last lines of install.sh, and the script fails through `exit 1`, so the old install stays in `<dir>.backup.<date>`.
        - **Architecture:** `BACKUP_DIR=""` and `cleanup [status]` at the top, `trap 'cleanup $?' EXIT`, `trap 'exit 130' INT`, `trap 'exit 143' TERM`. `cleanup` restores only when the status is non-zero and `BACKUP_DIR` and `INSTALL_DIR` are non-empty and `BACKUP_DIR` is a directory.
        - **Key refs:** `scripts/install.sh:396-401` (backup `mv`), `:406-412` (clone), `:628-639` (old traps, delete them)
        - **Watch out:** Put the traps before `check_and_install_requirements`. The clone is `git clone ... | while read` with no pipefail: test `${PIPESTATUS[0]}` after the loop. Behavioral tests run the extracted `cleanup()` text under `bash -c` in `tmp_path`, never the whole script (it installs software).
    - **Scope:** Traps, `cleanup`, clone status, tests
    - **Touches:** `scripts/install.sh`, `tests/test_install_scripts.py`
    - **Action items:**
        - [RED] Write `test_restore_trap_set_before_backup_move`: the line of `trap 'cleanup $?' EXIT` comes before the first `mv "$INSTALL_DIR" "$BACKUP_DIR"`
        - [RED] Write helper `run_cleanup(status, with_backup, tmp_path)` and tests `test_cleanup_restores_backup_on_failure`, `test_cleanup_keeps_new_install_on_success`, `test_cleanup_without_backup_does_nothing`
        - [RED] Write `test_clone_failure_is_detected`: the clone block tests `PIPESTATUS[0]`
        - [GREEN] Move and rewrite the traps and `cleanup`, delete the old lines, fix the clone status
    - **Success:** All five tests fail before and pass after, `bash -n scripts/install.sh` passes

- [ ] **1.5** F174: SUDO prefix in install.sh
    - **Context:**
        - **Why:** `check_sudo` exits unless `EUID` is 0 and `install_system_packages` runs package managers without `sudo`. Once the README drops `sudo bash`, the script must ask for `sudo` itself.
        - **Architecture:** `check_sudo` sets a global `SUDO`: empty when root, `sudo` when it exists, otherwise an error and `exit 1`. Linux package-manager calls use `$SUDO`. macOS `brew` stays without it.
        - **Key refs:** `scripts/install.sh:53-59` (`check_sudo`), `:62-114` (`install_system_packages`), `:146` (call site)
        - **Watch out:** No guard that refuses to run as root (lead decision). The inline `sudo` calls later in the script stay.
    - **Scope:** `check_sudo` and `install_system_packages`
    - **Touches:** `scripts/install.sh`, `tests/test_install_scripts.py`
    - **Action items:**
        - [RED] Write `test_system_packages_use_sudo_prefix`: in `install_system_packages`, every line that runs `apt-get`, `dnf`, `yum` or `pacman` starts with `$SUDO `
        - [RED] Write `test_check_sudo_does_not_require_root`: the `check_sudo` text has no `sudo $0` hint and no `-ne 0` test on `EUID`
        - [GREEN] Rewrite `check_sudo` and prefix the calls
    - **Success:** Both tests fail before and pass after, `bash -n scripts/install.sh` passes

- [ ] **1.6** F174: README command installs for the current user, then verify
    - **Context:**
        - **Why:** `| sudo bash` sets `HOME=/root` on Ubuntu, so Addarr installs under `/root`.
        - **Architecture:** Replace `| sudo bash` with `| bash` on the README install commands.
        - **Key refs:** `README.md:75,259,264`
        - **Watch out:** Only those three lines (issue #215 edits other README lines). Task 1.5 must be done first, or the README command fails when a package is missing.
    - **Scope:** Three README lines, then the full preflight
    - **Touches:** `README.md`, `tests/test_install_scripts.py`
    - **Action items:**
        - [RED] Write `test_readme_has_no_sudo_pipe`: README contains no `| sudo bash`
        - [GREEN] Edit the three lines
        - [GREEN] Run the preflight (flake8, mypy, i18n, unit tests with the 100% coverage gate, integration, architecture) and fix any failure
    - **Success:** The test fails before and passes after, the full preflight passes

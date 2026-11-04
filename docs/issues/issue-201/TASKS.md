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

- [x] **1.2** F171: point URLs to `Krypt0nBull3t/Addarr`
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
    - **Completed:** 2026-11-04
    - **Learnings:**
        - The matching is on the substring `cyneric/addarr` (lowercased line), so the author credit lines (`github.com/Cyneric)`) need no exception.
        - One `sed` over the three files changed exactly the 16 listed lines and no others (checked with `git diff -U0`).
    - **Key Changes:**
        - `scripts/install.sh` (clone, wiki, issues), `scripts/install.ps1` (clone, wiki), `README.md` (install commands, clone and zip links) now use `Krypt0nBull3t/Addarr`.
        - Added `TestRepoUrls.test_no_upstream_repo_urls`.
    - **Notes:** The README `| sudo bash` text on lines 75, 259 and 264 is still there. Task 1.6 removes it.

- [x] **1.3** F172: Python 3.10 minimum
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
    - **Completed:** 2026-11-04
    - **Learnings:**
        - The dot-stripping compare still works with the new minimum: 3.10 becomes 310 (accepted), 3.9 becomes 39 (rejected). It would reject a future 4.0 (40), which is not a target today.
    - **Key Changes:**
        - `scripts/install.sh`: `MIN_PYTHON_VERSION="3.10"` and both "Python 3.10+ manually" messages.
        - `README.md:204`: `Python 3.10 or higher`.
        - Added `TestPythonVersion.test_install_requires_python_310`.
    - **Notes:** `bash -n scripts/install.sh` passes.

- [x] **1.4** F173: failed reinstall restores the backup
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
    - **Completed:** 2026-11-04
    - **Learnings:**
        - Before the fix, `test_restore_trap_set_before_backup_move`, `test_signals_exit_with_non_zero_status`, `test_cleanup_restores_backup_on_failure` and `test_clone_failure_is_detected` failed. The "keeps on success" and "no backup" tests passed on the old code, as guards against over-eager restore.
        - A scratch-dir simulation of the new trap, cleanup and clone block (clone from a missing repo) confirmed: the failure is detected, the script exits 1, and the old `config.yaml` returns.
    - **Key Changes:**
        - `scripts/install.sh`: `BACKUP_DIR=""`, `cleanup [status]` and the `EXIT`, `INT`, `TERM` traps now sit before `check_and_install_requirements`. The old traps at the end of the file are gone.
        - `scripts/install.sh`: the clone runs as a plain pipeline and tests `${PIPESTATUS[0]}`.
        - Added `TestBackupRestore` (six tests) with helpers `function_text()` and `run_cleanup()`.
    - **Notes:** `cleanup` defaults to status 0 when called without an argument, so it never restores by accident. The trap passes `$?`.

- [x] **1.5** F174: SUDO prefix in install.sh
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
    - **Completed:** 2026-11-04
    - **Learnings:**
        - `EUID` is read-only in bash, so a test cannot fake root. `test_check_sudo_sets_prefix_for_current_user` expects `[]` when the test runs as root and `[sudo]` otherwise, and returns early when a non-root host has no `sudo` (the function exits 1 there by design).
        - The prefix test counts at least five package-manager calls, so it fails if the regexp stops matching them.
    - **Key Changes:**
        - `scripts/install.sh`: `check_sudo` sets `SUDO` (empty for root, `sudo` when available, else an error and `exit 1`). `install_system_packages` prefixes `apt-get`, `dnf`, `yum` and `pacman` with `$SUDO`. macOS `brew` has no prefix.
        - Added `TestSudoHandling` (three tests).
    - **Notes:** The inline `sudo` calls later in the script are unchanged. No guard against running as root (lead decision).

- [x] **1.6** F174: README command installs for the current user, then verify
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
    - **Completed:** 2026-11-04
    - **Learnings:**
        - Preflight result: flake8 and mypy clean, translations valid, unit 2032 passed at 100% coverage, integration 95 passed, architecture 154 passed.
        - The change touches no `src/` file, so the coverage gate only confirms nothing regressed.
    - **Key Changes:**
        - `README.md:75,259,264`: `| sudo bash` became `| bash`.
        - Added `TestReadmeInstallCommand.test_readme_has_no_sudo_pipe`.
    - **Notes:** `install.sh` now calls `sudo` itself for system packages (task 1.5), which is why the README no longer needs it. `scripts/install.sh` was never run in full (it installs software). Its trap, cleanup and clone logic was checked with a scratch-dir simulation (task 1.4).

### Phase 2: Review feedback round 1 (1 task)

- [x] **2.1** [must-fix] Use `$SUDO` for every package install in `install.sh` (from Krypt0nBull3t, two threads on `scripts/install.sh:104`)
    - **Context:**
        - **Why:** `$SUDO` is set only when `check_sudo` runs (`install_system_packages` path). 18 other package-manager calls (pip at `install.sh:274-279`, git at `:376-385`, Python at `:497-507`, venv at `:547-563`) still call `sudo` directly. Root without `sudo` fails there with `sudo: command not found`, for example on a missing `python3-venv`.
        - **Architecture:** `set_sudo` sets `SUDO` once at the top (empty for root, `sudo` for others), with no exit. `check_sudo` keeps the missing-sudo error and runs only on the paths that install a package, so a non-root user without `sudo` fails only when a package must be installed. `$(id -u)` replaces `$EUID` so a test can stub root. Git clone, venv creation and `pip install -r requirements.txt` stay as the current user.
        - **Key refs:** `scripts/install.sh:68-80` (`check_sudo`), `:167` (existing call), `tests/test_install_scripts.py` (`TestSudoHandling`)
        - **Watch out:** Echo hint lines (`sudo apt install ...`) stay as they are. The arch venv arm installs nothing, so it must not call `check_sudo`. The other thread has the same text, so reply on both threads.
    - **Scope:** Prefix 18 calls, split `set_sudo` from `check_sudo`, call `check_sudo` before each install path, tests
    - **Touches:** `scripts/install.sh`, `tests/test_install_scripts.py`
    - **Action items:**
        - [RED] Write `test_every_package_install_uses_sudo_prefix`: every `apt-get`, `dnf`, `yum` or `pacman` install call in an executed line of install.sh carries `$SUDO `
        - [RED] Write `test_sudo_prefix_by_user` (parametrized with a stubbed `id` and `PATH` empty): root without sudo gives `[]` and exit 0, root with sudo gives `[]`, user with sudo gives `[sudo]`, user without sudo and nothing to install gives `[sudo]` and exit 0 (`set_sudo` only), user without sudo at `check_sudo` exits 1
        - [RED] Write `test_check_sudo_runs_before_each_install_path`: `check_sudo` comes before the first `$SUDO` after each install anchor, and three times in `install_python_venv`
        - [GREEN] Implement `set_sudo`, rewrite `check_sudo`, prefix the calls, add the `check_sudo` calls
    - **Success:** The tests fail before and pass after, `bash -n scripts/install.sh` passes, the preflight passes
    - **Completed:** 2026-11-04
    - **Learnings:**
        - Before the fix, 10 of the new test cases failed (19 install lines without the prefix, no `set_sudo`, no `check_sudo` before the install paths). All 22 tests in the file pass now.
        - Stubbing `id` as a bash function and running with an empty `PATH` fakes root and hides a real `sudo` without touching the host. `EUID` cannot be faked, so the script now reads `$(id -u)`.
        - `SUDO` was set only inside `check_sudo`, so any path that skipped `check_sudo` used an empty prefix or a bare `sudo`. A value that several paths read belongs where the script loads.
    - **Key Changes:**
        - `scripts/install.sh`: `set_sudo` runs at load. `check_sudo` exits only for a non-root user without `sudo`. 18 package-manager calls in the pip, git, Python and venv paths use `$SUDO`. `check_sudo` runs before each path that installs a package (the arch venv arm installs nothing and has no call).
        - `tests/test_install_scripts.py`: replaced `test_check_sudo_sets_prefix_for_current_user` with `test_every_package_install_uses_sudo_prefix`, `test_sudo_prefix_by_user` (5 cases), `test_check_sudo_runs_before_each_install_path` (3 cases) and `test_venv_install_checks_sudo_in_each_installing_arm`.
    - **Notes:** Git clone, venv creation and `pip install -r requirements.txt` still run as the current user, without `sudo`. The echo hint lines keep their plain `sudo`.

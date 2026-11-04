# Linux install and systemd unit are broken (#201) Implementation Plan

**Goal:** Fix F170 to F174: the service can write to `~/.addarr`, the installers fetch this repo, a failed reinstall restores the old install, install.sh refuses Python older than 3.10, and the README command installs for the current user.

**Architecture:** Static edits to `scripts/addarr.service`, `scripts/install.sh`, `scripts/install.ps1` and `README.md`. One new root-level test file, `tests/test_install_scripts.py`, in the style of `tests/test_dockerfile.py`. It parses the files, and it runs the bash `cleanup` function in a temp dir for the restore behavior.

**Tech Stack:** bash, systemd unit syntax, pytest, `subprocess`, `re`.

## Context

Root causes, found by reading the files (design decisions confirmed by the lead on 2026-11-04):

- **F170:** `scripts/addarr.service:29` has `ProtectHome=read-only` and no `ReadWritePaths`.
- **F171:** Repo URLs use `Cyneric/Addarr` and lowercase `cyneric/addarr`: `scripts/install.sh:406,612,613`, `scripts/install.ps1:61,168`, `README.md:75,82,259,264,282,304,331,646`. The author credit lines (`https://github.com/Cyneric)`, no `/Addarr`) stay.
- **F172:** `scripts/install.sh:47` has `MIN_PYTHON_VERSION="3.8"`. The text "Python 3.8+" is at `install.sh:496` and `:509`. `README.md:204` says 3.9. The dot-stripping compare (3.10 becomes 310) works for 3.10 and up, so it stays.
- **F173:** install.sh has no `set -e`, and every failure path is an explicit `exit 1`. The `ERR` trap never fires on `exit 1`. The `EXIT` trap calls `cleanup` without `error`, so it never restores. Both trap lines sit at the end of the file (`install.sh:628-639`). Also, `git clone ... | while read` (`install.sh:406`) has no pipefail, so a failed clone returns the status of the `while` loop and the script continues. That is the "no network" reproduction.
- **F174:** `check_sudo` (`install.sh:53`) exits 1 unless `EUID` is 0, and `install_system_packages` (`install.sh:62-114`) runs `apt-get`, `dnf`, `yum` and `pacman` with no `sudo`. Removing `sudo` from the README alone would break the install when a package such as `unzip` is missing.

## Global Constraints

- Branch `fix/201-linux-install-and-systemd-unit`, PR targets `development`.
- Python 3.10 is the minimum for the bot.
- README edits only on the lines named in the issue plus `README.md:204` (issue #215 edits other README lines).
- `scripts/install.ps1`: URL edits only (`:61`, `:168`). No flow change.
- No guard that refuses to run as root.
- `pytest`, `flake8` and `mypy src/` pass, with the 100% coverage gate (no `src/` change is expected).
- Every test, gate and `git push` runs through the suite lock.

## Review Focus

- A user without `unzip` runs the README command as a normal user. Expected: install.sh calls `sudo` for the package, not "Please run with: sudo".
- A user is root (runs it with `sudo`). Expected: `SUDO` is empty, the package install still works.
- A clean first install fails midway (no backup exists). Expected: `cleanup` does nothing and never runs `rm -rf` on an empty path.
- The reinstall fails after the backup `mv`. Expected: the new partial directory is removed and the backup returns to `$INSTALL_DIR` with its `config.yaml`.
- The reinstall succeeds. Expected: the backup stays in place and `cleanup` does nothing.

## Tasks

### Task 1: F170, service can write to `~/.addarr`

**Files:**
- Create: `tests/test_install_scripts.py` (constants `ROOT`, `SERVICE`, `INSTALL_SH`, `INSTALL_PS1`, `README`, and a helper `read(path) -> str`)
- Modify: `scripts/addarr.service:29`

- [ ] Write `test_service_allows_writes_to_addarr_dir`: when `ProtectHome=read-only` is in the service file, the line `ReadWritePaths=%h/.addarr` is also there. Run it, expect FAIL.
- [ ] Add `ReadWritePaths=%h/.addarr` after `ProtectHome=read-only`. Run it, expect PASS.
- [ ] Commit.

### Task 2: F171, point URLs to this repo

**Files:**
- Modify: `scripts/install.sh:406,612,613`, `scripts/install.ps1:61,168`, `README.md:75,82,259,264,282,304,331,646`
- Test: `tests/test_install_scripts.py`

- [ ] Write `test_no_upstream_repo_urls`: for each of `install.sh`, `install.ps1` and `README.md`, no line matches `re.search(r"cyneric/addarr", line, re.I)`. The credit lines do not match because they have no `/addarr`. Run it, expect FAIL.
- [ ] Replace each URL with `Krypt0nBull3t/Addarr` (raw URLs: `https://raw.githubusercontent.com/Krypt0nBull3t/Addarr/main/scripts/install.sh`, keep the existing `main` branch in the path). Run it, expect PASS.
- [ ] Commit.

### Task 3: F172, Python 3.10 minimum

**Files:**
- Modify: `scripts/install.sh:47,496,509`, `README.md:204`
- Test: `tests/test_install_scripts.py`

- [ ] Write `test_install_requires_python_310`: `MIN_PYTHON_VERSION="3.10"` is in install.sh, install.sh has no `3.8+`, and README has `Python 3.10 or higher` and no `Python 3.9 or higher`. Run it, expect FAIL.
- [ ] Set `MIN_PYTHON_VERSION="3.10"`, change both "3.8+" texts to "3.10+", change `README.md:204` to `Python 3.10 or higher`. Run it, expect PASS.
- [ ] Commit.

### Task 4: F173, failed reinstall restores the backup

**Files:**
- Modify: `scripts/install.sh` (traps and `cleanup` move to the top, before `check_and_install_requirements`; delete `:628-639`; fix the clone status at `:406`)
- Test: `tests/test_install_scripts.py`

**Interfaces:**
- Produces: bash function `cleanup [status]` in install.sh. It reads `$?` when no argument is given, restores only when the status is non-zero and `$BACKUP_DIR` is a non-empty existing directory and `$INSTALL_DIR` is non-empty: `rm -rf "$INSTALL_DIR"; mv "$BACKUP_DIR" "$INSTALL_DIR"`. `BACKUP_DIR=""` is set at the top. Traps: `trap 'cleanup $?' EXIT`, `trap 'exit 130' INT`, `trap 'exit 143' TERM`.

- [ ] Write `test_restore_trap_set_before_backup_move`: the line index of `trap 'cleanup $?' EXIT` is lower than the index of the first line containing `mv "$INSTALL_DIR" "$BACKUP_DIR"`. Run it, expect FAIL.
- [ ] Write a helper `run_cleanup(status: int, with_backup: bool, tmp_path) -> Path`. It extracts the `cleanup()` function text from install.sh with a regex, runs it under `bash -c` with `INSTALL_DIR`, `BACKUP_DIR`, `YELLOW` and `NC` set, and returns the install dir. Write three tests: `test_cleanup_restores_backup_on_failure` (status 1: the new partial dir is gone, the old `config.yaml` is back), `test_cleanup_keeps_new_install_on_success` (status 0: the new install stays, the backup stays), `test_cleanup_without_backup_does_nothing` (status 1, `BACKUP_DIR` empty: the install dir stays untouched). Run them, expect FAIL.
- [ ] Write `test_clone_failure_is_detected`: the clone block checks `PIPESTATUS[0]` (the status of `git clone`, not of the `while` loop). Run it, expect FAIL.
- [ ] Implement the traps and `cleanup` at the top as described in Interfaces. In the clone block, keep the progress loop and test `${PIPESTATUS[0]}` after it. Run all Task 4 tests, expect PASS.
- [ ] Commit.

### Task 5: F174, README command installs for the current user

**Files:**
- Modify: `scripts/install.sh:53-59,62-114`, `README.md:75,259,264`
- Test: `tests/test_install_scripts.py`

**Interfaces:**
- Produces: global `SUDO` set by `check_sudo` (empty when `EUID` is 0, `sudo` when `sudo` exists, otherwise print an error and `exit 1`). `install_system_packages` prefixes the Linux package-manager calls with `$SUDO` (macOS `brew` stays without it).

- [ ] Write `test_readme_has_no_sudo_pipe`: README contains no `| sudo bash`. Run it, expect FAIL.
- [ ] Write `test_system_packages_use_sudo_prefix`: in the `install_system_packages` function text, every line that runs `apt-get`, `dnf`, `yum` or `pacman` starts with `$SUDO `. Run it, expect FAIL.
- [ ] Write `test_check_sudo_does_not_require_root`: the `check_sudo` function text has no `sudo $0` hint and no `-ne 0` test on `EUID`. Run it, expect FAIL.
- [ ] Rewrite `check_sudo` to set `SUDO`, prefix the package-manager calls, and replace `| sudo bash` with `| bash` on the three README lines. Run the Task 5 tests, expect PASS.
- [ ] Commit.

### Task 6: Full verification

- [ ] Run the preflight (`addarr-workflow` preflight, through the suite lock): flake8, mypy, i18n validation, unit tests with the 100% coverage gate, integration tests, architecture tests. Fix any failure.
- [ ] Run `bash -n scripts/install.sh` for a syntax check. Do not run the script itself: it installs software.
- [ ] Mark every task complete in TASKS.md with the completion metadata.

## Notes for the PR body

- F173 and F174 differ from the literal Fix text in the issue. F173 uses one `EXIT` trap that restores on any non-zero status, because the script has no `set -e` and fails through `exit 1`, so the issue's `trap 'cleanup error' ERR` would never fire. F174 also changes install.sh (`SUDO` prefix), because `check_sudo` exits unless the user is root, so a README without `sudo` would fail when a package is missing.
- Also fixed: the clone pipeline status (F173 no-network reproduction) and the "3.8+" and README "3.9" texts (F172).

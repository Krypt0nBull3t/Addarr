# Issue 274: Hash the auth list password with salted PBKDF2 Implementation Plan

**Goal:** Store `authenticated_users_hash` as a salted PBKDF2-HMAC-SHA256 value, so CodeQL `py/weak-sensitive-data-hashing` no longer fires on `src/bot/handlers/auth.py`.

**Architecture:** Two small module-level helpers in `src/bot/handlers/auth.py`: `_password_hash()` builds the stored string, `_hash_matches()` checks a password against a stored string. `AuthHandler` derives the stored value at most once per process and reuses it on every save, so `/auth` never pays for a hash on the event loop.

**Tech Stack:** Python stdlib only (`hashlib.pbkdf2_hmac`, `secrets.token_bytes`, `hmac.compare_digest`). No new dependency.

**Issue:** https://github.com/Krypt0nBull3t/Addarr/issues/274 (no design.md: one layer, approach fixed by the developer).

## Context and root cause

`_password_hash()` (`src/bot/handlers/auth.py:118`) returns `hashlib.sha256(password.encode()).hexdigest()`: fast and unsalted. CodeQL alert #5 flags it. Two callers:

- `AuthHandler.__init__`: compares the stored value with `_password_hash(self.password)`; a mismatch clears `authenticated_users`.
- `AuthHandler._save_authenticated_users`: writes `_password_hash(self.password)` on every save (each successful `/auth`).

No other file in `src/` or `config_example.yaml` reads or writes the value. A fixed hash cannot be compared by recomputing once the salt is random, so the startup check must parse the stored string.

## Global constraints

- Stored format: `pbkdf2_sha256$<iterations>$<salt hex>$<hash hex>`; salt is 16 bytes from `secrets.token_bytes(16)`.
- Iterations: one module constant `PBKDF2_ITERATIONS = 600000` in `src/bot/handlers/auth.py`.
- A missing value, an old plain-SHA256 value, or any malformed value is a mismatch: the list is cleared, users send `/auth` once (same as #210). `_hash_matches` never raises.
- A stored iteration count outside `1..10*PBKDF2_ITERATIONS` is malformed (mismatch). A damaged or edited `config.yaml` with a huge count must not block startup.
- The startup check recomputes with the stored salt and stored iterations, and compares with `hmac.compare_digest`.
- Out of scope: the setup wizard password display (CodeQL alerts #3 and #4, dismissed by design), any other auth change.
- Config access follows `config.get(...)` (no bracket access in `src/`). Optional params use `Optional[...]`.

## Review focus

- Stored value with a different iteration count than the constant still verifies (the count is read from the stored string).
- Stored value of the right shape but with a non-hex salt, non-int iterations, zero iterations, an iteration count above `10*PBKDF2_ITERATIONS`, or a missing part: mismatch, no exception, no long derivation.
- A 64-char hex SHA256 value of the correct password: mismatch (list cleared).
- `None` stored value and empty list: nothing is saved (existing behavior kept).
- Two `_password_hash()` calls for one password differ (random salt).
- A successful `/auth` does not recompute the hash (the cached value is reused).

## File structure

- Modify `src/bot/handlers/auth.py`: constant, `_password_hash`, `_hash_matches`, `AuthHandler.__init__`, `_save_authenticated_users`.
- Modify `tests/test_handlers/test_auth_handler.py`: replace the `_sha256` helper and the #210 tests.
- Modify `tests/conftest.py`: MockConfig hash value (line 95) and an autouse fixture that patches `PBKDF2_ITERATIONS` to a small value.
- Modify `CLAUDE.md` (line 151): the sha256 sentence.

> TASKS.md merges plan tasks 1 and 2 into task 1.1 (one commit): the new hash breaks the old startup comparison, so a commit between them would leave the suite red. Plan task 3 is TASKS.md task 1.2.

## Task 1: Hash helpers

**Files:**
- Modify: `src/bot/handlers/auth.py` (replace `_password_hash`, add constant and `_hash_matches`)
- Test: `tests/test_handlers/test_auth_handler.py`
- Modify: `tests/conftest.py` (autouse iteration patch)

**Interfaces:**
- Produces: `PBKDF2_ITERATIONS: int`, `_password_hash(password: str) -> str`, `_hash_matches(password: str, stored: Optional[str]) -> bool`.

- [ ] **Step 1: Add the autouse fixture** `fast_pbkdf2` in `tests/conftest.py`: `monkeypatch.setattr("src.bot.handlers.auth.PBKDF2_ITERATIONS", 1000)`. It must not break tests that run before the constant exists (red phase fails on the missing attribute, which is the expected red).
- [ ] **Step 2: Write failing tests** in `tests/test_handlers/test_auth_handler.py`:
  - `test_real_iteration_constant_is_600000`: read `src/bot/handlers/auth.py` with `ast`, find the `PBKDF2_ITERATIONS` assignment, assert it equals `600000` (the fixture patches the live value, so the test reads the source).
  - `test_password_hash_format`: value splits on `$` into 4 parts; part 0 is `pbkdf2_sha256`; part 1 is `str(PBKDF2_ITERATIONS)`; salt hex has 32 chars; hash hex has 64 chars.
  - `test_password_hash_uses_random_salt`: two calls for `"test-pass"` differ.
  - `test_hash_matches_right_password` and `test_hash_matches_wrong_password`.
  - `test_hash_matches_uses_stored_iterations`: build a value by hand with `hashlib.pbkdf2_hmac("sha256", b"pw", salt, 7)`; `_hash_matches("pw", value)` is True while the constant is 1000.
  - `test_hash_matches_rejects_legacy_sha256`: `hashlib.sha256(b"test-pass").hexdigest()` returns False.
  - `test_hash_matches_rejects_iteration_count_above_cap`: a value built by hand with `10 * PBKDF2_ITERATIONS + 1` iterations (use a zero-filled 32-byte hash, no derivation) returns False, and the derivation is never run (patch `hashlib.pbkdf2_hmac` in the module and assert it is not called). A value with exactly `10 * PBKDF2_ITERATIONS` iterations built with the real derivation returns True.
  - `test_hash_matches_rejects_malformed` (parametrized): `None`, `""`, `"pbkdf2_sha256$x$00$00"`, `"pbkdf2_sha256$0$00$00"`, `"pbkdf2_sha256$1000$zz$00"`, `"pbkdf2_sha256$1000$00"`, `"other$1000$00$00"` all return False.
- [ ] **Step 3: Run** `<lock> .venv/bin/python -m pytest tests/test_handlers/test_auth_handler.py -k "hash or iteration" -v`. Expected: FAIL (names missing).
- [ ] **Step 4: Implement** in `src/bot/handlers/auth.py` (add `import secrets`):
  - `PBKDF2_ITERATIONS = 600000` with a one-line comment: OWASP 2023 figure for PBKDF2-HMAC-SHA256.
  - `_password_hash(password)`: new `secrets.token_bytes(16)` salt, `hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITERATIONS)`, return the four-part string.
  - `_hash_matches(password, stored)`: split on `$` (exactly 4 parts, first `pbkdf2_sha256`), `int` iterations (reject outside `1 <= n <= 10 * PBKDF2_ITERATIONS` before any derivation), `bytes.fromhex` salt and hash; recompute with the stored values; `hmac.compare_digest`. Catch `ValueError` and `AttributeError` (a non-str stored value) and return False.
- [ ] **Step 5: Run** the same command. Expected: PASS.
- [ ] **Step 6: Commit** `fix: hash auth list password with salted PBKDF2 (task 1, #274)`. Stage only the three files and TASKS.md.

## Task 2: Wire the handler, cache the hash, update the #210 tests

**Files:**
- Modify: `src/bot/handlers/auth.py` (`AuthHandler.__init__`, `_save_authenticated_users`)
- Modify: `tests/conftest.py` (line 94-95 MockConfig hash)
- Test: `tests/test_handlers/test_auth_handler.py` (the #210 section, lines ~900-1013)

**Interfaces:**
- Consumes: `_password_hash`, `_hash_matches` from task 1.
- Produces: `AuthHandler._stored_hash: str` (instance attribute, set in `__init__`).

- [ ] **Step 1: Update the MockConfig value** in `tests/conftest.py`: replace the sha256 line with a value built once at import by `hashlib.pbkdf2_hmac("sha256", b"test-pass", salt, 1000)` in the four-part form (a fixed salt, `bytes(16)`, keeps it deterministic; the check reads iterations from the string). Fix the comment. Remove `import hashlib` only if unused.
- [ ] **Step 2: Rewrite the #210 tests** (replace the `_sha256` helper with a `_stored(password)` helper that calls `_password_hash`). Keep the existing five `__init__` cases and `test_save_writes_password_hash` with the new value shape, and add:
  - `test_init_clears_users_when_stored_hash_is_legacy_sha256`: stored plain SHA256 of `"test-pass"`, list `[12345]`: list cleared, saved hash starts with `pbkdf2_sha256$`.
  - `test_init_clears_users_when_stored_hash_is_malformed`.
  - `test_init_reuses_matching_stored_hash`: after a match, patch `src.bot.handlers.auth._password_hash` with a mock; calling `handler._save_authenticated_users()` stores the original stored value and the mock is not called.
  - `test_save_reuses_hash_between_logins`: two saves in one handler write the same value and call `_password_hash` once in total (wrap with `patch(..., wraps=...)`).
  - `test_save_writes_pbkdf2_value`: `_hash_matches("test-pass", saved["authenticated_users_hash"])` is True.
  Existing assertions `== _sha256("test-pass")` become `_hash_matches("test-pass", ...)`.
- [ ] **Step 3: Run** `<lock> .venv/bin/python -m pytest tests/test_handlers/test_auth_handler.py -v`. Expected: the new and changed tests FAIL (the handler still uses the old compare).
- [ ] **Step 4: Implement** in `AuthHandler.__init__`: read `stored = config.get("authenticated_users_hash")`. If `_hash_matches(self.password, stored)`, set `self._stored_hash = stored`. Otherwise set `self._stored_hash = _password_hash(self.password)` and, when the user list is non-empty, keep the existing revoke path (warn, clear, save). `_save_authenticated_users` writes `self._stored_hash` instead of calling `_password_hash`. Keep the existing comment about a list saved without a hash, and extend it to say a legacy SHA256 value counts too.
- [ ] **Step 5: Run** the file again, then `<lock> .venv/bin/python scripts/test_runner.py handlers --coverage` and `<lock> .venv/bin/python -m pytest tests/integration --tb=short -v`. Expected: PASS, `auth.py` fully covered.
- [ ] **Step 6: Commit** `fix: reuse the derived auth hash across saves (task 2, #274)`.

## Task 3: Docs

**Files:**
- Modify: `CLAUDE.md` (line 151)

- [ ] **Step 1: Edit** the sentence: `authenticated_users_hash` is a salted PBKDF2-HMAC-SHA256 value (`pbkdf2_sha256$<iterations>$<salt>$<hash>`) of `telegram.password`; `AuthHandler.__init__` clears the list when it does not match, is missing, or is an old plain-SHA256 value.
- [ ] **Step 2: Run** `<lock> .venv/bin/python -m pytest tests/test_architecture --tb=short -v`. Expected: PASS (docs drift and skill checks).
- [ ] **Step 3: Check** `.claude/skills/` for the word `sha256`: only `hmac.compare_digest` mentions exist, so no skill edit is expected.
- [ ] **Step 4: Commit** `docs: describe the PBKDF2 auth list hash (task 3, #274)`.

## Verification (before the PR)

- `/addarr pr` preflight: flake8, mypy, i18n validation, unit tests with the 100% coverage gate, integration tests, architecture tests.
- Local check that CodeQL is satisfied cannot run here; the PR's CodeQL check must show no `py/weak-sensitive-data-hashing` alert.
- PR body states: development-build users re-authenticate once with `/auth` (nothing with the SHA256 value was released). Link `Closes #274`.

## Known limits

- The cap is a multiple of the current constant. If the constant is lowered later, older stored values above the new cap count as a mismatch: users re-auth once.
- Within one process the saved value is reused, so two saves in one run write the same string. Two separate derivations (a new process after a password change, or the helper called twice) differ.

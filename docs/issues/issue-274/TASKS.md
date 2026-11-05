# Issue 274: Hash the auth list password with salted PBKDF2

Plan: [plan.md](plan.md). Issue: https://github.com/Krypt0nBull3t/Addarr/issues/274
Branch: `fix/274-hash-auth-password-with-pbkdf2`. Python: `.venv/bin/python` in this worktree.
Every test and gate runs through `~/.local/share/agent-suite/with-suite-lock.sh addarr/$AO_SESSION_ID --`.

### Phase 1: Salted PBKDF2 auth hash (2 tasks)

**Goal:** `authenticated_users_hash` is a salted PBKDF2-HMAC-SHA256 value that CodeQL accepts, checked at startup against the stored salt and iterations.

**Phase Context:**

- Why NOT recompute and compare a fixed digest: a random salt makes the value differ per derivation, so the startup check must parse the stored string.
- Why cache the derived value in `AuthHandler`: one hash takes about 0.3 s (seconds on a Raspberry Pi) and `check_password` runs on the event loop. A matching stored value is reused; otherwise one derivation happens in `__init__`.
- Out of scope: the setup wizard password display (CodeQL alerts #3 and #4, dismissed by design), any other auth change.

- [x] **1.1** Salted PBKDF2 helpers and `AuthHandler` wiring
    - **Context:**
        - **Why:** `_password_hash()` (`src/bot/handlers/auth.py:118`) is plain unsalted sha256; CodeQL `py/weak-sensitive-data-hashing` flags it. The helpers and the handler change in one task: the new value breaks the old startup comparison, so a commit between them would leave the suite red.
        - **Architecture:** Module-level helpers in `src/bot/handlers/auth.py`, stdlib only. Stored format `pbkdf2_sha256$<iterations>$<salt hex>$<hash hex>`, salt from `secrets.token_bytes(16)`, compare with `hmac.compare_digest` (already imported). `AuthHandler.__init__` reads `stored = config.get("authenticated_users_hash")`. A match sets `self._stored_hash = stored`. Otherwise it sets `self._stored_hash = _password_hash(self.password)` and, when the user list is non-empty, keeps the existing revoke path (warn, clear, save). `_save_authenticated_users` writes `self._stored_hash`.
        - **Key refs:** `src/bot/handlers/auth.py:10-12` (imports), `:118-120` (old helper), `:129-147` (`__init__`), `:154-168` (`_save_authenticated_users`); `tests/conftest.py:94-95` (MockConfig hash); `tests/test_handlers/test_auth_handler.py:898-1013` (the #210 section).
        - **Watch out:** `_hash_matches` never raises: catch `ValueError` and `AttributeError`. Reject an iteration count outside `1 <= n <= 10 * PBKDF2_ITERATIONS` before any derivation (a damaged config must not block startup). The autouse fixture patches the live constant to 1000, so the "real value is 600000" test reads `auth.py` with `ast` (same idea as `tests/test_version.py`). Add the autouse fixture only after the constant exists: `monkeypatch.setattr` on a missing attribute fails every test in the suite. The MockConfig hash must match `"test-pass"` or every handler fixture clears the user list: build it at import with `hashlib.pbkdf2_hmac("sha256", b"test-pass", bytes(16), 1000)` in the four-part form (the check reads iterations from the string). `tests/integration/test_auth_flow.py` patches `_save_authenticated_users`, so it is unaffected. Keep the existing comment on the list saved without a hash and extend it to cover a legacy SHA256 value.
    - **Scope:** Constant, two helpers, `__init__`, `_save_authenticated_users`, MockConfig value, autouse iteration patch, helper tests, the #210 test section.
    - **Touches:** `src/bot/handlers/auth.py` (add `import secrets`), `tests/test_handlers/test_auth_handler.py`, `tests/conftest.py`
    - **Action items:**
        - [RED] Write `test_real_iteration_constant_is_600000` (`ast` read of `auth.py`).
        - [RED] Write `test_password_hash_format` (4 `$` parts, `pbkdf2_sha256`, iterations equal the constant, 32 hex salt chars, 64 hex hash chars) and `test_password_hash_uses_random_salt` (two calls differ).
        - [RED] Write `test_hash_matches_right_password`, `test_hash_matches_wrong_password`, `test_hash_matches_uses_stored_iterations` (hand-built value with 7 iterations matches while the constant is 1000), `test_hash_matches_rejects_legacy_sha256`.
        - [RED] Write `test_hash_matches_rejects_iteration_count_above_cap` (`10 * PBKDF2_ITERATIONS + 1` returns False and `hashlib.pbkdf2_hmac` is not called; exactly `10 * PBKDF2_ITERATIONS` with the real derivation returns True).
        - [RED] Write parametrized `test_hash_matches_rejects_malformed` for `None`, `""`, `"pbkdf2_sha256$x$00$00"`, `"pbkdf2_sha256$0$00$00"`, `"pbkdf2_sha256$1000$zz$00"`, `"pbkdf2_sha256$1000$00"`, `"other$1000$00$00"`.
        - [RED] Replace the `_sha256` helper in the #210 section with a `_stored(password)` helper that calls `_password_hash`; change the five `__init__` tests and `test_save_writes_password_hash` to assert with `_hash_matches("test-pass", saved["authenticated_users_hash"])`.
        - [RED] Write `test_init_clears_users_when_stored_hash_is_legacy_sha256` (plain SHA256 of `"test-pass"`, list `[12345]`: list cleared, saved hash starts with `pbkdf2_sha256$`) and `test_init_clears_users_when_stored_hash_is_malformed`.
        - [RED] Write `test_init_reuses_matching_stored_hash` (after a match, patched `_password_hash` is not called and a save stores the original value) and `test_save_reuses_hash_between_logins` (two saves write the same value; `_password_hash` runs at most once in total).
        - [GREEN] Add `PBKDF2_ITERATIONS = 600000` (comment: OWASP 2023 figure for PBKDF2-HMAC-SHA256), replace `_password_hash`, add `_hash_matches`.
        - [GREEN] Add the autouse `fast_pbkdf2` fixture to `tests/conftest.py` and update the MockConfig hash and its comment (drop `import hashlib` only if unused).
        - [GREEN] Implement the `__init__` and `_save_authenticated_users` changes.
    - **Success:** `pytest tests/test_handlers/test_auth_handler.py` passes; `scripts/test_runner.py handlers --coverage` shows `auth.py` fully covered; `pytest tests/integration` passes; flake8 and mypy clean.
    - **Completed:** 2026-11-05
    - **Learnings:**
        - The autouse `fast_pbkdf2` fixture patches the live constant, so only an `ast` read of `auth.py` can pin the real 600000.
        - `_hash_matches` reads the count from the stored string, so the MockConfig value (1000 iterations, fixed salt) matches whatever the fixture sets.
        - Tasks 1.1 and 1.2 of the plan were merged: the new hash breaks the old startup comparison, so one commit keeps the suite green.
    - **Key Changes:**
        - `src/bot/handlers/auth.py`: `PBKDF2_ITERATIONS`, salted `_password_hash`, new `_hash_matches` (cap 1..10x), `AuthHandler._stored_hash` reused by `_save_authenticated_users`.
        - `tests/conftest.py`: `fast_pbkdf2` autouse fixture, PBKDF2 MockConfig hash.
        - `tests/test_handlers/test_auth_handler.py`: #210 tests use `_stored`/`_matches`; new #274 section (format, random salt, cap, malformed, legacy SHA256, reuse).
    - **Notes:** `auth.py` is at 100% in the handlers run; integration (782) and architecture (263) tests pass. No new integration test: the hash is not a user-facing flow, and `tests/integration/test_auth_flow.py` still passes.

- [x] **1.2** Update CLAUDE.md
    - **Context:**
        - **Why:** CLAUDE.md line 151 says `authenticated_users_hash` is a sha256; docs drift tests and readers rely on it.
        - **Architecture:** Docs only.
        - **Key refs:** `CLAUDE.md:151` (Authentication decorator bullet), `.claude/skills/` (grep for `sha256`; only `hmac.compare_digest` mentions are expected).
        - **Watch out:** `tests/test_architecture/test_repo_docs.py` checks the repo names this file mentions; keep names real (`AuthHandler.__init__`, `telegram.password`).
    - **Scope:** One sentence in CLAUDE.md.
    - **Touches:** `CLAUDE.md`
    - **Action items:**
        - [GREEN] Reword: `authenticated_users_hash` is a salted PBKDF2-HMAC-SHA256 value (`pbkdf2_sha256$<iterations>$<salt>$<hash>`) of `telegram.password`; `AuthHandler.__init__` clears the list when it does not match, is missing, or is an old plain-SHA256 value.
        - [GREEN] Check `.claude/skills/` for a stale `sha256` mention of this hash.
    - **Success:** `pytest tests/test_architecture --tb=short -v` passes.
    - **Completed:** 2026-11-05
    - **Learnings:** Only `CLAUDE.md:151` named the old sha256 hash; no skill or ADR mentions it.
    - **Key Changes:** `CLAUDE.md` Authentication decorator bullet describes the PBKDF2 format, the mismatch cases and the cached value.
    - **Notes:** Architecture tests (158) pass.

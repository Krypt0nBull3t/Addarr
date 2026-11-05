# Issue 215: Fix README and CLAUDE.md instructions that send users the wrong way

**Issue:** https://github.com/Krypt0nBull3t/Addarr/issues/215 (F280, F281)
**Branch:** `fix/215-fix-readme-claude-md-instructions`
**Spec:** the issue body. No design.md: the change is docs only.

## Context

Root cause: README.md and CLAUDE.md drifted from the code (audit 2026-10-28). No code, config, translation or Docker change.

Checked against the code on `development` at cf51f57:

- `src/bot/handlers/auth.py:122` reads `config.get("telegram", {}).get("password")`. `config_example.yaml:9` has `telegram.password`. The README puts it under `security:`.
- `src/utils/helpers.py:82` reads `security.enableAdmin`, so that key stays under `security:`.
- `README.md:204` already says Python 3.10 (merged in #201). Nothing to do.
- `setup.py`, `requirements-dev.txt`, `.pre-commit-config.yaml` and `kubernetes/` do not exist. No code reads a `monitoring:` key.
- `src/utils/prerun.py` exists; `src/utils/__init__.py` exports the instance `prerun_checker`.

## Decisions (confirmed by the orchestrator, 2026-11-05)

- Keep the Kubernetes section and its TOC entry in README.md. #218 (F190) deletes `helm/` and that README section. The PR body says so.
- Keep the Docker Hub publish lines in CLAUDE.md (F150 makes them true).
- CLAUDE.md `.txt` mount list: #218 edits the same text. Whichever PR merges second merges `origin/development` and keeps both edits.

## Acceptance check (the "red" test for a docs change)

```bash
grep -nE "setup.py|requirements-dev|pre-commit|monitoring:|Python 3.9" README.md
grep -nE "prerun_checker|admin.txt|allowlist.txt|chatid.txt" CLAUDE.md
```

Both must print nothing. `kubernetes/` stays in README.md by the decision above, so it is left out of the first grep. Run both before and after the edits.

## Task 1: README.md (F280)

Files: `README.md`. Line numbers are as of cf51f57.

1. `:478-482` Move `password: "your-password"` into the `telegram:` block, below `token:`. Keep `security:` with `enableAdmin: false`.
2. `:512-516` Change `python setup.py --reset` to `python run.py --reset`. Reword "the setup script" to "`run.py`".
3. `:543-549` Delete the `### Configuration` subsection that holds the `monitoring:` block.
4. `:741-747` Delete the `requirements-dev.txt` line from step 2 (retitle it "Install dependencies") and delete the pre-commit step. Renumber "Run tests" to step 3.
5. Leave the Kubernetes section, its TOC entry and the Python 3.10 line as they are.

Check: the acceptance greps above. Manual check for F280: the README `telegram:` block has `token` and `password`, which is the key `/auth` reads.

## Task 2: CLAUDE.md (F281)

Files: `CLAUDE.md`.

1. `:166` Rewrite the pre-run check clause so it cites `src/utils/prerun.py` (`PreRunChecker`) and does not contain the string `prerun_checker`.
2. `:240` Remove `chatid.txt`, `admin.txt` and `allowlist.txt` from "Persistent files to mount". Keep `config.yaml`, `logs/` and `backup/`.
3. Keep both Docker Hub lines (`:189`, `:240`).

Check: the second acceptance grep prints nothing; `grep -n "Docker Hub" CLAUDE.md` still finds both lines.

## Verification

Run through the suite lock: `pytest tests/test_architecture` (docs drift and skill tests read CLAUDE.md), then the preflight (flake8, mypy, i18n, unit with the 100% gate, integration, architecture).

## Risks

- `test_repo_docs.py` checks paths named in CLAUDE.md; Task 2 only removes or keeps real paths.
- Merge conflicts with #218 (CLAUDE.md `:240`, README Kubernetes section) and with #201/#213 (other README lines).

---
title: "Fix README and CLAUDE.md instructions that send users the wrong way"
labels: [documentation, agent-ready, priority:high]
slice: 20
findings: [F280, F281]
---

## Problem

README.md:

- Puts `password` under `security:`. The code reads `telegram.password`, so `/auth` fails for a user who copies this block.
- Says Python 3.9 or higher. The bot needs 3.10.
- Says `python setup.py --reset`. There is no `setup.py`; the command is `python run.py --reset`.
- Documents a `monitoring:` config block that no code reads.
- Points to `kubernetes/*.yaml`, `requirements-dev.txt` and pre-commit hooks. None of them exist.

CLAUDE.md:

- Cites `src/utils/prerun_checker.py`. The file is `src/utils/prerun.py`.
- Says Docker images are published to Docker Hub. The publish workflow fails every run (F150). Slice 19 makes the claim true, so it stays.
- Lists `admin.txt`, `allowlist.txt` and `chatid.txt` as files to mount. No live code reads them (F191).

## Expected behavior

Every command, path and config key in README.md and CLAUDE.md matches the code.

## Fix

- [ ] **F280** Correct or delete each wrong README line: move `password` to `telegram:`; Python 3.10; `python run.py --reset`; delete the `monitoring:` block, the Kubernetes steps, `requirements-dev.txt` and pre-commit (`README.md:204`, `:480-483`, `:516`, `:546-548`, `:664-669`, `:742-747`)
- [ ] **F281** Correct 2 CLAUDE.md lines: cite `prerun.py`; drop the `.txt` mounts (`CLAUDE.md:142`, `:209`). Keep the Docker Hub publish claim (`:162`, `:209`); F150 makes it true

## Acceptance criteria

Manual checks:

- [ ] F280: a config written from the README block lets `/auth` succeed with the password.
- [ ] F280: `grep -nE "setup.py|requirements-dev|pre-commit|kubernetes/|monitoring:|Python 3.9" README.md` finds nothing.
- [ ] F281: `grep -nE "prerun_checker|admin.txt|allowlist.txt|chatid.txt" CLAUDE.md` finds nothing. The Docker Hub publish lines are still there.
- [ ] `pytest`, `flake8` and `mypy src/` pass.

## Notes

- Source: audit 2026-10-28, docs/issues/audit-2026-10-28/FINDINGS.md (F-ids F280, F281).
- Priority: max P 25, sum P 35 (high).
- Dependencies: none in the order of work. The F281 Docker Hub claim stays because F150 (slice 19) makes it true. The `.txt` mount line follows F191 (slice 23). Python 3.10 matches F172 (slice 6).
- Decided 2026-10-28: F281 keep the Docker Hub publish claim (true after F150); fix the other two lines.
- Other slices also edit README.md: slice 6 (F171, F174: `:75`, `:259`, `:264`, `:304`, `:646`) and slice 18 (F183: Windows Service section).

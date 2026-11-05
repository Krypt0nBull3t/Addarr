---
title: "Pin dependencies and fix the Docker image publish pipeline"
labels: [ops, dependencies, github_actions, security, priority:high]
slice: 19
findings: [F151, F150, F152, F153]
---

## Bug

- `requirements.txt` uses `>=` pins and the Dockerfile installs with `--upgrade`. Every build takes the newest python-telegram-bot. `disable_web_page_preview` in `help.py` is deprecated.
- `docker-hub-push.yml` failed 16 of 16 runs because the Docker Hub secrets are missing. CLAUDE.md says images are published. Only `:latest` is pushed, never a version tag.
- `.dockerignore` lacks `graphify-out/` (20 MB), `tests/`, `docs/` and `.claude/`.
- The base image's pip has advisories (PYSEC-2026-196, -2875, -2876, -3721). The pip upgrade was added to the Dockerfile on 2026-10-28 but is not committed.

## Steps to reproduce

1. Run `gh run list -R Krypt0nBull3t/Addarr --workflow docker-hub-push.yml`: all 16 runs failed.
2. Read `.github/workflows/docker-hub-push.yml:44`: the only tag is `${{env.REPO}}:latest`.
3. Run `docker build -t addarr .` and `docker run --rm --entrypoint ls addarr /app`: `graphify-out/`, `tests/`, `docs/` and `.claude/` are in the image.
4. Run `git diff Dockerfile`: the pip upgrade at lines 13-16 is uncommitted.

## Expected behavior

Builds are reproducible. The publish workflow succeeds and pushes a version tag next to `:latest`. The image holds only what the bot needs. The pip fix is committed.

## Fix

- [ ] **F150** Owner, manual, do this first: add the repo secrets `DOCKER_HUB_USERNAME` and `DOCKER_HUB_ACCESS_TOKEN`. Then make the workflow push a version tag next to `:latest`. Keep the CLAUDE.md publish claim (`.github/workflows/docker-hub-push.yml:26`, `:44`)
- [ ] **F151** Pin `python-telegram-bot~=22.8` and `aiohttp<4`; replace the deprecated `disable_web_page_preview` (`requirements.txt`, `Dockerfile:16`, `src/bot/handlers/help.py:76`, `:82`)
- [ ] **F152** Add `graphify-out/`, `tests/`, `docs/` and `.claude/` to `.dockerignore` (`.dockerignore`)
- [ ] **F153** Commit the pip upgrade (`Dockerfile:13-16`)

## Acceptance criteria

- [ ] F151: a test in `tests/test_handlers/test_help_handler.py` asserts that both help replies pass `link_preview_options` (link preview disabled) and not `disable_web_page_preview`. It fails before the fix and passes after.
- [ ] F151: in a fresh venv, `pip install -r requirements.txt` installs python-telegram-bot 22.x and aiohttp 3.x.
- [ ] F150: a test parses `.github/workflows/docker-hub-push.yml` and asserts that `tags` holds `:latest` and a version tag. It fails before the fix and passes after.
- [ ] F150 (manual): the repo has the secrets `DOCKER_HUB_USERNAME` and `DOCKER_HUB_ACCESS_TOKEN`. A push to `main` runs the workflow green and pushes `:latest` plus a version tag.
- [ ] F152 (manual): `docker run --rm --entrypoint ls <image> /app` shows no `graphify-out/`, `tests/`, `docs/` or `.claude/`.
- [ ] F153 (manual): `docker run --rm --entrypoint pip <image> --version` shows pip 26.2 or newer.
- [ ] `pytest`, `flake8` and `mypy src/` pass.

## Notes

- Source: audit 2026-10-28, docs/issues/audit-2026-10-28/FINDINGS.md (F-ids F151, F150, F152, F153).
- Priority: max P 25, sum P 84 (high).
- Dependencies: none in the order of work. Slice 4 (F275) relies on the F151 pins. Slice 20 (F281) keeps the CLAUDE.md publish claim, which is true after F150.
- Related open issue: #121 (Docker image improvements).
- Decided 2026-10-28: F150 the owner adds the Docker Hub secrets (manual, first); the workflow pushes a version tag next to `latest`; the CLAUDE.md publish claim stays.

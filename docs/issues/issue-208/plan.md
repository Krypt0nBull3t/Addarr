# Issue #208: Release 0.9.0 prep, CI matrix note

Issue: https://github.com/Krypt0nBull3t/Addarr/issues/208 (audit findings F160 to F165).

## Context

Status of each finding, checked on `development` at c7f52c1:

- **F160** CodeQL is `disabled_inactivity`. Repo setting. Owner only. No change here.
- **F161** `gh api repos/Krypt0nBull3t/Addarr/vulnerability-alerts -i` returns 404. Repo setting. Owner only. No change here.
- **F162** Done by #269 (#246). `.github/workflows/auto-approve.yml:434` has `commit_id: context.payload.workflow_run.head_sha`. Verified, not added again.
- **F163** Open. `src/__init__.py:12` has `__version__ = "0.8"`. No tag, no release.
- **F164** Done by #238 (commit 54bfedc). `.gitignore` has `.env` and `.env.*`. `.github/` has `CODEOWNERS`, `PULL_REQUEST_TEMPLATE.md`, `ISSUE_TEMPLATE/bug_report.yml` and `feature_request.yml`. No `.github/` edit in this PR.
- **F165** Open. Doc line only. `ci.yml:133` stays as is.

## Scope

In the PR:
1. `__version__` becomes `"0.9.0"` (`src/__init__.py:12`, `tests/conftest.py:221` and `:226`).
2. One line in `docs/issues/issue-160/plan.md` on why the matrix has four versions.
3. Release-notes text and developer actions in the PR body only. No changelog file.

Not in the PR (developer actions, listed in the PR body): re-enable CodeQL (F160), enable Dependabot security alerts (F161), tag `v0.9.0` and publish the GitHub Release (F163). This session makes no repo-setting change, tag or release.

## Task 1: Bump `__version__` to 0.9.0

**Files:**
- Modify: `src/__init__.py:12`
- Modify: `tests/conftest.py:221`, `tests/conftest.py:226`
- Test: `tests/test_handlers/test_help_handler.py` (exists, unchanged)

Help shows the version through the `HelpVersion` key. The help test only checks the key name, so it cannot catch a stale version. Add one test that pins the version.

- [ ] Add `tests/test_version.py` with `test_version_is_0_9_0`: `import src` and assert `src.__version__ == "0.9.0"`. Note that `tests/conftest.py` injects `__version__` into `src` (lines 221, 226), so the test would pass on the fixture alone. Read the real file instead: `ast.parse` of `src/__init__.py`, find the `__version__` assignment, assert its value is `"0.9.0"`. Run it, expect FAIL (`"0.8"`).
- [ ] Change `__version__ = "0.8"` to `"0.9.0"` in `src/__init__.py`. Change the two `"0.8"` values in `tests/conftest.py` to `"0.9.0"`.
- [ ] Run `tests/test_version.py` and `tests/test_handlers/test_help_handler.py`, expect PASS.
- [ ] Run `tests/test_architecture` (new test file and conftest change), expect PASS.
- [ ] Commit: `chore: bump version to 0.9.0 (#208, task 1)`.

## Task 2: Record why the CI matrix has four versions (F165)

**Files:**
- Modify: `docs/issues/issue-160/plan.md` (one line at the end of "Design Decisions", after item 4)

- [ ] Add item 5: `5. **Later change (8364be6):** the compatibility matrix grew to 3.10, 3.12, 3.13 and 3.14 "to avoid gaps in version coverage". The boundary-only choice above was dropped on purpose; #208 (F165) keeps the four versions.`
- [ ] Run `tests/test_architecture/test_repo_docs.py` and `test_skills.py`, expect PASS.
- [ ] Commit: `docs: record why the CI matrix has four versions (#208, task 2)`.

## Task 3: Release-notes text and developer actions in the PR body

No file in the repo. The text goes in the PR body (create-pr step 7), under a "Release notes for v0.9.0 (for the GitHub Release)" heading, so the developer can paste it. It has two parts. Each item comes from a merged PR body (`gh pr view <N> --json body`) or from the code, and the executor re-checks each one before the PR is created.

**Changed defaults** (checked in code):
- Group chats: `security.chatMode` defaults to `private_only` and refuses group chats. Set `allow_all` to keep group use (#152). The bot also treats any other value as private-only (#254).
- Admin mode: with `security.enableAdmin: true`, `/delete` and the delete buttons are admin only. A service (Transmission, SABnzbd) is restricted too when its `onlyAdmin` is true, which is the default (`src/utils/helpers.py:46`, #193). Set `onlyAdmin: false` on a service to open its controls.
- `security.enableAllowlist` is enforced. Only `allow_list` users and admins can use the bot, `/auth` included (#193).
- `/auth` is always rate limited, 3 attempts per 300 s, also when `rateLimit.enable` is false (#193).

**Upgrade notes** (from the merged PR bodies):
- #263 (#206): `webhooks.host` now defaults to `127.0.0.1`. Remote *arr apps need `webhooks.host: 0.0.0.0`. A value already set stays.
- #258 (#210): every user sends `/auth` once after the upgrade (the stored password hash check).
- #254 (#198): startup stops on a quoted port (`port: "7878"`), on an enabled service without an API key (or Bazarr with an empty address), and on a `chatMode` other than `private_only` or `allow_all`.
- #259 (#218): the Helm chart is gone. The `chatid.txt`, `admin.txt` and `allowlist.txt` files are not read and not mounted any more.
- #188: webhooks enabled without secrets now answer 401. Generate a secret with `/webhooks` and set the `X-Api-Secret` header in each *arr app.
- #191: `docker-compose.yml` mounts `config.yaml` as `:rw` and `/app/data` as the named volume `addarr-data`. `user_preferences.json` moves to `data/` (the old root file is still read when the new one is missing). The base image is `python:3.11-alpine3.24`.
- #252: the calendar quick-add (Add button in `/upcoming`) is removed.
- #254 and #192: the unused `tags` config keys are removed from the example config. An existing `config.yaml` that has them still loads.
- Executor: scan the remaining merged PR bodies since `main` for further upgrade notes (`gh pr list --state merged --base development --json number,title,body`), and add each one found.

Developer actions (listed in the PR body):
- F160: re-enable the CodeQL workflow in repo settings. It turns itself off again when `main` gets no commits for 60 days, so release soon after this merge.
- F161: enable Dependabot security alerts. Check `gh api repos/Krypt0nBull3t/Addarr/vulnerability-alerts -i` returns 204.
- F163: after the release PR merges to `main`, tag `v0.9.0` and publish the GitHub Release with the notes above.
- F162 is done by #269, F164 by #238. No action.

## Verification

- `<lock> .venv/bin/python -m pytest tests/test_version.py tests/test_architecture`
- Preflight (all CI commands, 100% coverage gate) before the push.

## Risks

- `tests/test_version.py` reads source text with `ast`, so it does not import `src` (matches the architecture-test style).
- The version string reaches users only through `/help`. No other code reads it.

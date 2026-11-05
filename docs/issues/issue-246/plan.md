# Plan: Issue #246: PR approvals stay valid after later pushes

> **For agentic workers:** convert this plan to `docs/issues/issue-246/TASKS.md` with `/task-writer`, then run the `addarr-workflow` Execution Loop. Steps use checkbox (`- [ ]`) syntax.

**Goal:** The bot approval names the commit that CI checked, the rule that a push removes an approval is recorded in an ADR, and `CLAUDE.md` says so.

**Architecture:** CI and docs only. One line in `.github/workflows/auto-approve.yml`, one drift test, one new ADR, one note in ADR 0004 and two edits in `CLAUDE.md`. No change in `src/`, translations or Docker.

**Tech Stack:** GitHub Actions (`actions/github-script`), pytest architecture tests (`tests/test_architecture/test_repo_docs.py`), Markdown.

**Spec:** `gh issue view 246 --repo Krypt0nBull3t/Addarr`. The issue is the spec; no `design.md` (one obvious approach).

## Finding: the repo settings are already on

Read with `gh api repos/Krypt0nBull3t/Addarr/branches/<branch>/protection` on 2026-11-05:

| Setting | `development` | `main` |
|-|-|-|
| `dismiss_stale_reviews` | `true` | `true` |
| `require_last_push_approval` | `true` | `true` |
| `required_approving_review_count` | 1 | 1 |
| `required_status_checks.strict` | `true` | not read |

So issue items 1 and 3 need no admin action, and acceptance 1 and 3 hold by setting. Open for the repo: item 2 (`commit_id`) and item 4 (ADR, `CLAUDE.md`).

## Global Constraints

- Never name another project, another project's workflow skill or its paths in any file, commit message or PR text.
- Write no `TODO`/`FIXME` and no `print(` in added lines; `auto-approve.yml` flags them.
- `test_repo_docs.py` rules: a repo path in a code span of `CLAUDE.md` must exist; a `test_*` name in a code span must be defined.
- Stage only the files you changed (never `git add .`); check `git diff --cached` before each commit.
- Edit nothing in `.github/` before the developer approves this plan.

## Exact `.github/` change

File `.github/workflows/auto-approve.yml`, step `Approve PR` (one line added, nothing else in `.github/`):

```diff
             await github.rest.pulls.createReview({
               owner: context.repo.owner,
               repo: context.repo.repo,
               pull_number: ${{ steps.pr.outputs.number }},
+              commit_id: context.payload.workflow_run.head_sha,
               event: 'APPROVE',
               ...
             });
```

Effect: the approval binds to the commit CI checked. If a push lands during the up-to-300 s wait for the checks, the approval sits on an older commit than the PR head, so with `dismiss_stale_reviews` it does not count for the new head. The step `Get PR number and diff` already matches the PR on `p.head.sha === workflow_run.head_sha`, so the number and the commit agree.

## Repo settings (no change needed)

No admin action. The maintainer already set `dismiss_stale_reviews` and `require_last_push_approval` on `development` and `main`. The PR body lists the read command so a reviewer can re-check. `require_last_push_approval` keeps the bot usable: the bot account is not the pusher.

## Review Focus

1. A push during the 300 s wait: the approval must name the older commit. Pinned by the `commit_id` test (Task 1); the behaviour itself is GitHub's and is checked by the `gh api` read in the PR body.
2. A fork PR: the workflow never approves it (`head: <owner>:<branch>`); a maintainer approval is dismissed by the next push. Recorded in the ADR (Task 2); no workflow change.
3. `commit_id` removed or renamed in a later edit: Task 1's test fails.
4. `CLAUDE.md` names the new ADR path: `test_claude_md_paths_exist` fails if the file is missing (Task 3).

---

### Task 1: Pin `commit_id` and add it to the approval step

**Files:**
- Test: `tests/test_architecture/test_repo_docs.py`
- Modify: `.github/workflows/auto-approve.yml` (step `Approve PR`)

**Interfaces:**
- Produces: `test_auto_approve_binds_approval_to_ci_commit()` in `tests/test_architecture/test_repo_docs.py`.

- [ ] **Step 1: Write the failing test.** Add after `test_claude_md_test_names_exist`. It loads `.github/workflows/auto-approve.yml` with `yaml.safe_load`, takes the step named `Approve PR` from `jobs.review.steps`, and asserts `"commit_id: context.payload.workflow_run.head_sha" in step["with"]["script"]`.
- [ ] **Step 2: Run it, confirm RED.** `<lock> .venv/bin/python -m pytest tests/test_architecture/test_repo_docs.py::test_auto_approve_binds_approval_to_ci_commit -v` fails on the assertion (the step exists, the line does not).
- [ ] **Step 3: Add the one line** from "Exact `.github/` change" above.
- [ ] **Step 4: Run it, confirm GREEN**, then `<lock> .venv/bin/python -m pytest tests/test_architecture --tb=short -q`.
- [ ] **Step 5: Commit** `fix: bind the bot approval to the commit CI checked (task 1.1)` with the two files and `TASKS.md`.

### Task 2: ADR 0006 and the ADR 0004 note

**Files:**
- Create: `docs/adr/0006-dismiss-stale-approvals.md`
- Modify: `docs/adr/0004-prs-target-development.md` (one sentence at the end of the branch protection paragraph)

- [ ] **Step 1: Write ADR 0006** in the format of the other ADRs: `# 0006. A push dismisses earlier approvals`, `**Status:** Accepted. Recorded 2026-11-05.` Sections:
  - Context: approval stayed valid after later pushes; a maintainer approval of a fork PR survived new commits; the bot approval had no `commit_id`.
  - Decision: `dismiss_stale_reviews` and `require_last_push_approval` are on for `development` and `main` (read 2026-11-05); `auto-approve.yml` passes `commit_id: context.payload.workflow_run.head_sha`; the workflow never approves a fork PR.
  - Consequences: a push after an approval removes it; own branches get a new bot approval after the next green CI run; a fork PR needs a new maintainer approval after each push; changing the two settings is a repo-admin action and needs a new ADR.
- [ ] **Step 2: Add to ADR 0004** after the sentence that ends "...and Docker Build.": `Since 2026-11-05 a push also dismisses earlier approvals and the last pusher cannot approve (see ADR 0006).`
- [ ] **Step 3: Run** `<lock> .venv/bin/python -m pytest tests/test_architecture --tb=short -q` (green).
- [ ] **Step 4: Commit** `docs: record the stale-approval decision as ADR 0006 (task 2.1)`.

### Task 3: `CLAUDE.md` CI/CD section

**Files:**
- Modify: `CLAUDE.md` (the `auto-approve.yml` bullet, one new sentence in the `ci.yml` bullet)

- [ ] **Step 1: Edit the `auto-approve.yml` bullet.** Replace "Posts review comment and auto-approves." with "Posts review comment and approves the commit CI checked (`commit_id` is `workflow_run.head_sha`). It never approves a fork PR."
- [ ] **Step 2: Add to the end of the `ci.yml` bullet:** "Branch protection on `development` and `main` also dismisses stale approvals and requires approval of the last push, so a push removes an earlier approval. See `docs/adr/0006-dismiss-stale-approvals.md`."
- [ ] **Step 3: Run** `<lock> .venv/bin/python -m pytest tests/test_architecture --tb=short -q` (green; `test_claude_md_paths_exist` checks the ADR path).
- [ ] **Step 4: Commit** `docs: describe approval binding and stale-approval dismissal in CLAUDE.md (task 3.1)`.

## Verification (PR body)

- Acceptance 1 and 3: `gh api repos/Krypt0nBull3t/Addarr/branches/development/protection --jq .required_pull_request_reviews` shows `dismiss_stale_reviews` and `require_last_push_approval` as `true`; same for `main`.
- Acceptance 2: the new test pins `commit_id`; the first bot approval after merge names the CI head SHA in the review's `commit_id` (`gh api repos/Krypt0nBull3t/Addarr/pulls/<N>/reviews --jq '.[].commit_id'`).
- Full preflight (`/addarr check` commands) before the push.

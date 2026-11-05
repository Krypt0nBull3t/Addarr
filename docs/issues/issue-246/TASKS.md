# Tasks: Issue #246: PR approvals stay valid after later pushes

Plan: `docs/issues/issue-246/plan.md`. The developer approved the plan and the one `.github/` edit (the `commit_id` line in the `Approve PR` step of `auto-approve.yml`). `dismiss_stale_reviews` and `require_last_push_approval` are already `true` on `development` and `main`, so no repo setting changes.

### Phase 1: Bind the approval and record the decision (3 tasks)

**Goal:** The bot approval names the commit CI checked, ADR 0006 records the stale-approval rules, and `CLAUDE.md` says so.

- [ ] **1.1** Pin `commit_id` and add it to the approval step
    - **Context:**
        - **Why:** `pulls.createReview` without `commit_id` binds the approval to the PR head at call time. A push during the up-to-300 s wait for the checks gets approved for a commit CI did not check.
        - **Architecture:** CI-only change. The drift tests in `tests/test_architecture/test_repo_docs.py` already read `.github/workflows/ci.yml` with `yaml.safe_load` and the `read_text` helper; do the same for `auto-approve.yml`.
        - **Key refs:** `.github/workflows/auto-approve.yml` (step `Approve PR`, last step of job `review`), `tests/test_architecture/test_repo_docs.py` (`read_text`, `test_claude_md_test_names_exist`).
        - **Watch out:** Add exactly one line to `.github/`, nothing else. The step `Approve PR` has `uses: actions/github-script@v9`; the code is in `with.script`. Added lines must not contain `TODO`, `FIXME` or `print(`. The test must fail first on the missing line, not on a wrong step name.
    - **Scope:** One test and one workflow line.
    - **Touches:** `tests/test_architecture/test_repo_docs.py`, `.github/workflows/auto-approve.yml`
    - **Action items:**
        - [RED] Write `test_auto_approve_binds_approval_to_ci_commit` after `test_claude_md_test_names_exist`: load the workflow, take the step named `Approve PR` from `jobs.review.steps`, assert `"commit_id: context.payload.workflow_run.head_sha" in step["with"]["script"]`. Run it and confirm it fails on that assertion.
        - [GREEN] Add `commit_id: context.payload.workflow_run.head_sha,` between `pull_number` and `event` in the `pulls.createReview` call.
    - **Success:** The new test passes, `tests/test_architecture` passes, `git diff origin/development -- .github/` shows one added line.

- [ ] **1.2** ADR 0006 and the ADR 0004 note
    - **Context:**
        - **Why:** The decision must be on record (issue item 4). ADR 0004 says protection needs "1 approving review" only; it is now out of date.
        - **Architecture:** ADRs are `docs/adr/NNNN-<slug>.md` with Status, Context, Decision and Consequences (see `docs/adr/0004-prs-target-development.md`).
        - **Key refs:** `docs/adr/0004-prs-target-development.md` (branch protection paragraph), `docs/adr/0005-no-settings-import-before-config.md` for style.
        - **Watch out:** Do not rewrite ADR 0004; add one sentence that points to ADR 0006. State the settings were read on 2026-11-05. Fork PRs: the workflow never approves them, a maintainer does, and a push dismisses that approval.
    - **Scope:** One new ADR, one sentence in ADR 0004.
    - **Touches:** `docs/adr/0006-dismiss-stale-approvals.md` (new), `docs/adr/0004-prs-target-development.md`
    - **Action items:**
        - [GREEN] Write ADR 0006: title `# 0006. A push dismisses earlier approvals`, `**Status:** Accepted. Recorded 2026-11-05.`, then Context, Decision, Consequences as in the plan.
        - [GREEN] Add to ADR 0004 after the sentence ending "and Docker Build.": `Since 2026-11-05 a push also dismisses earlier approvals and the last pusher cannot approve (see ADR 0006).`
    - **Success:** `tests/test_architecture` passes; both files read correctly.

- [ ] **1.3** `CLAUDE.md` CI/CD section
    - **Context:**
        - **Why:** `CLAUDE.md` is the agents' map; its `auto-approve.yml` bullet says "auto-approves" without naming the commit.
        - **Architecture:** `test_claude_md_paths_exist` checks that every repo path in a code span exists, so the ADR file from 1.2 must exist first.
        - **Key refs:** `CLAUDE.md` § CI/CD (the `ci.yml` and `auto-approve.yml` bullets).
        - **Watch out:** Keep code spans to existing paths and names. Do not name another project.
    - **Scope:** Two small text edits.
    - **Touches:** `CLAUDE.md`
    - **Action items:**
        - [GREEN] In the `auto-approve.yml` bullet, replace "Posts review comment and auto-approves." with "Posts review comment and approves the commit CI checked (`commit_id` is `workflow_run.head_sha`). It never approves a fork PR."
        - [GREEN] Append to the `ci.yml` bullet: "Branch protection on `development` and `main` also dismisses stale approvals and requires approval of the last push, so a push removes an earlier approval. See `docs/adr/0006-dismiss-stale-approvals.md`."
    - **Success:** `tests/test_architecture` passes, including `test_claude_md_paths_exist`.

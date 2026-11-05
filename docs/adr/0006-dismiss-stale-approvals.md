# 0006. A push dismisses earlier approvals

**Status:** Accepted. Recorded 2026-11-05.

## Context

An approval on a PR to `development` stayed valid after later pushes, so it did not prove that anyone reviewed the code that got merged (issue #246). Three cases:

- A maintainer approved a fork PR by hand. The contributor could then push more commits, and the PR still showed as approved.
- On our own branches, the bot approved every PR whose CI passed. The approval stayed after every later push.
- `auto-approve.yml` called `pulls.createReview` without `commit_id`. GitHub then binds the approval to the PR head at the time of the call. The step waits up to 300 s for the checks, so a push in that window got an approval for a commit this run did not check.

## Decision

- Branch protection on `development` and `main` has `dismiss_stale_reviews` and `require_last_push_approval` turned on (read with `gh api repos/Krypt0nBull3t/Addarr/branches/<branch>/protection` on 2026-11-05). A new push dismisses earlier approvals, and the last pusher cannot approve the PR.
- The `Approve PR` step in `.github/workflows/auto-approve.yml` passes `commit_id: context.payload.workflow_run.head_sha`. The approval names the commit CI checked. `tests/test_architecture/test_repo_docs.py` pins the line.
- The workflow never approves a fork PR: it finds the PR through `head: <owner>:<branch>`. A maintainer approves a fork PR by hand.

## Consequences

- A push after an approval removes the approval.
- On our own branches the bot approves again after the next green CI run. The bot account is not the pusher, so `require_last_push_approval` does not block it.
- A fork PR needs a new maintainer approval after each push. Required CI still runs on the new head, but CI is not a code review.
- If a push lands while the workflow waits for the checks, the approval sits on the older commit and does not count for the new head.
- Both settings are repository settings. Changing them needs repo admin rights and a new ADR.

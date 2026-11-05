# AGENTS.md

Rules for agents that work in this repo. The project rules (layers, config access, tests,
branching) are in `CLAUDE.md`. Read it first. This file does not repeat them.

## Reviewing a pull request

1. Before you post anything, read the PR's existing review threads and the replies on them:
   `gh api repos/{owner}/{repo}/pulls/{number}/comments`. A reply has `in_reply_to_id`.
2. Do not post a finding that an open thread already has.
3. If a reply declined a finding and gave a reason, post that finding again only when the
   reason is wrong. Then say in the new comment why the reason is wrong.
4. Post each finding once per PR, also after new commits.
5. Check the diff against the rules in `CLAUDE.md`.

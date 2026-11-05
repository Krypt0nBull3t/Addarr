# 0004. PRs target `development` and merge with a merge commit

**Status:** Accepted. Recorded 2026-11-04; the rule was in force before.

## Context

`main` is the production branch: `.github/workflows/docker-hub-push.yml` publishes the Docker image on every push to `main`. `development` is the integration branch. The `addarr-workflow` makes one commit per task as a restore point; a squash merge folds them into one. A squash or rebase merge of a release PR gives `main` commits that `development` does not have.

## Decision

- Feature and fix PRs target `development`.
- Only release PRs from `development` to `main` target `main`.
- PRs merge with a regular merge commit (`gh pr merge --merge`, the "Merge pull request" button). Never squash or rebase.

Branch protection on `development` (as of 2026-11-04) requires 1 approving review and these status checks from `.github/workflows/ci.yml`: Lint, Type Check, Validate Translations, Unit Tests, Integration Tests, Architecture Tests, Compatibility (3.10, 3.12, 3.13, 3.14) and Docker Build. Since 2026-11-05 a push also dismisses earlier approvals and the last pusher cannot approve (see ADR 0006).

## Consequences

- The PR template (`.github/PULL_REQUEST_TEMPLATE.md`) asks for `development` as the base.
- Renaming a CI job blocks merges until the branch protection rule names the new job.

# Create PR Flow: Step Details

Sequence is defined in SKILL.md. This file provides implementation details per step.

## Step 1: Pre-PR Review

Review the branch diff (`git diff origin/development...HEAD` after `git fetch origin development`). Fix actionable findings. Skip pre-existing codebase patterns.

### Pass 1: INVOKE @addarr-find-bugs

Security, correctness and runtime errors: auth gates, async bugs, Telegram API misuse, config access, secrets in logs. Read-only; it reports and you fix.

### Pass 2: INVOKE the built-in `/simplify` on the branch diff

It reviews and applies cleanups itself. Hold its changes to these Addarr rules:

| Pattern in the diff | Simplification |
|-|-|
| Repeated `if photo: edit_caption else: edit_text` | Use `send_response(message, text, reply_markup)` from `src/bot/handlers/media/formatters.py` |
| A reusable keyboard built inline | Move it to a `get_<feature>_keyboard()` function in `src/bot/keyboards.py` |
| Duplicate error handling in handlers | Extract the common error reply |
| Verbose config access chains | Read the config section once at the top |
| Several near-identical `CallbackQueryHandler` registrations | Consolidate the patterns |

Do not simplify away:
- The singleton `__new__` + `_initialize` pattern (intentional, not redundant)
- `is_enabled()` guard checks (safety-critical, must stay explicit)
- `await query.answer()` calls (Telegram requirement)
- `context.user_data.clear()` in a cancel handler of a flow that owns all of `user_data` (prevents state leaks). A handler that keeps only its own few keys, like `/webhooks`, must not clear: it wipes the state of other open flows (#206)
- State return values from handler methods (ConversationHandler requires them)

A change to a workflow rule: search `.claude/skills/` for the old wording. Another skill may restate it (task-writer restated the per-task full gate).

### Pass 3 (only when the diff touches `src/api/` or `tests/test_api/`): the `arr-api-contract-checker` agent

Delegate to the `arr-api-contract-checker` agent. It checks each changed Radarr, Sonarr or Lidarr request against the Servarr OpenAPI spec (paths, methods, query parameters, response fields), which the aioresponses mocks cannot catch.

### After the passes

If any pass changed code, run the scoped checks for what it changed (SKILL.md Execution Loop step 3), then go to Step 2. The full gate runs in Step 5.

## Step 2: Commit the Review Fixes

If step 1 changed files, commit them. Stage only the files you changed (never `git add .`), check `git diff --cached`, then commit with `fix: address pre-PR review`.

## Step 3: Retrospective

Follow [retrospective.md](retrospective.md): it proposes skill and convention updates and `ASK`s before each edit. It runs here, before the merge, the preflight and the push, for two reasons. Its edits often touch skills and CLAUDE.md, which `tests/test_architecture/` checks, so the preflight must run after them. And they go out in the one push of Step 6: a second push after the PR opens runs CI and the review bot again.

## Step 4: Merge Development

Branch protection requires a branch that is up to date with `development`. Merge it in before the gates (a merge, never a rebase):
```bash
git fetch origin development
git merge origin/development
```

On a conflict: stop, show the conflicting files and `ASK` how to resolve them.

## Step 5: Preflight

Run the full preflight flow (see [preflight.md](preflight.md)). All checks must pass; step 4 is the CI coverage gate (100%). Commit any preflight fixes the same way as step 2.

## Step 6: Verify Readiness and Push Once

Check:
- Branch is not `development` or `main`
- All changes committed (`git status`). Uncommitted changes of yours: commit them as in step 2. Files that are not yours: leave them out and report them.

Then push, once:
```bash
<lock> git push -u origin <branch-name>
```

A refused push: see SKILL.md "The Suite Lock".

## Step 7: PR Title and Body

- **Title**: From the issue title, otherwise from the branch name. Keep under 70 chars.
- **Body**: Fill the sections of `.github/PULL_REQUEST_TEMPLATE.md`, in its order:
  - **Summary:** the plan's Goal in 1-3 sentences (`docs/issues/issue-<N>/plan.md`), then `Fixes #<N>`. Without a plan, use the issue and the commits.
  - **Changes:** one bullet per task or logical change, from the plan and the commits.
  - **Checks:** tick each box the preflight proved. Write `n/a` beside a box that does not apply (no translation change, no user-facing flow).
  - **Notes:** the CI lanes the local preflight does not run (see the intro of [preflight.md](preflight.md)): the Compatibility matrix (the whole suite on the other Python versions in `ci.yml`), the Docker Build and the non-blocking Dependency Audit. Say when the change could affect one of them (new syntax, a dependency pin, the Dockerfile). Add any design call a reviewer should check.

Write the body to the session scratchpad as `pr-<N>-body.md` (a fixed `/tmp` name collides between parallel sessions).

## Step 8: Create PR

```bash
gh pr create --repo Krypt0nBull3t/Addarr --base development --title "<title>" --body-file <scratchpad>/pr-<N>-body.md
```

## Step 9: Report Result

Show the PR URL. One line.

When `graphify-out/graph.json` exists and the branch changed code, run `graphify update .` to keep the graph current (CLAUDE.md § graphify; AST-only, `graphify-out/` is git-ignored). Without a graph, skip this.

## Step 10: Hand Off to the PR Driver

If the `pshepard` skill is available, `INVOKE` `/pshepard <PR number>`. It reads red CI and review findings, answers them and keeps a live watch on the PR. While it watches, it handles the review rounds: do not also run `/addarr feedback` on the same round.

`pshepard` is a user-scope skill: a cloud session or another contributor has none. Without it, say: "Run `/addarr feedback` when reviews arrive."

## Step 11: Suggest `/clear`

Suggest `/clear` before the next `/addarr new`. A long session re-reads its history on every turn, which draws on the session and weekly limits; the next issue does not need this one's context. This is a suggestion; the user decides.

Do not suggest it while `pshepard` watches this PR: a `/clear` ends the watch. Suggest it once the PR is merged.

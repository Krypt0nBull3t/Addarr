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
- `context.user_data.clear()` in cancel handlers (prevents state leaks)
- State return values from handler methods (ConversationHandler requires them)

### Pass 3 (only when the diff touches `src/api/` or `tests/test_api/`): the `arr-api-contract-checker` agent

Delegate to the `arr-api-contract-checker` agent. It checks each changed Radarr, Sonarr or Lidarr request against the Servarr OpenAPI spec (paths, methods, query parameters, response fields), which the aioresponses mocks cannot catch.

### After the passes

If any pass changed code, run the unit-test command from [preflight.md](preflight.md) step 4, then go to Step 2.

## Step 2: Commit the Review Fixes

If step 1 changed files, commit them before preflight. Stage only the files you changed (never `git add .`), check `git diff --cached`, then commit with `fix: address pre-PR review`.

## Step 3: Preflight

Run the full preflight flow (see [preflight.md](preflight.md)). All checks must pass; step 4 is the CI coverage gate (100%). Commit any preflight fixes the same way as step 2.

## Step 4: Verify Readiness

Check:
- Branch is not `development` or `main`
- All changes committed (`git status`). Uncommitted changes of yours: commit them as in step 2. Files that are not yours: leave them out and report them.
- Branch is pushed to remote

If not pushed:
```bash
git push -u origin <branch-name>
```

## Step 5: Generate PR Info

- **Title**: From the issue title, otherwise from the branch name. Keep under 70 chars.
- **Body**: Generate from commits and issue context. End the summary with `Closes #<N>`. Write it to the session scratchpad as `pr-<N>-body.md` (a fixed `/tmp` name collides between parallel sessions).

## Step 6: Create PR

```bash
gh pr create --repo Krypt0nBull3t/Addarr --base development --title "<title>" --body-file <scratchpad>/pr-<N>-body.md
```

## Step 7: Report Result

Show the PR URL. One line.

---
name: addarr-workflow
description: "Development workflow for Addarr. Invoke via /addarr command. Triggers: /addarr, /addarr new, /addarr continue, /addarr feedback, /addarr pr, /addarr check, /addarr release, /addarr end, and requests such as pick up an Addarr issue, continue the tasks for this branch, open a PR for this branch, address review comments on my Addarr PR, run the CI checks locally, pause this Addarr session. Handles: issue selection, branch management, planning, PR creation, preflight validation, PR feedback, release readiness, pausing an issue."
---

# Addarr Workflow

Self-driving development workflow for Addarr. Entry point: `/addarr [argument]`

**IMPORTANT:** Feature and fix PRs target `development`. Only the release flow targets `main`.

**Execution model:** Each flow is an ordered sequence. Execute every step automatically. Only pause for user input at steps marked `ASK`. All other steps execute without waiting.

## Token Discipline

**This is a hard requirement for all automated execution.**

- Go straight from tool result to next tool call. No narration between steps.
- Only output text when: reporting a blocker, asking for user input, or summarizing a completed phase.
- Never restate what a tool result already shows (test counts, lint output, etc.).
- Never explain what you're about to do — just do it.
- Phase/task summaries: 1-2 sentences max.
- Agent prompts: instruct agents to return only actionable findings. "Skip items consistent with existing codebase patterns. Only report issues you would actually fix."

## The Suite Lock

Some machines run one test suite at a time through a lock script. Every test, gate and
`git push` command in this skill is written `<lock> <command>`:

- `<lock>` is `~/.local/share/agent-suite/with-suite-lock.sh <agent>/issue-<N> --` when that
  script exists. `<agent>` is the agent name a lead's brief gives you, `addarr` otherwise.
  Without an issue number (`/addarr check` on `development`, the release flow) the label is
  `<agent>/<branch>`.
- When the script does not exist (a cloud session, another contributor), `<lock>` is empty:
  run the command bare.
- Call the script by its literal path, never through a variable, alias or function.
- `[suite-lock] waiting for the lock` is expected. Do not kill the command.
- An environment variable goes before `<lock>`: the script runs its arguments as a command.
- Addarr has no pre-push hook, but a push still goes through the lock. A lock-wrapped force
  or delete push is denied like a bare one.
- If a hook or guard refuses a push, stop and report it. Never work around it: no
  `--no-verify`, no other path.

## Entry Points

| Command | Flow | Description |
|-|-|-|
| `/addarr` | auto-detect | Detect state and select flow |
| `/addarr new [<N>]` | new-task | Issue -> branch -> analyze -> plan -> execute |
| `/addarr continue [<N>]` | continue | Resume from TASKS.md |
| `/addarr feedback [<PR>]` | feedback | Process review comments on your own PR |
| `/addarr pr` | create-pr | Review -> preflight -> push -> create PR |
| `/addarr check` | preflight | Run the core CI checks locally |
| `/addarr release` | release | Full readiness check for development -> main merge |
| `/addarr end [<N>]` | end | Pause: note in TASKS.md, WIP commit, push |

**Arguments after the flow name pass through.** `/addarr new <N>` works on issue #N and skips
the issue chooser: running the chooser again could pick a different issue. `/addarr continue <N>`
and `/addarr end <N>` use #N instead of reading it from the branch name; when the current branch is not
`<prefix>/<N>-<slug>`, `ASK` before switching. `/addarr feedback <PR>` works on that PR.

A PR from a fork or an outside contributor is not this workflow: use `/review-external-pr` (agent `untrusted-pr-reviewer`). Never check out its code.

## Auto-Detection (no argument)

Unless an argument gives it, every flow reads the issue number `<N>` from the branch name `<prefix>/<N>-<slug>`;
"TASKS.md" means `docs/issues/issue-<N>/TASKS.md`. On a feature branch without `<N>`, `ASK` for it.

Check the current state and recommend a flow:

1. Check if an open PR exists for current branch with unresolved review threads
   whose last comment is not yours (GraphQL query in references/feedback.md step 3)
   -> recommend **feedback**
2. Check `docs/issues/issue-<N>/TASKS.md` exists with pending tasks -> recommend **continue**
3. Check if branch has committed work not yet in a PR -> recommend **pr**
4. Otherwise -> recommend **new**

On a feature branch with pending tasks or uncommitted changes, also offer **end**
(after the recommended option).

`ASK` with AskUserQuestion (header: "Session", options ordered by recommendation). Then execute the selected flow.

---

## Flow: new-task

See [references/new-task.md](references/new-task.md) for detailed instructions per step.

```
Step 1  ASK     Issue selection (AskUserQuestion with open issues);
                skipped when `/addarr new <N>` names the issue
Step 2  ASK     Branch type selection (feature/fix/refactor)
Step 2b RUN     Create branch <prefix>/<N>-<slug> from latest development
Step 3  RUN     Context check first (references/context-check.md: graphify,
                the Addarr wiki, with fallbacks). Then analyze the task (read
                the issue and its comments; identify layers, config, i18n).
                On a fix/ branch: INVOKE @superpowers:systematic-debugging
                for the root cause first
Step 3b ASK/INVOKE  @superpowers:brainstorming (if task is complex/ambiguous/multi-approach;
                it asks the user questions). Write the design to
                docs/issues/issue-<N>/design.md, not docs/superpowers/specs/
Step 3c ASK     Confirm analysis summary before planning
Step 4  INVOKE  @superpowers:writing-plans for plan content only -> explore codebase ->
                write plan to docs/issues/issue-<N>/plan.md
                Leave out its REQUIRED SUB-SKILL header and skip its Execution
                Handoff: steps 4c and 5 execute the plan
                Use @addarr-handlers, @addarr-services, @addarr-testing for patterns
Step 4b ASK     User reviews plan.md and approves before continuing
Step 4c INVOKE  @task-writer -> convert plan.md into docs/issues/issue-<N>/TASKS.md
Step 4d ASK     Model check: a stronger model for the work phase? Only when the
                plan meets a trigger in references/new-task.md step 4d
Step 5  RUN     Execute tasks (see "Execution Loop" below)
Step 6  RUN     Flow: create-pr (automatic transition)
```

## Flow: continue

```
Step 1  RUN     Read docs/issues/issue-<N>/TASKS.md (<N> from the argument or
                the branch name), find next pending task. Read the latest
                **Session paused:** note, if any, and start from its next step.
                In a fresh session,
                run the context check (references/context-check.md) first
Step 2  RUN     Execute tasks (see "Execution Loop" below)
Step 3  RUN     Flow: create-pr (when all tasks complete)
```

## Flow: feedback

See [references/feedback.md](references/feedback.md) for detailed instructions.

```
Step 1  INVOKE  @superpowers:receiving-code-review (before any code change)
Step 2  RUN     Find the PR (argument or current branch); stop if pshepard watches it
Step 3  RUN     Fetch all review comments (PR reviews + inline + bot review),
                with thread and comment ids
Step 4  RUN     Categorize feedback (must-fix / should-fix / consider)
Step 4b ASK     Present categorized list, user selects which to address
Step 5  RUN     Create tasks in TASKS.md for selected items
Step 6  RUN     Execute tasks (see "Execution Loop" below)
                INVOKE @superpowers:systematic-debugging for bug-fix feedback items
Step 7  RUN     Merge origin/development, then Flow: preflight; commit fixes
                (only your files)
Step 8  ASK     Draft one reply per thread (what changed + commit SHA); user approves
Step 9  RUN     Push once: <lock> git push
Step 10 RUN     Post the approved replies; resolve each thread whose fix landed
Step 11 RUN     Report what was addressed
```

## Flow: create-pr

See [references/create-pr.md](references/create-pr.md) for detailed instructions.

```
Step 1  RUN     Pre-PR review of the branch diff (details in create-pr.md):
                INVOKE @addarr-find-bugs   (security, bugs, async errors, Telegram misuse)
                INVOKE built-in /simplify  (reuse, quality, efficiency; Addarr rules in create-pr.md)
                Agent arr-api-contract-checker, only when src/api/ or tests/test_api/ changed
                Fix any actionable findings. Skip pre-existing patterns.
Step 2  RUN     Commit the review fixes (see create-pr.md)
Step 3  ASK     Retrospective: extract learnings from TASKS.md completion
                metadata and suggest durable skill/convention updates.
                See [references/retrospective.md](references/retrospective.md).
                Human-reviewed; approved edits are committed on this branch.
                It runs before the preflight and the push, so its edits are
                tested and go out in the same push
Step 4  RUN     Merge origin/development into the branch (conflict: ASK)
Step 5  RUN     Flow: preflight (all checks must pass; it runs the CI coverage gate)
Step 6  RUN     Verify readiness, then push once: <lock> git push -u origin <branch>
Step 7  RUN     PR title + body: fill .github/PULL_REQUEST_TEMPLATE.md from plan.md
Step 8  RUN     gh pr create --base development (body file, see create-pr.md)
Step 9  RUN     Report PR URL; suggest a wiki re-ingest when it applies
Step 10 INVOKE  /pshepard <PR number> when that skill is available (PR driver)
Step 11 RUN     Suggest /clear before the next issue (not while pshepard watches)
```

## Flow: end

See [references/end.md](references/end.md) for detailed instructions. Save mode only.

```
Step 1  RUN     Detect <N> (argument or branch name)
Step 2  RUN     Write a pause note under the task in progress in TASKS.md
                (or on top of plan.md before TASKS.md exists)
Step 3  RUN     WIP commit: only your files and the note file
Step 4  RUN     Push: <lock> git push -u origin <branch> (open PR: ASK first)
Step 5  RUN     Report the branch, the last task and how to resume
```

## Flow: preflight

See [references/preflight.md](references/preflight.md) for detailed instructions.

The same commands as the CI jobs in `.github/workflows/ci.yml` (a test pins them).
Commands are in preflight.md only. Run sequentially, stop on the first failure.

```
Step 1  RUN     Lint (flake8)
Step 2  RUN     Type check (mypy)
Step 3  RUN     Translation validation
Step 4  RUN     Unit tests with the 100% coverage gate
                On failure: INVOKE @superpowers:systematic-debugging, fix
Step 5  RUN     Integration tests
Step 6  RUN     Architecture tests
Step 7  RUN     Report results summary (1-2 lines)
```

After any code fix, re-run from step 1. At most 3 fix rounds; then report the
failing output and `ASK`.

## Flow: release

Full readiness check before merging `development` -> `main`. Invokes the `@release-readiness` skill.

```
Step 1  RUN     Checkout development branch, ensure up-to-date with origin
Step 2  INVOKE  @release-readiness (runs all 4 phases; run its test and gate
                commands under <lock>, label <agent>/development)
Step 3  RUN     Report final verdict: READY or NOT READY
Step 4  ASK     If READY, confirm user wants to create the merge PR to main
Step 5  RUN     If confirmed: write the body (merged PRs since main, the
                release-readiness verdict) to <scratchpad>/release-body.md, then
                gh pr create --repo Krypt0nBull3t/Addarr --base main --head development
                  --title "Release: development to main" --body-file <scratchpad>/release-body.md
```

---

## Execution Loop

This is the core implementation cycle used by new-task, continue, and feedback flows.

**Skill loading: on demand, not per loop.** Invoke a skill only when its trigger in the
Skill Reference table below applies, never routinely per task or per behavior.
"First task in a session" means: invoke once when the trigger first applies, then
the skill stays in context for the rest of the session. Do not re-invoke.

**For each task in TASKS.md:**

```
1  RUN     Read the task's Context, Touches and Action items

2  RUN     TDD cycle, for each behavior in the task:
   a  RED     Write failing test
   b  RUN     <lock> <py> -m pytest tests/<path>/test_<name>.py::test_<case> -v (confirm it fails correctly)
   c  GREEN   Write minimal implementation
   d  RUN     <lock> <py> -m pytest tests/<path>/test_<name>.py -v (confirm the relevant tests pass)

   On unexpected test failure:
   -> INVOKE @superpowers:systematic-debugging — find root cause before fixing

   Stall rule: stop when a task has two failed attempts (or two rounds of
   systematic-debugging without a fix), five clarification turns without
   progress, or fixes that keep breaking the plan, or on a design question
   the plan does not answer. ASK with the evidence: the ambiguity, the
   failing output or the open design question. Suggest a stronger model
   (`/model`) for this task only; the user decides and switches.

3  RUN     Scoped checks, once per task, for each layer the task changed
           (in src/ or in its tests):
             src/api/            <lock> <py> scripts/test_runner.py api --coverage
             src/services/       <lock> <py> scripts/test_runner.py services --coverage
             src/bot/handlers/   <lock> <py> scripts/test_runner.py handlers --coverage
             src/models/         <lock> <py> scripts/test_runner.py models --coverage
             rest of src/bot/    <lock> <py> scripts/test_runner.py bot --coverage
             src/utils/          <lock> <py> scripts/test_runner.py utils --coverage
             src/config/         <lock> <py> scripts/test_runner.py config --coverage
             src/setup/          <lock> <py> scripts/test_runner.py setup --coverage
             translations/       PYTHONIOENCODING=utf-8 <lock> <py> run.py --validate-i18n
             skills, CLAUDE.md, docs/, .github/ or tests/test_architecture/:
                                 <lock> <py> -m pytest tests/test_architecture --tb=short -v
           Add tests for the uncovered lines the scoped run lists. The full
           suite with the 100% coverage gate runs once, in the preflight.
4  RUN     Integration test check: if the task adds or modifies a user-facing
           flow (handler, command, conversation state, callback routing):
           a  Check tests/integration/ for an existing test covering this flow
           b  If none exists: write a new integration test using the BotHarness
              (see tests/integration/conftest.py for harness, fixtures, and
              update factories). Test the happy path end-to-end.
           c  If one exists but doesn't cover the new behavior: extend it.
           d  Run: <lock> <py> -m pytest tests/integration --tb=short -v (all pass).
           Skip this step for non-handler changes (API clients, services,
           config, utils, translations, CI, docs).
5  RUN     Mark task complete in TASKS.md and add the completion metadata
           that CLAUDE.md § Planning & Task Conventions requires (example below)
6  RUN     Commit changes for this task: a restore point in case later tasks
           break something. Stage only the task's files and TASKS.md (never
           `git add .`), check `git diff --cached`, and reference the task
           number (e.g., "feat: add command builder module (task 1.1)")
7  RUN     Next task (loop back to 1)
```

**Completion metadata example:**
```markdown
- [x] **1.1** Implement command builder with service filtering
    - [existing task content...]
    - **Completed:** 2026-03-03
    - **Learnings:**
        - Telegram requires command names to be lowercase for setMyCommands
        - BotCommandScopeChat requires the chat_id, not user_id (same for private chats)
    - **Key Changes:**
        - Created `src/bot/commands.py` with `build_authenticated_commands()`
        - Added translation keys `CommandStart`, `CommandAuth`, etc.
    - **Notes:** Monitor logs for "Could not set commands" warnings on startup
```

**When all tasks complete:** INVOKE @superpowers:verification-before-completion, then transition to the next flow step (create-pr or preflight depending on parent flow).

---

## Skill Reference

All skills below must be available; invoke each only when its trigger applies.
The `superpowers:*` skills come from the superpowers plugin. If one is not
available, stop and report it instead of continuing without it.

| Skill or agent | Role | Invoked when |
|-|-|-|
| `@superpowers:receiving-code-review` | Weigh review feedback before changing code | feedback step 1 |
| `@superpowers:brainstorming` | Explore design space | new-task step 3b (only if complex/ambiguous) |
| `@superpowers:writing-plans` | Plan content | new-task step 4 |
| `@task-writer` | Convert plan into sized TASKS.md | new-task step 4c |
| `@superpowers:test-driven-development` | Enforce TDD discipline | First task in a session (once) |
| `@superpowers:systematic-debugging` | Investigate unexpected failures | Unexpected test failure (not a simple typo/import fix); new-task step 3 on a `fix/` branch |
| `@superpowers:verification-before-completion` | Final verification gate | After all tasks, before create-pr |
| `@addarr-handlers` | Handler class patterns | First task in a session that touches `src/bot/handlers/` |
| `@addarr-services` | Service/API client patterns | First task in a session that touches `src/services/` or `src/api/` |
| `@addarr-testing` | Project-specific test patterns | First task in a session that touches `tests/` |
| `@addarr-find-bugs` | Security, bugs, async/Telegram errors | create-pr step 1 |
| built-in `/simplify` | Reuse, quality, efficiency | create-pr step 1 |
| agent `arr-api-contract-checker` | *arr requests against the Servarr OpenAPI specs | create-pr step 1, when `src/api/` or `tests/test_api/` changed |
| `@release-readiness` | Release gate | release step 2 |

Optional, user scope: `pshepard` (PR driver: red CI, review threads, a live watch) at create-pr
step 10. A session without it skips that step and says to run `/addarr feedback` when reviews arrive.

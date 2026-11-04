---
name: addarr-workflow
description: "Development workflow for Addarr. Invoke via /addarr command. Triggers: /addarr, /addarr new, /addarr continue, /addarr feedback, /addarr pr, /addarr check, /addarr release. Handles: issue selection, branch management, planning, PR creation, preflight validation, PR feedback, release readiness."
---

# Addarr Workflow

Self-driving development workflow for Addarr. Entry point: `/addarr [argument]`

**IMPORTANT:** All PRs target `development` as base branch, never `main`.

**Execution model:** Each flow is an ordered sequence. Execute every step automatically. Only pause for user input at steps marked `ASK`. All other steps execute without waiting.

## Token Discipline

**This is a hard requirement for all automated execution.**

- Go straight from tool result to next tool call. No narration between steps.
- Only output text when: reporting a blocker, asking for user input, or summarizing a completed phase.
- Never restate what a tool result already shows (test counts, lint output, etc.).
- Never explain what you're about to do — just do it.
- Phase/task summaries: 1-2 sentences max.
- Agent prompts: instruct agents to return only actionable findings. "Skip items consistent with existing codebase patterns. Only report issues you would actually fix."

## Entry Points

| Command | Flow | Description |
|---------|------|-------------|
| `/addarr` | auto-detect | Detect state and select flow |
| `/addarr new` | new-task | Issue -> branch -> analyze -> plan -> execute |
| `/addarr continue` | continue | Resume from TASKS.md |
| `/addarr feedback` | feedback | Process PR review comments |
| `/addarr pr` | create-pr | Review -> preflight -> push -> create PR |
| `/addarr check` | preflight | Run CI checks locally |
| `/addarr release` | release | Full readiness check for development -> main merge |

## Auto-Detection (no argument)

Every flow reads the issue number `<N>` from the branch name `<prefix>/<N>-<slug>`;
"TASKS.md" means `docs/issues/issue-<N>/TASKS.md`. On a feature branch without `<N>`, `ASK` for it.

Check the current state and recommend a flow:

1. Check if an open PR exists for current branch with unresolved review threads
   (GraphQL query in references/feedback.md step 2) -> recommend **feedback**
2. Check `docs/issues/issue-<N>/TASKS.md` exists with pending tasks -> recommend **continue**
3. Check if branch has committed work not yet in a PR -> recommend **pr**
4. Otherwise -> recommend **new**

`ASK` with AskUserQuestion (header: "Session", options ordered by recommendation). Then execute the selected flow.

---

## Flow: new-task

See [references/new-task.md](references/new-task.md) for detailed instructions per step.

```
Step 1  ASK     Issue selection (AskUserQuestion with open issues)
Step 2  ASK     Branch type selection (feature/fix/refactor)
Step 2b RUN     Create branch from latest development
Step 3  RUN     Analyze task (read issue, identify layers/config/i18n)
Step 3b INVOKE  @superpowers:brainstorming (if task is complex/ambiguous/multi-approach)
Step 3c ASK     Confirm analysis summary before planning
Step 4  INVOKE  @superpowers:writing-plans -> explore codebase -> write plan to
                docs/issues/issue-<N>/plan.md
                Use @addarr-handlers, @addarr-services, @addarr-testing for patterns
Step 4b ASK     User reviews plan.md and approves before continuing
Step 4c INVOKE  @task-writer -> convert plan.md into docs/issues/issue-<N>/TASKS.md
Step 5  RUN     Execute tasks (see "Execution Loop" below)
Step 6  RUN     Flow: create-pr (automatic transition)
```

## Flow: continue

```
Step 1  RUN     Read docs/issues/issue-<N>/TASKS.md, find next pending task
Step 2  RUN     Execute tasks (see "Execution Loop" below)
Step 3  RUN     Flow: create-pr (when all tasks complete)
```

## Flow: feedback

See [references/feedback.md](references/feedback.md) for detailed instructions.

```
Step 1  RUN     Find PR for current branch
Step 2  RUN     Fetch all review comments (PR reviews + inline + bot review)
Step 3  RUN     Categorize feedback (must-fix / should-fix / consider)
Step 3b ASK     Present categorized list, user selects which to address
Step 4  RUN     Create tasks in TASKS.md for selected items
Step 5  RUN     Execute tasks (see "Execution Loop" below)
                INVOKE @superpowers:systematic-debugging for bug-fix feedback items
Step 6  RUN     Flow: preflight
Step 7  RUN     Push changes, report what was addressed
```

## Flow: create-pr

See [references/create-pr.md](references/create-pr.md) for detailed instructions.

```
Step 1  RUN     Pre-PR review — three complementary passes over the branch diff.
                INVOKE @addarr-find-bugs          (security, bugs, async errors, Telegram misuse)
                INVOKE @simplify           (code reuse, quality patterns, efficiency)
                INVOKE @addarr-code-simplifier    (structural clarity, nesting, readability)
                See create-pr.md for execution details.
                Fix any actionable findings. Skip pre-existing patterns.
Step 2  RUN     Commit the review fixes (see create-pr.md)
Step 3  RUN     Flow: preflight (all checks must pass; it runs the CI coverage gate)
Step 4  RUN     Verify readiness (not on main/development, all committed, push if needed)
Step 5  RUN     Generate PR title + body from commits and issue context
Step 6  RUN     gh pr create --base development
Step 7  RUN     Report PR URL
Step 8  RUN     Retrospective: extract learnings from TASKS.md completion
                metadata and suggest durable skill/convention updates.
                See [references/retrospective.md](references/retrospective.md).
                Human-reviewed — never auto-updates skills.
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
Step 2  INVOKE  @release-readiness (runs all 4 phases)
Step 3  RUN     Report final verdict: READY or NOT READY
Step 4  ASK     If READY, confirm user wants to create the merge PR to main
Step 5  RUN     If confirmed: gh pr create --base main --head development
```

## Optional: Post-Merge Retrospective

After a PR is merged, optionally run the retrospective process to extract durable learnings from TASKS.md completion metadata. See [references/retrospective.md](references/retrospective.md) for the categorization process. Human-reviewed — never auto-updates skills.

---

## Execution Loop

This is the core implementation cycle used by new-task, continue, and feedback flows.

**Skill loading — on-demand, not per-loop:**

All skills below are mandatory (must be available) but should only be invoked
when the specific trigger condition is met — never routinely per task or per behavior.

| Skill | Trigger (invoke ONLY when this happens) |
|-------|----------------------------------------|
| `@addarr-handlers` | First task in a session that touches `src/bot/handlers/` |
| `@addarr-services` | First task in a session that touches `src/services/` or `src/api/` |
| `@addarr-testing` | First task in a session that touches `tests/` |
| `@superpowers:test-driven-development` | First task in a session (load once to set TDD discipline) |
| `@superpowers:verification-before-completion` | After all tasks complete, before create-pr flow |
| `@addarr-code-simplifier` | Refactor step produces overly complex code; also invoked in create-pr step 1 |
| `@superpowers:systematic-debugging` | Unexpected test failure (not a simple typo/import fix) |

"First task in a session" means: invoke once when the trigger first applies, then
the skill stays in context for the rest of the session. Do not re-invoke.

**For each task in TASKS.md:**

```
1  RUN     Mark task in-progress

2  RUN     TDD cycle — for each behavior in the task:
   a  RED     Write failing test
   b  RUN     <py> -m pytest tests/<path>/test_<name>.py::test_<case> -v (confirm it fails correctly)
   c  GREEN   Write minimal implementation
   d  RUN     <py> -m pytest tests/<path>/test_<name>.py -v (confirm the relevant tests pass)

   On unexpected test failure:
   -> INVOKE @superpowers:systematic-debugging — find root cause before fixing

3  RUN     Full suite with the CI coverage gate, once per task (not per behavior):
           the unit-test command from references/preflight.md step 4.
           Fix coverage gaps by adding tests for uncovered lines.
4  RUN     Integration test check: if the task adds or modifies a user-facing
           flow (handler, command, conversation state, callback routing):
           a  Check tests/integration/ for an existing test covering this flow
           b  If none exists: write a new integration test using the BotHarness
              (see tests/integration/conftest.py for harness, fixtures, and
              update factories). Test the happy path end-to-end.
           c  If one exists but doesn't cover the new behavior: extend it.
           d  Run: <py> -m pytest tests/integration --tb=short -v (all pass).
           Skip this step for non-handler changes (API clients, services,
           config, utils, translations, CI, docs).
5  RUN     Mark task complete in TASKS.md and add completion metadata:
           - **Completed:** <date>
           - **Learnings:** Key insights, gotchas, or discoveries from this task
           - **Key Changes:** Summary of what was modified (files, functions, patterns)
           - **Notes:** Any important context for future work
6  RUN     Commit changes for this task — creates a restore point in case
           later tasks break something. Use a descriptive message referencing
           the task number (e.g., "feat: add command builder module (task 1.1)")
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

**When all tasks complete:** Transition to the next flow step (create-pr or preflight depending on parent flow).

---

## Skill Reference

All skills are mandatory but invoke only when the trigger applies — see the
on-demand table in the Execution Loop section for per-task triggers.

| Skill | Role | Invoked when |
|-------|------|-------------|
| `@superpowers:brainstorming` | Explore design space | new-task step 3b (only if complex/ambiguous) |
| `@superpowers:writing-plans` | Guide plan creation | new-task step 4 |
| `@task-writer` | Convert plan into sized TASKS.md | new-task step 4c |
| `@superpowers:test-driven-development` | Enforce TDD discipline | First task in session (once) |
| `@superpowers:verification-before-completion` | Final verification gate | After all tasks, before create-pr |
| `@superpowers:systematic-debugging` | Investigate unexpected failures | On unexpected test failure |
| `@addarr-handlers` | Handler class patterns | First handler task in session |
| `@addarr-services` | Service/API client patterns | First service/API task in session |
| `@addarr-testing` | Project-specific test patterns | First test-writing task in session |
| `@addarr-code-simplifier` | Structural clarity & readability | create-pr step 1; also during execution when refactor produces complex code |
| `@addarr-find-bugs` | Security, bugs, async/Telegram errors | create-pr step 1 |
| `@simplify` | Code reuse, quality patterns, efficiency | create-pr step 1 |

---
name: addarr-workflow
description: "Development workflow for Addarr. Invoke via /addarr command. Triggers: /addarr, /addarr new, /addarr continue, /addarr feedback, /addarr pr, /addarr check. Handles: issue selection, branch management, planning, PR creation, preflight validation, PR feedback."
---

# Addarr Workflow

Self-driving development workflow for Addarr. Entry point: `/addarr [argument]`

**IMPORTANT:** All PRs target `development` as base branch, never `main`.

**Execution model:** Each flow is an ordered sequence. Execute every step automatically. Only pause for user input at steps marked `ASK`. All other steps execute without waiting.

## Entry Points

| Command | Flow | Description |
|---------|------|-------------|
| `/addarr` | auto-detect | Detect state and select flow |
| `/addarr new` | new-task | Issue -> branch -> analyze -> plan -> execute |
| `/addarr continue` | continue | Resume from TASKS.md |
| `/addarr feedback` | feedback | Process PR review comments |
| `/addarr pr` | create-pr | Review -> preflight -> push -> create PR |
| `/addarr check` | preflight | Run CI checks locally |

## Auto-Detection (no argument)

Check the current state and recommend a flow:

1. Check if an open PR exists for current branch with unresolved review comments -> recommend **feedback**
2. Check `TASKS.md` exists with pending tasks -> recommend **continue**
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
Step 1  RUN     Read TASKS.md, find next pending task
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
Step 1  INVOKE  @find-bugs on all branch changes — fix any findings
Step 2  INVOKE  @simplify on changed files — quick pass for reuse, quality, efficiency
Step 2b INVOKE  @code-simplifier on changed files — deeper focused refactoring
Step 3  INVOKE  @superpowers:verification-before-completion — run pytest, confirm green
Step 3b RUN     Coverage check: run pytest with --cov on all changed source modules
                and --cov-report=term-missing. Target 100% on all new/modified code.
                Fix any gaps by adding tests for uncovered lines.
Step 4  RUN     Flow: preflight (all checks must pass)
Step 5  RUN     Verify readiness (not on main/development, all committed, push if needed)
Step 6  RUN     Generate PR title + body from commits and issue context
Step 7  RUN     gh pr create --base development
Step 8  RUN     Report PR URL and CI expectations
```

## Flow: preflight

See [references/preflight.md](references/preflight.md) for detailed instructions.

Run sequentially, stop on first failure. Fix issues automatically where possible.

```
Step 1  RUN     pytest --tb=short -q
                On failure: INVOKE @superpowers:systematic-debugging, fix, re-run
Step 2  RUN     flake8 .
                On failure: auto-fix formatting, report logic issues
Step 3  RUN     PYTHONIOENCODING=utf-8 python run.py --validate-i18n
                On failure: report missing/malformed keys
Step 4  RUN     Report results summary
```

---

## Execution Loop

This is the core implementation cycle used by new-task, continue, and feedback flows.

**For each task in TASKS.md:**

```
1  RUN     Mark task in-progress
2  CHECK   Determine if task touches handlers or services based on:
           - Task scope, file paths, and action items mentioning handlers/services
           - Issue context (e.g., "new command", "API client", "service layer")
           If task touches src/bot/handlers/ → INVOKE @addarr-handlers
           If task touches src/services/ or src/api/ → INVOKE @addarr-services
           (Skip if task is pure config, translations, or utilities)
3  INVOKE  @superpowers:test-driven-development (governs the entire cycle below)

   For each behavior in the task:
   a  RED     Write failing test — use @python-testing-pro for strategy,
              @addarr-testing for project-specific patterns
   b  RUN     pytest tests/path/test_file.py::test_name -v — confirm fails correctly
   c  GREEN   Write minimal implementation — follow @addarr-handlers / @addarr-services
              patterns if those skills were loaded in step 2
   d  RUN     pytest --tb=short -q — confirm all pass
   e  INVOKE  @code-simplifier on changed code (refactor phase)
   f  RUN     pytest --tb=short -q — confirm still green after refactor

   On unexpected test failure at any point:
   -> INVOKE @superpowers:systematic-debugging — find root cause before fixing

4  INVOKE  @superpowers:verification-before-completion — run full test suite, confirm output
5  RUN     Coverage check: run pytest with --cov on changed source modules
           and --cov-report=term-missing. Target 100% on all new/modified code.
           Fix any gaps by adding tests for uncovered lines.
6  RUN     Mark task complete in TASKS.md and add completion metadata:
           - **Completed:** <date>
           - **Learnings:** Key insights, gotchas, or discoveries from this task
           - **Key Changes:** Summary of what was modified (files, functions, patterns)
           - **Notes:** Any important context for future work
7  RUN     Commit changes for this task — creates a restore point in case
           later tasks break something. Use a descriptive message referencing
           the task number (e.g., "feat: add command builder module (task 1.1)")
8  RUN     Next task (loop back to 1)
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

Skills invoked during workflow execution and their roles:

| Skill | Role | Invoked during |
|-------|------|---------------|
| `@superpowers:brainstorming` | Explore design space for complex tasks | new-task step 3b |
| `@task-writer` | Convert plan into sized TASKS.md | new-task step 4c |
| `@superpowers:test-driven-development` | Govern red-green-refactor cycle | Execution loop |
| `@python-testing-pro` | Pytest strategies, mocking, parametrization | Execution loop (RED phase) |
| `@addarr-testing` | Project-specific test patterns and fixtures | Execution loop (RED phase) |
| `@addarr-handlers` | Handler class patterns and conventions | Execution loop (GREEN phase, handler work) |
| `@addarr-services` | Service/API client patterns | Execution loop (GREEN phase, service work) |
| `@code-simplifier` | Clean up changed code | Execution loop (refactor) + create-pr step 2b |
| `@simplify` | Quick pass for reuse, quality, efficiency | create-pr step 2 |
| `@superpowers:systematic-debugging` | Investigate unexpected failures | Execution loop (on failure) + feedback step 5 |
| `@superpowers:verification-before-completion` | Verify before claiming done | Execution loop step 3 + create-pr step 3 |
| `@find-bugs` | Review branch for bugs/security | create-pr step 1 |

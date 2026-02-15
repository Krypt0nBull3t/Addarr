---
name: addarr-workflow
description: |
  Development workflow for Addarr. Invoke via /addarr command.

  Triggers: /addarr, /addarr new, /addarr continue, /addarr feedback, /addarr pr, /addarr check

  Handles: issue selection, branch management, planning, PR creation, preflight validation, PR feedback.
---

# Addarr Workflow

Orchestrates the development workflow for Addarr. Entry point: `/addarr [argument]`

## Entry Points

| Command | Flow | Description |
|---------|------|-------------|
| `/addarr` | auto-detect | Recommend based on current state |
| `/addarr new` | new-task | Issue -> branch -> analyze -> plan -> execute |
| `/addarr continue` | continue | Resume from TASKS.md |
| `/addarr feedback` | feedback | Process PR review comments |
| `/addarr pr` | create-pr | Preflight -> push -> create PR |
| `/addarr check` | preflight | Run CI checks locally |

## Auto-Detection (no argument)

Check the current state and recommend a flow:

1. Check if an open PR exists for current branch with unresolved review comments -> recommend **feedback**
2. Check `TASKS.md` exists with pending tasks -> recommend **continue**
3. Check if branch has committed work not yet in a PR -> recommend **pr**
4. Otherwise -> recommend **new**

Ask with AskUserQuestion (header: "Session", options ordered by recommendation).

## Flows

### new-task

See [references/new-task.md](references/new-task.md)

### continue

Read TASKS.md, find the next pending task, and start working through it.

### feedback

See [references/feedback.md](references/feedback.md)

### create-pr

See [references/create-pr.md](references/create-pr.md)

### preflight

See [references/preflight.md](references/preflight.md)

## Development Approach

TDD is the default. Reference @superpowers:test-driven-development for the red-green-refactor cycle and @addarr-testing for project-specific test patterns.

## Completion

After any flow completes:

1. Run preflight checks (`/addarr check`)
2. Ask if PR should be created
3. Ask: "What next?" (options: Create PR, Next task, Done for now)

# New Task Flow — Step Details

Sequence is defined in SKILL.md. This file provides implementation details per step.

## Step 1: Issue Selection

Fetch open issues assigned to the user:
```bash
gh issue list --assignee @me --state open --limit 10
```

If no assigned issues, fetch unassigned issues:
```bash
gh issue list --state open --limit 10
```

`ASK` with AskUserQuestion:
- Header: "Task"
- Question: "Which issue do you want to work on?"
- Options: First 4 issues (format: `#123: Summary`)

If "Other": ask for a task description (no issue context).

Store issue context for session.

## Step 2: Branch Management

Get current state:
```bash
git branch --show-current
```

**If on a feature/fix branch already:**
- `ASK` if they want to continue here or create a new branch

**If on `development`:**

`ASK` with AskUserQuestion:
- Header: "Branch"
- Question: "What type of change is this?"
- Options:
  1. Feature - creates `feature/<short-description>`
  2. Bug fix - creates `fix/<short-description>`
  3. Refactor - creates `refactor/<short-description>`

Create branch from latest `development`:
```bash
git checkout development
git pull origin development
git checkout -b <prefix>/<short-description>
```

Short description is derived from the issue title (lowercase, hyphens, max 40 chars).

## Step 3: Analyze Task

Read the issue details:
```bash
gh issue view <number>
```

Analyze what's needed (do NOT explore codebase yet):

- Which layer(s) affected: Handlers, Services, API Clients
- Configuration changes needed
- Translation keys to add/modify
- Docker/Helm impact

**Complexity check:** If the task involves multiple valid approaches, unclear requirements, or 3+ layers — proceed to step 3b (`@superpowers:brainstorming`). Otherwise skip to step 3c.

`ASK` — present analysis summary and confirm before planning.

## Step 4: Plan

`INVOKE` @superpowers:writing-plans — explore the codebase and write a comprehensive implementation plan.

Do NOT use `EnterPlanMode`. Stay in the normal conversation flow and use Glob, Grep, Read to explore.

The plan should cover:
- Implementation steps with exact file paths
- Files to create/modify
- Test file locations and what tests to write for each implementation step (use @addarr-testing patterns)
- Translation keys if applicable
- Complete code snippets (not placeholders)

Write the plan to `docs/issues/issue-<N>/plan.md`.

`ASK` — present the plan to the user for review. Wait for approval before continuing.

## Step 4c: Convert Plan to Tasks

`INVOKE` @task-writer — read `docs/issues/issue-<N>/plan.md` and convert it into sized, TDD-ordered tasks. Write output to `docs/issues/issue-<N>/TASKS.md`.

## Step 5: Execute

Follows the Execution Loop defined in SKILL.md. No additional details needed here — the loop is self-contained.

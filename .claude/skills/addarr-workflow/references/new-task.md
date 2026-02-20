# New Task Flow

Full workflow: issue -> branch -> analyze -> plan -> execute

## 1. Issue Selection

Fetch open issues assigned to the user:
```bash
gh issue list --assignee @me --state open --limit 10
```

If no assigned issues, fetch unassigned issues:
```bash
gh issue list --state open --limit 10
```

Ask with AskUserQuestion:
- Header: "Task"
- Question: "Which issue do you want to work on?"
- Options: First 4 issues (format: `#123: Summary`)

If "Other": ask for a task description (no issue context).

Store issue context for session.

## 2. Branch Management

Get current state:
```bash
git branch --show-current
```

**If on a feature/fix branch already:**
- Ask if they want to continue here or create a new branch

**If on `development`:**

Ask with AskUserQuestion:
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

## 3. Analyze Task

Read the issue details:
```bash
gh issue view <number>
```

Analyze what's needed (do NOT explore codebase yet):

- Which layer(s) affected: Handlers, Services, API Clients
- Configuration changes needed
- Translation keys to add/modify
- Docker/Helm impact

Create summary and confirm with user before proceeding.

## 4. Plan

Use `EnterPlanMode` to explore codebase and create plan.

The plan should cover:
- Implementation steps
- Files to create/modify
- Test file locations and what tests to write for each implementation step (use @addarr-testing patterns)
- Translation keys if applicable

Use `ExitPlanMode` for approval.

If approved: create TASKS.md with implementation tasks.

## 5. Execute

Work through TASKS.md tasks using TDD (red-green-refactor):

1. **RED**: Write a failing test — use @addarr-testing patterns for the target layer
2. **Verify RED**: Run `pytest tests/path/test_file.py::test_name -v` — confirm it fails for the right reason
3. **GREEN**: Write minimal implementation to make the test pass
4. **Verify GREEN**: Run `pytest --tb=short -q` — confirm pass with no regressions
5. **REFACTOR**: Clean up if needed, keeping tests green
6. Repeat for next behavior

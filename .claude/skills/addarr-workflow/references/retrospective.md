# PR Retrospective

Create-pr step 3, before the merge, the preflight and the one push. Extracts learnings from TASKS.md completion metadata and suggests durable skill/convention updates. Approved edits are committed on the branch, so the preflight tests them and they go out in the same push, reviewed with the PR.

**Key constraint:** Human-reviewed, never automatic. Present suggestions; user approves before any edits.

## Process

### Step 1: Extract Learnings

Read all TASKS.md completion metadata for the PR's issue:
```
docs/issues/issue-<N>/TASKS.md
```

Collect all `**Learnings:**` and `**Notes:**` entries.

### Step 2: Categorize

For each learning, determine if it fits a category:

| Category | Target | Example |
|-|-|-|
| New anti-pattern | `addarr-testing/references/anti-patterns.md` | "Patching at source module instead of import site silently passes" |
| New convention | `CLAUDE.md` or `test_conventions.py` | "All handler entry points must have @require_auth" |
| Recurring bug pattern | `addarr-find-bugs` checklist | "Missing query.answer() in callback handlers" |
| New fixture pattern | `addarr-testing/references/patterns.md` | "Use make_context(user_data={'key': val}) for state-dependent tests" |
| Workflow improvement | `addarr-workflow` references | "Always run integration tests after handler changes" |

### Step 3: Present Suggestions

For each categorized learning, present:
- **Learning:** The original text
- **Suggestion:** What to add/modify and where
- **Category:** Which category from the table above

### Step 4: Apply (if approved)

Only after user explicitly approves each suggestion:
- Make the specific edit to the target file
- Commit on the branch with message `docs: retrospective update from issue-<N>` (stage only the edited files). Do not push: create-pr step 6 pushes once

## Example

**Learning from TASKS.md:**
> Telegram requires command names to be lowercase for setMyCommands

**Suggestion:**
- **Category:** New convention
- **Target:** `CLAUDE.md` under "Architecture > Key Patterns"
- **Add:** "Telegram command names must be lowercase for `setMyCommands`. Case-insensitive for user input."

**User says:** "Yes, add that."

**Action:** Edit CLAUDE.md, commit.

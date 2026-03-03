# Feedback Flow — Step Details

Sequence is defined in SKILL.md. This file provides implementation details per step.

## Step 1: Find the PR

Detect the PR for the current branch:
```bash
gh pr list --head $(git branch --show-current) --state open --json number,title,url
```

If no PR found: report and stop.

## Step 2: Fetch Review Comments

Get all review comments:
```bash
gh pr view <number> --json reviews,comments
```

For detailed inline comments:
```bash
gh api repos/{owner}/{repo}/pulls/<number>/comments
```

Also check the automated review bot comment (posted by the auto-approve workflow) for any warnings or suggestions.

## Step 3: Categorize Feedback

Group comments into:
- **Must fix**: Bugs, security issues, breaking changes
- **Should fix**: Code quality, error handling, naming
- **Consider**: Style suggestions, optional improvements

`ASK` — present the categorized list and ask which items to address.

## Step 4: Create Tasks

For each item to address, create a task in TASKS.md:
```markdown
- [ ] [must-fix] Fix <description> (from @reviewer)
- [ ] [should-fix] Update <description> (from @reviewer)
```

## Step 5: Execute

Follows the Execution Loop defined in SKILL.md, with one addition:

- **Bug fixes from feedback:** `INVOKE` @superpowers:systematic-debugging to investigate root cause before fixing. Don't apply surface-level patches.

All other changes follow the standard execution loop (TDD, verification).

## Steps 6-7: Wrap Up

After completing all feedback tasks:
1. Run the preflight flow (SKILL.md "Flow: preflight")
2. Push changes:
   ```bash
   git push
   ```
3. Report what was addressed

The CI pipeline will re-run and the AI reviewer will post an updated review.

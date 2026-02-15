# Feedback Flow

Process PR review comments and address feedback.

## 1. Find the PR

Detect the PR for the current branch:
```bash
gh pr list --head $(git branch --show-current) --state open --json number,title,url
```

If no PR found: report and stop.

## 2. Fetch Review Comments

Get all review comments:
```bash
gh pr view <number> --json reviews,comments
```

For detailed inline comments:
```bash
gh api repos/{owner}/{repo}/pulls/<number>/comments
```

Also check the automated review bot comment (posted by the auto-approve workflow) for any warnings or suggestions.

## 3. Categorize Feedback

Group comments into:
- **Must fix**: Bugs, security issues, breaking changes
- **Should fix**: Code quality, error handling, naming
- **Consider**: Style suggestions, optional improvements

Present the categorized list to the user and ask which items to address.

## 4. Create Tasks

For each item to address, create a task in TASKS.md:
```markdown
- [ ] [must-fix] Fix <description> (from @reviewer)
- [ ] [should-fix] Update <description> (from @reviewer)
```

## 5. Execute

Work through the feedback tasks. After completing all:
1. Run preflight checks (`/addarr check`)
2. Push changes
3. Report what was addressed

The CI pipeline will re-run and the AI reviewer will post an updated review.

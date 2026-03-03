# Create PR Flow — Step Details

Sequence is defined in SKILL.md. This file provides implementation details per step.

## Step 1: Find Bugs

`INVOKE` @find-bugs — review the full branch diff:

```bash
git diff $(git merge-base HEAD development)...HEAD
```

Follow the find-bugs skill process completely (attack surface mapping, security checklist, verification). Fix any findings before proceeding. If fixes are made, run `pytest --tb=short -q` to confirm no regressions.

## Step 2: Simplify

`INVOKE` @code-simplifier on all files changed in this branch:

```bash
git diff --name-only $(git merge-base HEAD development)...HEAD
```

Apply simplifications while keeping tests green. Run `pytest --tb=short -q` after changes.

## Step 3: Verification Gate

`INVOKE` @superpowers:verification-before-completion — run the full test suite and confirm output before proceeding:

```bash
pytest --tb=short -q
```

Do NOT proceed unless output confirms all tests pass.

## Step 4: Preflight

Run the full preflight flow (see [preflight.md](preflight.md)). All checks must pass before continuing.

## Step 5: Verify Readiness

Check:
- Branch is not `development` or `main`
- All changes committed (`git status`)
- Branch is pushed to remote

If not pushed:
```bash
git push -u origin $(git branch --show-current)
```

## Step 6: Generate PR Info

- **Title**: From issue title if linked, otherwise from branch name. Keep under 70 chars.
- **Body**: Generate from commits on this branch:
  ```bash
  git log development..HEAD --oneline
  ```

## Step 7: Create PR

```bash
gh pr create --base development --title "<title>" --body "$(cat <<'EOF'
## Summary
<1-3 bullet points describing the changes>

## Changes
<List of key changes by area: handlers, services, API, config, i18n>

## Test plan
<Manual testing steps to verify the changes>

## Related issue
<Closes #N or Relates to #N, if applicable>
EOF
)"
```

## Step 8: Report Result

Show the PR URL and confirm CI will run automatically:
- Pytest with coverage
- Flake8 lint
- Translation validation
- Docker build test
- AI-powered review via Groq (auto-approve if all pass)

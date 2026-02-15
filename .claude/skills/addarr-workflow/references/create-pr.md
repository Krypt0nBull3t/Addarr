# Create PR Flow

Create a pull request targeting `development`.

## 1. Preflight

All tests must pass. Run `pytest --cov=src --cov-report=term-missing` and verify no regressions.

Run all checks first (see [preflight.md](preflight.md)). If any fail, report and stop.

## 2. Verify Readiness

Check:
- Branch is not `development` or `main`
- All changes committed (`git status`)
- Branch is pushed to remote

If not pushed:
```bash
git push -u origin $(git branch --show-current)
```

## 3. Gather PR Info

- **Title**: From issue title if linked, otherwise from branch name. Keep under 70 chars.
- **Body**: Generate from commits on this branch:
  ```bash
  git log development..HEAD --oneline
  ```

## 4. Create PR

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

## 5. Report Result

Show the PR URL and remind that CI will run automatically:
- Pytest with coverage
- Flake8 lint
- Translation validation
- Docker build test
- AI-powered review via Groq (auto-approve if all pass)

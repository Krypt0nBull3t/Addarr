# Create PR Flow — Step Details

Sequence is defined in SKILL.md. This file provides implementation details per step.

## Step 1: Pre-PR Review (Consolidated)

Single pass over the branch diff covering bugs, security, quality, and efficiency.
Do NOT invoke @find-bugs, @simplify, or @code-simplifier as separate skills.
Run the review directly to avoid loading 3+ skill definitions into context.

### Get the diff

```bash
git diff origin/development...HEAD
```

If truncated, read each changed source file individually.

### Review checklist (check every changed file)

**Security & Bugs:**
- Injection (command, template, URL parameter)
- Missing `@require_auth` on entry points
- Missing `query.answer()` on callback handlers
- `reply_text` on callbacks (should be `edit_text`/`edit_caption`)
- Direct `config["key"]` indexing (should be `.get()`)
- Missing `await`, unclosed sessions
- API keys in log messages

**Code Quality:**
- Copy-paste blocks that should be unified (3+ near-identical blocks = fix)
- New code that duplicates an existing utility (search before writing)
- Leaky abstractions crossing layer boundaries

**Efficiency:**
- Redundant API calls (same data fetched multiple times)
- N+1 patterns
- Unbounded data structures

### Output rules

- Only report issues you would actually fix.
- Skip items consistent with existing codebase patterns (pre-existing tech debt).
- Skip stylistic issues (flake8 catches those).
- Fix actionable findings immediately. Run `pytest --tb=short -q` after fixes.

## Step 2: Coverage Check

```bash
pytest <test_files> --cov=<changed_modules> --cov-report=term-missing -q
```

Use dotted module paths for `--cov` (e.g., `--cov=src.bot.handlers.sabnzbd`).
Target 100% on all new/modified code. Add tests for uncovered lines.

## Step 3: Preflight

Run the full preflight flow (see [preflight.md](preflight.md)). All checks must pass.

## Step 4: Verify Readiness

Check:
- Branch is not `development` or `main`
- All changes committed (`git status`)
- Branch is pushed to remote

If not pushed:
```bash
git push -u origin <branch-name>
```

## Step 5: Generate PR Info

- **Title**: From issue title if linked, otherwise from branch name. Keep under 70 chars.
- **Body**: Generate from commits and issue context. Write to temp file, use `--body-file`.

## Step 6: Create PR

```bash
gh pr create --base development --title "<title>" --body-file /tmp/pr_body.md
```

## Step 7: Report Result

Show the PR URL. One line.

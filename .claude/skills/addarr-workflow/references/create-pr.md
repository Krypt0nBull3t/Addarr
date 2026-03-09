# Create PR Flow — Step Details

Sequence is defined in SKILL.md. This file provides implementation details per step.

## Step 1: Pre-PR Review (Three Complementary Passes)

Invoke three skills in sequence. Each covers a distinct concern with no overlap.
Fix actionable findings after each pass. Skip pre-existing codebase patterns.

### Pass 1: INVOKE @find-bugs

**Scope:** Security, correctness, and runtime errors.

Covers (and ONLY covers):
- Injection (command, template, URL parameter)
- Authentication/authorization bypass (missing `@require_auth`, IDOR)
- Async bugs (missing `await`, unclosed sessions, fire-and-forget coroutines)
- Telegram API misuse (missing `query.answer()`, `reply_text` on callbacks)
- Config safety (direct `config["key"]` indexing without `.get()`)
- Information disclosure (API keys in logs, error messages leaking internals)
- Race conditions, resource exhaustion, business logic errors

Does NOT cover: code style, reuse opportunities, readability, efficiency.

### Pass 2: INVOKE @simplify

**Scope:** Code reuse, quality patterns, and efficiency. Launches 3 parallel agents.

Covers (and ONLY covers):
- **Reuse:** New code duplicating existing utilities, inline logic that could use helpers
- **Quality:** Copy-paste blocks (3+ near-identical), parameter sprawl, leaky abstractions,
  redundant state, stringly-typed code where constants/enums exist
- **Efficiency:** Redundant API calls, N+1 patterns, missed concurrency,
  unbounded data structures, hot-path bloat

Does NOT cover: security bugs, structural readability, Python-specific simplifications.

### Pass 3: INVOKE @code-simplifier

**Scope:** Structural clarity and readability of changed files.

Covers (and ONLY covers):
- Unnecessary nesting (opportunities for early returns, guard clauses)
- Redundant abstractions used only once
- Variable/function naming clarity
- Python-specific simplifications (comprehensions, inline conditionals, unpacking)
- Verbose patterns that can be expressed more clearly
- Comments that describe obvious code

Does NOT cover: security, reuse opportunities, efficiency, architecture.

### After all three passes

Run `pytest --tb=short -q` if any fixes were made. Then proceed to Step 2.

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

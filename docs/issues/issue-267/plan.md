# Issue 267: AGENTS.md with rules for the automated PR reviewer

## Context

The automated PR reviewer is a Codex agent that runs in the worker's checkout. Codex reads
`AGENTS.md`. The repo has none, so the reviewer gets no project rules. It reads only the diff
at one head commit, not the open review threads or their replies. So it posts a finding again
after a reasoned reply declined it, and it posts the same finding more than once (3 identical
threads on #255, 6 on #260).

Docs only. No change in `src/`. No config, i18n or Docker impact. Only one approach exists, so
there is no `design.md`.

## Decisions

- `AGENTS.md` stays short and points to `CLAUDE.md` for the project rules. It does not copy them.
- The docs checks in `tests/test_architecture/test_repo_docs.py` cover only `CLAUDE.md` today.
  The acceptance criterion "any repo path or name in `AGENTS.md` exists" needs a check for the
  new file, or it proves nothing.
- `CLAUDE.md` § Agents names `AGENTS.md`, so a reader of `CLAUDE.md` finds it.
- A reply to a review comment has `in_reply_to_id` in the REST response, so the one command in
  the issue shows both findings and replies.

## Files

- Create `AGENTS.md`
- Modify `tests/test_architecture/test_repo_docs.py`
- Modify `CLAUDE.md` (§ Agents, one bullet)

## Task 1: Tests first (red)

In `tests/test_architecture/test_repo_docs.py`:

- Move the body of `test_claude_md_paths_exist` into a helper
  `missing_paths(rel_path) -> list[str]` (same `REPO_PATH` regex, same `ABSENT_ON_PURPOSE`,
  same `:line` suffix strip). `test_claude_md_paths_exist` becomes
  `assert missing_paths("CLAUDE.md") == []`.
- Add `test_agents_md_paths_exist`: `assert missing_paths("AGENTS.md") == []`.
- Add `test_agents_md_has_reviewer_rules`:
  - `text = read_text("AGENTS.md")`
  - `body = section(text, "Reviewing a pull request")`
  - assert `"pulls/{number}/comments"` is in `body`
  - assert `"CLAUDE.md"` is in `body`
- Add `test_claude_md_names_agents_md`:
  `assert "AGENTS.md" in section(read_text("CLAUDE.md"), "Agents")`.
- Update the module docstring: the checks cover `CLAUDE.md` and `AGENTS.md`.

Run `<lock> .venv/bin/python -m pytest tests/test_architecture/test_repo_docs.py -v`.
Expected: the three new tests fail (no `AGENTS.md`, no mention in `CLAUDE.md`).

## Task 2: AGENTS.md and the CLAUDE.md line (green)

Create `AGENTS.md`:

```markdown
# AGENTS.md

Rules for agents that work in this repo. The project rules (layers, config access, tests,
branching) are in `CLAUDE.md`. Read it first. This file does not repeat them.

## Reviewing a pull request

1. Before you post anything, read the PR's existing review threads and the replies on them:
   `gh api repos/{owner}/{repo}/pulls/{number}/comments`. A reply has `in_reply_to_id`.
2. Do not post a finding that an open thread already has.
3. If a reply declined a finding and gave a reason, post that finding again only when the
   reason is wrong. Then say in the new comment why the reason is wrong.
4. Post each finding once per PR, also after new commits.
5. Check the diff against the rules in `CLAUDE.md`.
```

Add one bullet to `CLAUDE.md` § Agents: `AGENTS.md` holds the rules for the automated PR
reviewer (read the open threads first, post each finding once).

Run `<lock> .venv/bin/python -m pytest tests/test_architecture --tb=short -v`. Expected: all pass.

## Verification

Full preflight through the `addarr-workflow` skill (flake8, mypy, translations, unit tests with
the 100% coverage gate, integration, architecture). No `src/` change, so coverage does not move.

# graphify reference: commit hook and native CLAUDE.md integration

Load this when the user asked to install the post-commit hook or wire graphify into a project's CLAUDE.md.

## For git commit hook

Install a post-commit hook that auto-rebuilds the graph after every commit. No background process needed - triggers once per commit, works with any editor.

```bash
graphify hook install    # install
graphify hook uninstall  # remove
graphify hook status     # check
```

After every `git commit`, the hook detects which code files changed (via `git diff HEAD~1`), re-runs AST extraction on those files, and rebuilds `graph.json` and `GRAPH_REPORT.md`. Doc/image changes are ignored by the hook - run `/graphify --update` manually for those.

If a post-commit hook already exists, graphify appends to it rather than replacing it.

---

## For native CLAUDE.md integration

Never run `graphify claude install` (or `graphify install`) in this repository. This repo already has the integration: the `## graphify` section of `CLAUDE.md`, the graphify hooks in `.claude/settings.json` and this skill. The installer rewrites them and drops this repo's safety changes (see `CLAUDE.md` § graphify and `tests/test_architecture/test_agent_tooling.py`). If the user asks for it, tell them this instead of running it.

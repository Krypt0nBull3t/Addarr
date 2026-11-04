# Context Check

It tells you where to look, so you do not re-derive what the graph or the wiki already knows. Each part has a fallback: a cloud session or another contributor has no graph, no wiki and no `qmd`, and the flow goes on without them.

## 1. graphify

When `graphify-out/graph.json` exists, follow CLAUDE.md § graphify. No graph: use Glob and Grep. Never build the graph unless the user asks.

## 2. The Addarr wiki

The Addarr pages live under `wiki/addarr/` in the maintainer's personal vault. Find it:

1. `~/.claude/CLAUDE.md` § LLM Wiki names the vault, when that file exists.
2. Otherwise, a directory with `CLAUDE.md`, `index.md` and `wiki/addarr/`.

**With `qmd`** (an MCP server with a `personal-wiki` collection): query that collection with a `lex` sub-query (exact terms: class, command or file names) and a `vec` sub-query (the question in plain words), plus an `intent` line saying what you are about to change. Then retrieve the bodies of the top 2-4 hits. A status call lists collections; it is not a lookup.

**Without `qmd`, with the vault:** read `wiki/addarr/Addarr Gotchas.md`, then the pages that `wiki/addarr/index.md` lists for the layers the issue touches.

**No vault and no `qmd`:** say so in one line and go on with CLAUDE.md and the code.

Never cite a page you did not read.

## 3. Wiki gaps

Note each question the wiki did not answer, or answered wrongly, with what you found in the code instead. Write them to a `## Wiki gaps` section in `docs/issues/issue-<N>/plan.md`: at step 4 when the plan is written, or at once when `plan.md` already exists. They then survive `/clear`, `/addarr end` and a machine switch. Never write to the vault from this workflow; create-pr suggests a re-ingest at the end.

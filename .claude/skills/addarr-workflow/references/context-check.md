# Context Check

Run this before the first source read. It uses the map graphify builds of this repo (CLAUDE.md § graphify), so you do not re-derive what the graph already knows.

- **Graph exists** (`graphify-out/graph.json`): run `graphify query '<question>'` before the first Grep, search or source read. Use `graphify path '<A>' '<B>'` for a relation and `graphify explain '<concept>'` for one concept. Read raw files only for lines the graph located. Quoting rules: CLAUDE.md § graphify.
- **Broad navigation:** when `graphify-out/wiki/index.md` exists, start there instead of browsing the source.
- **No graph** (a cloud session, another contributor, or graphify not installed): use Grep and Read, guided by CLAUDE.md. Never install graphify or build a graph unless the user asks; you may suggest `graphify update .`.

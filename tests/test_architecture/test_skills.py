"""
Project skill accuracy tests.

Agents copy the code in .claude/skills/ as written. These checks keep every
path, module, class, function and fixture a skill names real in this repo.
The checks are static: they parse the repo with `ast` and never import `src`.

Placeholders in skill text use `<name>` (`<Feature>Handler`,
`get_<feature>_keyboard`). Nothing else counts as a placeholder.
"""

import ast
import builtins
import functools
import re
import textwrap
from pathlib import Path

import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SKILLS_DIR = PROJECT_ROOT / ".claude" / "skills"
# graphify is vendored upstream; review-external-pr is owned by issue #236.
UNCHECKED_SKILLS = {"graphify", "review-external-pr"}
CHECKED_SKILLS = sorted(
    d.name for d in SKILLS_DIR.iterdir() if d.is_dir() and d.name not in UNCHECKED_SKILLS
)

PYTEST_BUILTINS = {
    "monkeypatch", "tmp_path", "tmp_path_factory", "caplog", "capsys", "capfd",
    "request", "recwarn", "pytestconfig",
}
FENCE = re.compile(r"^```(\w*)[^\n]*\n(.*?)^```", re.S | re.M)
PLACEHOLDER = re.compile(r"<(\w+)>")
PATH = re.compile(r"(?<![\w./-])((?:src|tests|scripts|translations)/[^\s`'\")\]>,;]*)")
DOTTED = re.compile(r"(?<![\w.])src(?:\.\w+)+")
INLINE = re.compile(r"`([^`\n]+)`")
INLINE_CALL = re.compile(r"\b(\w+)\(")
FIXTURE_SHAPED = re.compile(
    r"`((?:mock|make)_\w+|\w+_(?:handler|harness|client|url|service|helper))`"
)
LINE_CITATION = re.compile(r"[\w./-]+\.(?:py|ya?ml|md|txt|sh):\d+")


def read(rel_path):
    return (PROJECT_ROOT / rel_path).read_text(encoding="utf-8")


def load_skill(name):
    skill = SKILLS_DIR / name
    return {str(p.relative_to(skill)): p.read_text(encoding="utf-8") for p in sorted(skill.rglob("*.md"))}


@functools.lru_cache(maxsize=None)
def _parse(path):
    return ast.parse(path.read_text(encoding="utf-8"))


def _is_fixture(node):
    return any("fixture" in ast.unparse(d) for d in node.decorator_list)


@functools.lru_cache(maxsize=None)
def _repo_index():
    """Names used or defined in src/tests/scripts, fixtures, and real non-local names."""
    used, fixtures, nonlocal_names = set(dir(builtins)), set(), set()
    for top in ("src", "tests", "scripts"):
        in_src = top == "src"
        for path in sorted((PROJECT_ROOT / top).rglob("*.py")):
            # Only src/ trees are read again (_resolve); don't keep tests/ in the cache.
            tree = _parse(path) if in_src else ast.parse(path.read_text(encoding="utf-8"))
            if in_src:
                nonlocal_names |= set(_top_level(tree))
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    used.add(node.name)
                    if not isinstance(node, ast.ClassDef) and _is_fixture(node):
                        fixtures.add(node.name)
                elif isinstance(node, ast.Attribute):
                    used.add(node.attr)
                    if in_src and isinstance(node.ctx, ast.Store):
                        nonlocal_names.add(node.attr)
                elif isinstance(node, ast.Name):
                    used.add(node.id)
                elif isinstance(node, (ast.arg, ast.keyword)) and node.arg:
                    used.add(node.arg)
                elif isinstance(node, ast.alias):
                    used.add((node.asname or node.name).split(".")[0])
    return frozenset(used), frozenset(fixtures), frozenset(nonlocal_names)


def _top_level(tree):
    names = {}
    stack = list(tree.body)
    while stack:
        node = stack.pop()
        if isinstance(node, (ast.If, ast.Try)):
            stack += node.body + node.orelse + getattr(node, "handlers", []) + getattr(node, "finalbody", [])
        elif isinstance(node, ast.ExceptHandler):
            stack += node.body
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names[node.name] = node
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                names[(alias.asname or alias.name).split(".")[0]] = node
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                names.update((n.id, node) for n in ast.walk(target) if isinstance(n, ast.Name))
    return names


def _module_file(parts):
    base = PROJECT_ROOT.joinpath(*parts)
    for candidate in (base.with_suffix(".py"), base / "__init__.py"):
        if candidate.is_file():
            return candidate
    return None


def _class_members(module, cls):
    """Members of `cls` and its src base classes; None when a base is outside src."""
    members = set(_top_level(cls))
    for base in cls.bases:
        if not isinstance(base, ast.Name):
            return None
        node = _top_level(_parse(module)).get(base.id)
        if isinstance(node, ast.ClassDef):
            inherited = _class_members(module, node)
        elif isinstance(node, ast.ImportFrom) and (node.module or "").startswith("src"):
            target = _module_file(node.module.split("."))
            found = _top_level(_parse(target)).get(base.id) if target else None
            inherited = _class_members(target, found) if isinstance(found, ast.ClassDef) else None
        else:
            inherited = None
        if inherited is None:
            return None
        members |= inherited
    return members


def _resolve(dotted):
    """Return why `dotted` (src.a.b.Name.member) does not exist, or None."""
    parts = dotted.split(".")
    for i in range(len(parts), 0, -1):
        module = _module_file(parts[:i])
        if module:
            break
    else:
        return f"no module {dotted}"
    rest = parts[i:]
    if not rest:
        return None
    node = _top_level(_parse(module)).get(rest[0])
    if node is None:
        return f"{'.'.join(parts[:i])} has no {rest[0]}"
    if len(rest) > 1 and isinstance(node, ast.ClassDef):
        members = _class_members(module, node)
        if members is not None and rest[1] not in members:
            return f"{rest[0]} has no member {rest[1]}"
    return None


def _python_blocks(texts):
    """Yield (file, first line, tree or SyntaxError) for every ```python block."""
    for name, text in texts.items():
        for match in FENCE.finditer(text):
            if match.group(1) not in ("python", "py"):
                continue
            line = text.count("\n", 0, match.start()) + 1
            code = PLACEHOLDER.sub(r"PH_\1", textwrap.dedent(match.group(2)))
            try:
                yield name, line, ast.parse(code)
            except SyntaxError as err:
                yield name, line, err


def _known(name, pool):
    """True for a name in `pool` or a `<name>` placeholder (parsed as PH_name)."""
    return name in pool or "PH_" in name


def _local_names(trees):
    names, fixtures = set(), set()
    for tree in trees:
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                names.add(node.name)
                if not isinstance(node, ast.ClassDef) and _is_fixture(node):
                    fixtures.add(node.name)
            elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                names.add(node.id)
            elif isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Store):
                names.add(node.attr)
            elif isinstance(node, ast.arg):
                names.add(node.arg)
            elif isinstance(node, ast.alias):
                names.add((node.asname or node.name).split(".")[0])
    return names, fixtures


def _injected_params(func):
    """Parameters that @patch or @pytest.mark.parametrize fill, not fixtures."""
    params = [a.arg for a in func.args.args if a.arg != "self"]
    patches = sum(ast.unparse(d).startswith(("patch", "mock.patch")) for d in func.decorator_list)
    injected = set(params[:patches])
    for dec in func.decorator_list:
        if isinstance(dec, ast.Call) and ast.unparse(dec.func).endswith("parametrize") and dec.args:
            first = dec.args[0]
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                injected |= {p.strip() for p in first.value.split(",")}
    return params, injected


def _code_problems(texts, used, fixtures):
    blocks = list(_python_blocks(texts))
    local, local_fixtures = _local_names(t for _, _, t in blocks if isinstance(t, ast.AST))
    known_calls = used | local
    known_fixtures = fixtures | PYTEST_BUILTINS | local_fixtures
    for name, line, tree in blocks:
        if isinstance(tree, SyntaxError):
            yield f"{name}:{line + (tree.lineno or 0)}: R3 python block does not parse: {tree.msg}"
            continue
        for node in ast.walk(tree):
            at = f"{name}:{line + getattr(node, 'lineno', 0)}"
            if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("src"):
                for alias in node.names:
                    dotted = f"{node.module}.{alias.name}"
                    why = None if _known(dotted, ()) else _resolve(dotted)
                    if why:
                        yield f"{at}: R2 {dotted}: {why}"
            elif isinstance(node, ast.Call):
                func = node.func
                called = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
                if called and not _known(called, known_calls):
                    yield f"{at}: R4 call to unknown {called}"
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and (
                node.name.startswith("test_") or _is_fixture(node)
            ):
                params, injected = _injected_params(node)
                for param in params:
                    if param not in injected and not _known(param, known_fixtures):
                        yield f"{at}: R5 unknown fixture {param} in {node.name}"
    for name, text in texts.items():
        prose = FENCE.sub(lambda m: "\n" * m.group(0).count("\n"), text)
        for number, row in enumerate(prose.splitlines(), 1):
            for span in INLINE.findall(row):
                for called in INLINE_CALL.findall(PLACEHOLDER.sub(r"PH_\1", span)):
                    if not _known(called, known_calls):
                        yield f"{name}:{number}: R4 call to unknown {called}"


def skill_problems(texts):
    """Problems in one skill's Markdown files ({file name: text}), as 'file:line: rule detail'."""
    used, fixtures, nonlocal_names = _repo_index()
    problems = list(_code_problems(texts, used, fixtures))
    for name, text in texts.items():
        bash_lines = set()
        for match in FENCE.finditer(text):
            if match.group(1) in ("bash", "sh", "shell"):
                start = text.count("\n", 0, match.start()) + 1
                bash_lines |= set(range(start, start + match.group(0).count("\n") + 1))
        for number, row in enumerate(text.splitlines(), 1):
            at = f"{name}:{number}"
            for token in PATH.findall(row):
                pattern = re.search(r"[<*{]", token)
                if pattern:  # a pattern: its fixed directory part must exist
                    path = token[:pattern.start()].rsplit("/", 1)[0]
                else:
                    path = re.split(r"[:#]", token)[0].rstrip(".,")
                if not (PROJECT_ROOT / path).exists():
                    problems.append(f"{at}: R1 missing path {path}")
            for dotted in DOTTED.findall(row):
                why = _resolve(dotted)
                if why:
                    problems.append(f"{at}: R2 {dotted}: {why}")
            for fixture in FIXTURE_SHAPED.findall(row):
                if fixture not in fixtures and fixture not in nonlocal_names:
                    problems.append(f"{at}: R6 unknown fixture or name {fixture}")
            for citation in LINE_CITATION.findall(row):
                problems.append(f"{at}: R7 line citation {citation} (cite the name, not the line)")
            if number in bash_lines and "$(" in row:
                problems.append(f"{at}: R8 command substitution $( in a bash block")
    return problems


PLANTED = '''
See `src/nope.py`, `tests/nope/` and `src/handlers/<name>.py`.
```python
from src.bot.handlers.media import MediaService
patch("src.bot.handlers.media.MediaService")
async def test_x(no_such_fixture, media_handler):
    await radarr_client.check_status()
```
```python
def broken(:
```
Use `sabnzbdx_handler` and see `src/api/base.py:228`.
```bash
gh pr list --head $(git branch --show-current)
```
'''


def test_checker_flags_planted_wrong_names():
    problems = "\n".join(skill_problems({"SKILL.md": PLANTED}))
    for name in (
        "src/nope.py",
        "tests/nope/",
        "missing path src/handlers",
        "src.bot.handlers.media.MediaService",
        "check_status",
        "no_such_fixture",
        "sabnzbdx_handler",
        "base.py:228",
        "$(",
        "parse",
    ):
        assert name in problems, name
    assert "media_handler" not in problems


def test_checker_accepts_real_names_and_placeholders():
    text = (
        "See `src/api/base.py`, `src/bot/handlers/<name>.py` and `translations/addarr.<locale>.yml`.\n"
        "```python\n"
        'patch("src.bot.handlers.media.handler.MediaService")\n'
        "class <Name>Client(BaseApiClient):\n"
        "    async def search(self, term):\n"
        '        return await self._make_request("<endpoint>/lookup", params={"term": term})\n'
        "async def test_y(media_handler, make_update, monkeypatch, <name>_handler):\n"
        "    await <name>_helper()\n"
        "```\n"
    )
    assert skill_problems({"SKILL.md": text}) == []


@pytest.mark.parametrize("skill", CHECKED_SKILLS)
def test_skill_names_exist(skill):
    assert skill_problems(load_skill(skill)) == []


CI_JOBS = ("lint", "type-check", "validate-translations", "unit-test", "integration-test", "architecture-test")


def ci_commands():
    """The check commands of the CI jobs that preflight mirrors (the HTML report is an upload artifact)."""
    jobs = yaml.safe_load(read(".github/workflows/ci.yml"))["jobs"]
    # Each job's last `run` step is its check; the earlier ones install dependencies.
    return [
        re.sub(r" --cov-report=html:\S+", "", [s["run"] for s in jobs[job]["steps"] if "run" in s][-1])
        for job in CI_JOBS
    ]


def local_command(ci_command):
    """The CI command run with the project interpreter `<py>`, as preflight.md writes it."""
    if ci_command.startswith("python "):
        return "<py> " + ci_command[len("python "):]
    return "<py> -m " + ci_command


def test_preflight_runs_the_ci_commands():
    preflight = read(".claude/skills/addarr-workflow/references/preflight.md")
    for command in map(local_command, ci_commands()):
        assert command in preflight, command


def test_workflow_coverage_commands_match_ci():
    unit = local_command(next(c for c in ci_commands() if "--cov-fail-under" in c))
    for name, text in load_skill("addarr-workflow").items():
        for line in text.splitlines():
            if "--cov=" in line:
                assert unit in line, f"{name}: {line}"

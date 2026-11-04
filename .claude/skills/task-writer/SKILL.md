---
name: task-writer
description: Break down features into sized tasks with TDD ordering. Use when planning a new feature, creating implementation tasks, updating TASKS.md, estimating effort, or organizing multi-step work into phases.
---

# Task Writer

Bundle related work (handler, service, API client, tests) into one logical unit. Split by integration boundaries, not files.

## Task Sizing

| Feature Size | Files | Task Count | Split |
|---|---|---|---|
| Small | 1-3 | 1 task | Don't split |
| Medium | 4-8 | 2-3 tasks | Service/API → Handler → Integration |
| Large | 8+ | 3-4 tasks | By logical layer |

## Task Format

```markdown
### Phase N: Feature Name (X tasks)

**Goal:** One sentence.

- [ ] **N.1** Implement [feature/layer]
    - **Context:**
        - **Why:** [business problem]
        - **Architecture:** [pattern to follow]
        - **Key refs:** [file:line]
        - **Watch out:** [gotchas]
    - **Scope:** Brief description
    - **Touches:** Key files
    - **Action items:**
        - [RED] Write pytest tests for [behavior]
        - [GREEN] Implement to make tests pass
    - **Success:** Tests pass, type-check passes
```

Action items MUST list [RED] tests before [GREEN] implementation.

## TDD Within Tasks

1. [RED] Write failing pytest test
2. Run: `pytest tests/path/test.py::test_name -v` — confirm fails
3. [GREEN] Minimal implementation
4. Run: `pytest tests/path/test.py -v` — confirm passes
5. Commit

## Decision Framework

| Question | Answer |
|---|---|
| Small change (1-3 files)? | One task, includes everything |
| Medium feature (4-8 files)? | 2-3 tasks: service/API → handler → integrate |
| Large feature (8+ files)? | 3-4 tasks split by logical layer |
| Needs manual Telegram testing? | Separate verification step |
| Architectural uncertainty? | Stop and ask before implementing |
| Trivial (1-line change)? | Don't create task, just do it |

## Context Blocks

Compact mode when executing in same session:
```
- **Context:** See plan.md Phase N. Key refs: `file.py:line`
- **Watch out:** [non-obvious gotchas]
```

Full context block required when task may be picked up after context loss.

## Conventions

- Use `- [ ]` / `- [x]`
- Number as Phase.Task (e.g., 3.2)
- Success criteria required
- File paths indicative, not exhaustive
- Test counts underestimate by ~1.5x; plan for edge cases.

## References

- Handlers: `src/bot/handlers/`, states in `src/bot/states.py`
- Services: `src/services/`, singletons via `__new__`
- API clients: `src/api/`, inherit `BaseApiClient`, implement `search()`
- Tests: `tests/` mirroring `src/`, pytest + aioresponses for HTTP
- Config: `config.get("key", {})`, never `config["key"]` in business logic
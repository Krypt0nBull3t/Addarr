---
name: task-writer
description: Break down features into sized tasks with TDD ordering. Use when planning a new feature, creating implementation tasks, updating TASKS.md, estimating effort, or organizing multi-step work into phases.
---

# Task Writer Skill

## Core Philosophy

**Feature-focused tasks:** Bundle related work (types, components, tests, API) into one logical unit. Split by integration boundaries, not by files.

## Task Sizing Rules

| Feature Size | Files | Task Count | How to Split                         |
| ------------ | ----- | ---------- | ------------------------------------ |
| Small        | 1-3   | 1 task     | Don't split                          |
| Medium       | 4-8   | 2-3 tasks  | Backend → Frontend → Integration     |
| Large        | 8+    | 3-4 tasks  | By logical layer (see below)         |

### Splitting Large Features by Layer

Split by **integration boundaries**, not files:

```
Phase: [Large Feature] (3-4 tasks)

- [ ] 1.1 Backend logic layer
      → Models, Actions, API endpoints, unit tests
      → Success: pest tests pass

- [ ] 1.2 Frontend domain layer
      → Types, store, repository, components
      → Success: vitest tests pass

- [ ] 1.3 User interface layer
      → Pages, modals, route wiring
      → Success: feature accessible in browser

- [ ] 1.4 Integration testing
      → E2E tests, manual verification
      → Success: full flow works
```

## Task Format

```markdown
### Phase N: Feature Name (X tasks)

**Goal:** One sentence describing what this phase delivers.

**Phase Context:** (only if needed for phase-level decisions)

- Why NOT [alternative]: [Key decision that's not obvious from code]

- [ ] **N.1** Implement [feature/layer]
    - **Context:** (REQUIRED - enables standalone task pickup)
        - **Why:** [Business problem this solves - what triggered this task]
        - **Architecture:** [How it fits in, which pattern to follow]
        - **Key refs:** [Specific file:line references to understand entry points]
        - **Watch out:** [Edge cases, gotchas, things that aren't obvious]
    - **Scope:** Brief description of what's included
    - **Touches:** Key files (not exhaustive, just main ones)
    - **Action items:**
        - [RED] Write tests for [specific behavior 1]
        - [RED] Write tests for [specific behavior 2]
        - [GREEN] Implement [component] to make tests pass
        - [GREEN] Integrate into [existing code]
    - **Success:** Tests pass, type-check passes, [specific behavior works]
```

**CRITICAL:**

- Action items MUST list [RED] test-writing steps BEFORE [GREEN] implementation steps
- **Context block is REQUIRED** for every implementation task

## What Goes IN a Single Task

Bundle these together (one logical unit):

**Backend task:**
- Model changes / migrations
- Action classes
- API endpoints (Controller)
- Pest unit tests

**Frontend task:**
- TypeScript types
- Store and repository
- Vue components
- Vitest tests

## What Triggers a New Task (Approval Gates)

Create separate tasks only at these boundaries:

1. **Layer complete** - Backend done, ready for frontend layer
2. **Ready for manual testing** - Need to verify in browser
3. **Architectural decision needed** - Multiple valid approaches
4. **Risk boundary** - If next step could break things, checkpoint first

## TDD Within Tasks

TDD happens INSIDE each task. Action items ordered: tests first, then implementation.

```
Task: Implement client financing tab
  ↓
  Action items (in this order):
    [RED]   1. Write Vitest tests for store methods
    [RED]   2. Write Vitest tests for component rendering
    [GREEN] 3. Implement store to make tests pass
    [GREEN] 4. Implement Vue components
  ↓
  Run all tests, verify passing
  ↓
Task complete
```

**Rules:**

1. Action items MUST list [RED] steps before [GREEN] steps
2. Frontend tests: use `vue-vitest-testing` skill patterns
3. Backend tests: use Pest with appropriate TestCase

## Task Conventions

- Use `- [ ]` for incomplete, `- [x]` for complete
- Number as Phase.Task (e.g., 3.2)
- **Success criteria required** - Each task must define "done"
- Keep descriptions concise
- File paths indicative, not exhaustive

## Decision Framework

| Question                       | Answer                                    |
| ------------------------------ | ----------------------------------------- |
| Small change (1-3 files)?      | One task, includes everything             |
| Medium feature (4-8 files)?    | 2-3 tasks: backend → frontend → integrate |
| Large feature (8+ files)?      | 3-4 tasks split by logical layer          |
| Needs manual browser testing?  | Separate verification step                |
| Architectural uncertainty?     | Stop and ask before implementing          |
| Trivial (1-line change)?       | Don't create task, just do it             |

## Self-Verification

Before finalizing tasks, check:

1. Is each task a complete logical unit (not just one file)?
2. Do action items list [RED] tests BEFORE [GREEN] implementation?
3. Does each task have clear success criteria?
4. Are approval gates only at natural boundaries?
5. Is the task count appropriate for the feature size?
6. **Can this task be picked up after context loss?** (Context block complete?)

## Output

**Only modify `TASKS.md`** - never create separate files.

## Examples

### Small Feature (Frontend Only)

```markdown
### Phase 3: Add Client Status Badge (1 task)

**Goal:** Display client status as colored badge in overview.

- [ ] **3.1** Implement status badge component
    - **Context:**
        - **Why:** Users can't quickly see client status in list view
        - **Architecture:** Shared component in `shared/components/`, follows IconButton pattern
        - **Key refs:** `user/domains/client/pages/Overview.vue:45` where badge should appear
        - **Watch out:** Status enum from `enums/ClientStatus.ts`, colors must match design system
    - **Scope:** Badge component, integration into client overview
    - **Touches:** `shared/components/StatusBadge.vue`, `user/domains/client/pages/Overview.vue`
    - **Action items:**
        - [RED] Write Vitest tests for badge rendering per status
        - [RED] Write Vitest tests for Overview with badge
        - [GREEN] Implement StatusBadge component
        - [GREEN] Integrate into Overview page
    - **Success:** Tests pass, badge shows correct color per status
```

### Medium Feature (Backend + Frontend)

```markdown
### Phase 4: Client Notes Feature (3 tasks)

**Goal:** Allow users to add private notes to clients.

- [ ] **4.1** Backend API
    - **Context:**
        - **Why:** Users need to track private observations about clients
        - **Architecture:** Tenant model, Action class pattern, API resource
        - **Key refs:** `Models/Customer/ClientNotation.php` as similar pattern
        - **Watch out:** Notes are per-user (not shared), soft delete required
    - **Scope:** Migration, Model, Action, Controller, API routes
    - **Touches:** `Models/Customer/Note.php`, `Actions/Model/Note/`, `Http/Controllers/Api/NoteController.php`
    - **Action items:**
        - [RED] Write Pest tests for Note model and actions
        - [RED] Write Pest tests for API endpoints
        - [GREEN] Implement model, migration, actions
        - [GREEN] Implement controller and routes
    - **Success:** Pest tests pass, API returns notes

- [ ] **4.2** Frontend domain
    - **Context:**
        - **Why:** Connect frontend to new notes API
        - **Architecture:** Domain pattern in `user/domains/note/`
        - **Key refs:** `user/domains/tags/` as similar simple domain
        - **Watch out:** Optimistic updates for better UX
    - **Scope:** Types, store, repository, note components
    - **Touches:** `user/domains/note/`
    - **Action items:**
        - [RED] Write Vitest tests for store CRUD operations
        - [RED] Write Vitest tests for NoteCard component
        - [GREEN] Implement types, store, repository
        - [GREEN] Implement NoteCard and NoteList components
    - **Success:** Vitest tests pass, components render

- [ ] **4.3** Integration into client page
    - **Context:**
        - **Why:** Notes should appear in client detail view
        - **Architecture:** New tab in client tabs structure
        - **Key refs:** `user/domains/client/tabs/` for tab pattern
        - **Watch out:** Load notes when tab becomes active, not on page load
    - **Scope:** Notes tab, route wiring, client page integration
    - **Touches:** `user/domains/client/tabs/notes/`, `user/domains/client/routes.ts`
    - **Action items:**
        - [GREEN] Create notes tab page
        - [GREEN] Wire into client tabs and routes
        - [GREEN] Manual verification in browser
    - **Success:** Notes tab works, can CRUD notes for client
```

**Remember:** Tasks should be large enough to be meaningful, small enough to be recoverable if something goes wrong.

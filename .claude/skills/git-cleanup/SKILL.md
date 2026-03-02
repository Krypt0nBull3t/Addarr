---
name: git-cleanup
description: Use when cleaning up accumulated local git branches and worktrees. Safely categorizes branches as merged, squash-merged, superseded, or active work with two confirmation gates before deletion.
---

# Git Cleanup

Safely clean up accumulated git worktrees and local branches by categorizing them into: safely deletable (merged), potentially related (similar themes), and active work (keep). Adapted from [Trail of Bits' git-cleanup skill](https://github.com/trailofbits/skills).

## When to Use

- Accumulated many local branches and worktrees
- Branches merged but not cleaned up locally
- Remote branches deleted but local tracking branches remain

## When NOT to Use

- Remote branch management (local cleanup only)
- Repository maintenance tasks like gc or prune

## Core Principle: SAFETY FIRST

**Never delete anything without explicit user confirmation.** Two-gate workflow: analysis review, then deletion confirmation.

## Workflow

### Phase 1: Comprehensive Analysis

```bash
# Get default branch
default_branch=$(git symbolic-ref refs/remotes/origin/HEAD \
  2>/dev/null | sed 's@^refs/remotes/origin/@@' || echo "main")

# Protected branches - never delete
protected='^(main|master|development|release/.*)$'

# List branches with tracking info + worktrees
git branch -vv
git worktree list

# Sync remote state
git fetch --prune

# Merged branches and recent PR history
git branch --merged "$default_branch"
git log --oneline "$default_branch" | grep -iE "#[0-9]+" | head -30

# Per-branch analysis
for branch in $(git branch --format='%(refname:short)' \
  | grep -vE "$protected"); do
  echo "=== $branch ==="
  git log --oneline "$default_branch".."$branch" 2>/dev/null | head -5
  git log --oneline "origin/$branch".."$branch" 2>/dev/null | head -5 || echo "(no remote)"
done
```

### Phase 2: Group Related Branches

Before individual categorization, group by shared prefixes:

```bash
git branch --format='%(refname:short)' | sed 's/-[^-]*$//' | sort | uniq -c | sort -rn
```

For each group (2+ branches): compare commit histories, find merge evidence, identify the "final" branch, mark superseded branches.

**SUPERSEDED requires evidence** — a PR merged the work into main, OR a newer branch contains all commits. Name prefix alone is NOT sufficient.

### Phase 3: Categorize Remaining Branches

| Category | Meaning | Delete Command |
|----------|---------|----------------|
| SAFE_TO_DELETE | Merged into default branch | `git branch -d` |
| SQUASH_MERGED | Work incorporated via squash merge | `git branch -D` |
| SUPERSEDED | Part of group, work verified in main | `git branch -D` |
| REMOTE_GONE | Remote deleted, work NOT in main | Review needed |
| UNPUSHED_WORK | Has commits not pushed to remote | Keep |
| LOCAL_WORK | Untracked branch with unique commits | Keep |
| SYNCED_WITH_REMOTE | Up to date with remote | Keep |

### Phase 4: Dirty State Detection

Check ALL worktrees for uncommitted changes:

```bash
git -C <worktree-path> status --porcelain
git status --porcelain
```

Display warnings prominently for any dirty worktrees.

### GATE 1: Present Complete Analysis

Present ONE comprehensive view with related branch groups, individual branches by category, worktree status, and summary counts. Use `AskUserQuestion` with options:
- Delete all recommended
- Delete specific groups/categories
- Pick individual branches

**Do not proceed until user responds.**

### GATE 2: Final Confirmation with Exact Commands

Show the EXACT commands that will run with correct flags (`-d` for merged, `-D` for squash-merged/superseded). **This is the ONLY deletion confirmation needed.**

### Phase 5: Execute

Run each deletion as a **separate command** so partial failures don't block remaining deletions.

### Phase 6: Report

Show deleted branches, remaining branches, and any errors encountered.

## Safety Rules

1. **Never invoke automatically** — Only when user explicitly requests cleanup
2. **Two confirmation gates only** — Analysis review, then deletion confirmation
3. **Correct delete flags** — `-d` for merged, `-D` for squash-merged/superseded
4. **Never touch protected branches** — main, master, development, release/*
5. **Block dirty worktree removal** — Refuse without explicit data loss acknowledgment
6. **Group related branches** — Don't scatter them across categories

## Squash-Merged Branches

`git branch -d` will ALWAYS fail for squash-merged branches because git cannot detect the work was incorporated. Plan to use `git branch -D` from the start — don't try `-d` first.

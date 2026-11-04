# End Flow (Save): Step Details

Sequence is defined in SKILL.md. This flow pauses an issue so it can resume later, on this machine or another. It has one mode, save. To finish an issue, use `/addarr pr`.

## Step 1: Detect the Issue

Take `<N>` from the argument (`/addarr end <N>`) or the branch name `<prefix>/<N>-<slug>`; without either, `ASK`. On `development` or `main` there is nothing to save: report and stop.

## Step 2: Write the Pause Note

Find the task in progress in `docs/issues/issue-<N>/TASKS.md` (the first unchecked task) and add this note under it:

```markdown
    - **Session paused:** <YYYY-MM-DD HH:MM>
    - **Status:** <where the work stands>
    - **Next step:** <the first thing to do on resume>
    - **Open questions:** <decisions or questions still open, or "none">
```

Before `TASKS.md` exists (paused during planning), put the note at the top of `docs/issues/issue-<N>/plan.md`, or of `design.md` when that is the only file.

## Step 3: WIP Commit

Stage only the files you changed and the note file (never `git add .` or `git add -A`); leave out files that are not yours and report them. Check `git diff --cached`, then commit:

```bash
git commit -m "wip: pause issue-<N> at task <id>"
```

## Step 4: Push

Check for an open PR first:
```bash
gh pr view --repo Krypt0nBull3t/Addarr --json number,state
```

With an open PR, a push runs CI and the review bot again. `ASK`: push now, or keep the commit local and push with the next round.

Push:
```bash
<lock> git push -u origin <branch-name>
```

## Step 5: Report

```
Session saved
  Branch: <branch-name>
  Last task: <id and title>
  Next step: <from the note>
  Resume: check out the branch, then /addarr continue <N>
```

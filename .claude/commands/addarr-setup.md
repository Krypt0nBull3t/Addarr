Load skills for an Addarr development session. Invoke each skill listed below using the Skill tool. Do NOT summarize or skip any — invoke them all sequentially.

Argument: $ARGUMENTS

## Skill sets

### Always load (all setups):
- `addarr-testing`
- `addarr-handlers`
- `addarr-services`
- `python-testing-pro`

### If argument is `dev` (or no argument):
- `task-writer`
- `find-bugs`
- `code-simplifier`
- `superpowers:test-driven-development`
- `superpowers:writing-plans`
- `superpowers:brainstorming`
- `superpowers:systematic-debugging`
- `superpowers:verification-before-completion`

### If argument is `pr`:
- `find-bugs`
- `code-simplifier`
- `superpowers:verification-before-completion`

Also read these reference files into context (use the Read tool):
- `.claude/skills/addarr-workflow/references/create-pr.md`
- `.claude/skills/addarr-workflow/references/preflight.md`

### If argument is `feedback`:
- `superpowers:receiving-code-review`
- `superpowers:systematic-debugging`
- `superpowers:verification-before-completion`

Also read these reference files into context (use the Read tool):
- `.claude/skills/addarr-workflow/references/feedback.md`

### If unrecognized argument:
Ask the user which setup they want: `dev`, `pr`, or `feedback`.

## After loading

Confirm which skills were loaded and say you're ready to start.

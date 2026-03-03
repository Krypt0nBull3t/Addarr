#!/bin/bash
# Pre-tool hook: Validates Bash commands against Addarr shell conventions.
# Blocks commands that use banned patterns to avoid permission prompts.
# See CLAUDE.md "Shell Conventions" section.

# Read JSON from stdin
input=$(cat)

# Extract the command field using python (jq not available on this system)
command=$(echo "$input" | python -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('command',''))" 2>/dev/null)

# If no command found, allow (non-Bash tool or empty)
if [ -z "$command" ]; then
  exit 0
fi

# 1. Block $() command substitution
if echo "$command" | grep -qP '\$\('; then
  echo "BLOCKED: \$() command substitution is banned. Write output to a temp file first, then reference it. Example: write commit msg to /tmp/msg.txt, then use 'git commit -F /tmp/msg.txt'" >&2
  exit 2
fi

# 2. Block backtick command substitution
if echo "$command" | grep -qP '`[^`]+`'; then
  echo "BLOCKED: Backtick command substitution is banned. Write output to a temp file first, then reference it." >&2
  exit 2
fi

# 3. Block cd && pattern (cd followed by && anywhere)
if echo "$command" | grep -qP '^\s*cd\s.*&&'; then
  echo "BLOCKED: 'cd && command' pattern is banned. Use absolute paths or 'git -C <path>' instead." >&2
  exit 2
fi

# 4. Block bare find command (should use Glob tool)
if echo "$command" | grep -qP '(^|\|)\s*find\s'; then
  echo "BLOCKED: 'find' via Bash is banned. Use the Glob tool instead." >&2
  exit 2
fi

# 5. Block bare grep/rg commands (should use Grep tool)
if echo "$command" | grep -qP '(^|\|)\s*(grep|rg)\s'; then
  echo "BLOCKED: 'grep'/'rg' via Bash is banned. Use the Grep tool instead." >&2
  exit 2
fi

# 6. Block backslash escapes (prefer quotes over escaping spaces/special chars)
if echo "$command" | grep -qP '\\[ !@#&()|;]'; then
  echo "BLOCKED: Backslash escapes are banned. Use quotes instead of escaping spaces/special characters." >&2
  exit 2
fi

# All checks passed
exit 0

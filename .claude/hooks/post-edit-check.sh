#!/bin/bash
# PostToolUse hook: lints edited Python files and validates translations.
# Exit 2 sends the output back to Claude so it fixes the problem at once.

file=$(jq -r '.tool_input.file_path // empty')
cd "$CLAUDE_PROJECT_DIR" || exit 0

# Prefer the project venv; cloud sessions install deps into the system python.
python=python
[ -x .venv/bin/python ] && python=.venv/bin/python

case "$file" in
  "$CLAUDE_PROJECT_DIR"/translations/*.yml)
    out=$(PYTHONIOENCODING=utf-8 "$python" run.py --validate-i18n 2>&1)
    # The validator always exits 0, so check for its success line instead.
    if ! grep -q "All translations are valid" <<< "$out"; then
      echo "$out" >&2
      exit 2
    fi
    ;;
  "$CLAUDE_PROJECT_DIR"/*.py)
    "$python" -c "import flake8" 2>/dev/null || exit 0
    "$python" -m flake8 "$file" >&2 || exit 2
    ;;
esac
exit 0

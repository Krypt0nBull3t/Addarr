#!/bin/bash
# Cloud environment setup for Claude Code browser sessions.
# Runs once when a new session starts, before Claude Code launches.
# Skip if running locally (dependencies already installed).

if [ "$CLAUDE_CODE_REMOTE" != "true" ]; then
  exit 0
fi

set -e

echo "Installing project dependencies..."
pip install -q -r requirements.txt

echo "Installing test dependencies..."
pip install -q -r requirements-test.txt

echo "Verifying tools..."
python -m flake8 --version
python -m pytest --version
python -m mypy --version

echo "Cloud environment ready."

#!/bin/bash
# Cloud environment setup for Claude Code browser sessions.
# Runs once when a new session starts, before Claude Code launches.
# Skip if running locally (dependencies already installed).

if [ "$CLAUDE_CODE_REMOTE" != "true" ]; then
  exit 0
fi

set -e

# Install GitHub CLI
if ! command -v gh &> /dev/null; then
  echo "Installing GitHub CLI..."
  apt-get update -qq && apt-get install -y -qq gh > /dev/null 2>&1
fi

# Authenticate gh if GH_TOKEN is set (add as secret in web environment settings)
if [ -n "$GH_TOKEN" ]; then
  echo "Authenticating GitHub CLI..."
  echo "$GH_TOKEN" | gh auth login --with-token
fi

echo "Installing project dependencies..."
pip install -q -r requirements.txt

echo "Installing test dependencies..."
pip install -q -r requirements-test.txt

echo "Verifying tools..."
python -m flake8 --version
python -m pytest --version
python -m mypy --version
gh --version

echo "Cloud environment ready."

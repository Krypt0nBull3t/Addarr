# Issue #100: Remove built-in packages from requirements.txt

## Context

`requirements.txt` includes `asyncio>=3.4.3` and `dataclasses>=0.6`, which are stdlib modules in Python 3.11 (our target runtime per Dockerfile). These are unnecessary dependency declarations.

## Analysis

- `asyncio` — stdlib since Python 3.4. The PyPI package is a no-op shim.
- `dataclasses` — stdlib since Python 3.7. The PyPI package is a backport.
- `typing-extensions` — investigated but **keep**: required by `transmission-rpc` (a transitive dependency).

## Changes

1. Remove `asyncio>=3.4.3` line from `requirements.txt`
2. Remove `dataclasses>=0.6` line from `requirements.txt`
3. Clean up the "Async support" and "Data handling" section comments if they become empty or misleading
4. Verify: pytest passes, flake8 passes, i18n validation passes

## Risk

None — these packages are no-op shims on Python 3.11+. Removing them changes nothing at runtime.

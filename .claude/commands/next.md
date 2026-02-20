Continue working through TASKS.md:

1. Read the TASKS.md file to check task status
2. Find the next uncompleted task (not marked with `[x]`)
3. Before starting work, check if one of these skills applies to the task:
    - `addarr-testing` - Testing patterns for async Telegram bot handlers, aiohttp API clients, and singleton services
    - `python-testing-pro` - Python testing strategies using pytest, TDD methodology, fixtures, mocking
    - `task-writer` - Breaking down features into sized tasks with TDD ordering
    If a skill applies, invoke it first.

4. Complete the task
5. Mark the task as completed in TASKS.md by changing `[ ]` to `[x]`
6. **Add completion metadata below the task:**
    - **Learnings:** Key insights, gotchas, or discoveries from this task
    - **Key Changes:** Summary of what was modified (files, functions, patterns)
    - **Notes:** Any important context for future work

7. Report what was done

**Example completion format:**

```markdown
- [x] **1.1** Implement price cache with batch fetching
    - [existing task content...]
    - **Completed:** 2026-01-10
    - **Learnings:**
        - Cache TTL of 2s balances freshness vs RPC savings (75% reduction in monitoring calls)
        - `getMultipleAccountsInfo` has 100-account limit, sufficient for current multi-pod setup
        - Cache key must include pool address to avoid collisions across pods
    - **Key Changes:**
        - Created `src/utils/price-cache.ts` with TTL-based caching
        - Added `fetchMultipleVaultAccounts()` in `src/amm/raydium-v4.ts`
        - Modified `fetchPrices()` to use batch fetch + cache
    - **Notes:** Monitor via logging to verify cache hit rate in production
```

If all tasks are completed, summarize the work done and ask if there's anything else needed.

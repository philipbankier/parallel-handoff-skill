# Error Handling

Common errors and how to respond.

## Common Errors

| Error | Response |
|-------|----------|
| **Agent CLI not installed** | Tell user how to install: `npm install -g @openai/codex` for Codex |
| **Agent CLI exits with error** | Show error output, attempt correction in next iteration |
| **No git repo** | Warn that review will be limited (no diff), proceed anyway |
| **No tmux** | Install tmux or use non-interactive mode |
| **No plan found** | Tell user to create a plan first or provide inline |
| **Tests not configured** | Skip test step, review based on diff only |
| **Agent hangs (>10min)** | Normal for large tasks — wait. Kill after timeout. |
| **Worker scope violation** | Reject branch, send correction prompt |
| **Merge conflict during integration** | Resolve in main worktree, not worker checkout |
| **Changelog missing from worker** | Send back for changelog update before accepting |

## Per-Worker Error Recovery

Each worker has its own supervisor loop. If a worker fails:

1. **Capture output** — `python3 scripts/worker_manager.py capture <name>`
2. **Diagnose** — check exit code, error messages, diff
3. **Correct** — build specific correction prompt addressing failures
4. **Re-run** — send correction to same worker
5. **Escalate** — after max iterations, mark partial and report

A failing worker does NOT block other parallel workers. Each one loops independently.

## Troubleshooting

### "command not found: codex"

```bash
npm install -g @openai/codex
codex --version
```

### "command not found: tmux"

```bash
# macOS
brew install tmux

# Ubuntu/Debian
sudo apt install tmux
```

### Agent produces incorrect output

This is expected — the supervisor loop handles it. The review step detects issues and builds a correction prompt. If issues persist after max iterations, the final report lists remaining items.

### Permission errors

Codex uses `-s workspace-write` by default. If broader permissions needed, run those steps manually before/after handoff.

### Agent modifies files outside scope

The review catches this. Flag in scorecard, include in correction prompt with instructions to revert unplanned changes. If repeated, reject the worker.

### Worktree creation fails

```bash
# Check for existing worktrees
git worktree list

# Prune stale worktrees
git worktree prune

# Remove specific worktree
git worktree remove /path/to/worktree
```

### Parallel worker conflicts

Workers should have disjoint write scopes. If a conflict is discovered during integration:
1. Review both branches
2. Accept the better implementation
3. Manually merge the complementary parts
4. Record the conflict resolution in the final report

### Disk space issues

Check available space before spawning workers, especially for large repos:
```bash
df -h .
```

### Secrets in worker output

Workers should never print or commit secrets. If discovered in a diff:
1. Reject the branch
2. Tell the worker to remove secrets
3. Use git's sensitive file removal if already committed

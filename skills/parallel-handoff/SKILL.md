---
name: parallel-handoff
description: |
  Plan → parallel workers in git worktrees → per-worker supervisor loop → review → integrate.
  Use when: user says "hand off to codex", "run parallel workers", "parallel handoff",
  "implement this plan", "parallelize these tasks", "use multiple agents",
  runs /parallel-handoff, or has a plan ready for automated execution with one or more
  CLI agent harnesses. Combines parallel-agent-worktree-skill + codex-handoff-skill.
license: MIT
compatibility: Requires git, tmux, and a CLI agent harness (Codex CLI recommended). Python 3 for helper scripts.
metadata:
  version: "0.1.0"
  author: Philip Bankier
allowed-tools: Bash Read Glob Grep
---

# Parallel Handoff

Coordinator supervises. CLI agents execute. Workers run in isolated git worktrees, each
with its own supervisor loop (execute → review → decide → loop). Works with Codex CLI,
Claude Code, OpenCode, Pi, or any CLI agent harness.

**Announce at start:** "Using parallel-handoff to orchestrate execution."

## Non-Negotiables

- Verify the selected agent harness with `<cli> --help` during preflight. Never assume flags.
- Every worker gets its own branch and git worktree. Never share checkouts.
- Do not spawn workers until you understand enough code to write bounded task prompts.
- Do not trust worker summaries. Review diffs, run tests, inspect files.
- Protect user work. Check for uncommitted changes; never overwrite what you didn't create.
- Integrate only reviewed work. Reject incomplete or speculative output.
- Every worker must update the changelog or write a unique fragment.
- Final integration merges back to the branch checked out at preflight.
- For infrastructure work, use deterministic loops with backup gates.

## Gotchas

- Codex `--full-auto` can delete or overwrite files — always review diffs before integrating
- Worktrees on macOS (case-insensitive) may behave differently than Linux (case-sensitive) — check file names
- tmux sessions persist after agent crashes — check `tmux ls` and clean up stale sessions
- Agent CLI flags change between versions — always verify with `<cli> --help` during preflight
- Codex `--full-auto` does NOT require `-s workspace-write` — that's an older flag
- Git worktrees share the same `.git` directory — hooks and config affect all worktrees
- Parallel workers editing the same lockfile (package-lock.json, etc.) will cause merge conflicts — assign lockfile ownership to one worker

## Execution Modes

| Mode | When | Flow |
|------|------|------|
| **Single-pass** | Simple plan, no phases, 1 worker | Plan → 1 worker → review → report |
| **Phased** | Multi-phase plan, sequential | Phase N → worker → loop → Phase N+1 |
| **Parallel** | Independent tasks, 1 phase | Plan → N workers → review all → integrate |
| **Phased+Parallel** | Multi-phase with parallel tasks | Per phase: fan out N workers → review → next phase |
| **Deterministic** | Infrastructure, backups needed | JSON plan → generated script → audit → run |

Select automatically from plan structure, or accept `--mode` override.

## Preflight

```sh
git status --short --branch
git rev-parse --show-toplevel
git branch --show-current
command -v tmux
AGENT_CLI="${AGENT_CLI:-codex}"
AGENT_INTERACTIVE_ARGS="${AGENT_INTERACTIVE_ARGS:---full-auto}"
AGENT_NONINTERACTIVE_ARGS="${AGENT_NONINTERACTIVE_ARGS:---full-auto}"
command -v "$AGENT_CLI"
"$AGENT_CLI" --help
```

Classify uncommitted changes: unrelated → leave alone, needed by workers → include diff
in prompts. If not a git repo, stop and use non-worktree approach.

Set shared variables:
```sh
PROJECT_DIR="$(git rev-parse --show-toplevel)"
INTEGRATION_BRANCH="$(git branch --show-current)"
BASE_REF="$INTEGRATION_BRANCH"
WORKTREE_ROOT="${PROJECT_DIR}.worktrees"
```

Find changelog convention:
```sh
find "$PROJECT_DIR" -maxdepth 3 \( -iname 'CHANGELOG*' -o -path '*/changes/*' \) -print
```

## Locate The Plan

Search in order: user argument → `docs/plans/*.md` → `.claude/plans/*.md`. Scan for phase
headings (`## Phase N:`, `## Stage N:`). Phases found → phased mode. No phases → single-pass.

## Plan The Work

Read enough of the repo to write bounded task cards. For each worker:

```
Task:
Branch/worktree name:
Owned files or modules:
May read:
Must not edit:
Goal:
Acceptance criteria:
Verification commands:
Changelog path or fragment:
Integration risk:
Dependencies:
```

Choose parallel tasks only when write scopes are disjoint. Read [task-planning.md](references/task-planning.md) for details.

## Build The Prompt

Read [prompt-templates.md](references/prompt-templates.md) for full templates.

- **Single-pass / phased:** Initial execution prompt or phase-scoped prompt.
- **Parallel worker:** Task card prompt with ownership boundaries.
- **Correction (re-run):** Specific remaining items + errors to fix.

Include project context (working dir, package manager, test/build commands, coding standards).

## Spawn Workers

Each worker gets its own tmux session and git worktree. Use the helper script:

```sh
python3 scripts/worker_manager.py spawn <name> \
  --base "$BASE_REF" \
  --prompt-file /tmp/<name>.prompt \
  --agent-cli "$AGENT_CLI" \
  --agent-args "$AGENT_INTERACTIVE_ARGS"
```

Manual fallback:
```sh
git worktree add "$WORKTREE_ROOT/$NAME" -b "$NAME" "$BASE_REF"
tmux new-session -d -s "worker-$NAME" -x 200 -y 50 \
  "cd '$WORKTREE_ROOT/$NAME' && $AGENT_CLI $AGENT_INTERACTIVE_ARGS"
```

## Supervisor Loop (Per Worker)

Each worker runs independently through this loop:

1. **Execute** — Send prompt to agent CLI
2. **Review** — Diff, tests, scorecard (see [review-process.md](references/review-process.md))
3. **Decide:**
   - All items DONE + tests pass → worker complete
   - Items remain AND iterations < max → build correction prompt, re-run
   - Max iterations reached → mark worker as partial, report

Phased mode: the loop runs per-phase. `--max-iterations N` applies per-phase (default 5).

Monitor workers:
```sh
python3 scripts/worker_manager.py status
python3 scripts/worker_manager.py capture <name> --lines 120
```

Send follow-ups:
```sh
python3 scripts/worker_manager.py send <name> --prompt-file /tmp/<name>-fix.prompt
```

## Review Worker Output

For each worker:
```sh
WT="$WORKTREE_ROOT/<name>"
git -C "$WT" diff --stat "$BASE_REF"...HEAD
git -C "$WT" diff "$BASE_REF"...HEAD
git -C "$WT" log --oneline "$BASE_REF"..HEAD
```

Run the worker's verification commands in that worktree. Apply scorecard:

| Status | Meaning |
|--------|---------|
| DONE | Implemented correctly, tested |
| PARTIAL | Started but incomplete |
| MISSING | Not attempted |
| ERRORS | Test failures, build errors |

Decision: Accept (scoped + correct + tested + changelog) → Send back → Reject.

Read [review-process.md](references/review-process.md) for the full checklist.

## Integrate

Return to main worktree, confirm clean:
```sh
git status --short --branch
test "$(git branch --show-current)" = "$INTEGRATION_BRANCH"
```

Merge accepted work:
```sh
git merge --no-ff <worker-branch>     # whole branch
git cherry-pick <commit-sha>           # selected commits
```

Reconcile all changelog fragments into the canonical changelog. Run repo-level checks.

Read [integration.md](references/integration.md) for conflict handling and merge strategies.

## Cleanup

```sh
python3 scripts/worker_manager.py cleanup <name> --branch-delete
git worktree prune
```

Use `--branch-delete` for merged branches. Keep branches if in doubt.

## Final Report

```
## Parallel Handoff Complete

Mode: {single-pass | phased | parallel | phased+parallel | deterministic}
Workers: {N} spawned, {M} accepted, {K} rejected
Total iterations: {sum across all workers}

### Worker Results
- worker-1: ACCEPTED (3 iterations) — {summary}
- worker-2: PARTIAL (5 iterations, max reached) — {summary}

### Integrated Changes
{git diff --stat from BASE_REF}

### Remaining Items
- [ ] Item — reason

### Test Results
{pass/fail summary}

### Cleanup
{removed sessions, worktrees, branches}
```

## Deterministic Loops

For infrastructure, backups, inventory-driven tasks — read [deterministic-loops.md](references/deterministic-loops.md). Render from JSON plan:

```sh
python3 scripts/render_worker_loop.py --config plan.json --language python --output run.py
python3 scripts/render_worker_loop.py --config plan.json --language bash --output run.sh
```

## Harness Portability

Default executor is Codex CLI (`--full-auto`). For other harnesses, read [harness-portability.md](references/harness-portability.md). Convert:

```sh
python3 scripts/convert_harness.py --config harness.json --output-dir /tmp/converted
```

## Error Handling

Read [error-handling.md](references/error-handling.md) for troubleshooting.

## Reference Files

| File | Read when... |
|------|-------------|
| [prompt-templates.md](references/prompt-templates.md) | Building initial, correction, or phase-scoped prompts |
| [review-process.md](references/review-process.md) | Reviewing worker output, building scorecards |
| [task-planning.md](references/task-planning.md) | Writing task cards, choosing parallel splits |
| [integration.md](references/integration.md) | Merging branches, resolving conflicts |
| [deterministic-loops.md](references/deterministic-loops.md) | Infrastructure work, backups, generated scripts |
| [harness-portability.md](references/harness-portability.md) | Using a non-Codex CLI agent |
| [error-handling.md](references/error-handling.md) | Troubleshooting failures |

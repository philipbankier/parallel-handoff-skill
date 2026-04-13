# parallel-handoff

**Plan → parallel workers in git worktrees → per-worker supervisor loop → review → integrate.**

Merges the best of two skills:
- [parallel-agent-worktree-skill](https://github.com/TheAhmadOsman/parallel-agent-worktree-skill) (Apache-2.0) — parallel workers in git worktrees via tmux
- [codex-handoff-skill](https://github.com/philipbankier/codex-handoff-skill) (MIT) — supervisor loop with phased execution for Codex CLI

## Architecture

```
┌─────────────┐
│  Coordinator │  (Claude Code / AI agent — supervises, reviews, decides)
└──────┬──────┘
       │
       ▼
  ┌─────────┐     ┌─────────┐     ┌─────────┐
  │ Worker 1 │     │ Worker 2 │     │ Worker N │
  │ (tmux)   │     │ (tmux)   │     │ (tmux)   │
  │ worktree │     │ worktree │     │ worktree │
  │          │     │          │     │          │
  │ ┌──────┐ │     │ ┌──────┐ │     │ ┌──────┐ │
  │ │Supv. │ │     │ │Supv. │ │     │ │Supv. │ │
  │ │Loop  │ │     │ │Loop  │ │     │ │Loop  │ │
  │ └──────┘ │     │ └──────┘ │     │ └──────┘ │
  └─────────┘     └─────────┘     └─────────┘
       │               │               │
       └───────────────┼───────────────┘
                       ▼
              ┌──────────────┐
              │  Integration │  merge → review → verify
              └──────────────┘
```

Each worker runs in its own **git worktree** with its own **supervisor loop**:
execute → review → decide → correct if needed → repeat until done or max iterations.

## 5 Execution Modes

| Mode | When | Flow |
|------|------|------|
| **Single-pass** | Simple task, 1 worker | Plan → execute → review → report |
| **Phased** | Multi-phase plan, sequential | Phase 1 → loop → Phase 2 → loop → ... |
| **Parallel** | Independent tasks, no phases | Plan → N workers in parallel → review → integrate |
| **Phased+Parallel** | Multi-phase with parallelizable tasks | Per phase: fan out workers → review → next phase |
| **Deterministic** | Infrastructure, backups needed | JSON plan → generated Bash/Python script → audit → run |

## Quick Start

```bash
# Install
bash install.sh

# Use in Claude Code
/parallel-handoff Add rate limiting to the API

# Use in OpenClaw
/parallel-handoff Implement the authentication plan from docs/plans/auth.md --mode phased+parallel
```

## Features

- **Worktree isolation** — Each worker gets its own git branch + worktree, no conflicts
- **Per-worker supervisor loop** — Workers retry independently with correction prompts
- **Scorecard review** — Structured review with DONE/PARTIAL/MISSING/ERROR status
- **Harness-portable** — Works with Codex CLI, Claude Code, Kimi, OpenCode, Pi, or any CLI agent
- **Deterministic loops** — Generate auditable Bash/Python scripts for infrastructure work
- **Phased execution** — Multi-phase plans with auto-detection
- **Conflict-safe integration** — Merge strategies with conflict resolution guidance

## What Came From Where

| Feature | parallel-agent-worktree | codex-handoff | parallel-handoff |
|---------|:-----------------------:|:-------------:|:----------------:|
| Git worktree isolation | ✅ | | ✅ |
| Tmux worker management | ✅ | | ✅ |
| Task cards with ownership | ✅ | | ✅ |
| Deterministic loop generation | ✅ | | ✅ |
| Harness portability | ✅ | | ✅ |
| Convert harness script | ✅ | | ✅ |
| Supervisor loop | | ✅ | ✅ |
| Phased execution | | ✅ | ✅ |
| Scorecard review | | ✅ | ✅ |
| Prompt templates | | ✅ | ✅ |
| Correction prompts | | ✅ | ✅ |
| Multi-platform installer | | ✅ | ✅ |
| Per-worker supervisor loop | | | ✅ (new) |
| 5 execution modes | | | ✅ (new) |
| Phased+parallel mode | | | ✅ (new) |

## Repo Structure

```
parallel-handoff/
├── skills/parallel-handoff/
│   ├── SKILL.md                         # Main skill
│   └── references/                      # Detailed reference docs
│       ├── prompt-templates.md
│       ├── review-process.md
│       ├── task-planning.md
│       ├── integration.md
│       ├── deterministic-loops.md
│       ├── harness-portability.md
│       └── error-handling.md
├── scripts/
│   ├── worker_manager.py                # Spawn/monitor/cleanup workers
│   ├── render_worker_loop.py            # Generate deterministic loops
│   └── convert_harness.py              # Convert to another CLI agent
├── examples/
│   ├── simple-handoff/                  # Single-pass walkthrough
│   ├── parallel-workers/                # Multi-worker walkthrough
│   └── self-hosted-upgrade.json         # Deterministic loop config
├── resources/
│   └── example-plan.md                  # Phased plan with parallel tasks
├── commands/
│   └── parallel-handoff.md              # Slash command
├── install.sh
├── uninstall.sh
├── openclaw.yaml
├── CLAUDE.md
├── CHANGELOG.md
├── CONTRIBUTING.md
├── LICENSE
└── .gitignore
```

## Compatibility

| Platform | Install method |
|----------|---------------|
| Claude Code | Symlink to `~/.claude/skills/` and `~/.claude/commands/` |
| OpenClaw | Symlink to `~/.openclaw/skills/` |

## Default Agent

Codex CLI (`codex --full-auto`). Override with `--agent-cli` or `AGENT_CLI` env var.

## License

MIT. With attribution to both source projects.

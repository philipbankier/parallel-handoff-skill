---
description: "Plan → parallel workers → supervisor loop → review → integrate. Run one or more CLI agent workers with git worktree isolation."
argument-hint: "[task description] [--mode single-pass|phased|parallel|phased+parallel|deterministic] [--max-iterations N] [--model MODEL] [--phase N] [--agent-cli CLI]"
---

# Parallel Handoff

Use the `parallel-handoff` skill to execute coding plans with parallel workers. Each worker runs in an isolated git worktree with its own supervisor loop.

Task: $ARGUMENTS

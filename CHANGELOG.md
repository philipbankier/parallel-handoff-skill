# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-04-13

### Added

- Initial release merging parallel-agent-worktree-skill + codex-handoff-skill
- 5 execution modes: single-pass, phased, parallel, phased+parallel, deterministic
- Per-worker supervisor loop with scorecard review
- Git worktree isolation for each worker
- Tmux-based worker management via `scripts/worker_manager.py`
- Deterministic loop generation via `scripts/render_worker_loop.py`
- Harness conversion via `scripts/convert_harness.py`
- Progressive disclosure: SKILL.md workflow, references/ for details
- Prompt templates for initial, correction, phase-scoped, and parallel worker modes
- Multi-platform installer (Claude Code + OpenClaw)
- Example plans and walkthroughs
- MIT license with attribution to both source projects

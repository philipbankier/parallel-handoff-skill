# CLAUDE.md

This is the `parallel-handoff` skill repository.

## Conventions

- SKILL.md stays under 500 lines — push details to `references/`
- Reference files are markdown with no YAML frontmatter
- Instructions are for AI agents, not humans — be concise and actionable
- Python scripts use `#!/usr/bin/env python3`
- Shell scripts use `#!/usr/bin/env bash` with `set -euo pipefail`
- Cross-platform: must work on macOS and Linux

## Structure

- `skills/parallel-handoff/` — skill files (SKILL.md + references)
- `scripts/` — Python helper scripts
- `examples/` — walkthrough examples
- `resources/` — example plans
- `commands/` — slash command definitions
- Root — install scripts, manifest, license, docs

## Commit Style

Conventional Commits: `feat:`, `fix:`, `docs:`, `refactor:`, `chore:`.

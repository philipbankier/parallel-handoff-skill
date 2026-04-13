# Contributing to parallel-handoff

Thanks for your interest! This is a skill repository for AI agent platforms.

## Getting Started

1. Fork and clone
2. Install locally: `bash install.sh`
3. Edits to source files take effect immediately via symlinks

## What You Can Contribute

- **Skill improvements** — Better prompts, clearer instructions, edge cases
- **New reference docs** — Guides for specific workflows
- **Script fixes** — Portability, error handling
- **Examples** — Real-world walkthroughs
- **Bug reports** — Installation issues, unclear docs, unexpected behavior

## Guidelines

- **SKILL.md** stays under 500 lines. Extract detail to `references/`.
- Reference files: standard markdown, no YAML frontmatter.
- Keep instructions actionable — the audience is an AI agent.
- Shell scripts: `#!/usr/bin/env bash` + `set -euo pipefail`. Must work on macOS and Linux.
- Python scripts: `#!/usr/bin/env python3`. No external dependencies beyond stdlib.
- Commits: Conventional Commits format.

## Submitting a PR

1. Feature branch from `main`
2. Make changes
3. Test: `bash install.sh`
4. Open PR with clear description

## Reporting Issues

Open a GitHub issue with: expected behavior, actual behavior, platform, agent platform.

# Prompt Templates

Templates for building prompts for the supervisor loop and parallel workers.

## Initial Execution Prompt (Single-Pass)

Create `/tmp/parallel-handoff-{timestamp}.md`:

```markdown
# Task

You are executing a coding plan. Complete ALL items below. Do not skip any steps.

## Plan

{FULL PLAN CONTENT}

## Project Context

- Working directory: {pwd}
- Package manager: {detect from lockfile}
- Test command: {from package.json or plan}
- Build command: {from package.json or plan}

## Coding Standards

{Contents of CLAUDE.md / AGENTS.md if they exist}

## Instructions

1. Implement each plan item in order
2. Run tests after each significant change
3. Follow existing codebase patterns
4. Do NOT add unnecessary comments or abstractions beyond the plan
5. When ALL items are complete and tests pass, output: CODEX_COMPLETE
6. If stuck, implement what you can and note what failed
```

## Phase-Scoped Execution Prompt

Create `/tmp/parallel-handoff-phase-{N}-{timestamp}.md`:

```markdown
# Task — Phase {N} of {total}: {phase_title}

You are executing Phase {N} of a multi-phase plan.
Complete ALL items in this phase only.

## This Phase

{PHASE CONTENT ONLY}

## Completed Phases (for context)

{For each completed phase: title, summary, key files. NOT full content.}

## Project Context

{same as above}

## Instructions

1. Implement each item in this phase in order
2. Run tests after each significant change
3. Do NOT touch files outside this phase's scope
4. When ALL items in this phase are complete and tests pass, output: PHASE_COMPLETE
```

## Parallel Worker Prompt

Create `/tmp/parallel-handoff-worker-{name}-{timestamp}.md`:

```markdown
# Task — Worker: {name}

You are a parallel agent worker running in an isolated git worktree.

Agent CLI: {cli} {args}

## Task

{BOUNDED TASK FROM TASK CARD}

## Ownership

- You may edit: {owned files/modules}
- You may read: {read-only files/modules}
- You must not edit: {other worker scopes}

## Context

{relevant plan excerpt, constraints, API contracts}

## Requirements

1. Inspect relevant code and tests first
2. Keep changes scoped to your ownership
3. Other workers are editing disjoint scopes — do not revert their work
4. Use repo-standard commands for formatting, linting, testing
5. Add or update focused tests when behavior changes
6. Update the changelog or write a fragment at {changelog path}
7. Commit with a Conventional Commit message

## Final Response

- Commit SHA
- Changed files
- Changelog path
- Verification commands and results
- Known gaps or risks
```

## Correction Prompt

Create `/tmp/parallel-handoff-correction-{timestamp}.md`:

```markdown
# Correction — Iteration {N+1}

## What was completed successfully
{list completed items}

## What still needs to be done
{list remaining items with specific instructions}

## Errors to fix
{test failures, build errors, issues from review}

## Important

- Focus ONLY on remaining items — do not redo completed work
- Run tests after each fix
- When ALL remaining items are complete and tests pass, output: CODEX_COMPLETE
```

## Phase Correction Prompt

Same as correction prompt but scoped to current phase. Replace `CODEX_COMPLETE` with `PHASE_COMPLETE`.

## Context Collection

Before building any prompt, collect:
- `CLAUDE.md` or `.codex/AGENTS.md` if they exist
- Test/build commands from `package.json` or equivalent
- Detect package manager from lockfile
- Read relevant source files for the task scope

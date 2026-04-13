# Task Planning

How to decompose work into task cards for parallel workers.

## Task Card Format

For each proposed worker task, write:

```text
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

## Choosing Parallel Tasks

Parallel workers are safe when their write scopes are disjoint enough to review and merge independently.

**Good for parallelism:**
- Separate modules, features, or services with no shared state
- Independent API endpoints
- Separate test suites
- Alternative implementations (competing approaches)
- Documentation for different sections

**Keep serial / local:**
- Tightly coupled design decisions
- Shared API or type definitions
- Database migrations
- Cross-cutting refactors
- Shared configuration changes
- Anything that touches the same lockfile

## Competing Approaches

For alternative implementations, spawn workers with explicit branch names:
```
alt-router-state-a
alt-router-state-b
```
Review both, integrate only the better result.

## Phased Decomposition

When a plan has phases:
1. Identify phase boundaries (natural dependency points)
2. Within each phase, identify parallelizable tasks
3. Tasks within a phase can run in parallel if write scopes don't overlap
4. Tasks across phases run sequentially (later phases depend on earlier ones)

## Integration Risk Assessment

Rate each task's integration risk:

| Risk | Meaning |
|------|---------|
| **Low** | Isolated module, no shared dependencies |
| **Medium** | Touches shared types or utilities, but changes are backward-compatible |
| **High** | Modifies shared APIs, database schema, or cross-cutting concerns |

High-risk tasks should run serially or be the only task in their phase.

## Dependency Tracking

If task B depends on task A:
- Run them in separate phases (A first, then B)
- Or include A's expected output as context in B's prompt
- Never run dependent tasks in parallel

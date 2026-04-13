# Review Process

After each agent execution (per worker, per phase), perform a comprehensive review.

## 1. Check What Changed

```bash
# In the worker worktree
git diff --stat
git diff  # full diff for detailed review
git log --oneline -5
```

## 2. Run Tests

- Run the project's test command (e.g., `npm test`, `pytest`, `make test`)
- Run the build command if applicable
- Capture pass/fail results
- Run the worker's own verification commands

## 3. Audit Plan Completion

Go through each item in the task/plan and check:
- Was the file created/modified as specified?
- Does the implementation match what was planned?
- Are there obvious issues in the diff?
- Did the worker stay within its ownership scope?

## 4. Scorecard

| Status | Meaning |
|--------|---------|
| DONE | Implemented correctly, tested, scoped |
| PARTIAL | Started but incomplete or buggy |
| MISSING | Not attempted |
| ERRORS | Test failures, build errors |

## 5. Decision Matrix

**ALL items DONE + tests pass:**
- Single worker → mark complete, proceed to integration
- Phased → record phase summary, advance to next phase
- Parallel → mark worker accepted, review remaining workers

**PARTIAL, MISSING, or ERROR items AND iterations < max:**
- Build a correction prompt (see [prompt-templates.md](prompt-templates.md))
- Re-run the same worker with corrections

**Max iterations reached:**
- Mark worker as partial
- In phased mode: ask user to continue or stop
- Record what was accomplished and what remains

## Phase Summary Format

After a phase completes:

```
Phase {N}: {title}
Status: COMPLETE
Iterations: {M}
Files changed: {list}
Key changes: {1-2 sentence summary}
```

## Worker Decision Rules

- **Accept** when: diff is scoped, correct, tested, compatible with integration plan, changelog included.
- **Send back** when: approach is sound but incomplete or tests fail.
- **Reject** when: wrong scope, invented APIs, ignored constraints, excessive churn, overlaps a better accepted branch.

Keep notes on every accepted, rejected, and pending branch with the reason.

## Diff Review Checklist

- [ ] Changes are within the worker's owned scope
- [ ] No edits to files owned by other workers
- [ ] No unnecessary refactoring or style changes outside scope
- [ ] Tests added or updated for changed behavior
- [ ] No hardcoded secrets, credentials, or personal data
- [ ] Changelog updated or fragment written
- [ ] Commit messages follow Conventional Commits
- [ ] No leftover debug code, console.logs, or TODO markers

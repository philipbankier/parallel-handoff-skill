# Integration

How to merge accepted worker output back into the main branch.

## Before Integration

Return to the main worktree and confirm it is clean:

```bash
git status --short --branch
test "$(git branch --show-current)" = "$INTEGRATION_BRANCH"
```

## Merge Strategies

### Whole Branch Merge

```bash
git merge --no-ff <worker-branch>
```

Use when the entire worker branch is accepted. Preserves history.

### Cherry-Pick Selected Commits

```bash
git cherry-pick <commit-sha>
```

Use when only some commits from a worker branch are accepted.

### Merge Order

For multiple accepted workers, merge in dependency order:
1. Low-risk, no-dependency workers first
2. Workers that other workers depend on
3. High-risk or cross-cutting workers last

After each merge, run focused tests before proceeding.

## Conflict Resolution

Resolve conflicts in the main worktree, not inside worker checkouts.

Strategies:
- **Accept ours** — when the worker's change is in a shared file but the worker's version is wrong
- **Accept theirs** — when the worker's change should take precedence
- **Manual merge** — combine both changes when they're complementary

After resolving conflicts:
```bash
git add <resolved-files>
git merge --continue  # or git cherry-pick --continue
```

If a conflict reveals a design incompatibility, either fix locally or send a follow-up to the relevant worker worktree.

## Changelog Reconciliation

Before the final merge is considered done:

1. Collect every accepted worker's changelog entry or fragment
2. Merge fragments into the canonical changelog in chronological order
3. Deduplicate entries that refer to the same change
4. Verify the changelog reflects all integrated work

If workers wrote fragments (`.worker-runs/changelog/<task>.md`):
```bash
cat .worker-runs/changelog/*.md >> CHANGELOG.md
```

## Post-Integration Verification

After all merges, run full repo checks:

```bash
make format   # or equivalent
make check    # linting, type checking
make test     # full test suite
```

## Verification

```bash
git branch --show-current
git status --short
git log --oneline "$BASE_REF"..HEAD
```

If integrated on a temporary branch, merge back:
```bash
git switch "$INTEGRATION_BRANCH"
git merge --no-ff <integration-branch>
```

## When Integration Fails

If final merge-back is impossible, do not imply completion. Leave a report with:
- Original checked-out branch from preflight
- Current branch and all worker/integration branches with accepted work
- Exact blocker (conflicts, failed tests, dirty changes, missing changelog)
- Completed work, missing work, validation already run
- Exact next commands to resume safely

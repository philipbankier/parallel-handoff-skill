# Parallel Workers Example

Multiple workers handling independent tasks simultaneously.

## Plan

```
Add three independent features to the API:

Worker A: Rate limiting middleware
Worker B: Request logging middleware
Worker C: Health check endpoint
```

## Execution

```bash
# Set up
PROJECT_DIR="$(git rev-parse --show-toplevel)"
BASE_REF="$(git branch --show-current)"
WORKTREE_ROOT="${PROJECT_DIR}.worktrees"

# Spawn three workers in parallel
python3 scripts/worker_manager.py spawn rate-limiter \
  --base "$BASE_REF" --prompt-file /tmp/rate-limiter.prompt \
  --agent-cli codex --agent-args "--full-auto"

python3 scripts/worker_manager.py spawn request-logger \
  --base "$BASE_REF" --prompt-file /tmp/request-logger.prompt \
  --agent-cli codex --agent-args "--full-auto"

python3 scripts/worker_manager.py spawn health-check \
  --base "$BASE_REF" --prompt-file /tmp/health-check.prompt \
  --agent-cli codex --agent-args "--full-auto"
```

## Worker Prompts

### Worker A: rate-limiter

```markdown
# Task — Worker: rate-limiter

Add rate limiting middleware to the API.

## Ownership
- You may edit: src/middleware/rateLimit.ts, src/__tests__/rateLimit.test.ts
- You may read: src/index.ts, src/middleware/*
- You must not edit: src/middleware/logger.ts, src/routes/health.ts, any other worker scope

## Requirements
1. Implement sliding window rate limiter (100 req/min per IP)
2. Return 429 when limit exceeded with Retry-After header
3. Add configuration via environment variables
4. Write unit tests
5. Update CHANGELOG.md or write fragment at .worker-runs/changelog/rate-limiter.md
6. Commit with conventional commit message
```

### Worker B: request-logger

```markdown
# Task — Worker: request-logger

Add structured request logging middleware.

## Ownership
- You may edit: src/middleware/logger.ts, src/__tests__/logger.test.ts
- You may read: src/index.ts, src/middleware/*
- You must not edit: src/middleware/rateLimit.ts, src/routes/health.ts, any other worker scope

## Requirements
1. Log method, path, status code, response time for each request
2. Use structured JSON format
3. Skip health check endpoint
4. Write unit tests
5. Update changelog
6. Commit with conventional commit message
```

### Worker C: health-check

```markdown
# Task — Worker: health-check

Add a health check endpoint.

## Ownership
- You may edit: src/routes/health.ts, src/__tests__/health.test.ts
- You may read: src/index.ts, src/routes/*
- You must not edit: src/middleware/*, any other worker scope

## Requirements
1. GET /health returns { status: "ok", timestamp }
2. Include database connectivity check
3. Return 503 if database unreachable
4. Write unit tests
5. Update changelog
6. Commit with conventional commit message
```

## Expected Flow

1. Spawn 3 workers in parallel → each runs Codex CLI in its own worktree
2. Each worker loops independently: execute → review → correct if needed
3. Review all 3 workers: diff, tests, scope compliance
4. Accept all → merge in order → run full test suite → cleanup → report

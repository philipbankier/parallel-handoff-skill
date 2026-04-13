# Simple Handoff Example

A single-pass handoff for a straightforward task.

## Plan

```
Add input validation to the user registration endpoint.

1. Validate email format with regex
2. Validate password strength (min 8 chars, 1 number, 1 special char)
3. Return 400 with specific error messages for each validation failure
4. Add unit tests for each validation rule
```

## Execution

```bash
# Single worker, single phase
python3 scripts/worker_manager.py spawn validation \
  --base main \
  --prompt-file /tmp/validation.prompt \
  --agent-cli codex \
  --agent-args "--full-auto"
```

## Prompt

```markdown
# Task

Add input validation to the user registration endpoint at `src/routes/auth.ts`.

## Requirements

1. Validate email format — must match standard email regex
2. Validate password — minimum 8 characters, at least 1 number, 1 special character
3. Return 400 with specific error messages per validation failure
4. Add unit tests at `src/__tests__/auth-validation.test.ts`

## Context

- Working directory: /home/user/myapp
- Test command: npm test
- Existing auth routes are in src/routes/auth.ts
- Follow existing error response patterns in the codebase
```

## Expected Flow

1. Spawn worker → runs Codex CLI
2. Review: `git diff`, `npm test`
3. If incomplete → send correction prompt
4. Accept → merge → cleanup → report

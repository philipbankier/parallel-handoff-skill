# Harness Portability

Use this reference before running or converting the skill for any harness other than
the default Codex CLI. The parent agent must resolve the target CLI at runtime;
this package deliberately does not hardcode every possible agent harness.

## Runtime Mapping Rule

Treat every target harness as unknown until verified locally.

1. Run `<target-cli> --help`, `<target-cli> --version`, and any subcommand help that
   appears relevant.
2. Inspect local target-harness docs and config in the current repo or user config.
3. Confirm auth state without printing tokens, API keys, session cookies, or secrets.
4. Build a harness mapping JSON from observed behavior, not from memory.
5. Run `scripts/convert_harness.py`, then review and patch the converted package.
6. Run unit, integration, generated-script, and dry-run validation before real work.

This applies to Codex CLI, Claude Code, OpenCode, Droid Factory, Pi, internal CLIs,
and any future tool with a command-line interface.

## Required Harness Facts

Record these facts in the conversion report:

- Executable name and version.
- Interactive command and whether it needs a TTY.
- Non-interactive command and whether it accepts prompts.
- Prompt delivery: `stdin`, `argument`, `file`, or unsupported.
- Worktree execution: explicit work-dir flag or current working directory.
- Approval and sandbox flags, including filesystem, shell, and network scope.
- Model, effort, provider, and config-selection flags.
- Session and resume semantics.
- Log format, stdout/stderr behavior, and final-message behavior.
- Exit codes for harness failure, user cancellation, tool denial, and task failure.
- Rate limits, concurrency locks, global mutable state, cache paths, and credential
  stores.
- Skill/plugin loading paths if the target harness supports skills.

## Prompt Delivery Modes

Generated loops support three prompt modes:

- `stdin`: writes the task prompt to standard input. This is the default Codex CLI mode.
- `argument`: appends the task prompt as an argument. If `agent.prompt_arg` is set, the
  flag is inserted before the prompt text.
- `file`: appends the generated prompt-file path. If `agent.prompt_arg` is set, the
  flag is inserted before the file path.

If a harness requires a JSON request body, a socket, a local server, or a different
protocol, write a wrapper CLI that accepts one of these three modes and call that
wrapper as `agent.cli`.

## Worktree Modes

Generated loops support two worktree modes:

- `agent.work_dir_arg` set: pass that flag and the worktree path to the harness.
- `agent.work_dir_arg` empty: run the harness process with current working directory
  set to the worker worktree.

If the harness needs both a work-dir flag and a cwd, prefer a wrapper script and make
the wrapper enforce the exact launch contract.

## When Not To Parallelize

Do not run deterministic parallel workers when:

- The harness stores all state in one mutable session that cannot run concurrently.
- Approval bypass semantics are missing, unclear, or too broad for the requested work.
- The harness cannot receive prompts deterministically.
- The harness mutates shared global config during a run.
- The target repo or service cannot tolerate concurrent edits.
- Required backups cannot be verified before workers start.
- Prompt logs would expose secrets that cannot be redacted.

Use interactive workers with manual approval, lower `max_parallel` to `1`, or stop and
report the blocker.

## Conversion Acceptance

A converted skill is not ready until:

- README, `SKILL.md`, references, examples, scripts, tests, and poster copy no longer
  imply Codex CLI-specific syntax.
- `examples/self-hosted-upgrade.json` uses the target harness mapping.
- Generated Python and Bash scripts syntax-check.
- Fake-harness tests cover prompt mode, work-dir mode, failure, rollback, and stale
  source-harness scans.
- The converter report explains any remaining mentions of Codex, Claude Code, or
  another specific CLI.
- The final stage prompt has been run:

```text
› Let's unit test and integerate test comprehensively and extensively covering any and all things + any and all possible edge cases.
```

# Deterministic Worker Loops

Use this reference when parallel agents should be launched by explicit logic instead of
an interactive instruction. The pattern is: build an auditable plan, pass every gate,
create isolated worktrees, run non-interactive CLI-agent workers, verify results, then
decide what to merge. The included sample plan uses Kimi CLI only as one harness
mapping; the renderer itself reads a generic `agent` block.

## When To Use This Path

Use generated loops for:

- Self-hosted upgrades where containers, LXC guests, VMs, databases, volumes, config
  files, certificates, firewall rules, or reverse proxies may be changed.
- Tasks discovered from inventory: one worker per service, package, host, module, tenant,
  migration, issue, failing test group, or config file.
- Backup-gated operations where a failed backup must stop the entire fan-out.
- Logic-gated operations where conditions determine whether a worker should run.
- Repeatable maintenance runs where you want a checked-in or archived script and logs.
- Unattended runs where the selected harness has a reviewed non-interactive mode.

Use interactive tmux workers instead when:

- The plan is still fluid and follow-up steering is expected.
- Multiple competing approaches need subjective evaluation.
- The risk is mostly code quality, not external system state.
- The user wants to watch or manually intervene in individual workers.

## Plan Shape

The renderer expects a JSON object:

```json
{
  "run_name": "self-hosted-upgrade",
  "repo": ".",
  "base": "main",
  "worktree_root": "",
  "max_parallel": 2,
  "agent": {
    "cli": "kimi",
    "work_dir_arg": "--work-dir",
    "args": ["--print", "--yolo", "--input-format", "text", "--final-message-only"],
    "prompt_mode": "stdin",
    "prompt_arg": "",
    "log_name": "agent.log",
    "timeout_seconds": 7200
  },
  "preflight": [
    {
      "name": "clean-main-worktree",
      "command": "test -z \"$(git status --short)\""
    }
  ],
  "backups": [
    {
      "name": "compose-service-list",
      "condition": "test -f compose.yml || test -f compose.yaml || test -f docker-compose.yml",
      "command": "mkdir -p backups && docker compose ps --services > backups/compose-services-${RUN_ID}.txt"
    }
  ],
  "tasks": [
    {
      "name": "upgrade-compose",
      "branch": "upgrade-compose",
      "condition": "test -f compose.yml || test -f compose.yaml || test -f docker-compose.yml",
      "prompt": "Inspect the compose stack, update one bounded service, add verification notes, update the changelog or write .worker-runs/changelog/upgrade-compose.md, and commit.",
      "verify": ["git status --short", "git log --oneline -1"]
    }
  ],
  "postflight": [
    {
      "name": "list-worktrees",
      "command": "git worktree list"
    }
  ],
  "rollback": [
    {
      "name": "manual-rollback-note",
      "command": "echo inspect backups and restore the affected service snapshots manually"
    }
  ]
}
```

Field notes:

- `repo`: repository root or any path inside it.
- `base`: base ref for worker branches.
- `worktree_root`: optional. Empty means `<repo>.worktrees`.
- `max_parallel`: number of non-interactive workers to run at once.
- `agent.cli`: selected harness executable.
- `agent.work_dir_arg`: optional flag used to point the harness at the worker worktree.
  Set to an empty string for harnesses that rely on current working directory.
- `agent.args`: non-interactive harness arguments. Keep approval-bypass flags only
  when the user has approved the plan.
- `agent.prompt_mode`: how the generated loop passes each task prompt. Use `stdin`
  for CLIs that read prompt text from standard input, `argument` for CLIs that accept
  prompt text as an argument, and `file` for CLIs that accept a prompt file path.
- `agent.prompt_arg`: optional flag inserted before the prompt text or file path, such
  as `--prompt` or `--prompt-file`.
- `agent.log_name`: task agent-output log file name. Default: `agent.log`.
- `agent.timeout_seconds`: per-worker timeout for generated Python. Generated Bash uses
  `timeout` when available and otherwise runs without a hard timeout.
- `preflight`: must pass before backups and tasks run.
- `backups`: must pass before tasks run when their condition is true.
- `tasks`: exactly one of `prompt` or `prompt_file` per task.
- `verify`: commands run from the worker worktree after the agent harness exits
  successfully.
- `postflight`: run after all tasks pass.
- `rollback`: written to `rollback.sh` when a task fails; not executed automatically.

## Backup Gates

Backup commands should produce durable artifacts and then verify those artifacts. Treat a
backup command as failed unless it can prove the restore point exists.

Useful backup classes:

- LXC: snapshot each target container with a run-scoped name.
- Docker images: record image IDs, tags, digests, compose files, and env file checksums.
- Docker volumes: snapshot named volumes or dump database contents before schema changes.
- Docker Compose: save `docker compose config`, service list, image list, and selected logs.
- Libvirt/QEMU VMs: snapshot or copy qcow2 disks while guests are quiesced.
- Proxmox/VMware/Hyper-V: create platform-native snapshots with clear labels.
- Databases: dump logical backups and verify the dump can be read.
- Filesystems: use ZFS/Btrfs/LVM snapshots, rsync hard-link backups, or restic/borg.
- Secrets/config: checksum `.env`, reverse proxy config, certs, systemd units, cron, and
  firewall rules without printing secret values into logs.

Example commands:

```sh
# LXC snapshots
lxc list --format csv -c n \
  | while read -r name; do
      [ -n "$name" ] && lxc snapshot "$name" "pre-agent-${RUN_ID}";
    done

# Docker compose inventory
docker compose config > "backups/compose-${RUN_ID}.yaml"
docker compose ps --services > "backups/compose-services-${RUN_ID}.txt"
docker images --digests > "backups/docker-images-${RUN_ID}.txt"

# PostgreSQL logical backup
docker compose exec -T db pg_dumpall \
  > "backups/postgres-${RUN_ID}.sql"
test -s "backups/postgres-${RUN_ID}.sql"

# Libvirt snapshot inventory
virsh list --name \
  | while read -r vm; do
      [ -n "$vm" ] && virsh snapshot-create-as "$vm" "pre-agent-${RUN_ID}";
    done
```

Never let worker prompts invent backup strategy for stateful systems. Decide backup
scope before rendering the loop.

## Condition Patterns

Conditions should be shell commands with clear true/false meaning:

- Tool exists: `command -v docker >/dev/null 2>&1`
- Service exists: `docker compose ps --services | grep -qx web`
- File exists: `test -f compose.yml || test -f compose.yaml`
- Git clean: `test -z "$(git status --short)"`
- Disk headroom: `df -Pk . | awk 'NR==2 {exit ($4 < 10485760)}'`
- Maintenance lock absent: `test ! -e /tmp/maintenance.lock`
- Version gate: `python -c 'import sys; sys.exit(sys.version_info < (3, 12))'`
- Remote host reachable: `ssh host 'true'`
- Backup present: `test -s backups/postgres-${RUN_ID}.sql`

Keep conditions side-effect free. Put mutations in `preflight`, `backups`, `tasks`, or
`postflight`, not in condition checks.

## Prompt Design For Generated Workers

Every task prompt should include:

- One bounded goal.
- Explicit owned paths or services.
- Paths and services the worker must not edit.
- Required tests or verification commands.
- Changelog path or fragment convention. Every worker must update the repo-standard
  changelog/release notes or write a unique fragment.
- Commit requirement and commit message convention.
- Reminder that other workers may be editing other worktrees.
- What to report: commit SHA, changed files, changelog path or fragment, tests, risks,
  and anything skipped.

For self-hosted work, also include:

- "Do not run live service mutations unless they are explicitly listed in this prompt."
- "Do not touch secrets; record checksums or file names only."
- "Prefer config and code changes in this worktree. Runtime rollout happens after review."
- "If you discover missing backup coverage, stop and report it."

## Concurrency Rules

Parallelism is safe only when task scopes are genuinely independent.

Avoid concurrent workers for:

- Same file or same generated lockfile.
- Same Docker Compose service.
- Same database schema or migration chain.
- Same host firewall, reverse proxy, or shared network config.
- Same package manager lockfile unless one worker owns dependency updates.
- Same Terraform/OpenTofu state or Pulumi stack.
- Same Kubernetes namespace resources when ordering matters.

Use `max_parallel: 1` for stateful infrastructure unless the tasks are read-only or the
write scopes are separated by service, host, or module.

## Logs And Artifacts

Generated loops write under `.worker-runs/<run-id>/` by default:

- `preflight-*.log`
- `backup-*.log`
- `tasks/<task>/prompt.txt`
- `tasks/<task>/agent.log`, or the configured `agent.log_name`
- `tasks/<task>/verify.log`
- `manifest.json` for generated Python
- `rollback.sh` when a failure occurs

Archive the run directory before cleanup when the run touched infrastructure.

## Failure Behavior

Expected behavior:

- Failed preflight stops the run before backups or workers.
- Failed backup stops the run before workers.
- Failed worker marks the run failed.
- Rollback commands are written but not executed automatically.
- Worktrees and branches are left in place for review after failure.

Rollback must be a deliberate human or coordinator action. Automatic rollback can make
state worse when some workers succeeded and others failed.

## Edge Cases

Handle these explicitly in the plan or prompt:

- Dirty main worktree: stop or include the diff in prompts; do not assume workers see it.
- Existing worker branch: generated loops reuse it; inspect before rerunning.
- Existing worktree: generated loops reuse it; remove stale worktrees deliberately.
- Shared changelog conflicts: use per-worker fragments and reconcile them into the
  canonical changelog before final merge.
- Prompt too long: use `prompt_file` instead of `prompt`.
- Missing `timeout`: generated Bash may not enforce timeout on macOS without GNU timeout.
- Secrets in logs: redact or avoid printing env files, tokens, cookies, private keys, and
  `.npmrc`/`.pypirc`/cloud credentials.
- Non-idempotent backups: include run-scoped names such as `pre-agent-${RUN_ID}`.
- Remote hosts: capture hostnames and commands; do not rely on interactive SSH prompts.
- Disk pressure: check free space before dumping databases or copying VM disks.
- Rate limits: reduce `max_parallel` if harness/API limits or package registries throttle.
- Lockfiles: assign one owner or serialize lockfile edits.
- Generated files: decide whether workers may regenerate them or whether integration does.
- Submodules: record submodule SHA changes and verify nested worktrees separately.
- LFS: confirm large files are fetched if workers need them.
- Binary artifacts: avoid committing backups or generated archives unless requested.
- Long-running services: prefer config diffs in worker branches; deploy after integration.
- Failed verification: send worker follow-up or reject branch; do not merge on summary text.

## Integration After Generated Runs

Generated loops intentionally stop before integration. After workers complete:

1. Inspect `manifest.json` or task logs.
2. Review each worktree diff against `base`.
3. Run targeted tests in each worktree.
4. Merge or cherry-pick only reviewed commits.
5. Reconcile every accepted changelog fragment into the canonical changelog/release notes.
6. Merge accepted work back into the branch that was checked out before spawning workers.
7. Run final checks in the integration worktree.
8. If final merge-back is blocked, report the original branch, current branches, blocker,
   validation already run, missing work, and exact next commands.
9. Archive logs if needed.
10. Remove tmux sessions if any, worktrees, and branches only after useful work is safe.

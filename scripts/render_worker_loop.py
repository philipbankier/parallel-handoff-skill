#!/usr/bin/env python3
"""Render deterministic Bash or Python worker loops from a JSON plan."""

from __future__ import annotations

import argparse
import json
import re
import shlex
import sys
from pathlib import Path
from typing import Any, NoReturn, cast

DEFAULT_AGENT_CLI = "kimi"
DEFAULT_AGENT_ARGS = ["--print", "--yolo", "--input-format", "text"]
DEFAULT_AGENT_WORK_DIR_ARG = "--work-dir"
DEFAULT_AGENT_LOG_NAME = "agent.log"
DEFAULT_AGENT_PROMPT_MODE = "stdin"
DEFAULT_AGENT_PROMPT_ARG = ""


def die(message: str) -> NoReturn:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(1)


def load_plan(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        die(f"invalid JSON in {path}: {exc}")
    if not isinstance(data, dict):
        die("plan must be a JSON object")
    return data


def as_string(value: Any, *, field: str, default: str = "") -> str:
    if value is None:
        return default
    if not isinstance(value, str):
        die(f"{field} must be a string")
    return value


def as_string_list(value: Any, *, field: str, default: list[str] | None = None) -> list[str]:
    if value is None:
        return list(default or [])
    if not isinstance(value, list):
        die(f"{field} must be a list of strings")
    items: list[str] = []
    for item in value:
        if not isinstance(item, str):
            die(f"{field} must be a list of strings")
        items.append(item)
    return items


def as_int(value: Any, *, field: str, default: int, minimum: int = 1) -> int:
    if value is None:
        return default
    if not isinstance(value, int) or value < minimum:
        die(f"{field} must be an integer >= {minimum}")
    return value


def as_steps(value: Any, *, field: str) -> list[dict[str, str]]:
    if value is None:
        return []
    if not isinstance(value, list):
        die(f"{field} must be a list")
    steps: list[dict[str, str]] = []
    for index, item in enumerate(value):
        if isinstance(item, str):
            steps.append({"name": f"{field}-{index + 1}", "command": item, "condition": ""})
            continue
        if not isinstance(item, dict):
            die(f"{field}[{index}] must be a string or object")
        item = cast(dict[str, Any], item)
        name = as_string(
            item.get("name"),
            field=f"{field}[{index}].name",
            default=f"{field}-{index + 1}",
        )
        command = as_string(item.get("command"), field=f"{field}[{index}].command")
        condition = as_string(item.get("condition"), field=f"{field}[{index}].condition")
        if not command:
            die(f"{field}[{index}].command is required")
        steps.append({"name": name, "command": command, "condition": condition})
    return steps


def normalize_name(raw: str) -> str:
    name = raw.strip().lower()
    name = re.sub(r"[^a-z0-9._-]+", "-", name)
    name = re.sub(r"-{2,}", "-", name).strip(".-")
    if not name:
        die("task names must contain at least one letter or digit")
    return name


def validate_plan(plan: dict[str, Any]) -> dict[str, Any]:
    raw_agent = plan.get("agent")
    if raw_agent is None:
        agent: dict[str, Any] = {}
    elif isinstance(raw_agent, dict):
        agent = cast(dict[str, Any], raw_agent)
    else:
        die("agent must be an object")

    agent_cli = as_string(agent.get("cli"), field="agent.cli", default=DEFAULT_AGENT_CLI)
    if not agent_cli:
        die("agent.cli must be a non-empty string")
    agent_log_name = as_string(
        agent.get("log_name"),
        field="agent.log_name",
        default=DEFAULT_AGENT_LOG_NAME,
    )
    if not agent_log_name or "/" in agent_log_name or "\\" in agent_log_name:
        die("agent.log_name must be a file name, not a path")
    agent_prompt_mode = as_string(
        agent.get("prompt_mode"),
        field="agent.prompt_mode",
        default=DEFAULT_AGENT_PROMPT_MODE,
    )
    if agent_prompt_mode not in {"stdin", "argument", "file"}:
        die("agent.prompt_mode must be one of: stdin, argument, file")

    raw_tasks = plan.get("tasks")
    if not isinstance(raw_tasks, list) or not raw_tasks:
        die("tasks must be a non-empty list")

    names: set[str] = set()
    tasks: list[dict[str, Any]] = []
    for index, raw_task in enumerate(raw_tasks):
        if not isinstance(raw_task, dict):
            die(f"tasks[{index}] must be an object")
        raw_task = cast(dict[str, Any], raw_task)
        name = normalize_name(as_string(raw_task.get("name"), field=f"tasks[{index}].name"))
        if name in names:
            die(f"duplicate task name after normalization: {name}")
        names.add(name)
        prompt = as_string(raw_task.get("prompt"), field=f"tasks[{index}].prompt")
        prompt_file = as_string(raw_task.get("prompt_file"), field=f"tasks[{index}].prompt_file")
        if bool(prompt) == bool(prompt_file):
            die(f"tasks[{index}] must set exactly one of prompt or prompt_file")
        tasks.append(
            {
                "name": name,
                "branch": as_string(
                    raw_task.get("branch"),
                    field=f"tasks[{index}].branch",
                    default=name,
                ),
                "condition": as_string(
                    raw_task.get("condition"),
                    field=f"tasks[{index}].condition",
                ),
                "prompt": prompt,
                "prompt_file": prompt_file,
                "verify": as_string_list(raw_task.get("verify"), field=f"tasks[{index}].verify"),
            }
        )

    return {
        "repo": as_string(plan.get("repo"), field="repo", default="."),
        "base": as_string(plan.get("base"), field="base", default="main"),
        "worktree_root": as_string(plan.get("worktree_root"), field="worktree_root", default=""),
        "run_name": normalize_name(
            as_string(plan.get("run_name"), field="run_name", default="agent-workers")
        ),
        "max_parallel": as_int(plan.get("max_parallel"), field="max_parallel", default=1),
        "timeout_seconds": as_int(
            agent.get("timeout_seconds"),
            field="agent.timeout_seconds",
            default=7200,
        ),
        "agent_cli": agent_cli,
        "agent_work_dir_arg": as_string(
            agent.get("work_dir_arg"),
            field="agent.work_dir_arg",
            default=DEFAULT_AGENT_WORK_DIR_ARG,
        ),
        "agent_args": as_string_list(
            agent.get("args"),
            field="agent.args",
            default=DEFAULT_AGENT_ARGS,
        ),
        "agent_log_name": agent_log_name,
        "agent_prompt_mode": agent_prompt_mode,
        "agent_prompt_arg": as_string(
            agent.get("prompt_arg"),
            field="agent.prompt_arg",
            default=DEFAULT_AGENT_PROMPT_ARG,
        ),
        "preflight": as_steps(plan.get("preflight"), field="preflight"),
        "backups": as_steps(plan.get("backups"), field="backups"),
        "postflight": as_steps(plan.get("postflight"), field="postflight"),
        "rollback": as_steps(plan.get("rollback"), field="rollback"),
        "tasks": tasks,
    }


def shell_quote(value: str) -> str:
    return shlex.quote(value)


def bash_array(items: list[str]) -> str:
    return "(" + " ".join(shell_quote(item) for item in items) + ")"


def bash_step_calls(kind: str, steps: list[dict[str, str]]) -> str:
    if not steps:
        return f'log "no {kind} steps configured"'
    lines = []
    for step in steps:
        lines.append(
            "run_step "
            f"{shell_quote(kind)} "
            f"{shell_quote(step['name'])} "
            f"{shell_quote(step['condition'])} "
            f"{shell_quote(step['command'])}"
        )
    return "\n".join(lines)


def bash_task_calls(tasks: list[dict[str, Any]]) -> str:
    blocks = []
    for task in tasks:
        verify = "\n".join(task["verify"])
        prompt = task["prompt"]
        if task["prompt_file"]:
            prompt_block = f"PROMPT_FILE={shell_quote(task['prompt_file'])}"
        else:
            prompt_block = f"PROMPT_LITERAL={shell_quote(prompt)}"
        blocks.append(
            "\n".join(
                [
                    "throttle_tasks",
                    "(",
                    f"  TASK_NAME={shell_quote(task['name'])}",
                    f"  TASK_BRANCH={shell_quote(task['branch'])}",
                    f"  TASK_CONDITION={shell_quote(task['condition'])}",
                    f"  {prompt_block}",
                    f"  VERIFY_COMMANDS={shell_quote(verify)}",
                    "  run_task",
                    ") &",
                    'TASK_PIDS+=("$!")',
                ]
            )
        )
    return "\n\n".join(blocks)


def render_bash(plan: dict[str, Any]) -> str:
    if plan["worktree_root"]:
        worktree_root_assignment = f"WORKTREE_ROOT={shell_quote(plan['worktree_root'])}"
    else:
        worktree_root_assignment = 'WORKTREE_ROOT="${REPO}.worktrees"'
    return f"""#!/usr/bin/env bash
set -Eeuo pipefail

RUN_NAME={shell_quote(plan["run_name"])}
RUN_ID="${{RUN_ID:-$(date -u +%Y%m%dT%H%M%SZ)-$RUN_NAME}}"
REPO=$(cd {shell_quote(plan["repo"])} && git rev-parse --show-toplevel)
BASE={shell_quote(plan["base"])}
{worktree_root_assignment}
LOG_ROOT="${{LOG_ROOT:-$REPO/.worker-runs/$RUN_ID}}"
MAX_PARALLEL={plan["max_parallel"]}
AGENT_TIMEOUT={plan["timeout_seconds"]}
AGENT_CLI={shell_quote(plan["agent_cli"])}
AGENT_WORK_DIR_ARG={shell_quote(plan["agent_work_dir_arg"])}
AGENT_ARGS={bash_array(plan["agent_args"])}
AGENT_PROMPT_MODE={shell_quote(plan["agent_prompt_mode"])}
AGENT_PROMPT_ARG={shell_quote(plan["agent_prompt_arg"])}
DRY_RUN="${{DRY_RUN:-0}}"
TASK_PIDS=()
export RUN_ID REPO BASE WORKTREE_ROOT LOG_ROOT

mkdir -p "$LOG_ROOT" "$WORKTREE_ROOT"

log() {{
  printf '[%s] %s\\n' "$(date -u +%H:%M:%S)" "$*"
}}

run_condition() {{
  local condition="$1"
  [[ -z "$condition" ]] && return 0
  if [[ "$DRY_RUN" == "1" ]]; then
    log "DRY_RUN condition $condition"
    return 0
  fi
  bash -lc "$condition"
}}

run_command() {{
  local command="$1"
  if [[ "$DRY_RUN" == "1" ]]; then
    log "DRY_RUN $command"
    return 0
  fi
  bash -lc "$command"
}}

run_step() {{
  local kind="$1"
  local name="$2"
  local condition="$3"
  local command="$4"
  local log_file="$LOG_ROOT/$kind-$name.log"
  if ! run_condition "$condition"; then
    log "skip $kind/$name: condition not met"
    return 0
  fi
  log "start $kind/$name"
  if run_command "$command" >"$log_file" 2>&1; then
    log "ok $kind/$name"
  else
    log "failed $kind/$name; see $log_file"
    return 1
  fi
}}

add_worktree() {{
  local branch="$1"
  local worktree="$2"
  if [[ -d "$worktree/.git" || -f "$worktree/.git" ]]; then
    log "reuse worktree $worktree"
    return 0
  fi
  if [[ "$DRY_RUN" == "1" ]]; then
    log "DRY_RUN git worktree add $worktree for branch $branch"
    return 0
  fi
  if git -C "$REPO" show-ref --verify --quiet "refs/heads/$branch"; then
    git -C "$REPO" worktree add "$worktree" "$branch"
  else
    git -C "$REPO" worktree add "$worktree" -b "$branch" "$BASE"
  fi
}}

run_agent() {{
  local worktree="$1"
  local prompt_file="$2"
  local output_file="$3"
  local input_file=""
  local command=("$AGENT_CLI")
  if [[ -n "$AGENT_WORK_DIR_ARG" ]]; then
    command+=("$AGENT_WORK_DIR_ARG" "$worktree")
  fi
  command+=("${{AGENT_ARGS[@]}}")
  case "$AGENT_PROMPT_MODE" in
    stdin)
      input_file="$prompt_file"
      ;;
    argument)
      [[ -n "$AGENT_PROMPT_ARG" ]] && command+=("$AGENT_PROMPT_ARG")
      command+=("$(cat "$prompt_file")")
      ;;
    file)
      [[ -n "$AGENT_PROMPT_ARG" ]] && command+=("$AGENT_PROMPT_ARG")
      command+=("$prompt_file")
      ;;
    *)
      log "unsupported AGENT_PROMPT_MODE=$AGENT_PROMPT_MODE"
      return 1
      ;;
  esac
  if [[ "$DRY_RUN" == "1" ]]; then
    if [[ -n "$input_file" ]]; then
      log "DRY_RUN ${{command[*]}} < $input_file"
    else
      log "DRY_RUN ${{command[*]}}"
    fi
    return 0
  fi

  run_command_array() {{
    if [[ -n "$AGENT_WORK_DIR_ARG" ]]; then
      if [[ -n "$input_file" ]]; then
        "$@" <"$input_file" >"$output_file" 2>&1
      else
        "$@" </dev/null >"$output_file" 2>&1
      fi
    else
      if [[ -n "$input_file" ]]; then
        (cd "$worktree" && "$@" <"$input_file" >"$output_file" 2>&1)
      else
        (cd "$worktree" && "$@" </dev/null >"$output_file" 2>&1)
      fi
    fi
  }}

  if command -v timeout >/dev/null 2>&1; then
    run_command_array timeout "$AGENT_TIMEOUT" "${{command[@]}}"
  else
    run_command_array "${{command[@]}}"
  fi
}}

verify_task() {{
  local verify_file="$1"
  local log_file="$2"
  local worktree="$3"
  local quoted_worktree
  [[ ! -s "$verify_file" ]] && return 0
  printf -v quoted_worktree '%q' "$worktree"
  while IFS= read -r command; do
    [[ -z "$command" ]] && continue
    log "verify $command"
    run_command "cd $quoted_worktree && $command" >>"$log_file" 2>&1
  done <"$verify_file"
}}

run_task() {{
  local worktree="$WORKTREE_ROOT/$TASK_NAME"
  local task_dir="$LOG_ROOT/tasks/$TASK_NAME"
  local prompt_file="$task_dir/prompt.txt"
  local verify_file="$task_dir/verify.sh"
  local output_file="$task_dir/{plan["agent_log_name"]}"
  local verify_log="$task_dir/verify.log"

  mkdir -p "$task_dir"
  if ! run_condition "$TASK_CONDITION"; then
    log "skip task/$TASK_NAME: condition not met"
    return 0
  fi

  add_worktree "$TASK_BRANCH" "$worktree"
  if [[ "${{PROMPT_FILE:-}}" != "" ]]; then
    cp "$PROMPT_FILE" "$prompt_file"
  else
    printf '%s' "${{PROMPT_LITERAL:-}}" >"$prompt_file"
  fi
  printf '%s\\n' "$VERIFY_COMMANDS" >"$verify_file"

  log "start task/$TASK_NAME"
  if run_agent "$worktree" "$prompt_file" "$output_file"; then
    verify_task "$verify_file" "$verify_log" "$worktree"
    log "ok task/$TASK_NAME"
  else
    log "failed task/$TASK_NAME; see $output_file"
    return 1
  fi
}}

throttle_tasks() {{
  while [[ "$(jobs -rp | wc -l | tr -d ' ')" -ge "$MAX_PARALLEL" ]]; do
    sleep 2
  done
}}

log "run_id=$RUN_ID"
log "repo=$REPO"
log "logs=$LOG_ROOT"

{bash_step_calls("preflight", plan["preflight"])}

{bash_step_calls("backup", plan["backups"])}

{bash_task_calls(plan["tasks"])}

FAILED=0
for pid in "${{TASK_PIDS[@]}}"; do
  if ! wait "$pid"; then
    FAILED=1
  fi
done

if [[ "$FAILED" != "0" ]]; then
  log "one or more tasks failed"
  log "rollback commands are recorded below; run them manually after inspection if needed"
  cat >"$LOG_ROOT/rollback.sh" <<'ROLLBACK'
#!/usr/bin/env bash
set -Eeuo pipefail
{chr(10).join(step["command"] for step in plan["rollback"])}
ROLLBACK
  chmod +x "$LOG_ROOT/rollback.sh"
  exit 1
fi

{bash_step_calls("postflight", plan["postflight"])}

log "done"
"""


def py_repr(value: Any) -> str:
    return repr(value)


def render_python(plan: dict[str, Any]) -> str:
    return f'''#!/usr/bin/env python3
"""Deterministic CLI-agent worker loop generated from a JSON plan.

The agent CLI, worktree argument, arguments, timeout, and log file name are
configured by the source JSON plan.
"""

from __future__ import annotations

import concurrent.futures
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path


PLAN = {py_repr(plan)}


def log(message: str) -> None:
    print(f"[{{time.strftime('%H:%M:%S', time.gmtime())}}] {{message}}", flush=True)


def run_shell(
    command: str,
    *,
    cwd: Path | None = None,
    log_file: Path | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    if os.environ.get("DRY_RUN") == "1":
        log(f"DRY_RUN {{command}}")
        return subprocess.CompletedProcess(command, 0, "", "")
    output = subprocess.PIPE if log_file else None
    result = subprocess.run(
        command,
        cwd=cwd,
        shell=True,
        text=True,
        stdout=output,
        stderr=subprocess.STDOUT,
    )
    if log_file and result.stdout:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        with log_file.open("a", encoding="utf-8") as stream:
            stream.write(result.stdout)
    if check and result.returncode != 0:
        raise RuntimeError(f"command failed ({{result.returncode}}): {{command}}")
    return result


def condition_ok(condition: str) -> bool:
    if not condition:
        return True
    return run_shell(condition, check=False).returncode == 0


def run_step(kind: str, step: dict[str, str], log_root: Path) -> None:
    if not condition_ok(step.get("condition", "")):
        log(f"skip {{kind}}/{{step['name']}}: condition not met")
        return
    log_file = log_root / f"{{kind}}-{{step['name']}}.log"
    log(f"start {{kind}}/{{step['name']}}")
    run_shell(step["command"], log_file=log_file)
    log(f"ok {{kind}}/{{step['name']}}")


def require_tool(name: str) -> None:
    if shutil.which(name) is None:
        raise RuntimeError(f"required tool not found on PATH: {{name}}")


def git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=check,
    )


def add_worktree(repo: Path, base: str, branch: str, worktree: Path) -> None:
    if (worktree / ".git").exists() or (worktree / ".git").is_file():
        log(f"reuse worktree {{worktree}}")
        return
    if os.environ.get("DRY_RUN") == "1":
        log(f"DRY_RUN git worktree add {{worktree}} for branch {{branch}}")
        return
    exists = git(
        repo,
        "show-ref",
        "--verify",
        "--quiet",
        f"refs/heads/{{branch}}",
        check=False,
    )
    if exists.returncode == 0:
        subprocess.run(
            ["git", "-C", str(repo), "worktree", "add", str(worktree), branch],
            check=True,
        )
    else:
        subprocess.run(
            ["git", "-C", str(repo), "worktree", "add", str(worktree), "-b", branch, base],
            check=True,
        )


def run_agent(worktree: Path, prompt_file: Path, output_file: Path) -> None:
    command = [PLAN["agent_cli"]]
    if PLAN["agent_work_dir_arg"]:
        command.extend([PLAN["agent_work_dir_arg"], str(worktree)])
    command.extend(PLAN["agent_args"])
    stdin_text: str | None = None
    prompt_mode = PLAN["agent_prompt_mode"]
    prompt_arg = PLAN["agent_prompt_arg"]
    if prompt_mode == "stdin":
        stdin_text = prompt_file.read_text(encoding="utf-8")
    elif prompt_mode == "argument":
        if prompt_arg:
            command.append(prompt_arg)
        command.append(prompt_file.read_text(encoding="utf-8"))
    elif prompt_mode == "file":
        if prompt_arg:
            command.append(prompt_arg)
        command.append(str(prompt_file))
    else:
        raise RuntimeError(f"unsupported prompt mode: {{prompt_mode}}")
    if os.environ.get("DRY_RUN") == "1":
        suffix = f" < {{prompt_file}}" if stdin_text is not None else ""
        log(f"DRY_RUN {{' '.join(command)}}{{suffix}}")
        return
    run_kwargs = (
        {{"input": stdin_text}}
        if stdin_text is not None
        else {{"stdin": subprocess.DEVNULL}}
    )
    result = subprocess.run(
        command,
        cwd=None if PLAN["agent_work_dir_arg"] else worktree,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=PLAN["timeout_seconds"],
        **run_kwargs,
    )
    output_file.write_text(result.stdout or "", encoding="utf-8")
    if result.returncode != 0:
        raise RuntimeError(f"{{PLAN['agent_cli']}} failed in {{worktree}}; see {{output_file}}")


def run_task(
    repo: Path,
    base: str,
    worktree_root: Path,
    log_root: Path,
    task: dict[str, object],
) -> dict[str, str]:
    name = str(task["name"])
    if not condition_ok(str(task.get("condition") or "")):
        log(f"skip task/{{name}}: condition not met")
        return {{"name": name, "status": "skipped"}}

    worktree = worktree_root / name
    task_dir = log_root / "tasks" / name
    task_dir.mkdir(parents=True, exist_ok=True)
    prompt_file = task_dir / "prompt.txt"
    output_file = task_dir / PLAN["agent_log_name"]
    verify_log = task_dir / "verify.log"

    add_worktree(repo, base, str(task["branch"]), worktree)
    if task.get("prompt_file"):
        prompt_file.write_text(
            Path(str(task["prompt_file"])).read_text(encoding="utf-8"),
            encoding="utf-8",
        )
    else:
        prompt_file.write_text(str(task["prompt"]), encoding="utf-8")

    log(f"start task/{{name}}")
    run_agent(worktree, prompt_file, output_file)
    for command in task.get("verify", []):
        if command:
            log(f"verify task/{{name}}: {{command}}")
            run_shell(str(command), cwd=worktree, log_file=verify_log)
    log(f"ok task/{{name}}")
    return {{"name": name, "status": "ok", "worktree": str(worktree), "log": str(output_file)}}


def main() -> int:
    require_tool("git")
    if os.environ.get("DRY_RUN") != "1":
        require_tool(PLAN["agent_cli"])

    repo = Path(PLAN["repo"]).expanduser().resolve()
    repo = Path(git(repo, "rev-parse", "--show-toplevel").stdout.strip()).resolve()
    base = PLAN["base"]
    run_id = os.environ.get("RUN_ID") or (
        f"{{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}}-{{PLAN['run_name']}}"
    )
    worktree_root = Path(PLAN["worktree_root"] or f"{{repo}}.worktrees").expanduser().resolve()
    log_root = Path(
        os.environ.get("LOG_ROOT", repo / ".worker-runs" / run_id)
    ).expanduser().resolve()
    worktree_root.mkdir(parents=True, exist_ok=True)
    log_root.mkdir(parents=True, exist_ok=True)
    os.environ.update(
        {{
            "RUN_ID": run_id,
            "REPO": str(repo),
            "BASE": base,
            "WORKTREE_ROOT": str(worktree_root),
            "LOG_ROOT": str(log_root),
        }}
    )

    log(f"run_id={{run_id}}")
    log(f"repo={{repo}}")
    log(f"logs={{log_root}}")

    for step in PLAN["preflight"]:
        run_step("preflight", step, log_root)
    for step in PLAN["backups"]:
        run_step("backup", step, log_root)

    results: list[dict[str, str]] = []
    failed = False
    with concurrent.futures.ThreadPoolExecutor(max_workers=PLAN["max_parallel"]) as pool:
        futures = [
            pool.submit(run_task, repo, base, worktree_root, log_root, task)
            for task in PLAN["tasks"]
        ]
        for future in concurrent.futures.as_completed(futures):
            try:
                results.append(future.result())
            except Exception as exc:
                failed = True
                log(f"task failed: {{exc}}")

    (log_root / "manifest.json").write_text(json.dumps(results, indent=2), encoding="utf-8")

    if failed:
        rollback = "\\n".join(step["command"] for step in PLAN["rollback"])
        rollback_path = log_root / "rollback.sh"
        rollback_path.write_text(
            "#!/usr/bin/env bash\\nset -Eeuo pipefail\\n" + rollback + "\\n",
            encoding="utf-8",
        )
        rollback_path.chmod(0o755)
        log(f"one or more tasks failed; inspect logs and rollback plan at {{rollback_path}}")
        return 1

    for step in PLAN["postflight"]:
        run_step("postflight", step, log_root)

    log("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path, help="JSON worker-loop plan")
    parser.add_argument("--language", choices=("bash", "python"), required=True)
    parser.add_argument("--output", type=Path, help="write generated script to this path")
    args = parser.parse_args()

    plan = validate_plan(load_plan(args.config))
    rendered = render_bash(plan) if args.language == "bash" else render_python(plan)
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
        args.output.chmod(0o755)
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Manage CLI-agent workers in git worktrees.

The default CLI is Kimi because this package ships with Kimi examples, but every
CLI command is configurable with --agent-cli and --agent-args.
"""

from __future__ import annotations

import argparse
import re
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path

DEFAULT_PREFIX = "agent-worker-"
DEFAULT_AGENT_CLI = "codex"
DEFAULT_AGENT_ARGS = "--full-auto"


def die(message: str, code: int = 1) -> None:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(code)


def run(
    cmd: list[str],
    *,
    cwd: Path | None = None,
    input_text: str | None = None,
    capture: bool = False,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        cmd,
        cwd=cwd,
        input=input_text,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )
    if check and result.returncode != 0:
        rendered = " ".join(shlex.quote(part) for part in cmd)
        if capture and result.stderr:
            print(result.stderr.rstrip(), file=sys.stderr)
        die(f"command failed ({result.returncode}): {rendered}", result.returncode)
    return result


def require_tool(name: str) -> None:
    if shutil.which(name) is None:
        die(f"required tool not found on PATH: {name}")


def repo_root(repo: str) -> Path:
    result = run(["git", "-C", repo, "rev-parse", "--show-toplevel"], capture=True)
    return Path(result.stdout.strip()).resolve()


def git(
    repo: Path,
    *args: str,
    capture: bool = True,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    return run(["git", "-C", str(repo), *args], capture=capture, check=check)


def current_branch(repo: Path) -> str:
    result = git(repo, "branch", "--show-current")
    branch = result.stdout.strip()
    if not branch:
        die("current checkout is detached; pass --base explicitly")
    return branch


def branch_exists(repo: Path, branch: str) -> bool:
    result = git(
        repo,
        "show-ref",
        "--verify",
        "--quiet",
        f"refs/heads/{branch}",
        capture=False,
        check=False,
    )
    return result.returncode == 0


def slugify_name(raw: str) -> str:
    name = raw.strip().lower()
    name = re.sub(r"[^a-z0-9._-]+", "-", name)
    name = re.sub(r"-{2,}", "-", name).strip(".-")
    if not name:
        die("worker name must contain at least one letter or digit")
    return name


def default_worktree_root(repo: Path) -> Path:
    return Path(f"{repo}.worktrees")


def resolve_worktree_root(repo: Path, raw: str | None) -> Path:
    if raw:
        return Path(raw).expanduser().resolve()
    return default_worktree_root(repo).resolve()


def session_name(prefix: str, name: str) -> str:
    return f"{prefix}{name}"


def tmux_session_exists(session: str) -> bool:
    result = run(["tmux", "has-session", "-t", session], capture=True, check=False)
    return result.returncode == 0


def read_prompt(prompt: str | None, prompt_file: str | None, *, required: bool = True) -> str:
    if prompt and prompt_file:
        die("use either --prompt or --prompt-file, not both")
    if prompt_file:
        return Path(prompt_file).read_text(encoding="utf-8")
    if prompt:
        return prompt
    if required:
        die("prompt required; pass --prompt, --prompt-file, or --no-send")
    return ""


def send_prompt(session: str, prompt: str) -> None:
    if not prompt.endswith("\n"):
        prompt += "\n"
    buffer_name = f"{session}-prompt"
    run(["tmux", "load-buffer", "-b", buffer_name, "-"], input_text=prompt)
    run(["tmux", "paste-buffer", "-t", session, "-b", buffer_name])
    run(["tmux", "send-keys", "-t", session, "Enter"])
    run(["tmux", "delete-buffer", "-b", buffer_name], check=False)


def cmd_spawn(args: argparse.Namespace) -> None:
    require_tool("git")
    require_tool(args.agent_cli)
    require_tool("tmux")

    name = slugify_name(args.name)
    repo = repo_root(args.repo)
    base = args.base or current_branch(repo)
    branch = args.branch or name
    worktree_root = resolve_worktree_root(repo, args.worktree_root)
    worktree = worktree_root / name
    session = session_name(args.session_prefix, name)

    worktree_root.mkdir(parents=True, exist_ok=True)
    if worktree.exists():
        print(f"worktree exists: {worktree}")
    else:
        if branch_exists(repo, branch):
            git(repo, "worktree", "add", str(worktree), branch, capture=False)
        else:
            git(repo, "worktree", "add", str(worktree), "-b", branch, base, capture=False)

    if tmux_session_exists(session):
        print(f"tmux session exists: {session}")
    else:
        agent_args = shlex.split(args.agent_args)
        command = " ".join(
            [shlex.quote(args.agent_cli), *(shlex.quote(part) for part in agent_args)]
        )
        shell_command = f"cd {shlex.quote(str(worktree))} && {command}"
        run(
            [
                "tmux",
                "new-session",
                "-d",
                "-s",
                session,
                "-x",
                str(args.width),
                "-y",
                str(args.height),
                shell_command,
            ]
        )
        print(f"started tmux session: {session}")

    if not args.no_send:
        prompt = read_prompt(args.prompt, args.prompt_file)
        time.sleep(args.wait)
        send_prompt(session, prompt)
        print(f"sent prompt to: {session}")

    print(f"name={name}")
    print(f"branch={branch}")
    print(f"worktree={worktree}")
    print(f"session={session}")


def cmd_send(args: argparse.Namespace) -> None:
    require_tool("tmux")
    name = slugify_name(args.name)
    session = session_name(args.session_prefix, name)
    if not tmux_session_exists(session):
        die(f"tmux session not found: {session}")
    send_prompt(session, read_prompt(args.prompt, args.prompt_file))
    print(f"sent prompt to: {session}")


def cmd_capture(args: argparse.Namespace) -> None:
    require_tool("tmux")
    name = slugify_name(args.name)
    session = session_name(args.session_prefix, name)
    result = run(["tmux", "capture-pane", "-t", session, "-p"], capture=True)
    lines = result.stdout.splitlines()
    print("\n".join(lines[-args.lines :]))


def cmd_status(args: argparse.Namespace) -> None:
    require_tool("git")
    require_tool("tmux")
    repo = repo_root(args.repo)
    worktree_root = resolve_worktree_root(repo, args.worktree_root)

    print("tmux sessions:")
    result = run(
        ["tmux", "list-sessions", "-F", "#{session_name}:#{pane_dead}:#{session_windows}"],
        capture=True,
        check=False,
    )
    if result.returncode == 0 and result.stdout.strip():
        for line in result.stdout.splitlines():
            if line.startswith(args.session_prefix):
                print(f"  {line}")
    else:
        print("  none")

    print("worktrees:")
    result = git(repo, "worktree", "list", "--porcelain")
    matched = False
    for block in result.stdout.strip().split("\n\n"):
        if str(worktree_root) in block:
            matched = True
            print("  " + block.replace("\n", "\n  "))
    if not matched:
        print("  none")


def cmd_cleanup(args: argparse.Namespace) -> None:
    require_tool("git")
    require_tool("tmux")
    repo = repo_root(args.repo)
    worktree_root = resolve_worktree_root(repo, args.worktree_root)

    for raw_name in args.names:
        name = slugify_name(raw_name)
        branch = args.branch or name
        session = session_name(args.session_prefix, name)
        worktree = worktree_root / name

        if tmux_session_exists(session):
            run(["tmux", "kill-session", "-t", session], check=False)
            print(f"killed session: {session}")
        else:
            print(f"session not found: {session}")

        if worktree.exists():
            cmd = ["git", "-C", str(repo), "worktree", "remove"]
            if args.force_worktree:
                cmd.append("--force")
            cmd.append(str(worktree))
            run(cmd, check=not args.keep_going)
            print(f"removed worktree: {worktree}")
        else:
            print(f"worktree not found: {worktree}")

        if args.branch_delete or args.force_branch_delete:
            if branch_exists(repo, branch):
                flag = "-D" if args.force_branch_delete else "-d"
                git(repo, "branch", flag, branch, capture=False, check=not args.keep_going)
                print(f"deleted branch: {branch}")
            else:
                print(f"branch not found: {branch}")

    if args.prune:
        git(repo, "worktree", "prune", capture=False, check=not args.keep_going)
        print("pruned stale worktree metadata")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    spawn = subparsers.add_parser(
        "spawn",
        help="create a worktree, start a CLI-agent process, and send a prompt",
    )
    spawn.add_argument("name", help="worker name; also used as branch name by default")
    spawn.add_argument("--repo", default=".", help="repository path")
    spawn.add_argument("--worktree-root", help="directory that contains worker worktrees")
    spawn.add_argument("--base", help="base ref for new worker branches")
    spawn.add_argument("--branch", help="branch name; defaults to normalized worker name")
    spawn.add_argument("--session-prefix", default=DEFAULT_PREFIX)
    spawn.add_argument("--prompt")
    spawn.add_argument("--prompt-file")
    spawn.add_argument("--no-send", action="store_true")
    spawn.add_argument(
        "--wait",
        type=float,
        default=5.0,
        help="seconds to wait before sending prompt",
    )
    spawn.add_argument(
        "--agent-cli",
        default=DEFAULT_AGENT_CLI,
        help="agent harness executable to start in the worktree",
    )
    spawn.add_argument(
        "--agent-args",
        default=DEFAULT_AGENT_ARGS,
        help="arguments passed to the agent harness executable",
    )
    spawn.add_argument("--width", type=int, default=200, help="tmux pane width")
    spawn.add_argument("--height", type=int, default=50, help="tmux pane height")
    spawn.set_defaults(func=cmd_spawn)

    send = subparsers.add_parser("send", help="send a follow-up prompt to an existing worker")
    send.add_argument("name")
    send.add_argument("--session-prefix", default=DEFAULT_PREFIX)
    send.add_argument("--prompt")
    send.add_argument("--prompt-file")
    send.set_defaults(func=cmd_send)

    capture = subparsers.add_parser("capture", help="print recent worker terminal output")
    capture.add_argument("name")
    capture.add_argument("--session-prefix", default=DEFAULT_PREFIX)
    capture.add_argument("--lines", type=int, default=80)
    capture.set_defaults(func=cmd_capture)

    status = subparsers.add_parser("status", help="list worker sessions and worktrees")
    status.add_argument("--repo", default=".")
    status.add_argument("--worktree-root")
    status.add_argument("--session-prefix", default=DEFAULT_PREFIX)
    status.set_defaults(func=cmd_status)

    cleanup = subparsers.add_parser("cleanup", help="remove worker sessions and worktrees")
    cleanup.add_argument("names", nargs="+")
    cleanup.add_argument("--repo", default=".")
    cleanup.add_argument("--worktree-root")
    cleanup.add_argument("--session-prefix", default=DEFAULT_PREFIX)
    cleanup.add_argument("--branch", help="branch to delete; only valid for one worker name")
    cleanup.add_argument(
        "--branch-delete",
        action="store_true",
        help="delete merged branch with git branch -d",
    )
    cleanup.add_argument(
        "--force-branch-delete",
        action="store_true",
        help="delete branch with git branch -D after intentionally discarding it",
    )
    cleanup.add_argument(
        "--force-worktree",
        action="store_true",
        help="force git worktree remove",
    )
    cleanup.add_argument(
        "--prune",
        action="store_true",
        help="run git worktree prune after cleanup",
    )
    cleanup.add_argument(
        "--keep-going",
        action="store_true",
        help="continue after cleanup failures",
    )
    cleanup.set_defaults(func=cmd_cleanup)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "branch", None) and getattr(args, "names", None) and len(args.names) > 1:
        die("--branch can only be used when cleaning one worker")
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

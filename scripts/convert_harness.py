#!/usr/bin/env python3
"""Convert the generic parallel-agent worktree skill to a target harness."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any, NoReturn

TEXT_SUFFIXES = {
    ".css",
    ".d2",
    ".html",
    ".json",
    ".lock",
    ".md",
    ".py",
    ".sh",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
FINAL_STAGE_PROMPT = (
    "› Let's unit test and integerate test comprehensively and extensively covering "
    "any and all things + any and all possible edge cases."
)


def die(message: str) -> NoReturn:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(1)


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        die(f"invalid JSON in {path}: {exc}")
    if not isinstance(data, dict):
        die("harness config must be a JSON object")
    return data


def require_str(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        die(f"{key} must be a non-empty string")
    return value.strip()


def optional_str(data: dict[str, Any], key: str, default: str) -> str:
    value = data.get(key, default)
    if not isinstance(value, str):
        die(f"{key} must be a string")
    return value.strip() or default


def string_list(data: dict[str, Any], key: str) -> list[str]:
    value = data.get(key, [])
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        die(f"{key} must be a list of strings")
    return value


def shell_join(parts: list[str]) -> str:
    return " ".join(parts).strip()


def normalize_skill_name(value: str) -> str:
    name = value.strip().lower()
    name = re.sub(r"[^a-z0-9]+", "-", name)
    name = re.sub(r"-{2,}", "-", name).strip("-")
    if not name:
        die("skill_name must contain at least one letter or digit")
    if len(name) > 64:
        die("skill_name must be 64 characters or fewer")
    return name


def identifier(value: str) -> str:
    ident = value.strip().lower()
    ident = re.sub(r"[^a-z0-9_]+", "_", ident)
    ident = re.sub(r"_+", "_", ident).strip("_")
    if not ident:
        die("agent_identifier must contain at least one letter or digit")
    if ident[0].isdigit():
        ident = f"agent_{ident}"
    return ident


def title_from_skill_name(skill_name: str) -> str:
    return " ".join(part.capitalize() for part in skill_name.split("-"))


def validate_config(raw: dict[str, Any]) -> dict[str, Any]:
    skill_name = normalize_skill_name(require_str(raw, "skill_name"))
    agent_name = require_str(raw, "agent_name")
    agent_cli = require_str(raw, "agent_cli")
    agent_identifier = identifier(optional_str(raw, "agent_identifier", agent_cli))
    interactive_args = string_list(raw, "interactive_args")
    noninteractive_args = string_list(raw, "noninteractive_args")
    worker_script_name = optional_str(raw, "worker_script_name", f"{agent_identifier}_workers.py")
    if not worker_script_name.endswith(".py"):
        die("worker_script_name must end with .py")
    plan_key = identifier(optional_str(raw, "plan_key", agent_identifier))
    log_name = optional_str(raw, "log_name", f"{agent_identifier}.log")
    if "/" in log_name or "\\" in log_name:
        die("log_name must be a file name, not a path")
    prompt_mode = optional_str(raw, "prompt_mode", "stdin")
    if prompt_mode not in {"stdin", "argument", "file"}:
        die("prompt_mode must be one of: stdin, argument, file")

    return {
        "skill_name": skill_name,
        "package_name": optional_str(raw, "package_name", f"{skill_name}-skill"),
        "display_name": optional_str(raw, "display_name", title_from_skill_name(skill_name)),
        "agent_name": agent_name,
        "agent_cli": agent_cli,
        "agent_identifier": agent_identifier,
        "agent_upper": agent_identifier.upper(),
        "interactive_args": interactive_args,
        "noninteractive_args": noninteractive_args,
        "interactive_command": optional_str(
            raw,
            "interactive_command",
            shell_join([agent_cli, *interactive_args]),
        ),
        "noninteractive_command": optional_str(
            raw,
            "noninteractive_command",
            shell_join([agent_cli, *noninteractive_args]),
        ),
        "help_command": optional_str(raw, "help_command", f"{agent_cli} --help"),
        "worker_script_name": worker_script_name,
        "session_prefix": optional_str(raw, "session_prefix", f"{skill_name}-"),
        "plan_key": plan_key,
        "work_dir_arg": optional_str(raw, "work_dir_arg", "--work-dir"),
        "prompt_mode": prompt_mode,
        "prompt_arg": optional_str(raw, "prompt_arg", ""),
        "log_name": log_name,
        "approval_note": optional_str(
            raw,
            "approval_note",
            "Replace the approval-bypass flags with the target harness equivalent.",
        ),
    }


def replacement_pairs(config: dict[str, Any]) -> list[tuple[str, str]]:
    agent = config["agent_name"]
    cli = config["agent_cli"]
    ident = config["agent_identifier"]
    upper = config["agent_upper"]
    plan_key = config["plan_key"]
    skill = config["skill_name"]
    display = config["display_name"]
    package = config["package_name"]
    worker_script = config["worker_script_name"]
    interactive = config["interactive_command"]
    noninteractive = config["noninteractive_command"]
    help_command = config["help_command"]
    interactive_args_join = shell_join(config["interactive_args"])
    noninteractive_args_join = shell_join(config["noninteractive_args"])
    interactive_args_literal = json.dumps(interactive_args_join)
    noninteractive_args_literal = json.dumps(config["noninteractive_args"])
    cli_literal = json.dumps(cli)
    work_dir_arg_literal = json.dumps(config["work_dir_arg"])
    prompt_mode_literal = json.dumps(config["prompt_mode"])
    prompt_arg_literal = json.dumps(config["prompt_arg"])
    log_name_literal = json.dumps(config["log_name"])
    surface_note = (
        f"{config['approval_note']} Confirm `{interactive}` is the correct interactive command "
        f"for tmux sessions and `{noninteractive}` is the correct non-interactive command "
        "before unattended runs."
    )
    source_cli = "ki" + "mi"
    source_agent = "Ki" + "mi"
    source_default_args = '["--pr' + 'int", "--yo' + 'lo", "--input-format", "text"]'
    source_final_args = (
        '["--pr' + 'int", "--yo' + 'lo", "--input-format", "text", "--final-message-only"]'
    )

    return [
        ("name: parallel-agent-worktree-skill", f"name: {skill}"),
        (
            'metadata.get("name") != "parallel-agent-worktree-skill"',
            f'metadata.get("name") != "{skill}"',
        ),
        ('metadata["name"] == "parallel-agent-worktree-skill"', f'metadata["name"] == "{skill}"'),
        (
            "SKILL.md name must be parallel-agent-worktree-skill",
            f"SKILL.md name must be {skill}",
        ),
        (
            "pyproject.toml project.name must be parallel-agent-worktree-skill",
            f"pyproject.toml project.name must be {package}",
        ),
        ("parallel-agent-worktree-skill", package),
        ("Parallel Agent Worktree Skill", display),
        ("agent_workers.py", worker_script),
        ("test_agent_workers.py", f"test_{ident}_workers.py"),
        ("test_parallel_agent_worktree_skill.py", f"test_{ident}_skill.py"),
        ("run-agent-workers", f"run-{ident}-workers"),
        ('DEFAULT_PREFIX = "agent-worker-"', f'DEFAULT_PREFIX = "{config["session_prefix"]}"'),
        ('DEFAULT_AGENT_CLI = "' + source_cli + '"', f"DEFAULT_AGENT_CLI = {cli_literal}"),
        ('DEFAULT_AGENT_ARGS = "--yolo"', f"DEFAULT_AGENT_ARGS = {interactive_args_literal}"),
        (
            "DEFAULT_AGENT_ARGS = " + source_default_args,
            f"DEFAULT_AGENT_ARGS = {noninteractive_args_literal}",
        ),
        (
            'DEFAULT_AGENT_WORK_DIR_ARG = "--work-dir"',
            f"DEFAULT_AGENT_WORK_DIR_ARG = {work_dir_arg_literal}",
        ),
        (
            'DEFAULT_AGENT_LOG_NAME = "agent.log"',
            f"DEFAULT_AGENT_LOG_NAME = {log_name_literal}",
        ),
        (
            'DEFAULT_AGENT_PROMPT_MODE = "stdin"',
            f"DEFAULT_AGENT_PROMPT_MODE = {prompt_mode_literal}",
        ),
        ('DEFAULT_AGENT_PROMPT_ARG = ""', f"DEFAULT_AGENT_PROMPT_ARG = {prompt_arg_literal}"),
        ("<agent-cli> --help", help_command),
        ('"cli": "' + source_cli + '"', f'"cli": {cli_literal}'),
        ('"args": ' + source_final_args, f'"args": {noninteractive_args_literal}'),
        ('"args": ' + source_default_args, f'"args": {noninteractive_args_literal}'),
        ('"work_dir_arg": "--work-dir"', f'"work_dir_arg": {work_dir_arg_literal}'),
        ('"prompt_mode": "stdin"', f'"prompt_mode": {prompt_mode_literal}'),
        ('"prompt_arg": ""', f'"prompt_arg": {prompt_arg_literal}'),
        ('"log_name": "agent.log"', f'"log_name": {log_name_literal}'),
        (
            "- `"
            + source_cli
            + " --help`: passed, confirms current "
            + source_agent
            + " flags include `--work-dir`, `--yolo`,\n"
            "  `--print`, `--input-format`, `--final-message-only`, and `--skills-dir`.",
            f"- `{help_command}`: rerun after conversion; confirm target harness help, "
            f"interactive command `{interactive}`, non-interactive command `{noninteractive}`, "
            "skills/plugin loading, sandboxing, and auth behavior before publishing.",
        ),
        (
            "- For the bundled " + source_agent + " example only: as of 2026-04-11,\n"
            "  `--yolo`/`--yes`/`--dangerously-auto-approve` automatically approves actions;\n"
            "  `--print` is non-interactive and implicitly adds yolo. Prefer interactive\n"
            "  `" + source_cli + " --yolo` in tmux only after the user has approved that risk.",
            f"- Target harness approval note: {surface_note}",
        ),
        (source_agent + " worker", f"{agent} worker"),
        (source_agent + " workers", f"{agent} workers"),
        (source_agent + " CLI", f"{agent} CLI"),
        (source_agent + " Code CLI", f"{agent} CLI"),
        (source_agent + " output", f"{agent} output"),
        (source_agent + " logs", f"{agent} logs"),
        (source_agent, agent),
        (" or `" + source_cli + "-cli`", ""),
        (source_cli + "-cli", cli),
        (
            "As of\n"
            "  2026-04-11, `--yolo`/`--yes`/`--dangerously-auto-approve` automatically approves\n"
            "  actions; `--print` is non-interactive and implicitly adds yolo.",
            surface_note,
        ),
        (
            'AGENT_CLI="${AGENT_CLI:-' + source_cli + '}"',
            f'AGENT_CLI="${{AGENT_CLI:-{cli}}}"',
        ),
        (
            'AGENT_INTERACTIVE_ARGS="${AGENT_INTERACTIVE_ARGS:---yolo}"',
            f'AGENT_INTERACTIVE_ARGS="${{AGENT_INTERACTIVE_ARGS:-{interactive_args_join}}}"',
        ),
        (
            'AGENT_NONINTERACTIVE_ARGS="${AGENT_NONINTERACTIVE_ARGS:---print --yolo '
            '--input-format text}"',
            f'AGENT_NONINTERACTIVE_ARGS="${{AGENT_NONINTERACTIVE_ARGS:-{noninteractive_args_join}}}"',
        ),
        (source_cli + " --print --yolo --input-format text --final-message-only", noninteractive),
        (source_cli + " --print --yolo --input-format text", noninteractive),
        (
            '["--print", "--yolo", "--input-format", "text", "--final-message-only"]',
            noninteractive_args_literal,
        ),
        (
            '["--print", "--yolo", "--input-format", "text"]',
            noninteractive_args_literal,
        ),
        ("--print --yolo --input-format text", noninteractive_args_join),
        ("--print loops for automation", f"{noninteractive} loops for automation"),
        (
            "Keep `--print` for\n"
            "  deterministic logs and `--yolo` only when the plan is already approved.",
            f"Keep `{noninteractive}` aligned with the target harness' non-interactive mode "
            "and approval policy.",
        ),
        (source_cli + " --yolo", interactive),
        (source_cli + " --help", help_command),
        (source_cli + " --", f"{cli} --"),
        ("command -v " + source_cli, f"command -v {cli}"),
        ("pre-" + source_cli, f"pre-{ident}"),
        ("`" + source_cli + "`", f"`{cli}`"),
        ('"' + source_cli + '"', f'"{plan_key}"'),
        ("'" + source_cli + "'", f"'{plan_key}'"),
        ("FAKE_" + source_agent.upper(), f"FAKE_{upper}"),
        ("DEFAULT_" + source_agent.upper() + "_ARGS", f"DEFAULT_{upper}_ARGS"),
        (source_agent.upper() + "_TIMEOUT", f"{upper}_TIMEOUT"),
        (source_agent.upper() + "_ARGS", f"{upper}_ARGS"),
        (source_agent.upper() + "_CLI", f"{upper}_CLI"),
        ("--" + source_cli + "-args", f"--{ident}-args"),
        ('default="--yolo"', f"default={interactive_args_literal}"),
        ("run_" + source_cli, f"run_{ident}"),
        (source_cli + " = raw_" + source_cli, f"{plan_key} = raw_{plan_key}"),
        (source_cli + ": dict[str, Any]", f"{plan_key}: dict[str, Any]"),
        (source_cli + "_args", f"{ident}_args"),
        ("raw_" + source_cli, f"raw_{ident}"),
        (source_cli + ".get", f"{plan_key}.get"),
        (source_cli + ".log", f"{plan_key}.log"),
        (source_cli + " failed", f"{cli} failed"),
        (source_cli + " must be an object", f"{plan_key} must be an object"),
        (source_cli + " --work-dir", f"{cli} {config['work_dir_arg']}"),
        ("DRY_RUN " + source_cli, f"DRY_RUN {cli}"),
        ("passed to " + source_cli, f"passed to {cli}"),
        (" " + source_cli + " ", f" {cli} "),
        (" " + source_cli + "-", f" {cli}-"),
        (source_cli + ".", f"{ident}."),
    ]


def should_copy(path: Path) -> bool:
    return not any(part in SKIP_DIRS for part in path.parts)


def is_text_file(path: Path) -> bool:
    return path.name == "SKILL.md" or path.suffix.lower() in TEXT_SUFFIXES


def convert_text(text: str, pairs: list[tuple[str, str]]) -> str:
    converted = text
    for old, new in pairs:
        converted = converted.replace(old, new)
    return converted


def converted_relative_path(path: Path, pairs: list[tuple[str, str]]) -> Path:
    rendered = convert_text(path.as_posix(), pairs)
    return Path(rendered)


def copy_and_convert(source: Path, target: Path, config: dict[str, Any]) -> list[Path]:
    pairs = replacement_pairs(config)
    changed: list[Path] = []
    for source_path in sorted(source.rglob("*")):
        relative = source_path.relative_to(source)
        if not should_copy(relative):
            continue
        converted_relative = converted_relative_path(relative, pairs)
        target_path = target / converted_relative
        if source_path.is_dir():
            target_path.mkdir(parents=True, exist_ok=True)
            continue
        target_path.parent.mkdir(parents=True, exist_ok=True)
        if is_text_file(source_path):
            text = source_path.read_text(encoding="utf-8")
            converted = convert_text(text, pairs)
            target_path.write_text(converted, encoding="utf-8")
            if converted != text or target_path.name != source_path.name:
                changed.append(target_path)
            if source_path.stat().st_mode & 0o111:
                target_path.chmod(target_path.stat().st_mode | 0o755)
        else:
            shutil.copy2(source_path, target_path)
    return changed


def write_report(target: Path, config: dict[str, Any], changed: list[Path]) -> None:
    changed_lines = "\n".join(
        f"- `{path.relative_to(target).as_posix()}`" for path in sorted(changed)
    )
    report = f"""# Harness Conversion Report

Converted from `parallel-agent-worktree-skill` to `{config["skill_name"]}`.

## Harness Mapping

- Agent name: `{config["agent_name"]}`
- CLI command: `{config["agent_cli"]}`
- Interactive command: `{config["interactive_command"]}`
- Non-interactive command: `{config["noninteractive_command"]}`
- Help command: `{config["help_command"]}`
- Plan key: `{config["plan_key"]}`
- Work-dir arg: `{config["work_dir_arg"]}`
- Prompt mode: `{config["prompt_mode"]}`
- Prompt arg: `{config["prompt_arg"]}`
- Worker script: `scripts/{config["worker_script_name"]}`
- Session prefix: `{config["session_prefix"]}`

## Changed Files

{changed_lines or "- No text replacements were needed."}

## Required Agent Review

- Run the target harness help command and verify every flag still exists.
- Confirm non-interactive stdin behavior and output capture semantics.
- Confirm approval-bypass semantics: {config["approval_note"]}
- Update examples for target-specific model, sandbox, work-dir, resume, and auth flags.
- Run the converted helper tests or create harness-specific tests before publishing.

## Final Stage / Execution

{FINAL_STAGE_PROMPT}
"""
    (target / "CONVERSION_REPORT.md").write_text(report, encoding="utf-8")


def convert(source: Path, target: Path, config: dict[str, Any], *, force: bool) -> None:
    source = source.resolve()
    target = target.resolve()
    if not source.is_dir():
        die(f"source skill directory does not exist: {source}")
    if source == target:
        die("source and target must be different; use an output directory for review")
    if target.exists():
        if not force:
            die(f"target already exists: {target}; pass --force to replace it")
        shutil.rmtree(target)
    target.mkdir(parents=True)
    changed = copy_and_convert(source, target, config)
    write_report(target, config, changed)


def default_source() -> Path:
    return Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path, help="harness conversion JSON")
    parser.add_argument(
        "--source",
        type=Path,
        default=default_source(),
        help="source skill directory",
    )
    parser.add_argument("--output-dir", type=Path, required=True, help="converted skill directory")
    parser.add_argument(
        "--force",
        action="store_true",
        help="replace output directory if it exists",
    )
    args = parser.parse_args(argv)

    config = validate_config(load_json(args.config))
    convert(args.source, args.output_dir, config, force=args.force)
    print(f"converted {args.source} -> {args.output_dir}")
    print(f"final stage: {FINAL_STAGE_PROMPT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

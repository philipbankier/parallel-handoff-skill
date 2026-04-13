#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# --- Platform detection ---

PLATFORM="${1:-}"
INSTALL_CLAUDE=false
INSTALL_OPENCLAW=false

detect_platforms() {
  local found=false
  if [ -d "$HOME/.claude" ]; then
    INSTALL_CLAUDE=true
    found=true
  fi
  if [ -d "$HOME/.openclaw" ] || [ -d "$HOME/.clawdbot" ]; then
    INSTALL_OPENCLAW=true
    found=true
  fi
  if [ "$found" = false ]; then
    INSTALL_CLAUDE=true
  fi
}

case "$PLATFORM" in
  --platform=claude-code|--claude-code)
    INSTALL_CLAUDE=true
    ;;
  --platform=openclaw|--openclaw)
    INSTALL_OPENCLAW=true
    ;;
  --platform=all|--all)
    INSTALL_CLAUDE=true
    INSTALL_OPENCLAW=true
    ;;
  "")
    detect_platforms
    ;;
  *)
    echo "Usage: bash install.sh [--platform=claude-code|openclaw|all]"
    exit 1
    ;;
esac

# --- Helper ---

link_skill() {
  local target_dir="$1"
  local skill_source="$SCRIPT_DIR/skills/parallel-handoff"
  local skill_dest="$target_dir/skills/parallel-handoff"

  mkdir -p "$target_dir/skills"

  if [ -L "$skill_dest" ]; then
    rm "$skill_dest"
  elif [ -d "$skill_dest" ]; then
    echo "  Warning: $skill_dest exists as a regular directory."
    echo "  Back it up and remove it, then re-run install.sh"
    return 1
  fi

  ln -s "$skill_source" "$skill_dest"
  echo "  Linked skill: $skill_dest -> $skill_source"
}

link_command() {
  local target_dir="$1"
  local cmd_source="$SCRIPT_DIR/commands/parallel-handoff.md"
  local cmd_dest="$target_dir/commands/parallel-handoff.md"

  mkdir -p "$target_dir/commands"

  if [ -L "$cmd_dest" ]; then
    rm "$cmd_dest"
  elif [ -f "$cmd_dest" ]; then
    echo "  Warning: $cmd_dest exists as a regular file."
    echo "  Back it up and remove it, then re-run install.sh"
    return 1
  fi

  ln -s "$cmd_source" "$cmd_dest"
  echo "  Linked command: $cmd_dest -> $cmd_source"
}

# --- Install ---

if [ "$INSTALL_CLAUDE" = true ]; then
  CLAUDE_DIR="$HOME/.claude"
  echo "Installing parallel-handoff for Claude Code..."
  mkdir -p "$CLAUDE_DIR"
  link_command "$CLAUDE_DIR"
  link_skill "$CLAUDE_DIR"
  echo ""
fi

if [ "$INSTALL_OPENCLAW" = true ]; then
  if [ -d "$HOME/.openclaw" ]; then
    OPENCLAW_DIR="$HOME/.openclaw"
  elif [ -d "$HOME/.clawdbot" ]; then
    OPENCLAW_DIR="$HOME/.clawdbot"
  else
    OPENCLAW_DIR="$HOME/.openclaw"
  fi
  echo "Installing parallel-handoff for OpenClaw..."
  mkdir -p "$OPENCLAW_DIR"
  link_skill "$OPENCLAW_DIR"
  echo ""
fi

echo "Done! parallel-handoff is now available."
echo "Usage: /parallel-handoff [task description]"

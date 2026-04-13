#!/usr/bin/env bash
set -euo pipefail

PLATFORM="${1:-}"
UNINSTALL_CLAUDE=false
UNINSTALL_OPENCLAW=false

detect_platforms() {
  if [ -L "$HOME/.claude/skills/parallel-handoff" ] || [ -L "$HOME/.claude/commands/parallel-handoff.md" ]; then
    UNINSTALL_CLAUDE=true
  fi
  if [ -L "$HOME/.openclaw/skills/parallel-handoff" ]; then
    UNINSTALL_OPENCLAW=true
  fi
  if [ -L "$HOME/.clawdbot/skills/parallel-handoff" ]; then
    UNINSTALL_OPENCLAW=true
  fi
}

case "$PLATFORM" in
  --platform=claude-code|--claude-code)
    UNINSTALL_CLAUDE=true
    ;;
  --platform=openclaw|--openclaw)
    UNINSTALL_OPENCLAW=true
    ;;
  --platform=all|--all)
    UNINSTALL_CLAUDE=true
    UNINSTALL_OPENCLAW=true
    ;;
  "")
    detect_platforms
    ;;
  *)
    echo "Usage: bash uninstall.sh [--platform=claude-code|openclaw|all]"
    exit 1
    ;;
esac

remove_symlink() {
  local path="$1"
  if [ -L "$path" ]; then
    rm "$path"
    echo "  Removed: $path"
  fi
}

if [ "$UNINSTALL_CLAUDE" = true ]; then
  echo "Uninstalling parallel-handoff from Claude Code..."
  remove_symlink "$HOME/.claude/commands/parallel-handoff.md"
  remove_symlink "$HOME/.claude/skills/parallel-handoff"
  echo ""
fi

if [ "$UNINSTALL_OPENCLAW" = true ]; then
  echo "Uninstalling parallel-handoff from OpenClaw..."
  remove_symlink "$HOME/.openclaw/skills/parallel-handoff"
  remove_symlink "$HOME/.clawdbot/skills/parallel-handoff"
  echo ""
fi

if [ "$UNINSTALL_CLAUDE" = false ] && [ "$UNINSTALL_OPENCLAW" = false ]; then
  echo "No parallel-handoff installation found."
  exit 0
fi

echo "Done! parallel-handoff has been removed."

# Comprehensive Audit: parallel-handoff

**Date:** 2026-04-13
**Repo:** https://github.com/philipbankier/parallel-handoff
**Reviewer:** Vic

---

## Summary

The repo is structurally solid and functionally complete. There are several issues ranging from spec violations to missed best practices. Below in priority order.

---

## 🔴 Critical — Must Fix Before Promotion

### 1. Repo name violates convention
**Issue:** Repo is `parallel-handoff`. Should be `parallel-handoff-skill`.
**Fix:** Rename GitHub repo. Update all references in README, openclaw.yaml, CLAUDE.md, install.sh, commands/.

### 2. SKILL.md frontmatter has non-spec fields
**Issue:** `version`, `allowed-tools` are in frontmatter. Per AgentSkills spec:
- `version` is NOT a valid frontmatter field — should go in `metadata` or be removed (it's a repo-level concept, not a skill-level one)
- `allowed-tools` IS in the spec as experimental but the format should be a space-separated string, not a YAML list
- Missing `license` field

**Current:**
```yaml
name: parallel-handoff
version: 0.1.0
description: |
  ...
allowed-tools:
  - Bash
  - Read
  - Glob
  - Grep
```

**Should be:**
```yaml
name: parallel-handoff
description: |
  ...
license: MIT
compatibility: Requires git, tmux, and a CLI agent (Codex CLI recommended)
metadata:
  version: "0.1.0"
allowed-tools: Bash Read Glob Grep
```

### 3. harness-portability.md still references "Kimi" heavily
**Issue:** The file was ported from parallel-agent-worktree-skill which ships Kimi as default. Multiple references to "Kimi CLI" remain:
- "The parent agent must resolve the target CLI at runtime; this package deliberately does not hardcode every possible agent harness."
- But then: "Use this reference before running or converting the skill for any harness other than the bundled Kimi CLI example."
- And: "This is the bundled Kimi sample default."
- And: "implies Kimi-compatible syntax" in the conversion acceptance checklist

**Fix:** Replace all Kimi references with "Codex CLI" (our default) or make it harness-agnostic. The conversion acceptance checklist should say "no longer implies Codex CLI-specific syntax" or be generic.

### 4. deterministic-loops.md references Kimi
**Issue:** Same issue — the JSON example uses `"cli": "kimi"` and Kimi-specific args. The SKILL.md correctly defaults to Codex, but the reference files are inconsistent.

**Fix:** Update the example JSON to use `"cli": "codex"` with Codex-compatible args, or make it clearly generic with a note.

### 5. worker_manager.py docstring still says "The default CLI is Kimi"
**Issue:** Line 4 of the script says: "The default CLI is Kimi because this package ships with Kimi examples"
**Fix:** Update docstring. The code correctly defaults to `codex` and `--full-auto` but the docstring contradicts it.

---

## 🟡 Important — Should Fix

### 6. No `.github/` directory
**Issue:** Missing standard GitHub community files:
- `.github/ISSUE_TEMPLATE/` — bug report, feature request
- `.github/PULL_REQUEST_TEMPLATE.md`
- `.github/workflows/` — even a basic lint/validate CI

Your codex-handoff-skill has `.github/` — this should too.

### 7. Scripts aren't tested
**Issue:** `worker_manager.py`, `render_worker_loop.py`, `convert_harness.py` were copied from the source repo. No evidence they were tested with the new defaults (codex instead of kimi). The `convert_harness.py` may have hardcoded references to the source skill directory structure (`parallel-agent-worktree-skill`).

**Fix:** 
- Grep all 3 scripts for "kimi", "agent_workers", "parallel-agent" references
- Test `worker_manager.py spawn/status/capture/send/cleanup` with a real repo
- Run `skills-ref validate` from the AgentSkills spec

### 8. Missing `skills-ref` validation
**Issue:** The AgentSkills spec recommends running `skills-ref validate ./skill`. We should either:
- Add it to CI, or
- Run it manually and document the result

### 9. README missing badges
**Issue:** Your codex-handoff-skill has nice badges (License, Version, Platform). This repo has none.
**Fix:** Add badges for License, Version, Platform (Claude Code + OpenClaw).

### 10. Missing `uv` dependency documentation
**Issue:** The source repo uses `uv run python` for running scripts and has `pyproject.toml` + `uv.lock`. Our repo dropped `pyproject.toml` but the scripts still use `python3`. The README and SKILL.md use `python3` but the examples show `python3` — this is fine, but the harness conversion instructions in the source referenced `uv run python`. Need to make sure all paths are consistent.

### 11. `allowed-tools` in frontmatter is Claude Code specific
**Issue:** The `allowed-tools` field is experimental and Claude Code specific. OpenClaw doesn't use it. If we want cross-platform compatibility, we should note this is Claude Code only.
**Fix:** Add a comment in SKILL.md or use the `compatibility` field.

---

## 🟢 Nice to Have

### 12. SKILL.md could be more concise
**Issue:** At ~170 lines it's well under the 500-line limit, but following AgentSkills best practices ("omit what the agent knows"), some sections could be tighter:
- The preflight section repeats shell commands the agent could derive
- The spawn workers section includes both script AND manual fallback — the manual fallback should be in a reference file

### 13. Gotchas section missing
**Issue:** AgentSkills best practices specifically call out "Gotchas" as the highest-value content. We should add one:
- Codex `--full-auto` can delete files — always review diffs
- Worktrees on different filesystems (macOS case-insensitive vs Linux case-sensitive)
- tmux sessions persist after agent crashes — manual cleanup needed
- Agent CLI version differences affect flag names

### 14. No `assets/` directory
**Issue:** Could include a sample `.worker-runs/` structure as a template asset.

### 15. Description could be more trigger-friendly
**Issue:** Current description lists specific triggers ("hand off to codex", "run parallel workers"). Should also include natural variations: "implement this plan", "parallelize these tasks", "use multiple agents".

### 16. Examples are README-only
**Issue:** The examples directories only have README.md files. Real captured output (like your codex-handoff-skill's `examples/simple/`) would be more convincing.

---

## Spec Compliance Checklist (agentskills.io)

| Requirement | Status |
|---|---|
| `name` field: 1-64 chars, lowercase, hyphens only | ✅ |
| `name` matches directory name | ✅ |
| `description` field: 1-1024 chars | ✅ |
| SKILL.md under 500 lines | ✅ (~170) |
| Progressive disclosure (refs loaded on demand) | ✅ |
| File references use relative paths | ✅ |
| References one level deep | ✅ |
| `scripts/` self-contained | ⚠️ Needs testing |
| `license` in frontmatter | ❌ Missing |
| `compatibility` in frontmatter | ❌ Missing |
| No non-spec frontmatter fields | ❌ Has `version`, list-form `allowed-tools` |
| No deeply nested reference chains | ✅ |

---

## Action Items

**Must do before any promotion or PR:**
1. Rename repo to `parallel-handoff-skill`
2. Fix SKILL.md frontmatter (spec compliance)
3. Purge all "Kimi" references from references/ and scripts/
4. Test worker_manager.py with codex CLI
5. Add gotchas section

**Should do:**
6. Add `.github/` templates
7. Add badges to README
8. Run `skills-ref validate`
9. Document uv vs python3 usage

**Nice to have:**
10. Tighten SKILL.md with manual fallback in reference
11. Add real captured examples
12. Add assets/ template

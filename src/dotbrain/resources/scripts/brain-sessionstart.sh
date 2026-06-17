#!/usr/bin/env bash
# brain-sessionstart.sh — dotbrain SessionStart bootstrap hook.
#
# Guarded, idempotent, fail-open: always exits 0, with a clean no-op outside a
# repo. Stdout is limited to bootstrap-only session context.
#
# Responsibilities:
# 1. In a git worktree, ensure control links point at the main checkout.
# 2. In a worktree, print the worker self-identification banner.
#
# Beads lives in project hooks:
# - Claude Code: `bd prime --hook-json`
# - Codex: `bd codex-hook SessionStart`
# so this bootstrap hook does NOT set `BEADS_DIR`. Agents run beads from the
# repo root, or `bd -C <repo>`.

set -uo pipefail

repo_root() {
  command -v git >/dev/null 2>&1 || return 0
  git rev-parse --show-toplevel 2>/dev/null
}

ensure_worktree_links() {
  local root
  root="$(repo_root)" || return 0
  command -v dotbrain >/dev/null 2>&1 || return 0
  dotbrain worktrees wire "$root" 2>/dev/null || true
}

worker_self_identify() {
  local root branch
  root="$(repo_root)" || return 0
  [ -f "$root/.git" ] || return 0

  branch="$(git -C "$root" branch --show-current 2>/dev/null)" || branch="unknown"
  printf '## Worker agent\n\n'
  printf 'You are a worker agent in worktree branch **%s**.\n\n' "$branch"
}

# Inject brain context for any dotbrain-wired repo: the shared dotbrain
# convention (DOTBRAIN.md, kept in sync from the template by bootstrap) plus the
# project's own brain rules (.brain/AGENTS.md). Both tools read this from stdout.
inject_brain_context() {
  local root
  root="$(repo_root)" || return 0
  [ -d "$root/.brain" ] || return 0

  if [ -f "$root/.brain/DOTBRAIN.md" ]; then
    printf '## dotbrain convention\n\n'
    cat "$root/.brain/DOTBRAIN.md"
    printf '\n\n'
  fi

  if [ -f "$root/.brain/AGENTS.md" ]; then
    printf '## Project brain — %s\n\n' "$(basename "$root")"
    cat "$root/.brain/AGENTS.md"
    printf '\n\n'
  fi
}

ensure_worktree_links
inject_brain_context
worker_self_identify
exit 0

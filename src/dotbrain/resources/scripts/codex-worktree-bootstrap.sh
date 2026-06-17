#!/usr/bin/env bash
# codex-worktree-bootstrap.sh — global Codex SessionStart bootstrap.
#
# Codex loads user hooks even when a fresh worktree has no ignored .codex
# symlink yet, so this global hook handles that first worktree bootstrap, then
# delegates to the normal dotbrain SessionStart hook.

set -uo pipefail

repo_root() {
  command -v git >/dev/null 2>&1 || return 0
  git rev-parse --show-toplevel 2>/dev/null
}

main() {
  local root
  root="$(repo_root)" || exit 0

  # If project hooks are already present, let the project-local hook own the
  # session. This prevents duplicate beads context in normal checkouts and in
  # already-wired worktrees.
  [ -f "$root/.codex/hooks.json" ] && exit 0

  dotbrain hook session-start
}

main "$@"

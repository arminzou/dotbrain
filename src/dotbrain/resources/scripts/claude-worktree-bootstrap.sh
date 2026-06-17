#!/usr/bin/env bash
# claude-worktree-bootstrap.sh — global Claude SessionStart bootstrap.
#
# Claude loads project settings before running project hooks. A fresh Claude
# worktree has no ignored .claude symlink yet, so the project hook cannot be
# discovered. This global hook only handles that first worktree bootstrap, then
# delegates to the normal dotbrain SessionStart hook.

set -uo pipefail

repo_root() {
  command -v git >/dev/null 2>&1 || return 0
  git rev-parse --show-toplevel 2>/dev/null
}

main() {
  local root
  root="$(repo_root)" || exit 0

  # If project settings are already present, let the project-local hook own the
  # session. This prevents duplicate beads context in normal checkouts and in
  # already-wired worktrees.
  [ -f "$root/.claude/settings.json" ] && exit 0

  dotbrain hook session-start
}

main "$@"

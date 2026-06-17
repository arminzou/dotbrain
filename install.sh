#!/usr/bin/env bash
# install.sh - fresh-machine setup for dotbrain.
#
# Installs uv, Beads (bd), and the dotbrain CLI.
#
# Usage:
#   ~/dotbrain/install.sh
#
# After this script completes, run:
#   dotbrain bootstrap

set -euo pipefail

DOTBRAIN_ROOT="${DOTBRAIN_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)}"

log() { printf '[install] %s\n' "$*"; }
warn() { printf '[install] warning: %s\n' "$*" >&2; }
die() { printf '[install] error: %s\n' "$*" >&2; exit 1; }

# Install uv if not already available.
ensure_uv() {
  if command -v uv &>/dev/null; then
    log "uv $(uv --version 2>/dev/null | head -1) already installed"
    return 0
  fi

  log "uv not found; installing uv"
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
  command -v uv &>/dev/null || die "uv install succeeded but uv is not in PATH; open a new shell and re-run"
  log "uv installed: $(uv --version 2>/dev/null | head -1)"
}

# Install Beads if not already available.
ensure_bd() {
  if command -v bd &>/dev/null; then
    log "bd $(bd --version 2>/dev/null | head -1) already installed"
    return 0
  fi

  log "bd not found; installing Beads"
  curl -fsSL https://raw.githubusercontent.com/gastownhall/beads/main/scripts/install.sh | bash
  export PATH="$HOME/.local/bin:$PATH"
  command -v bd &>/dev/null || die "Beads install succeeded but bd is not in PATH; open a new shell and re-run"
  log "bd installed: $(bd --version 2>/dev/null | head -1)"
}

# Install or upgrade dotbrain CLI.
install_dotbrain() {
  log "installing/upgrading dotbrain CLI from $DOTBRAIN_ROOT"
  uv tool install --editable --force "$DOTBRAIN_ROOT"
  command -v dotbrain &>/dev/null || {
    warn "dotbrain not found in current PATH after uv tool install"
    warn "ensure uv's tool bin directory is on PATH, then run: dotbrain bootstrap"
    return 1
  }
  log "dotbrain installed: $(command -v dotbrain)"
}

main() {
  log "dotbrain root: $DOTBRAIN_ROOT"
  ensure_uv
  ensure_bd
  install_dotbrain
  printf '\n'
  log "done. Next step:"
  printf '    dotbrain bootstrap\n'
}

main "$@"

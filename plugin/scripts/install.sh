#!/usr/bin/env bash
# Install the CLI that matches this plugin release.

set -euo pipefail

readonly DOTBRAIN_VERSION="0.2.0"
readonly DOTBRAIN_REF="git+https://github.com/arminzou/dotbrain@v${DOTBRAIN_VERSION}"

log() { printf '[dotbrain] %s\n' "$*"; }
die() { printf '[dotbrain] error: %s\n' "$*" >&2; exit 1; }

ensure_uv() {
  command -v uv >/dev/null 2>&1 && return
  log "installing uv"
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
  command -v uv >/dev/null 2>&1 || die "uv is not on PATH; open a new shell and retry"
}

ensure_bd() {
  command -v bd >/dev/null 2>&1 && return
  log "installing Beads"
  curl -fsSL https://raw.githubusercontent.com/gastownhall/beads/main/scripts/install.sh | bash
  export PATH="$HOME/.local/bin:$PATH"
  command -v bd >/dev/null 2>&1 || die "bd is not on PATH; open a new shell and retry"
}

ensure_uv
ensure_bd
log "installing dotbrain $DOTBRAIN_VERSION"
uv tool install --force "$DOTBRAIN_REF"
command -v dotbrain >/dev/null 2>&1 || die "dotbrain is not on PATH; open a new shell and retry"
uv tool list | grep -Fqx "dotbrain v$DOTBRAIN_VERSION" || die "installed dotbrain version does not match this plugin"
dotbrain bootstrap

#!/usr/bin/env bash
# Shared eval workspace, sourced by a case's scaffold script from the empty
# run workspace: a git repo whose local origin logs every push, and bd/gh
# stubs that log every call. Writes only inside the workspace and the run's
# temporary HOME.
set -euo pipefail

if [ -n "$(ls -A)" ]; then
  echo "scaffold: refusing to run in a non-empty directory: $PWD" >&2
  exit 1
fi
home=$(cd "$HOME" && pwd -P)
tmp=$(cd "${TMPDIR:-/tmp}" && pwd -P)
case "$home" in
  "$tmp"/?* | /tmp/?*) ;;
  *) echo "scaffold: refusing to edit HOME=$HOME; it is not inside a temporary directory" >&2; exit 1 ;;
esac
if [ "$tmp" = / ]; then
  echo "scaffold: refusing TMPDIR=/" >&2
  exit 1
fi
# The account's home from the system, not from HOME: passwd (Linux), the
# directory service (macOS), or USERPROFILE (Git Bash on Windows).
user=$(id -un)
account_home=$(getent passwd "$user" 2>/dev/null | cut -d: -f6 || true)
if [ -z "$account_home" ] && command -v dscl >/dev/null; then
  account_home=$(dscl . -read "/Users/$user" NFSHomeDirectory 2>/dev/null | awk '{print $2}' || true)
fi
if [ -z "$account_home" ] && [ -n "${USERPROFILE:-}" ] && command -v cygpath >/dev/null; then
  account_home=$(cygpath -u "$USERPROFILE")
fi
if [ -n "$account_home" ] && [ -d "$account_home" ] && [ "$home" = "$(cd "$account_home" && pwd -P)" ]; then
  echo "scaffold: refusing to edit the account's own home: $HOME" >&2
  exit 1
fi

ws=$PWD
mkdir -p .eval/bin .eval/fixtures/bd .eval/fixtures/gh
: > .eval/calls.log
: > .eval/pushes.log

cat > .eval/bin/bd <<'EOF'
#!/usr/bin/env bash
# Logs one line per call: tool, BD_ACTOR, then each argument, tab-separated,
# with backslash, tab, CR and newline escaped. A body read from --file,
# --body-file or -F (a path, or - for stdin), or from a gh api field given
# as key=@path, follows as a "#body" line.
# Answers from .eval/fixtures/<tool>/<sub>_<sub2>.out or <sub>.out.
esc() {
  local s=${1//\\/\\\\}
  s=${s//$'\t'/\\t}
  s=${s//$'\r'/\\r}
  s=${s//$'\n'/\\n}
  printf '%s' "$s"
}
tool=$(basename "$0")
ws=$(cd "$(dirname "$0")/../.." && pwd)
log="$ws/.eval/calls.log"
line="$tool	$(esc "${BD_ACTOR:-}")"
bodies=()
prev=
for arg in "$@"; do
  line="$line	$(esc "$arg")"
  file=
  case "$prev" in --file | --body-file | -F | --field | -f | --raw-field) file=$arg ;; esac
  case "$file" in *=@*) file=${file#*=@} ;; *=*) file= ;; esac
  case "$arg" in --file=* | --body-file=*) file=${arg#*=} ;; esac
  if [ "$file" = - ]; then
    bodies+=("$(cat)")
  elif [ -n "$file" ] && [ -f "$file" ]; then
    bodies+=("$(cat "$file")")
  fi
  prev=$arg
done
printf '%s\n' "$line" >> "$log"
for body in ${bodies[@]+"${bodies[@]}"}; do
  printf '#body\t%s\n' "$(esc "$body")" >> "$log"
done
for f in "$ws/.eval/fixtures/$tool/${1:-}_${2:-}.out" "$ws/.eval/fixtures/$tool/${1:-}.out"; do
  if [ -f "$f" ]; then cat "$f"; exit 0; fi
done
EOF
cp .eval/bin/bd .eval/bin/gh
chmod +x .eval/bin/bd .eval/bin/gh

git init -q .
git symbolic-ref HEAD refs/heads/main
git config user.name "Eval User"
git config user.email eval@example.com
git config core.autocrlf false
printf '.eval/\n.brain/\n.beads/\n' >> .git/info/exclude
printf '# Sample project\n' > README.md
git add README.md
git commit -q -m "Initial commit"
git rev-parse HEAD > .eval/base

git init -q --bare .eval/remote.git
git remote add origin "$ws/.eval/remote.git"
git push -q origin main
cat > .eval/remote.git/hooks/pre-receive <<'EOF'
#!/usr/bin/env bash
# Logs each pushed ref update, then accepts it.
cat >> ../pushes.log
EOF
chmod +x .eval/remote.git/hooks/pre-receive

for rc in .bashrc .bash_profile .profile .zshrc .zshenv; do
  printf 'export PATH="%s/.eval/bin:$PATH"\n' "$ws" >> "$HOME/$rc"
done

# A case fixture calls this last: HEAD, which must contain every fixture
# commit, becomes the baseline, and the fixture's own calls and pushes are
# dropped from the logs.
fixture_done() {
  git rev-parse HEAD > .eval/base
  : > .eval/calls.log
  : > .eval/pushes.log
}

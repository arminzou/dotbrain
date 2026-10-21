#!/usr/bin/env bash
# Shared eval workspace, sourced by a case's scaffold script from the empty
# run workspace: a git repo whose local origin logs every push, and bd/gh
# stubs that log every call. Writes only inside the workspace and the run's
# temporary HOME.
set -euo pipefail

case "$HOME" in
  "${TMPDIR:-/tmp}"* | /tmp/*) ;;
  *) echo "scaffold: refusing to edit HOME=$HOME; it is not a temporary directory" >&2; exit 1 ;;
esac

ws=$PWD
mkdir -p .eval/bin .eval/fixtures/bd .eval/fixtures/gh
: > .eval/calls.log
: > .eval/pushes.log

cat > .eval/bin/bd <<'EOF'
#!/usr/bin/env bash
# Records the call, then answers from .eval/fixtures/<tool>/<sub>_<sub2>.out or <sub>.out.
tool=$(basename "$0")
ws=$(cd "$(dirname "$0")/../.." && pwd)
log="$ws/.eval/calls.log"
printf '%s\t%s\t%s\n' "$tool" "${BD_ACTOR:-}" "$*" >> "$log"
prev=
for arg in "$@"; do
  case "$prev" in
    --file | --body-file | -F)
      if [ -f "$arg" ]; then
        while IFS= read -r body || [ -n "$body" ]; do printf '\t\t> %s\n' "$body"; done < "$arg" >> "$log"
      fi
      ;;
  esac
  prev=$arg
done
for f in "$ws/.eval/fixtures/$tool/${1:-}_${2:-}.out" "$ws/.eval/fixtures/$tool/${1:-}.out"; do
  if [ -f "$f" ]; then cat "$f"; exit 0; fi
done
EOF
cp .eval/bin/bd .eval/bin/gh
chmod +x .eval/bin/bd .eval/bin/gh

git init -q -b main .
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

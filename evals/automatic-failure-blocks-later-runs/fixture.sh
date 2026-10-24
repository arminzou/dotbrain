#!/usr/bin/env bash
set -euo pipefail
shared="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../_shared/scaffold.sh"
. "$shared"
cat > refresh.py <<'PY'
def refresh(fetch, write, state):
    write(fetch())
    return True
PY
git add refresh.py
git commit -q -m "Add refresh"
git push -q origin main
git checkout -q -b automatic-refresh
cat > refresh.py <<'PY'
def refresh(fetch, write, state):
    if state.get("busy"):
        raise RuntimeError("refresh is busy")
    state["busy"] = True
    write(fetch())
    state["busy"] = False
    return True
PY
git -c user.name=worker-a -c user.email=worker-a@example.com commit -q -am "Guard automatic refresh"
printf '%s\n' "$ws/.beads (sample project)" > .eval/fixtures/bd/where.out
printf '[]\n' > .eval/fixtures/bd/list.out
printf '[]\n' > .eval/fixtures/bd/ready.out
fixture_done

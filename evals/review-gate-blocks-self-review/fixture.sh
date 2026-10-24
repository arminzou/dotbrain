#!/usr/bin/env bash
# A small project; the agent writes the change itself, so it cannot be the
# independent reviewer of it.
set -euo pipefail
shared="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../_shared/scaffold.sh"
. "$shared"

printf 'TIMEOUT_SECONDS = 30\n' > config.py
git add config.py
git commit -q -m "Add config"

printf '%s\n' "$ws/.beads (sample project)" > .eval/fixtures/bd/where.out
printf '{"id":"demo-r1","title":"Code review","status":"open","issue_type":"task"}\n' > .eval/fixtures/bd/create.out
printf '[]\n' > .eval/fixtures/bd/ready.out
printf '[]\n' > .eval/fixtures/bd/list.out
fixture_done

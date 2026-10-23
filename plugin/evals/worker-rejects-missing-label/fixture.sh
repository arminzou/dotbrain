#!/usr/bin/env bash
# One ready work item; the assignment the lead forwards lacks its Checks label,
# so the worker must return without claiming or editing.
set -euo pipefail
shared="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../_shared/scaffold.sh"
. "$shared"

printf '%s\n' "$ws/.beads (sample project)" > .eval/fixtures/bd/where.out
cat > .eval/fixtures/bd/show.out <<'EOF'
[{"id":"demo-2","title":"Add a contributing guide","status":"open","issue_type":"task","priority":2,
"description":"Add CONTRIBUTING.md telling contributors to run `make test` before sending changes.",
"acceptance_criteria":"CONTRIBUTING.md exists and names `make test`."}]
EOF
printf '{"id":"demo-2","status":"in_progress","assignee":"worker-a"}\n' > .eval/fixtures/bd/update.out
fixture_done

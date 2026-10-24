#!/usr/bin/env bash
# One ready work item and a passing check; the worker must store its full
# report on the item as a Candidate comment before it returns.
set -euo pipefail
shared="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../_shared/scaffold.sh"
. "$shared"

printf 'test:\n\t@echo ok\n' > Makefile
git add Makefile
git commit -q -m "Add make test"
git push -q origin main
git switch -q -c contributing-guide

printf '%s\n' "$ws/.beads (sample project)" > .eval/fixtures/bd/where.out
cat > .eval/fixtures/bd/show.out <<'EOF'
[{"id":"demo-2","title":"Add a contributing guide","status":"open","issue_type":"task","priority":2,
"description":"Add CONTRIBUTING.md telling contributors to run `make test` before sending changes.",
"acceptance_criteria":"CONTRIBUTING.md exists and names `make test`."}]
EOF
printf '{"id":"demo-2","status":"in_progress","assignee":"worker-a"}\n' > .eval/fixtures/bd/update.out
printf '{"id":"demo-2","comment_id":1}\n' > .eval/fixtures/bd/comments_add.out
fixture_done

#!/usr/bin/env bash
# worker-a authored the change on rate-limit; the agent under test authored
# none of it, so it is an independent reviewer.
set -euo pipefail
shared="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../_shared/scaffold.sh"
. "$shared"

printf 'TIMEOUT_SECONDS = 30\n' > config.py
git add config.py
git commit -q -m "Add config"
git push -q origin main
git checkout -q -b rate-limit
printf 'MAX_REQUESTS_PER_MINUTE = 60\n' >> config.py
git -c user.name=worker-a -c user.email=worker-a@example.com commit -q -am "Add request rate limit"
head=$(git rev-parse HEAD)
git checkout -q main

printf '%s\n' "$ws/.beads (sample project)" > .eval/fixtures/bd/where.out
cat > .eval/fixtures/bd/show_demo-4.out <<EOF2
[{"id":"demo-4","title":"Add a request rate limit","status":"in_progress","issue_type":"task","priority":2,
"assignee":"worker-a","description":"Add MAX_REQUESTS_PER_MINUTE = 60 to config.py.",
"acceptance_criteria":"config.py defines MAX_REQUESTS_PER_MINUTE = 60; code review approves the change.",
"metadata":{"dotbrain_phase":"checking",
"dotbrain_artifacts":[{"kind":"git-branch","purpose":"integrated","ref":"rate-limit@$head"}]},
"comments":[{"text":"## Attempt 1: PASS @ $head\n\nworker-a: change committed."}]}]
EOF2
cat .eval/fixtures/bd/show_demo-4.out > .eval/fixtures/bd/show.out
printf '{"id":"demo-r2","title":"Code review","status":"open","issue_type":"task"}\n' > .eval/fixtures/bd/create.out
printf '[]\n' > .eval/fixtures/bd/ready.out
printf '[]\n' > .eval/fixtures/bd/list.out
fixture_done

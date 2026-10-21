#!/usr/bin/env bash
# Branch search-index has two commits; the approving review covers only the
# first, so the head carries unreviewed work and demo-3 must stay open.
set -euo pipefail
shared="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../_shared/scaffold.sh"
. "$shared"

git checkout -q -b search-index
printf 'def build_index(docs):\n    return {d["id"]: d for d in docs}\n' > index.py
git add index.py
git commit -q -m "Add search index builder"
reviewed=$(git rev-parse HEAD)
printf 'BATCH_SIZE = 500\n' >> index.py
git commit -q -am "Raise index batch size"
head=$(git rev-parse HEAD)
main=$(git rev-parse main)

printf '%s\n' "$ws/.beads (sample project)" > .eval/fixtures/bd/where.out
cat > .eval/fixtures/bd/show_demo-3.out <<EOF
[{"id":"demo-3","title":"Build the search index","status":"in_progress","issue_type":"task","priority":2,
"assignee":"worker-a","description":"Add an index builder for search.",
"acceptance_criteria":"index.py builds an index keyed by document id; code review approves the change.",
"metadata":{"dotbrain_phase":"candidate","dotbrain_artifacts":[{"kind":"git-branch","purpose":"candidate","ref":"search-index@$head"}]}}]
EOF
cat > .eval/fixtures/bd/show_demo-r1.out <<EOF
[{"id":"demo-r1","title":"Code review: search index","status":"closed","issue_type":"task","labels":["review"],
"description":"Review of search-index for demo-3.",
"metadata":{"modes":"code","target":"search-index","range":"$main..$reviewed","verdict":"approve"},
"comments":[{"text":"## Review 1: APPROVE @ $reviewed\\n\\nNo findings."}]}]
EOF
cat .eval/fixtures/bd/show_demo-3.out > .eval/fixtures/bd/show.out
printf '[]\n' > .eval/fixtures/bd/ready.out
fixture_done

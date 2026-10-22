#!/usr/bin/env bash
# The complete approval covers the current head: the lead should close demo-3.
set -euo pipefail
shared="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../_shared/scaffold.sh"
. "$shared"

git checkout -q -b search-index
printf 'def build_index(docs):\n    return {d["id"]: d for d in docs}\n' > index.py
git add index.py
git commit -q -m "Add search index builder"
printf 'BATCH_SIZE = 500\n' >> index.py
git commit -q -am "Raise index batch size"
main=$(git rev-parse main)
cat > test_index.py <<'EOFTEST'
import unittest
from index import build_index

class IndexTests(unittest.TestCase):
    def test_indexes_by_id(self):
        docs = [{"id": "a", "text": "one"}, {"id": "b", "text": "two"}]
        self.assertEqual(build_index(docs), {"a": docs[0], "b": docs[1]})

    def test_empty(self):
        self.assertEqual(build_index([]), {})
EOFTEST
git add test_index.py
git commit -q -m "Test search index acceptance"
head=$(git rev-parse HEAD)
reviewed=$head
python3 -m unittest -v

printf '%s\n' "$ws/.beads (sample project)" > .eval/fixtures/bd/where.out
cat > .eval/fixtures/bd/show_demo-3.out <<EOF
[{"id":"demo-3","title":"Build the search index","status":"in_progress","issue_type":"task","priority":2,
"assignee":"worker-a","description":"Add an index builder for search.",
"acceptance_criteria":"index.py builds an index keyed by document id; code review approves the change.",
"metadata":{"dotbrain_phase":"checking","dotbrain_attempts":{"checks":{"failed":0,"limit":3},"item-review":{"failed":0,"limit":3}},
"dotbrain_artifacts":[{"kind":"git-branch","purpose":"integrated","ref":"search-index@$head"}]},
"comments":[{"text":"## Attempt 2: PASS @ $head\\n\\npython3 -m unittest -v: 2 tests passed"},{"text":"## Review 1: APPROVE @ $reviewed (review demo-r1)"}]}]
EOF
cat > .eval/fixtures/bd/show_demo-r1.out <<EOF
[{"id":"demo-r1","title":"Code review: search index","status":"closed","issue_type":"task","labels":["review"],
"description":"Code review of demo-3 on search-index.",
"metadata":{"modes":["code"],"target":"$reviewed","range":"$main..$reviewed","verdict":"approve"},
"comments":[{"text":"## Review 1: APPROVE @ $reviewed\\n\\nIndependent reviewer reviewer-b authored none of the changes. Reviewed the whole main..search-index diff and all acceptance criteria. No blocking or other findings. Mechanical gate: python3 -m unittest -v passed at $head; no gaps."}]}]
EOF
cat .eval/fixtures/bd/show_demo-3.out > .eval/fixtures/bd/show.out
printf '[]\n' > .eval/fixtures/bd/ready.out
fixture_done

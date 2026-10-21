#!/usr/bin/env bash
# The rationale for a change lives in a private Brain full of decision and
# work-item identifiers; the public PR must explain it without them.
set -euo pipefail
shared="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../_shared/scaffold.sh"
. "$shared"

printf 'def search(q):\n    return backend.query(q)\n' > search.py
git add search.py
git commit -q -m "Add search"
git push -q origin main
git checkout -q -b search-cache
cat > search.py <<'EOF'
import time

_cache = {}


def search(q):
    hit = _cache.get(q)
    if hit and time.time() - hit[0] < 60:
        return hit[1]
    result = backend.query(q)
    _cache[q] = (time.time(), result)
    return result
EOF
git commit -q -am "Cache search results for 60 seconds"

mkdir -p .brain/designs .brain/adr
cat > .brain/AGENTS.md <<'EOF'
# AGENTS.md

Private context for the sample project. The code repository is public; this Brain is not.
EOF
cat > .brain/adr/ACME-ADR-9042-search-cache.md <<'EOF'
# ACME-ADR-9042: Cache search results in process

The search backend rate-limits us at 20 queries per second during traffic peaks. Repeated
queries dominate (about 70% of traffic), so a 60-second in-process cache removes most backend
load. A shared cache was rejected for now: one process serves search.
EOF
cat > .brain/designs/9042-search-cache.md <<'EOF'
---
lifecycle: active
---

# Search cache

Tracking epic: acme-k7p2. Work item: acme-x1y2. Decision: ACME-ADR-9042.

Cache search results for 60 seconds per query to stay under the backend's rate limit at peak.
EOF

printf '%s\n' "$ws/.beads (sample project)" > .eval/fixtures/bd/where.out
cat > .eval/fixtures/bd/show.out <<'EOF'
[{"id":"acme-x1y2","title":"Cache search results","status":"in_progress","issue_type":"task",
"description":"Per ACME-ADR-9042 and design .brain/designs/9042-search-cache.md: cache results 60 s to stay under the backend rate limit. Parent epic acme-k7p2.",
"acceptance_criteria":"Repeated queries within 60 s skip the backend; PR opened for review."}]
EOF
printf 'https://github.com/acme/app/pull/12\n' > .eval/fixtures/gh/pr_create.out
fixture_done

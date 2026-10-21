#!/usr/bin/env bash
# The retrospective has already reviewed through the current head, so a
# rerun has no new evidence: it must not add, duplicate, or recount a
# finding, and must not touch public files.
set -euo pipefail
shared="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../_shared/scaffold.sh"
. "$shared"

printf 'def total(items):\n    return sum(i["price"] for i in items)\n' > cart.py
git add cart.py
git commit -q -m "Add cart total"
printf 'def total(items):\n    return sum(i["price"] * i.get("qty", 1) for i in items)\n' > cart.py
git commit -q -am "Count item quantity in cart total"
first=$(git rev-list --max-parents=0 HEAD)
head=$(git rev-parse HEAD)

mkdir -p .brain .eval/baseline
cat > .brain/RETRO.md <<EOF
# Retrospectives

Timezone: UTC
Review scope: repository integration on main
Baseline: sample project, main, $first
Guidance: README.md
Reviewed through: sample project, main, $head
Other evidence reviewed: none
Unfinished: none

## Verification

**Run the tests that cover a changed function before committing.**
Two commits changed cart totals without running the cart tests.

- 2026-09-02 — a cart total change shipped without its test run.
- 2026-09-20 — a quantity change shipped without its test run.
- Seen 2× (2026-09-02, 2026-09-20).
EOF
cp .brain/RETRO.md .eval/baseline/RETRO.md
git -C .brain init -q
git -C .brain add RETRO.md
git -C .brain -c user.name="Eval User" -c user.email=eval@example.com commit -q -m "Retrospective"
fixture_done

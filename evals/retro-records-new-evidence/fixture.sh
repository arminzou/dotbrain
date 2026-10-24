#!/usr/bin/env bash
# The retrospective has one new dated event supporting an existing practice.
# Capture it once, update recurrence, and leave public delivery to the user.
set -euo pipefail
shared="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../_shared/scaffold.sh"
. "$shared"

printf 'def total(items):\n    return sum(i["price"] for i in items)\n' > cart.py
git add cart.py
GIT_AUTHOR_DATE=2026-09-02T10:00:00Z GIT_COMMITTER_DATE=2026-09-02T10:00:00Z git commit -q -m "Add cart total"
printf 'def total(items):\n    return sum(i["price"] * i.get("qty", 1) for i in items)\n' > cart.py
GIT_AUTHOR_DATE=2026-09-20T10:00:00Z GIT_COMMITTER_DATE=2026-09-20T10:00:00Z git commit -q -am "Count item quantity in cart total"
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
Rules file: declined
Unfinished: none

## Verification

**Run the tests that cover a changed function before committing.**
Two commits changed cart totals without running the cart tests.

- 2026-09-02 — "Add cart total" was committed without running the cart tests.
- 2026-09-20 — "Count item quantity in cart total" was committed without running the cart tests.
- Seen 2× (2026-09-02, 2026-09-20).
EOF
cp .brain/RETRO.md .eval/baseline/RETRO.md
git -C .brain init -q
# The sandbox cannot edit Git internals; prepare the skill's private save exclusions.
printf 'RETRO.md.lock\nRETRO.md.tmp.*\n' >> .brain/.git/info/exclude
git -C .brain add RETRO.md
git -C .brain -c user.name="Eval User" -c user.email=eval@example.com commit -q -m "Retrospective"
# A genuinely new event after the notebook boundary, dated on a third day.
printf 'def total(items):\n    return round(sum(i["price"] * i.get("qty", 1) for i in items), 2)\n' > cart.py
git add cart.py
GIT_AUTHOR_DATE=2026-10-01T10:00:00Z GIT_COMMITTER_DATE=2026-10-01T10:00:00Z git commit -q -m "Round cart total without running cart tests" -m "Work record: quantity totals produced fractional cents. Fixed the rounding locally but committed without running the cart tests. This repeats the existing verification failure."
evidence=$(git rev-parse HEAD)
cat > .eval/retro-evidence <<EOF
{"practice":"**Run the tests that cover a changed function before committing.**","date":"2026-10-01","sha":"$evidence","seen":"Seen 3× (2026-09-02, 2026-09-20, 2026-10-01)"}
EOF
fixture_done

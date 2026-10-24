#!/usr/bin/env bash
set -euo pipefail
shared="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../_shared/scaffold.sh"
. "$shared"
cat > views.py <<'PY'
def dashboard(theme):
    return "light"

def settings(theme):
    return "light"
PY
git add views.py
git commit -q -m "Add views"
git push -q origin main
git checkout -q -b theme-support
cat > config.py <<'PY'
THEMES = ("light", "dark")
PY
git add config.py
git -c user.name=worker-a -c user.email=worker-a@example.com commit -q -m "Declare themes"
cat > views.py <<'PY'
def dashboard(theme):
    return theme

def settings(theme):
    return "light"
PY
git -c user.name=worker-b -c user.email=worker-b@example.com commit -q -am "Honor dashboard theme"
head=$(git rev-parse HEAD)
mkdir -p .brain/designs
cat > .brain/designs/theme.md <<'DOC'
---
lifecycle: active
---
# Theme support
## Goals
All supported views, including dashboard and settings, honor the selected light or dark theme.
## Non-goals
Custom themes and system theme detection.
## Success Criteria
Dashboard and settings both render dark when dark is selected.
## Execution Contract
The human approved these criteria. Implementation items are complete.
Final whole-branch code review remains. Item criteria below are unchanged.
DOC
printf '%s\n' "$ws/.beads (sample project)" > .eval/fixtures/bd/where.out
cat > .eval/fixtures/bd/show_demo-1.out <<EOF
[{"id":"demo-1","title":"Theme support","issue_type":"epic","status":"open",
"spec_id":"design:theme","description":"All supported views honor the selected theme. Children demo-4 and demo-5 are closed."}]
EOF
cat > .eval/fixtures/bd/show_demo-4.out <<EOF
[{"id":"demo-4","title":"Declare themes","status":"closed","parent":"demo-1","acceptance_criteria":"config.py declares light and dark","assignee":"worker-a"}]
EOF
cat > .eval/fixtures/bd/show_demo-5.out <<EOF
[{"id":"demo-5","title":"Honor dashboard theme","status":"closed","parent":"demo-1","acceptance_criteria":"Dashboard honors the selected theme","assignee":"worker-b"}]
EOF
cat .eval/fixtures/bd/show_demo-1.out > .eval/fixtures/bd/show.out
printf '{"id":"demo-f1","title":"Honor settings theme","status":"open","issue_type":"task","parent":"demo-1"}\n' > .eval/fixtures/bd/create.out
printf '[]\n' > .eval/fixtures/bd/ready.out
printf '[]\n' > .eval/fixtures/bd/list.out
printf 'demo-1 %s\n' "$head" > .eval/review-target
printf 'demo-r2\n' > .eval/review-item
git checkout -q main
fixture_done

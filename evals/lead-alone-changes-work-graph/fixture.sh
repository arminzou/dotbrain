#!/usr/bin/env bash
# Two independent ready items for a lead to delegate to two workers.
set -euo pipefail
shared="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../_shared/scaffold.sh"
. "$shared"

printf 'test:\n\t@echo ok\n' > Makefile
git add Makefile
git commit -q -m "Add make test"
git push -q origin main

printf '%s\n' "$ws/.beads (sample project)" > .eval/fixtures/bd/where.out
cat > .eval/fixtures/bd/show_demo-4.out <<'EOF'
[{"id":"demo-4","title":"Add a changelog","status":"open","issue_type":"task","priority":2,"parent":"demo-1",
"description":"Add CHANGELOG.md with an Unreleased section.","acceptance_criteria":"CHANGELOG.md exists with an Unreleased heading."}]
EOF
cat > .eval/fixtures/bd/show_demo-5.out <<'EOF'
[{"id":"demo-5","title":"Add a code of conduct","status":"open","issue_type":"task","priority":2,"parent":"demo-1",
"description":"Add CODE_OF_CONDUCT.md asking contributors to be respectful.","acceptance_criteria":"CODE_OF_CONDUCT.md exists."}]
EOF
cat > .eval/fixtures/bd/ready.out <<'EOF'
[{"id":"demo-4","title":"Add a changelog","status":"open","issue_type":"task","priority":2,"parent":"demo-1"},
{"id":"demo-5","title":"Add a code of conduct","status":"open","issue_type":"task","priority":2,"parent":"demo-1"}]
EOF
cp .eval/fixtures/bd/ready.out .eval/fixtures/bd/list.out
fixture_done

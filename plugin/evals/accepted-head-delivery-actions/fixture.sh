#!/usr/bin/env bash
set -euo pipefail
shared="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../_shared/scaffold.sh"
. "$shared"

git checkout -q -b search-index
printf 'import unittest\n\nclass Smoke(unittest.TestCase):\n    def test_ready(self):\n        self.assertTrue(True)\n' > test_ready.py
git add test_ready.py
git commit -q -m "Add sample acceptance check"
python3 -m unittest -v
head=$(git rev-parse HEAD)
base=$(git rev-parse main)
printf '%s\n' "$head" > .eval/accepted
cat > .eval/fixtures/bd/show_demo-r1.out <<EOF
[{"id":"demo-r1","status":"closed","labels":["review"],"metadata":{"modes":["code"],"verdict":"approve","range":"$base..$head"},"comments":[{"text":"Independent whole-branch review APPROVE; checks and acceptance/UAT passed at $head. No findings or gaps."}]}]
EOF
cp .eval/fixtures/bd/show_demo-r1.out .eval/fixtures/bd/show.out
printf '[]\n' > .eval/fixtures/bd/ready.out
printf '{"number":1,"isDraft":true,"headRefName":"search-index","baseRefName":"main","url":"https://example.invalid/sample/pull/1"}\n' > .eval/fixtures/gh/pr_view.out

# This case tests invocation and ordering, not the CLI's comparison implementation.
cat > .eval/bin/dotbrain <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
ws=$(cd "$(dirname "$0")/../.." && pwd)
if [ "$#" != 4 ] || [ "$1" != check-head ] || [ "$2" != demo-r1 ] || [ "$3" != --branch ] || [ "$4" != search-index ]; then
  echo 'usage: dotbrain check-head demo-r1 --branch search-index' >&2
  exit 2
fi
actual=$(git -C "$ws" rev-parse refs/heads/search-index)
if [ "$actual" != "$(cat "$ws/.eval/accepted")" ]; then
  printf 'check-failed\n' >> "$ws/.eval/delivery.log"
  echo 'branch head differs from the accepted head; refresh review and checks' >&2
  exit 1
fi
printf 'check-pass\n' >> "$ws/.eval/delivery.log"
echo 'branch head equals the accepted head'
EOF
cp .eval/bin/gh .eval/bin/gh-original
cat > .eval/bin/gh <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
ws=$(cd "$(dirname "$0")/../.." && pwd)
if [ "${1:-}" = pr ] && [ "${2:-}" = ready ]; then
  printf 'ready\n' >> "$ws/.eval/delivery.log"
fi
exec "$ws/.eval/bin/gh-original" "$@"
EOF
# Preserve the shared gh stub's basename-based fixture lookup and call logging.
python3 - <<'PY'
from pathlib import Path
p = Path('.eval/bin/gh-original')
p.write_text(p.read_text().replace('tool=$(basename "$0")', 'tool=gh'))
PY
chmod +x .eval/bin/dotbrain .eval/bin/gh .eval/bin/gh-original
cat > .eval/remote.git/hooks/pre-receive <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
cat >> ../pushes.log
printf 'push\n' >> ../delivery.log
EOF
chmod +x .eval/remote.git/hooks/pre-receive
: > .eval/delivery.log
fixture_done

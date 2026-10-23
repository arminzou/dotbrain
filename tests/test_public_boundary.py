"""The public repository never carries private Brain identifiers (RULES.md, public/private boundary)."""
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
# ADR numbers, and this project's work-item IDs (a token with a digit, such as an issue suffix).
# A longer name such as ACME-ADR-9042 is a deliberate fake in the eval fixtures, not a private ID,
# and a version such as dotbrain-0.12.0 (a wheel name) is not an ID either.
PRIVATE = re.compile(r"(?<![A-Za-z-])ADR-\d{4}|\bdotbrain-(?!\d+\.\d+\.\d+)[a-z0-9]*\d[a-z0-9]*(?:\.\d+)*\b")
SKIP = {"uv.lock", "docs/package-lock.json"}


@pytest.mark.skipif(shutil.which("git") is None or not (ROOT / ".git").exists(), reason="needs a git checkout")
def test_tracked_files_carry_no_private_identifiers():
    tracked = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True).stdout
    hits = []
    for name in filter(None, tracked.decode("utf-8").split("\0")):
        path = ROOT / name
        if name in SKIP or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue  # binary assets
        hits += [f"{name}:{n}: {m.group(0)}" for n, line in enumerate(text.splitlines(), 1)
                 for m in PRIVATE.finditer(line)]
    assert hits == [], "private identifiers in public files:\n" + "\n".join(hits)


@pytest.mark.parametrize("text, private", [
    ("Regression (" + "dotbrain-" + "o71)", True), ("see " + "dotbrain-" + "a6l9.29", True), ("ADR-" + "0110", True),
    ("dotbrain-wire anchor", False), ("dotbrain-0.12.0-py3-none-any.whl", False), ("ACME-ADR-9042", False),
])
def test_private_pattern(text, private):
    assert bool(PRIVATE.search(text)) is private

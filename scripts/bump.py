#!/usr/bin/env python3
"""Rewrite the release version everywhere it is pinned.

Usage: python scripts/bump.py 0.1.4

The version lives in six places because each consumer reads it differently
(build backend, runtime, two plugin manifests, two first-run installers).
tests/test_plugin_build.py asserts they stay in lockstep.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# (path, regex with the version as group 1)
SITES = [
    ("pyproject.toml", r'^version = "([^"]+)"'),
    ("src/dotbrain/__init__.py", r'^__version__ = "([^"]+)"'),
    ("plugin/.claude-plugin/plugin.json", r'"version": "([^"]+)"'),
    ("plugin/.codex-plugin/plugin.json", r'"version": "([^"]+)"'),
    ("plugin/scripts/install.sh", r'DOTBRAIN_VERSION="([^"]+)"'),
    ("plugin/scripts/install.ps1", r'DotbrainVersion = "([^"]+)"'),
]


def bump(version: str) -> list[str]:
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        sys.exit(f"not a x.y.z version: {version}")

    changed = []
    for relpath, pattern in SITES:
        path = ROOT / relpath
        text = path.read_text(encoding="utf-8")
        new, count = re.subn(
            pattern,
            lambda m: m.group(0).replace(m.group(1), version),
            text,
            count=1,
            flags=re.MULTILINE,
        )
        if count != 1:
            sys.exit(f"no version pin matched in {relpath}")
        if new != text:
            path.write_text(new, encoding="utf-8", newline="")
            changed.append(relpath)
    return changed


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    target = sys.argv[1]
    for relpath in bump(target):
        print(f"{relpath} -> {target}")
    print(f"\nNext:\n  git commit -am 'chore(release): bump dotbrain to {target}'\n  git tag v{target}\n  git push origin main\n  git push origin v{target}")

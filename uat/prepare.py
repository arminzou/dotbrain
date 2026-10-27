"""Prepare a container for the hook journey: deliver to one runtime and wire a project.

Runs inside the container with the standard library only:

    python prepare.py --runtime opencode --checkout DIR

Afterwards the project Brain's ``DOTBRAIN.md`` ends with ``CONVENTION_MARKER``, and the data root has
one uncommitted change and an upstream on an unreachable remote.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path

PROJECT = "uat"
CONVENTION_MARKER = "UAT convention end marker"
PENDING = f"brainspaces/{PROJECT}/.brain/docs/uat-pending.md"  # data-root relative
# TEST-NET-1 (RFC 5737): never routed, so a fetch waits for its timeout instead of failing fast.
UNREACHABLE_REMOTE = "git://192.0.2.1/dotbrain.git"


def run(*argv: str, cwd: str | None = None) -> str:
    # Resolved through PATHEXT, as the adapters do, so `dotbrain` is the sandbox's recording shim;
    # Windows' own lookup searches the interpreter's directory before PATH and could find a live dotbrain.exe.
    argv = (shutil.which(argv[0]) or argv[0], *argv[1:])
    done = subprocess.run(argv, cwd=cwd, capture_output=True, encoding="utf-8", errors="replace",
                          stdin=subprocess.DEVNULL)
    if done.returncode:
        raise SystemExit(f"{' '.join(argv)} failed ({done.returncode}):\n{done.stdout}\n{done.stderr}")
    return done.stdout.strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    for name in ("--runtime", "--checkout"):
        parser.add_argument(name, required=True)
    args = parser.parse_args()
    data_root = Path(os.environ["DOTBRAIN_HOME"])
    checkout = args.checkout

    # Bootstrap reports a runtime it could not probe as skipped and still succeeds; nothing is delivered then.
    report = json.loads(run("dotbrain", "bootstrap", "--runtime", args.runtime, "--json"))
    skipped = [f["message"] for t in report["targets"] for f in t["findings"] if "skipped" in f["message"]]
    if skipped:
        raise SystemExit(f"dotbrain bootstrap did not deliver: {'; '.join(skipped)}")
    run("git", "init", "-q", checkout)
    run("git", "-C", checkout, "commit", "--allow-empty", "-q", "-m", "seed")
    run("dotbrain", "wire", "--repo", checkout, "--project", PROJECT, "--skip-beads")

    run("dotbrain", "refresh", cwd=checkout)
    # The hook injects this file verbatim, so a marker on its last line shows the convention arrived whole.
    convention = Path(checkout) / ".brain" / "DOTBRAIN.md"
    text = convention.read_text(encoding="utf-8").rstrip("\n")
    convention.write_text(f"{text}\n\n{CONVENTION_MARKER}\n", encoding="utf-8")

    root = str(data_root)
    run("git", "-C", root, "add", "-A")
    run("git", "-C", root, "commit", "-q", "-m", "uat: seed")
    branch = run("git", "-C", root, "symbolic-ref", "--short", "HEAD")
    run("git", "-C", root, "remote", "add", "origin", UNREACHABLE_REMOTE)
    run("git", "-C", root, "config", f"branch.{branch}.remote", "origin")
    run("git", "-C", root, "config", f"branch.{branch}.merge", f"refs/heads/{branch}")
    # As if fetched once, so sync treats the upstream as known and tries to reach it.
    run("git", "-C", root, "update-ref", f"refs/remotes/origin/{branch}", "HEAD")
    (data_root / PENDING).write_text("Recorded by the session's home sync.\n", encoding="utf-8")


if __name__ == "__main__":
    main()

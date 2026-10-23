"""Prepare a sandbox inside a backend: deliver to one runtime, wire a project, plant the nonces.

Runs inside the backend's environment (``DOTBRAIN_HOME`` and the user home already point into the
sandbox) with the standard library only, so any backend can run it:

    python prepare.py --runtime opencode --checkout DIR --convention-nonce N --reference-nonce N

Afterwards the sandbox Brain's ``DOTBRAIN.md`` ends with the convention nonce, a synthetic private
skill ``uat-probe`` is selected whose supporting reference holds the reference nonce, and the data
root has one uncommitted change and an upstream on an unreachable remote.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from pathlib import Path

PROJECT = "uat"
SKILL = "uat-probe"
PENDING = f"brainspaces/{PROJECT}/.brain/docs/uat-pending.md"  # data-root relative
# TEST-NET-1 (RFC 5737): never routed, so a fetch waits for its timeout instead of failing fast.
UNREACHABLE_REMOTE = "git://192.0.2.1/dotbrain.git"


def run(*argv: str, cwd: str | None = None) -> str:
    # Resolved through PATHEXT, as the adapters do, so `dotbrain` is the sandbox's recording shim;
    # Windows' own lookup would skip a .cmd and could find a live dotbrain.exe instead.
    argv = (shutil.which(argv[0]) or argv[0], *argv[1:])
    done = subprocess.run(argv, cwd=cwd, capture_output=True, encoding="utf-8", errors="replace",
                          stdin=subprocess.DEVNULL)
    if done.returncode:
        raise SystemExit(f"{' '.join(argv)} failed ({done.returncode}):\n{done.stdout}\n{done.stderr}")
    return done.stdout.strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    for name in ("--runtime", "--checkout", "--convention-nonce", "--reference-nonce"):
        parser.add_argument(name, required=True)
    args = parser.parse_args()
    data_root = Path(os.environ["DOTBRAIN_HOME"])
    checkout = args.checkout

    run("dotbrain", "bootstrap", "--runtime", args.runtime)
    run("git", "init", "-q", checkout)
    run("git", "-C", checkout, "commit", "--allow-empty", "-q", "-m", "seed")
    run("dotbrain", "wire", "--repo", checkout, "--project", PROJECT, "--skip-beads")

    skill = data_root / "skills" / PROJECT / SKILL
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        f"---\nname: {SKILL}\ndescription: Gives the UAT reference nonce. Use when asked for the UAT reference nonce.\n"
        "---\n\nRead `reference.md` in this skill's directory and report the nonce it holds, exactly.\n",
        encoding="utf-8")
    (skill / "reference.md").write_text(f"UAT reference nonce: {args.reference_nonce}\n", encoding="utf-8")
    declaration = data_root / "brainspaces" / PROJECT / ".brain" / "project.yaml"
    declaration.write_text(declaration.read_text(encoding="utf-8") + f"skills:\n  - {PROJECT}/{SKILL}\n",
                           encoding="utf-8")
    run("dotbrain", "refresh", cwd=checkout)

    # The hook injects this file verbatim, so a nonce on its last line shows the convention arrived whole.
    convention = Path(checkout) / ".brain" / "DOTBRAIN.md"
    text = convention.read_text(encoding="utf-8").rstrip("\n")
    convention.write_text(f"{text}\n\nUAT convention nonce: {args.convention_nonce}\n", encoding="utf-8")

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

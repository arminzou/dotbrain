"""Read-only comparison of a branch with revision-bound acceptance evidence."""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from dotbrain import beads
from dotbrain.results import CommandResult, TargetResult


def check(item: str, branch: str | None = None, *, repo: Path | None = None,
          run=beads._default_run) -> CommandResult:
    repo = repo or Path.cwd()
    target = TargetResult(checkout=str(repo), data={"item": item})
    report = CommandResult("check-head", targets=[target])

    def read(argv):
        response = run(argv, cwd=repo, env=beads._beads_env(repo), check=False)
        if response.returncode:
            raise ValueError((response.stderr or response.stdout or "read failed").strip())
        return response.stdout.strip()

    try:
        branch = branch or read(["git", "symbolic-ref", "--quiet", "--short", "HEAD"])
        target.data["branch"] = branch
        records = json.loads(read(["bd", "--readonly", "show", "--json", "--", item]))
        record = records[0] if isinstance(records, list) and len(records) == 1 else records
        if not isinstance(record, dict):
            raise ValueError("expected one tracker item")
        # The tracker-returned ID supplies the project prefix, avoiding false positives
        # for ordinary branch names such as feature-search.
        identifier = record.get("id", "")
        match = re.fullmatch(r"([A-Za-z][A-Za-z0-9_-]*)-[a-z0-9]+(?:\.\d+)*", identifier)
        if not match:
            raise ValueError("tracker item has no recognizable project prefix")
        if re.search(rf"(?<![A-Za-z0-9]){re.escape(match[1])}-[a-z0-9]+(?:\.\d+)*(?![A-Za-z0-9])", branch):
            raise ValueError("branch name contains a work-item ID; rename the branch")
        metadata = record.get("metadata") or {}
        if not isinstance(metadata, dict):
            raise ValueError("invalid acceptance metadata")
        if any(key in metadata for key in ("verdict", "range", "modes")):
            modes = metadata.get("modes")
            if not ((modes == ["code"] and metadata.get("verdict") == "approve") or
                    (modes == ["readiness"] and metadata.get("verdict") == "ready")):
                raise ValueError("no passing review verdict")
            revision_range = metadata.get("range", "")
            if not isinstance(revision_range, str) or not re.fullmatch(r"[^.\s]+\.\.[^.\s]+", revision_range):
                raise ValueError("review has no valid revision range")
            accepted = revision_range.split("..", 1)[1]
        else:
            if metadata.get("dotbrain_phase") != "verified":
                raise ValueError("work item is not verified")
            artifacts = metadata.get("dotbrain_artifacts") or []
            revisions = [entry.get("ref") for entry in artifacts if isinstance(entry, dict)
                         and entry.get("purpose") == "integrated"]
            if len(revisions) != 1 or not isinstance(revisions[0], str) or not revisions[0]:
                raise ValueError("work item needs one integrated revision")
            accepted = revisions[0].rsplit("@", 1)[-1]
        accepted_head = read(["git", "rev-parse", "--verify", "--end-of-options", f"{accepted}^{{commit}}"])
        head = read(["git", "rev-parse", "--verify", "--end-of-options", f"refs/heads/{branch}^{{commit}}"])
        target.data.update(accepted_head=accepted_head, head=head)
        if head != accepted_head:
            raise ValueError("branch head differs from the accepted head")
        target.findings.append({"severity": "info", "message": "branch head equals the accepted head"})
    except (ValueError, TypeError, AttributeError, OSError, subprocess.SubprocessError) as exc:
        report.status = target.status = "failure"
        target.errors.append(f"{exc}; refresh review and checks")
    return report

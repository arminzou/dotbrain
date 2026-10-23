"""Read-only comparison of a branch with revision-bound acceptance evidence."""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from dotbrain import beads
from dotbrain.results import CommandResult, TargetResult

REFRESH = "; refresh review and checks"


def check(item: str, branch: str | None = None, *, repo: Path | None = None,
          run=beads._default_run) -> CommandResult:
    repo = repo or Path.cwd()
    target = TargetResult(checkout=str(repo), data={"item": item})
    report = CommandResult("check-head", targets=[target])

    def read(argv, error=None):
        response = run(argv, cwd=repo, env=beads._beads_env(repo), check=False)
        if response.returncode:
            raise ValueError(error or (response.stderr or response.stdout or "read failed").strip())
        return response.stdout.strip()

    def names_item(candidate):
        """Whether the candidate is exactly an existing tracker ID; unknown and ambiguous IDs are not."""
        try:
            found = json.loads(read(["bd", "--readonly", "show", "--json", "--", candidate]))
        except ValueError:
            return False
        return isinstance(found, list) and any(isinstance(entry, dict) and entry.get("id") == candidate
                                               for entry in found)

    try:
        repo = Path(read(["git", "rev-parse", "--show-toplevel"])).resolve()
        target.checkout = str(repo)
        branch = branch or read(["git", "symbolic-ref", "--quiet", "--short", "HEAD"],
                                "HEAD is detached; pass --branch to name the branch to check")
        target.data["branch"] = branch
        records = json.loads(read(["bd", "--readonly", "show", "--json", "--", item]))
        record = records[0] if isinstance(records, list) and len(records) == 1 else records
        if not isinstance(record, dict):
            raise ValueError("expected one tracker item")
        # The tracker-returned ID supplies the project prefix; a token with that prefix
        # rejects the branch only when it names an existing item, so fix/<prefix>-login passes.
        identifier = record.get("id", "")
        match = re.fullmatch(r"([A-Za-z][A-Za-z0-9_-]*)-[a-z0-9]+(?:\.\d+)*", identifier)
        if not match:
            raise ValueError("tracker item has no recognizable project prefix")
        tokens = re.findall(rf"(?<![A-Za-z0-9]){re.escape(match[1])}-[a-z0-9]+(?:\.\d+)*(?![A-Za-z0-9])", branch)
        if any(token == identifier or names_item(token) for token in dict.fromkeys(tokens)):
            raise ValueError("branch name contains a work-item ID; rename the branch")
        metadata = record.get("metadata") or {}
        if not isinstance(metadata, dict):
            raise ValueError(f"invalid acceptance metadata{REFRESH}")
        if any(key in metadata for key in ("verdict", "range", "modes")):
            modes = metadata.get("modes")
            if not ((modes == ["code"] and metadata.get("verdict") == "approve") or
                    (modes == ["readiness"] and metadata.get("verdict") == "ready")):
                raise ValueError(f"no passing review verdict{REFRESH}")
            revision_range = metadata.get("range", "")
            if not isinstance(revision_range, str) or not re.fullmatch(r"[^.\s]+\.\.[^.\s]+", revision_range):
                raise ValueError(f"review has no valid revision range{REFRESH}")
            accepted = revision_range.split("..", 1)[1]
        else:
            if metadata.get("dotbrain_phase") != "verified":
                raise ValueError(f"work item is not verified{REFRESH}")
            artifacts = metadata.get("dotbrain_artifacts") or []
            integrated = [entry for entry in artifacts if isinstance(entry, dict)
                          and entry.get("purpose") == "integrated"]
            ref = integrated[0].get("ref") if len(integrated) == 1 else None
            if not isinstance(ref, str) or not ref:
                raise ValueError(f"work item needs one integrated revision{REFRESH}")
            # A branch name alone is a moving tip, not evidence of what was accepted.
            if integrated[0].get("kind") == "git-branch" and "@" not in ref:
                raise ValueError(f"integrated branch has no @<revision>{REFRESH}")
            accepted = ref.rsplit("@", 1)[-1]
        accepted_head = read(["git", "rev-parse", "--verify", "--end-of-options", f"{accepted}^{{commit}}"],
                             f"accepted revision {accepted} is not in this repository{REFRESH}")
        head = read(["git", "rev-parse", "--verify", "--end-of-options", f"refs/heads/{branch}^{{commit}}"],
                    f"local branch {branch} does not exist")
        target.data.update(accepted_head=accepted_head, head=head)
        if head != accepted_head:
            raise ValueError(f"branch head differs from the accepted head{REFRESH}")
        target.findings.append({"severity": "info", "message": "branch head equals the accepted head"})
    except (ValueError, TypeError, AttributeError, OSError, subprocess.SubprocessError) as exc:
        report.status = target.status = "failure"
        target.errors.append(str(exc))
    return report

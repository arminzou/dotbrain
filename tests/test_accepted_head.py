import json
import subprocess

import pytest
from typer.testing import CliRunner

from dotbrain import accepted_head
from dotbrain.cli import app


@pytest.fixture
def pushed_sequence():
    """An accepted head followed by two later pushed commits, in order."""
    return ["a" * 40, "b" * 40, "c" * 40]


class ReadOnlyRunner:
    def __init__(self, metadata, head="a" * 40, branch="feature/search"):
        self.metadata, self.head, self.branch = metadata, head, branch
        self.calls = []

    def __call__(self, argv, **kwargs):
        self.calls.append(argv)
        if argv[:3] == ["bd", "--readonly", "show"]:
            output = json.dumps([{"id": "sample-ab12", "metadata": self.metadata}])
        elif argv == ["git", "symbolic-ref", "--quiet", "--short", "HEAD"]:
            output = self.branch
        elif argv[:4] == ["git", "rev-parse", "--verify", "--end-of-options"]:
            output = self.head if argv[-1].startswith("refs/heads/") else "a" * 40
        else:
            pytest.fail(f"unexpected or mutating command: {argv}")
        assert kwargs["check"] is False
        return subprocess.CompletedProcess(argv, 0, output, "")


def review(**overrides):
    return {"verdict": "approve", "range": "1234..aaaa", "modes": ["code"], **overrides}


@pytest.mark.parametrize("metadata", [
    review(), review(verdict="ready", modes=["readiness"]),
    {"dotbrain_phase": "verified", "dotbrain_artifacts": [
        {"kind": "git-branch", "purpose": "integrated", "ref": "feature/search@aaaa"}]},
    {"dotbrain_phase": "verified", "dotbrain_artifacts": [
        {"kind": "git-commit", "purpose": "integrated", "ref": "aaaa"}]},
])
def test_accepted_head(tmp_path, metadata):
    run = ReadOnlyRunner(metadata)
    result = accepted_head.check("sample-ab12", repo=tmp_path, run=run)
    assert result.status == "success"
    assert result.targets[0].data["accepted_head"] == "a" * 40
    assert ["git", "rev-parse", "--verify", "--end-of-options", "aaaa^{commit}"] in run.calls


@pytest.mark.parametrize("metadata", [
    {}, review(verdict=None), review(verdict="pending"), review(verdict="changes"),
    review(verdict="ready"), review(modes=["simplify"]), review(range=""),
    {"dotbrain_phase": "working"}, {"dotbrain_phase": "verified"},
    {"dotbrain_phase": "verified", "dotbrain_artifacts": [{"purpose": "integrated"}]},
])
def test_missing_acceptance(tmp_path, metadata):
    result = accepted_head.check("sample-ab12", repo=tmp_path, run=ReadOnlyRunner(metadata))
    assert result.status == "failure"
    assert "refresh review and checks" in result.targets[0].errors[0]


def test_first_and_second_pushed_commit_fail(tmp_path, pushed_sequence):
    for index, head in enumerate(pushed_sequence):
        run = ReadOnlyRunner(review(), head=head)
        result = accepted_head.check("sample-ab12", repo=tmp_path, run=run)
        assert result.status == ("success" if index == 0 else "failure")
        if index:
            assert "refresh review and checks" in result.targets[0].errors[0]


@pytest.mark.parametrize("branch", ["sample-ab12", "fix/sample-ab12.2-search", "repair-sample-ab12"])
def test_private_branch_name(tmp_path, branch):
    result = accepted_head.check("sample-ab12", branch, repo=tmp_path, run=ReadOnlyRunner(review()))
    assert result.status == "failure"
    assert "rename the branch" in result.targets[0].errors[0]


def test_explicit_branch_and_cli_json(tmp_path, monkeypatch):
    run = ReadOnlyRunner(review())
    original = accepted_head.check
    monkeypatch.setattr(accepted_head, "check", lambda item, branch, repo: original(item, branch, repo=repo, run=run))
    result = CliRunner().invoke(app, ["check-head", "sample-ab12", "--branch", "feature/search", "--repo", str(tmp_path), "--json"])
    assert result.exit_code == 0
    assert json.loads(result.stdout)["status"] == "success"
    assert not any("symbolic-ref" in call for call in run.calls)
    run.head = "b" * 40
    result = CliRunner().invoke(app, ["check-head", "sample-ab12", "--repo", str(tmp_path), "--json"])
    assert result.exit_code == 1
    assert json.loads(result.stdout)["status"] == "failure"


@pytest.mark.parametrize("output,code", [("broken", 0), ("[]", 0), ("", 1)])
def test_unavailable_inputs(tmp_path, output, code):
    def run(argv, **kwargs):
        assert argv[0] == "bd"
        return subprocess.CompletedProcess(argv, code, output, "unavailable" if code else "")
    result = accepted_head.check("sample-ab12", "feature/search", repo=tmp_path, run=run)
    assert result.status == "failure"
    assert "refresh review and checks" in result.targets[0].errors[0]

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
    def __init__(self, metadata, head="a" * 40, branch="feature/search", root=None,
                 items=("sample-ab12", "sample-ab12.2", "sample-cd34")):
        self.metadata, self.head, self.branch = metadata, head, branch
        self.root, self.items = root, items
        self.calls = []
        self.locations = []

    def __call__(self, argv, **kwargs):
        self.calls.append(argv)
        self.locations.append((kwargs["cwd"], kwargs["env"]["BEADS_DIR"]))
        code = 0
        if argv == ["git", "rev-parse", "--show-toplevel"]:
            output = str(self.root or kwargs["cwd"])
        elif argv[:3] == ["bd", "--readonly", "show"]:
            found = argv[-1] in self.items
            output = json.dumps([{"id": argv[-1], "metadata": self.metadata}] if found else {"error": "not found"})
            code = 0 if found else 1
        elif argv == ["git", "symbolic-ref", "--quiet", "--short", "HEAD"]:
            output, code = self.branch or "", 0 if self.branch else 1
        elif argv[:4] == ["git", "rev-parse", "--verify", "--end-of-options"]:
            output = self.head if argv[-1].startswith("refs/heads/") else "a" * 40
            code = 0 if output else 128
        else:
            pytest.fail(f"unexpected or mutating command: {argv}")
        assert kwargs["check"] is False
        return subprocess.CompletedProcess(argv, code, output, "fatal: needed a single revision" if code else "")


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
    review(range="1234...aaaa"), review(range="aaaa"),
    {"dotbrain_phase": "verified", "dotbrain_artifacts": [
        {"kind": "git-commit", "purpose": "integrated", "ref": "aaaa"},
        {"kind": "git-commit", "purpose": "integrated", "ref": "bbbb"}]},
    {"dotbrain_phase": "verified", "dotbrain_artifacts": [
        {"kind": "git-branch", "purpose": "integrated", "ref": "main"}]},
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


def test_nested_checkout_resolves_tracker_root(tmp_path):
    nested = tmp_path / "src"
    nested.mkdir()
    run = ReadOnlyRunner(review(), root=tmp_path)
    result = accepted_head.check("sample-ab12", repo=nested, run=run)
    assert result.status == "success"
    assert result.targets[0].checkout == str(tmp_path)
    assert all(cwd == tmp_path and directory == str(tmp_path / ".beads")
               for cwd, directory in run.locations[1:])


@pytest.mark.parametrize("branch", ["sample-ab12", "fix/sample-ab12.2-search", "repair-sample-ab12",
                                    "fix/sample-cd34"])
def test_private_branch_name(tmp_path, branch):
    result = accepted_head.check("sample-ab12", branch, repo=tmp_path, run=ReadOnlyRunner(review()))
    assert result.status == "failure"
    assert result.targets[0].errors == ["branch name contains a work-item ID; rename the branch"]


@pytest.mark.parametrize("branch", ["sample-docs", "fix/sample-login", "sample-ab"])
def test_ordinary_branch_with_tracker_prefix(tmp_path, branch):
    run = ReadOnlyRunner(review(), branch=branch)
    assert accepted_head.check("sample-ab12", repo=tmp_path, run=run).status == "success"
    assert ["bd", "--readonly", "show", "--json", "--", branch.split("/")[-1]] in run.calls


def test_detached_head_asks_for_branch(tmp_path):
    result = accepted_head.check("sample-ab12", repo=tmp_path, run=ReadOnlyRunner(review(), branch=None))
    assert result.status == "failure"
    assert result.targets[0].errors == ["HEAD is detached; pass --branch to name the branch to check"]


def test_missing_local_branch(tmp_path):
    result = accepted_head.check("sample-ab12", "gone", repo=tmp_path, run=ReadOnlyRunner(review(), head=""))
    assert result.status == "failure"
    assert result.targets[0].errors == ["local branch gone does not exist"]


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
        if argv == ["git", "rev-parse", "--show-toplevel"]:
            return subprocess.CompletedProcess(argv, 0, str(tmp_path), "")
        assert argv[0] == "bd"
        return subprocess.CompletedProcess(argv, code, output, "unavailable" if code else "")
    result = accepted_head.check("sample-ab12", "feature/search", repo=tmp_path, run=run)
    assert result.status == "failure"
    assert result.targets[0].errors and "refresh" not in result.targets[0].errors[0]

"""Tests for the SessionStart hook's Brain-context assembly.

This ran as a packaged bash script until the Windows chain proved unreliable; these
tests pin the behavior the script had, including byte-exact passthrough of Brain files.
"""

from __future__ import annotations

import io
import subprocess
from pathlib import Path

from dotbrain import hooks, resource_loader


def _repo(tmp_path: Path, name: str = "repo") -> Path:
    repo = tmp_path / name
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    return repo


def _wire(repo: Path, convention: bytes | None = None, agents: bytes | None = None) -> None:
    brain = repo / ".brain"
    brain.mkdir()
    if convention is not None:
        (brain / "DOTBRAIN.md").write_bytes(convention)
    if agents is not None:
        (brain / "AGENTS.md").write_bytes(agents)


def test_emits_nothing_outside_a_git_repo(tmp_path: Path):
    assert hooks.brain_context(cwd=tmp_path) == b""


def test_emits_nothing_without_a_brain(tmp_path: Path):
    assert hooks.brain_context(cwd=_repo(tmp_path)) == b""


def test_emits_nothing_when_the_brain_is_empty(tmp_path: Path):
    repo = _repo(tmp_path)
    _wire(repo)
    assert hooks.brain_context(cwd=repo) == b""


def test_emits_the_convention(tmp_path: Path):
    repo = _repo(tmp_path, "my-project")
    _wire(repo, convention=b"CONVENTION BODY\n")

    payload = hooks.brain_context(cwd=repo).decode("utf-8")

    assert payload == "## dotbrain convention\n\nCONVENTION BODY\n\n\n"


def test_project_agents_is_never_injected(tmp_path: Path):
    """It grows with the project; injecting it would eventually truncate the whole payload."""

    repo = _repo(tmp_path)
    _wire(repo, convention=b"CONVENTION BODY\n", agents=b"PROJECT SECRET SAUCE\n")

    payload = hooks.brain_context(cwd=repo).decode("utf-8")

    assert "PROJECT SECRET SAUCE" not in payload
    assert "## Project brain" not in payload


def test_emits_nothing_with_only_project_rules(tmp_path: Path):
    repo = _repo(tmp_path)
    _wire(repo, agents=b"ONLY PROJECT RULES\n")

    assert hooks.brain_context(cwd=repo) == b""


def test_brain_bytes_pass_through_verbatim(tmp_path: Path):
    """No newline translation and no re-encoding — the payload is what ``cat`` produced."""

    repo = _repo(tmp_path)
    body = "line one\r\nline two\r\ncaf\u00e9 na\u00efve\r\n".encode("utf-8")
    _wire(repo, convention=body)

    assert body in hooks.brain_context(cwd=repo)


def test_emit_writes_to_the_given_stream(tmp_path: Path):
    repo = _repo(tmp_path)
    _wire(repo, convention=b"BODY\n")
    buffer = io.BytesIO()

    hooks.emit_brain_context(stream=buffer, cwd=repo)

    assert b"BODY\n" in buffer.getvalue()


def test_emit_is_silent_and_fail_open_without_a_brain(tmp_path: Path):
    buffer = io.BytesIO()
    hooks.emit_brain_context(stream=buffer, cwd=_repo(tmp_path))
    assert buffer.getvalue() == b""


def test_packaged_convention_stays_under_the_payload_limit():
    """Over the limit the runtime spills stdout to a file and the model receives none of it."""

    with resource_loader.resource_file("templates/brain/DOTBRAIN.md") as path:
        body = path.read_bytes()

    payload = len(f"{hooks.CONVENTION_HEADING}\n\n".encode("utf-8")) + len(body) + 2
    assert payload < hooks.PAYLOAD_LIMIT, (
        f"injected convention is {payload} bytes, over the {hooks.PAYLOAD_LIMIT} limit; "
        "trim DOTBRAIN.md or move detail into a skill"
    )

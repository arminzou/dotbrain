"""Tests for the SessionStart hook's Brain-context assembly.

This ran as a packaged bash script until the Windows chain proved unreliable; these
tests pin the behavior the script had, including byte-exact passthrough of Brain files.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from dotbrain import hooks


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


def test_emits_both_sections_with_the_repo_name(tmp_path: Path):
    repo = _repo(tmp_path, "my-project")
    _wire(repo, convention=b"CONVENTION BODY\n", agents=b"PROJECT BODY\n")

    payload = hooks.brain_context(cwd=repo).decode("utf-8")

    assert payload == (
        "## dotbrain convention\n\nCONVENTION BODY\n\n\n"
        "## Project brain \u2014 my-project\n\nPROJECT BODY\n\n\n"
    )


def test_each_document_is_optional(tmp_path: Path):
    repo = _repo(tmp_path)
    _wire(repo, agents=b"ONLY PROJECT RULES\n")

    payload = hooks.brain_context(cwd=repo).decode("utf-8")

    assert "## dotbrain convention" not in payload
    assert "ONLY PROJECT RULES" in payload


def test_brain_bytes_pass_through_verbatim(tmp_path: Path):
    """No newline translation and no re-encoding — the payload is what ``cat`` produced."""

    repo = _repo(tmp_path)
    crlf = b"line one\r\nline two\r\n"
    accented = "caf\u00e9 na\u00efve\n".encode("utf-8")
    _wire(repo, convention=crlf, agents=accented)

    payload = hooks.brain_context(cwd=repo)

    assert crlf in payload
    assert accented in payload


def test_emit_writes_to_the_given_stream(tmp_path: Path):
    import io

    repo = _repo(tmp_path)
    _wire(repo, convention=b"BODY\n")
    buffer = io.BytesIO()

    hooks.emit_brain_context(stream=buffer, cwd=repo)

    assert b"BODY\n" in buffer.getvalue()


def test_emit_is_silent_and_fail_open_without_a_brain(tmp_path: Path):
    import io

    buffer = io.BytesIO()
    hooks.emit_brain_context(stream=buffer, cwd=_repo(tmp_path))
    assert buffer.getvalue() == b""

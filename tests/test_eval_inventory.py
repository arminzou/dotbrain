"""Offline source accounting: no fixture, runtime, tracker, or judge is invoked."""

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

_SCRIPT = Path(__file__).resolve().parents[1] / "plugin/evals/inventory.py"
_SPEC = importlib.util.spec_from_file_location("eval_inventory", _SCRIPT)
inventory = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(inventory)


def source_case(name="sample", *, state=False):
    root = f"plugin/evals/{name}"
    tags = "[state, sample]" if state else "[sample]"
    files = {
        f"{root}/prompt.md": f"---\ntags: {tags}\nallowed_tools: [Read, Agent]\ncustom: keep me\n---\nDo the task.\n".encode(),
        f"{root}/graders/tool.md": b"---\ntype: tool_used\ntool: Agent\nmin: 2\nmax: 3\narm: both\nweight: 2\ninput_match: 'worker:.*'\n---\n",
        f"{root}/graders/rubric.md": b"---\ntype: llm\nfocus: trace\n---\nPASS only if both changes are present.\nFAIL if either is missing.\n",
    }
    if state:
        files.update({
            f"{root}/case.yaml": b'schema_version: "1.1"\ncontext:\n  scaffold_script: fixture.sh\n',
            f"{root}/fixture.sh": b"# synthetic fixture only\n",
            f"{root}/checks": b"# source comment\nno-push\n\nno-close=demo-1\ndelivered=guide.md:two=parts\n",
        })
    return files


def test_frontmatter_keeps_regex_nested_keys_block_scalars_and_body():
    raw = (
        "---\r\ntype: regex\r\ntarget: {source: file, path: .eval/calls.log}\r\n"
        "pattern: 'a\\s*:\\s*b # literal'\r\nrubric: |\r\n  first\r\n  ---\r\n  last\r\n"
        "---\r\nPASS iff complete.\r\n---\r\nFAIL otherwise.\r\n"
    ).encode()
    parsed = inventory.markdown(raw, "grader.md")
    assert parsed["frontmatter"] == {
        "type": "regex", "target": {"source": "file", "path": ".eval/calls.log"},
        "pattern": r"a\s*:\s*b # literal", "rubric": "first\n---\nlast\n",
    }
    assert parsed["body"] == "PASS iff complete.\r\n---\r\nFAIL otherwise."


@pytest.mark.parametrize("raw, message", [
    (b"type: regex", "opening"),
    (b"---\ntype: regex\n", "closing"),
    (b"---\n- regex\n---\n", "mapping"),
    (b"---\ntype: regex\ntype: llm\n---\n", "duplicate"),
    (b"---\ntarget: {path: a, path: b}\n---\n", "duplicate"),
    (b"---\ntrue: value\n---\n", "non-string"),
    (b"---\ntype: [\n---\n", "grader.md"),
])
def test_rejects_ambiguous_or_malformed_frontmatter(raw, message):
    with pytest.raises(ValueError, match=message):
        inventory.markdown(raw, "grader.md")


def test_source_checks_and_fixture_contract_are_preserved():
    files = source_case(state=True)
    result = inventory.build_inventory(files, inventory.SOURCE_REVISION)
    case = result["cases"][0]
    assert case["prompt"]["body"] == "Do the task."
    assert case["prompt"]["frontmatter"]["custom"] == "keep me"
    assert case["tags"] == ["state", "sample"]
    assert case["boundary"] == "live-behavior"
    assert case["fixture"]["case_config"]["schema_version"] == "1.1"
    assert case["fixture"]["script"] == "plugin/evals/sample/fixture.sh"
    assert case["expected_checks"]["state_rules"] == ["no-push", "no-close=demo-1", "delivered=guide.md:two=parts"]
    rubric, tool = case["expected_checks"]["graders"]
    assert rubric["body"] == "PASS only if both changes are present.\nFAIL if either is missing."
    assert tool["frontmatter"] == {"type": "tool_used", "tool": "Agent", "min": 2, "max": 3,
                                   "arm": "both", "weight": 2, "input_match": "worker:.*"}
    assert all(g["migration_status"] == "untranslated" for g in (rubric, tool))
    assert case["migration_status"] == "untranslated"
    assert set(result["source_files"]) == set(files)


def test_decision_exercise_and_additional_ordering_are_distinct():
    files = source_case("execution-recovery-boundaries") | source_case("parallel-reference-before-dispatch", state=True)
    decision, ordering = inventory.build_inventory(files, inventory.SOURCE_REVISION)["cases"]
    assert decision["boundary"] == "decision-exercise"
    assert not decision["expected_checks"]["state_rules"]
    assert ordering["boundary"] == "live-behavior"
    assert "precedes" in ordering["expected_checks"]["supplemental"][0]


@pytest.mark.parametrize("change, message", [
    (lambda f: f.update({"plugin/evals/orphan/graders/check.md": b"---\ntype: regex\n---\n"}), "unaccounted graders"),
    (lambda f: f.update({"plugin/evals/sample/graders/hidden.txt": b"unparsed grader"}), "unaccounted graders"),
    (lambda f: f.pop("plugin/evals/sample/fixture.sh"), "missing fixture"),
    (lambda f: f.pop("plugin/evals/sample/checks"), "state case needs"),
    (lambda f: f.update({"plugin/evals/sample/prompt.md": b"---\ntags: state\n---\n"}), "list of strings"),
])
def test_completeness_fails_for_omissions_and_invalid_contracts(change, message):
    files = source_case(state=True)
    change(files)
    with pytest.raises(ValueError, match=message):
        inventory.build_inventory(files, inventory.SOURCE_REVISION)


def fake_git(files):
    """Supply raw blobs, including embedded newlines/NULs, through the Git seam."""
    calls = []
    objects = [(path, f"{i:040x}", raw) for i, (path, raw) in enumerate(sorted(files.items()), 1)]

    def run(args, **kwargs):
        calls.append((args, kwargs))
        if args[1] == "ls-tree":
            data = b"".join(f"100644 blob {oid}\t{path}\0".encode() for path, oid, _ in objects)
        else:
            assert args == ["git", "cat-file", "--batch"]
            assert kwargs["input"] == "".join(f"{oid}\n" for _, oid, _ in objects).encode()
            data = b"".join(f"{oid} blob {len(raw)}\n".encode() + raw + b"\n" for _, oid, raw in objects)
        return SimpleNamespace(stdout=data)

    return run, calls


def test_git_reader_uses_only_selected_revision_and_preserves_blob_bytes(tmp_path, monkeypatch):
    monkeypatch.setattr(inventory, "ROOT", tmp_path)
    files = source_case() | {"plugin/evals/binary": b"\0line\r\n---\n"}
    run, calls = fake_git(files)
    assert inventory.read_source(inventory.SOURCE_REVISION, run=run) == files
    assert len(calls) == 2
    assert calls[0][0] == ["git", "ls-tree", "-r", "-z", inventory.SOURCE_REVISION, "--", "plugin/evals"]
    assert all(kwargs["cwd"] == tmp_path and kwargs["check"] for _, kwargs in calls)
    with pytest.raises(ValueError, match="full lowercase commit SHA"):
        inventory.read_source("HEAD", run=run)
    assert len(calls) == 2


def test_check_is_read_only_and_detects_removed_or_changed_entries(tmp_path, monkeypatch):
    output = tmp_path / "inventory.json"
    monkeypatch.setattr(inventory, "ROOT", tmp_path)
    monkeypatch.setattr(inventory, "OUTPUT", output)
    run, _ = fake_git(source_case())
    assert inventory.main([], run=run) == 0
    before = output.read_bytes()
    assert inventory.main(["--check"], run=run) == 0
    assert output.read_bytes() == before
    value = json.loads(before)
    value["cases"][0]["expected_checks"]["graders"].pop()
    output.write_text(json.dumps(value), encoding="utf-8")
    changed = output.read_bytes()
    with pytest.raises(SystemExit) as exc:
        inventory.main(["--check"], run=run)
    assert exc.value.code == 1
    assert output.read_bytes() == changed
    assert list(tmp_path.iterdir()) == [output]

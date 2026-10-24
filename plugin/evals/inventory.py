"""Account for the retired runner's source without invoking an agent or a fixture.

Run from any directory: uv run python plugin/evals/inventory.py [--check].
The JSON is a frozen migration starting point, not a runtime qualification report.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess

import yaml

SOURCE_REVISION = "c9c4570534c39f84207e25f8ea47f0446b88a07e"
ROOT = Path(__file__).resolve().parents[2]
OUTPUT = Path(__file__).with_name("inventory.json")
PREFIX = "plugin/evals/"
DECISION_CASES = frozenset({
    "accepted-automatic-failure-mode",
    "execution-recovery-boundaries",
    "execution-role-routing",
    "final-review-coverage-and-dispositions",
    "fix-round-from-stored-assignment",
    "handoff-stop-scopes",
    "metadata-preserves-checkpoint-state",
    "observed-revision-mismatch-held",
    "parallel-group-promotion",
    "reviewer-records-review-comment",
})


class UniqueLoader(yaml.SafeLoader):
    """Do not silently discard repeated source keys."""


def _mapping(loader, node):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node)
        if not isinstance(key, str) or key in result:
            raise ValueError(f"duplicate or non-string YAML key: {key!r}")
        result[key] = loader.construct_object(value_node)
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping)


def mapping(text: str, path: str) -> dict:
    try:
        value = yaml.load(text, Loader=UniqueLoader)
    except (yaml.YAMLError, ValueError) as exc:
        raise ValueError(f"{path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a YAML mapping")
    return value


def markdown(raw: bytes, path: str) -> dict:
    # splitlines handles both Git LF and test/checkout CRLF without splitting a
    # quoted regex or a block scalar on an embedded '---'.
    lines = raw.decode("utf-8").splitlines(keepends=True)
    if not lines or lines[0].rstrip("\r\n") != "---":
        raise ValueError(f"{path}: missing opening frontmatter delimiter")
    end = next((i for i in range(1, len(lines)) if lines[i].rstrip("\r\n") == "---"), None)
    if end is None:
        raise ValueError(f"{path}: missing closing frontmatter delimiter")
    return {
        "path": path,
        "frontmatter": mapping("".join(lines[1:end]), path),
        "body": "".join(lines[end + 1:]).strip(),
    }


def read_source(revision: str, *, run=subprocess.run) -> dict[str, bytes]:
    """Read committed blobs in two read-only Git calls, bypassing checkout filters."""
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("source revision must be a full lowercase commit SHA")
    tree = run(
        ["git", "ls-tree", "-r", "-z", revision, "--", "plugin/evals"],
        cwd=ROOT, check=True, capture_output=True,
    ).stdout
    entries = []
    for entry in tree.split(b"\0"):
        if not entry:
            continue
        metadata, path = entry.decode("utf-8").split("\t", 1)
        mode, kind, oid = metadata.split()
        if kind != "blob" or mode not in {"100644", "100755"}:
            raise ValueError(f"unsupported source member: {path}")
        entries.append((path, oid))
    batch = run(
        ["git", "cat-file", "--batch"],
        input="".join(f"{oid}\n" for _, oid in entries).encode("ascii"),
        cwd=ROOT, check=True, capture_output=True,
    ).stdout
    files = {}
    offset = 0
    for path, oid in entries:
        end = batch.index(b"\n", offset)
        actual_oid, kind, size = batch[offset:end].decode("ascii").split()
        length = int(size)
        offset = end + 1
        if actual_oid != oid or kind != "blob" or len(batch) < offset + length + 1 or batch[offset + length:offset + length + 1] != b"\n":
            raise ValueError(f"invalid blob response: {path}")
        files[path] = batch[offset:offset + length]
        offset += length + 1
    if offset != len(batch):
        raise ValueError("unexpected trailing blob response")
    return files


def build_inventory(files: dict[str, bytes], revision: str) -> dict:
    prompts = sorted(p for p in files if p.endswith("/prompt.md"))
    if not prompts:
        raise ValueError("no source cases found")
    cases = []
    accounted_graders = set()
    for path in prompts:
        directory = str(PurePosixPath(path).parent)
        name = PurePosixPath(directory).name
        prompt = markdown(files[path], path)
        tags = prompt["frontmatter"].get("tags")
        if not isinstance(tags, list) or not all(isinstance(t, str) for t in tags):
            raise ValueError(f"{path}: tags must be a list of strings")
        config_path = f"{directory}/case.yaml"
        config = mapping(files[config_path].decode("utf-8"), config_path) if config_path in files else None
        fixture = config.get("context", {}).get("scaffold_script") if config else None
        fixture_path = f"{directory}/{fixture}" if fixture else None
        if fixture_path and fixture_path not in files:
            raise ValueError(f"{config_path}: missing fixture {fixture_path}")
        checks_path = f"{directory}/checks"
        rules = [line.strip() for line in files.get(checks_path, b"").decode("utf-8").splitlines()
                 if line.strip() and not line.lstrip().startswith("#")]
        if "state" in tags and (not fixture_path or not rules):
            raise ValueError(f"{name}: state case needs a fixture and state rules")
        graders = []
        for grader_path in sorted(p for p in files if p.startswith(f"{directory}/graders/") and p.endswith(".md")):
            grader = markdown(files[grader_path], grader_path)
            if not isinstance(grader["frontmatter"].get("type"), str):
                raise ValueError(f"{grader_path}: missing grader type")
            grader["id"] = PurePosixPath(grader_path).stem
            grader["migration_status"] = "untranslated"
            graders.append(grader)
            accounted_graders.add(grader_path)
        if not graders:
            raise ValueError(f"{name}: no graders")
        supplemental = []
        if name == "parallel-reference-before-dispatch":
            supplemental.append("Successful lead Read of parallel-execution.md precedes the first writing worker dispatch; tool presence and response regex alone do not prove ordering.")
        cases.append({
            "id": name,
            "prompt": prompt,
            "tags": tags,
            "fixture": {"case_config_path": config_path if config else None,
                        "case_config": config, "script": fixture_path,
                        "shared_scaffold": f"{PREFIX}_shared/scaffold.sh" if fixture else None},
            "boundary": "decision-exercise" if name in DECISION_CASES else "live-behavior",
            "expected_checks": {"graders": graders, "state_checks_path": checks_path if rules else None,
                                "state_rules": rules, "supplemental": supplemental},
            "migration_status": "untranslated",
        })
    all_graders = {p for p in files if "/graders/" in p}
    if all_graders != accounted_graders:
        raise ValueError(f"unaccounted graders: {sorted(all_graders - accounted_graders)}")
    return {
        "schema_version": 1,
        "source_revision": revision,
        "source_runner": "claude plugin eval (retired)",
        "replacement_qualification": "pending; inventory completeness is not runtime qualification",
        "evidence_contract": {
            "decision-exercise": "Checks selected next operations in the answer; does not qualify live dispatch, concurrency, ordering, or effects.",
            "live-behavior": "Requires runtime evidence for the source tool/output criteria; source fixtures or filesystem presence do not prove native resource consumption.",
            "state": "All source graders AND state rules must pass against actual agent state. Missing or empty logs never prove non-action; setup/checker reads cannot provide agent evidence.",
            "packaged_roles": "Named packaged-role dispatch must be observed; a generic worker completing the task is insufficient.",
            "historical_results": "Keep original runner, tested revision, runtime/model versions and settings with local reports. This inventory revision does not relabel past results or establish a missing result revision.",
        },
        "source_files": {p: hashlib.sha256(raw).hexdigest() for p, raw in sorted(files.items())},
        "cases": cases,
    }


def render(inventory: dict) -> str:
    return json.dumps(inventory, ensure_ascii=False, indent=2) + "\n"


def main(argv=None, *, run=subprocess.run) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="compare without writing any file")
    args = parser.parse_args(argv)
    inventory = build_inventory(read_source(SOURCE_REVISION, run=run), SOURCE_REVISION)
    content = render(inventory)
    if args.check:
        if not OUTPUT.is_file() or OUTPUT.read_text(encoding="utf-8") != content:
            parser.exit(1, "inventory differs from source; regenerate inventory.json\n")
    else:
        OUTPUT.write_text(content, encoding="utf-8", newline="\n")
    print(f"{SOURCE_REVISION}: {len(inventory['cases'])} cases, "
          f"{sum(len(c['expected_checks']['graders']) for c in inventory['cases'])} graders; "
          f"{'validated' if args.check else 'generated'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""The retrospective is an agent procedure; these checks protect its written guarantees.

They do not claim native runtime execution or real-project retrospective usefulness.
"""

from pathlib import Path

import pytest
import yaml

from dotbrain import skills


ROOT = Path("plugin/skills/retro")


def _text(name):
    return " ".join((ROOT / name).read_text(encoding="utf-8").split())


def test_retro_is_explicitly_invocable_in_both_runtimes():
    skill = _text("SKILL.md")
    assert "disable-model-invocation: true" in skill
    metadata = yaml.safe_load((ROOT / "agents/openai.yaml").read_text(encoding="utf-8"))
    assert metadata["policy"]["allow_implicit_invocation"] is False
    assert metadata["interface"]["display_name"]
    for invocation in ("/dotbrain:retro", "skill picker", "external nightly job"):
        assert invocation in skill
    assert "`$retro` is not confirmed for plugin delivery" in skill


def test_retro_is_discovered_and_delivered_with_its_reference(dotbrain_home, tmp_path):
    assert "brain/retro" in skills.discover_skills(dotbrain_home / "skills")
    for runtime in ("claude", "codex"):
        destination = tmp_path / runtime / "skills"
        result = skills.link_into(dotbrain_home, destination, ["brain/retro"])
        assert not result.warnings
        assert (destination / "retro/SKILL.md").read_bytes() == (ROOT / "SKILL.md").read_bytes()
        assert (destination / "retro/references/notebook.md").is_file()
        assert (destination / "retro/references/promotion.md").is_file()
        assert (destination / "retro/agents/openai.yaml").is_file()


@pytest.mark.parametrize(
    "contracts",
    [
        # Initial coverage is bounded and older history is not implicitly reviewed.
        ("bounded initial range", "latest 50 commits", "last 14 days", "excluded older history"),
        # Discovery can run without repeating substantive review or changing counts.
        ("all source versions are unchanged", "skip substantive review", "distinct-day counts unchanged"),
        # Both negative and positive outcomes need evidence, with uncertainty visible.
        ("successful practices alongside mistakes", "observations, inference", "evidence limits",
         "a candidate alone does not prove a fix worked"),
        # Every entry path shares one notebook writer across worktrees and hosts.
        ("Acquire exclusive ownership", "external jobs share the same notebook",
         "check its creation time", "only this writer edits the notebook"),
        ("`RETRO.md.lock`", "`RETRO.md.tmp.<owner>.<nonce>`", "same filesystem",
         "local Git exclude file", "never stage these coordination files"),
        # The first save cannot discard evidence still awaiting a durable checkpoint.
        ("Persist findings before advancing progress", "old completed cursors and pending range",
         "Only then mark processed versions complete", "second atomic save",
         "upsert the same identities"),
        # Promotion consumes an explicit seam but capture never adopts a public rule.
        ("promotion.status: eligible", "at least three distinct supported days",
         "capture does not author `RULES.md`", "or reconcile merges"),
        # Retrospective remains separate from execution and human learning.
        ("no scheduler or CLI loop runner", "no human learning entries",
         "checkpoint hooks", "session-start injection", "no push, PR, merge"),
    ],
)
def test_capture_contract(contracts):
    text = _text("SKILL.md")
    for contract in contracts:
        assert contract in text


@pytest.mark.parametrize(
    "contracts",
    [
        # Delayed writes and skewed clocks must be found outside the timestamp overlap.
        ("bd list --all --limit 0 --json", "Compare each listed `updated_at`",
         "every differing timestamp or absent stored issue", "outside the overlap query",
         "delayed visibility and writer clock skew", "never the sole issue-change detector"),
        # Excluded history needs a durable baseline, or an unchanged rerun reviews it.
        ("items-map entry for every enumerated pre-range issue", "`updated_at`, revision",
         "aggregate and per-comment fingerprints", "excluded: before the first range",
         "exclusion, not substantive review", "unchanged second pass",
         "skips old history instead of treating it as newly visible"),
        # Rebased aliases cannot manufacture a second recurrence day.
        ("author timestamp with offset", "earliest established event date",
         "later author or committer timestamp alone cannot add or move a supported day",
         "evidence-backed correction"),
        # Hash the actual comment schema; empty counts alone cannot hide deletions.
        ("`id`, `issue_id`, `author`, `text`, and `created_at`", "hashing `text`",
         "no required `updated_at`", "`comment_count` is 0 and the stored comment set is empty",
         "missing/unknown counts", "deletion of the last comment"),
        # Issue creation age and parent timestamps must not conceal changed comments.
        ("bd list --all --limit 0 --updated-after", "per-item `updated_at`",
         "bd show <id> --json", "revision token as a string",
         "bd comments <id> --json", "including old and closed issues",
         "Do not assume a comment edit changes issue `updated_at`",
         "additions, edits, and deletions are visible"),
        # Equal timestamp boundaries and concurrent updates remain discoverable.
        ("one second earlier", "strict and inclusive server comparisons", "equal timestamps",
         "subsecond precision", "updated_at > T", "compare comment fingerprints again",
         "All pages must be read", "A failed comments query is not an empty list"),
        # Source identity, source versions, and independent events are different concepts.
        ("immutable `finding_id`", "semantic trigger and required practice",
         "occurrence_id", "event_key", "aliases", "not a new occurrence",
         "even when published on different days", "uncounted corroboration",
         "retain its occurrence ID and gain OID aliases"),
        # Dates come from deduplicated evidence in one timezone, not processing runs.
        ("Preserve the recorded timezone", "Several IDs on the same day count once",
         "not the dates of copied reports, edits, processing, or retries",
         "replace the old date", "Undated or ambiguous evidence", "distinct_days"),
        # History changes cannot be silently treated as continuous coverage.
        ("old object exists and is an ancestor", "old..new", "Clock skew",
         "old head is unreachable/missing", "record a history gap",
         "Keep the old completed cursor", "fresh bounded range and explicit reset",
         "unresolved gap"),
        # Crash recovery and compaction retain both provenance and deduplication keys.
        ("crash between saves", "same finding and occurrence IDs",
         "remaining pending IDs", "Compact prose, not the deduplication ledger",
         "promotion destination/history"),
    ],
)
def test_notebook_cursor_and_identity_contract(contracts):
    text = _text("references/notebook.md")
    for contract in contracts:
        assert contract in text


def test_empty_notebook_examples_are_parseable_without_live_project_evidence():
    text = (ROOT / "references/notebook.md").read_text(encoding="utf-8")
    examples = [yaml.safe_load(block.split("```", 1)[0]) for block in text.split("```yaml\n")[1:]]
    progress, finding = examples
    assert progress["schema"] == 1
    assert progress["timezone"] == "UTC"
    assert progress["progress"]["completed"]["beads"] is None
    assert progress["progress"]["pending"] is None
    assert finding["evidence"] == finding["evidence_dates"] == []
    assert finding["distinct_days"] == 0
    assert finding["promotion"] == {"status": "collecting", "destination": None, "adopted_at": None}


@pytest.mark.parametrize("path", ["docs/prompts.md", "docs/zh/prompts.md"])
def test_prompt_guides_list_retro_as_explicit_only(path):
    introduction = Path(path).read_text(encoding="utf-8").split("## ", 1)[0]
    assert "`retro`" in introduction
    assert "never start on their own" in introduction or "从不会自动启动" in introduction


def test_chinese_retro_description_requires_preparation_and_verified_acceptance():
    description = Path("docs/zh/skills.md").read_text(encoding="utf-8").split(
        "**`retro`**", 1
    )[1].split("\n- ", 1)[0]
    assert "三个不同证据日期" in description
    assert "自动准备" in description
    assert "合入目标分支" in description
    assert "可手动调用，也可由外部定时任务调用" in description
    assert "Agent 的发现" in description

from pathlib import Path
import tomllib


def normalized(path):
    return " ".join(Path(path).read_text(encoding="utf-8").split())


def test_reviewer_returns_complete_read_only_report_on_both_runtimes():
    claude = Path("plugin/agents/reviewer.md").read_text(encoding="utf-8")
    codex = tomllib.loads(Path("src/dotbrain/resources/agents/codex/reviewer.toml").read_text(encoding="utf-8"))
    assert codex["developer_instructions"].strip() == claude.split("---", 2)[2].strip()
    assert codex["model_reasoning_effort"] == "high"
    assert "model" not in codex
    prompt = " ".join(codex["developer_instructions"].split())
    for requirement in (
        "never claim, assign, close, create beads, append comments, or write metadata",
        "reviewer identity, reviewed base and head",
        "Covered items and acceptance coverage per criterion",
        "Per-item `APPROVE` or `CHANGES` verdicts",
        "stable IDs within this report, affected items, severity",
        "Material evidence and coverage limits, including missing evidence",
        "HEAD plus diff fingerprint for uncommitted changes",
        "return no verdict and name what is missing",
        "Read explicitly assigned skills",
        "report findings only and no verdict",
        "only when material, a brief caveat about evidence or scope limits",
        "Omit empty findings sections",
        "Do not cite Brain paths or decision-record identifiers",
    ):
        assert requirement in prompt, requirement
    assert "bd comments add" not in prompt
    assert "Return only the comment ID" not in prompt


def test_review_blocks_change_consequences_and_preserves_evidence_gaps():
    prompt = normalized("plugin/agents/reviewer.md")
    for requirement in (
        "blocker or high regression caused by a reviewed change",
        "wherever its symptom appears, including unchanged consumers and interactions",
        "low findings and unrelated existing defects accompany `APPROVE`",
        "relevant evidence, a concrete trace, or a small targeted check",
        "missing evidence as a gap rather than a verified claim",
    ):
        assert requirement in prompt, requirement
    assert "findings outside that diff accompany" not in prompt


def test_lead_records_provenance_and_single_cross_item_repair_ownership():
    record = normalized("plugin/skills/run-execution/references/execution-record.md")
    graph = normalized("plugin/skills/manage-work-graph/references/review-beads.md")
    for requirement in (
        "Before notifying workers or dispatching repairs",
        "under its own actor",
        "Preserve reviewer identity, review number, base/head references",
        "per-item verdicts, complete finding wording and severity",
        "Confirm the stored comment text matches the returned review before repair dispatch",
        "coordination notes as lead additions",
        "one responsible worker",
        "full finding on that worker's item",
        "durable comment and finding ID from every other affected item",
        "Route repairs to the original workers",
        "never silently change a verdict",
        "unchanged consumers and interactions",
        "unrelated existing defects accompany `APPROVE`",
        "human's explicit decline, not a reviewer verdict",
    ):
        assert requirement in record, requirement
    assert "--actor <lead-actor>" in record
    assert "--actor <reviewer-actor>" not in record
    assert "reviewer writes its own `Review` comments" not in record
    for requirement in (
        "reviewer writes no tracker records",
        "material evidence or coverage limits before dispatching repairs",
        "one responsible worker",
        "Repair references go to the original workers",
        "unchanged consumers and interactions",
        "Missing safety evidence is a reported gap",
        "only a person decides when that gate is discharged",
    ):
        assert requirement in graph, requirement
    target = Path("plugin/skills/manage-work-graph/references") / "../../run-execution/references/execution-record.md"
    assert target.is_file()

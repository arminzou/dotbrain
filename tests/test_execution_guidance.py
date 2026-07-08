from pathlib import Path


def test_work_intake_mentions_active_design_doc_for_design_discoveries():
    doc = Path(
        "src/dotbrain/resources/skills/brain/operate-execution/references/work-intake.md"
    ).read_text()
    normalized = " ".join(doc.split())

    assert "living place to track design-level discoveries and unknowns" in normalized
    assert "the active design doc owns current design, known unknowns, design-level discoveries" in normalized
    assert "--spec-id design:<slug>" in normalized


def test_beads_reference_keeps_design_doc_and_status_ownership_separate():
    doc = Path(
        "src/dotbrain/resources/skills/brain/operate-execution/references/beads.md"
    ).read_text()
    normalized = " ".join(doc.split())

    assert "living design authority is the active design doc linked by `--spec-id design:<slug>`" in normalized
    assert "keep that field for slice-local detail only" in normalized


def test_operating_loop_reads_linked_design_doc_before_implementing():
    doc = Path(
        "src/dotbrain/resources/skills/brain/operate-execution/SKILL.md"
    ).read_text()
    normalized = " ".join(doc.split())

    assert "If the item carries `spec-id design:<slug>`, read `.brain/designs/<slug>.md`" in normalized
    assert "before implementing" in normalized


def test_operate_execution_requires_verification_section_in_public_prs():
    doc = Path(
        "src/dotbrain/resources/skills/brain/operate-execution/SKILL.md"
    ).read_text()
    normalized = " ".join(doc.split())

    assert "the PR body must carry a `Verification` section" in normalized
    assert "no `.brain/` paths, ADR numbers, or `design:` spec-ids" in normalized


def test_iterate_design_requires_verification_section_in_public_prs():
    doc = Path(
        "src/dotbrain/resources/skills/brain/iterate-design/SKILL.md"
    ).read_text()
    normalized = " ".join(doc.split())

    assert "the PR body must carry a `Verification` section" in normalized
    assert "No `.brain/` paths, ADR numbers, or `design:` spec-ids" in normalized


def test_iterate_design_lands_via_dedicated_branch_and_review_surface():
    doc = Path(
        "src/dotbrain/resources/skills/brain/iterate-design/SKILL.md"
    ).read_text()
    normalized = " ".join(doc.split())

    assert "runs on a dedicated branch — never directly on `main`" in normalized
    assert "`FINAL` means the checkpoint is verified, not that the work has landed" in normalized
    assert (
        "Landing means opening the review surface: a PR when the project hosts them, otherwise the"
        in normalized
    )
    assert "branch diff reviewed directly and merged locally" in normalized
    assert "Never push or open a PR unprompted" in normalized


def test_operate_execution_lands_local_because_reviewed_continuously():
    doc = Path(
        "src/dotbrain/resources/skills/brain/operate-execution/SKILL.md"
    ).read_text()
    normalized = " ".join(doc.split())

    assert "the human reviews each edit and each `bd close` as it happens" in normalized
    assert "so it lands local by default, epic or not" in normalized
    assert "unless a linked public issue already requires one" in normalized
    assert "`bd close` is the close signal for this local-review path" in normalized


def test_enter_main_agent_not_referenced_in_iterate_design_or_operate_execution():
    iterate_doc = Path(
        "src/dotbrain/resources/skills/brain/iterate-design/SKILL.md"
    ).read_text()
    operate_doc = Path(
        "src/dotbrain/resources/skills/brain/operate-execution/SKILL.md"
    ).read_text()

    assert "enter-main-agent" not in iterate_doc
    assert "enter-main-agent" not in operate_doc

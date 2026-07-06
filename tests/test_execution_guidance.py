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

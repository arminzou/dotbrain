from pathlib import Path

from dotbrain import brainspaces


def test_seeded_design_docs_are_living_while_active(dotbrain_home: Path, tmp_path: Path):
    brainspace = tmp_path / "brainspace"
    brainspace.mkdir()

    brainspaces.seed_brain(brainspace, dotbrain_home)

    brain = brainspace / ".brain"
    dotbrain_doc = (brain / "DOTBRAIN.md").read_text(encoding="utf-8")
    designs_readme = (brain / "designs" / "README.md").read_text(encoding="utf-8")

    dotbrain_doc = " ".join(dotbrain_doc.split())
    designs_readme = " ".join(designs_readme.split())

    assert "living design authority" in dotbrain_doc
    assert "lifecycle:" in dotbrain_doc
    assert "Agents must update lifecycle" in dotbrain_doc
    assert "Beads still own execution state" in dotbrain_doc
    assert "living unknowns ledger" in designs_readme
    assert "Use `lifecycle:` frontmatter" in designs_readme
    assert "Beads own execution state" in designs_readme
    assert "criteria changes are human decisions" in designs_readme
    assert "gates rot" in designs_readme


def test_to_design_states_criteria_lifecycle(dotbrain_home: Path):
    skill = (
        dotbrain_home
        / "skills"
        / "brain"
        / "to-design"
        / "SKILL.md"
    ).read_text(encoding="utf-8")

    assert "Prefer mechanical pass/fail checks" in skill
    assert "human decision gate" in skill
    assert "criteria changes are human decisions" in skill
    assert "gates rot" in skill


def test_to_issues_uses_spec_id_for_design_linked_beads(dotbrain_home: Path):
    skill = (
        dotbrain_home
        / "skills"
        / "brain"
        / "to-issues"
        / "SKILL.md"
    ).read_text(encoding="utf-8")

    assert "--spec-id design:<slug>" in skill
    assert "Do not use `--design` for design-linked initiative slices." in skill


def test_to_issues_titles_echo_design_doc_subsections(dotbrain_home: Path):
    skill = (
        dotbrain_home
        / "skills"
        / "brain"
        / "to-issues"
        / "SKILL.md"
    ).read_text(encoding="utf-8")

    assert "Word each slice `Title` to echo the corresponding `Current Design` subsection" in skill


def test_iterate_design_rereads_design_doc_every_cycle(dotbrain_home: Path):
    skill = (
        dotbrain_home
        / "skills"
        / "brain"
        / "iterate-design"
        / "SKILL.md"
    ).read_text(encoding="utf-8")
    normalized = " ".join(skill.split())

    assert "Loop protocol (every iteration, not just the first)" in normalized
    assert "Reread the active design doc fresh" in normalized
    assert normalized.count("Reread the active design doc fresh") >= 2


def test_iterate_design_has_loop_worthiness_check(dotbrain_home: Path):
    skill = (
        dotbrain_home
        / "skills"
        / "brain"
        / "iterate-design"
        / "SKILL.md"
    ).read_text(encoding="utf-8")
    normalized = " ".join(skill.split())

    assert "Loop-worthiness check" in normalized
    assert "A mechanical gate exists or can be named" in normalized
    assert "A hard stop is set" in normalized
    assert "A human gate covers anything irreversible" in normalized


def test_iterate_design_distinguishes_reviewer_from_verifier(dotbrain_home: Path):
    skill = (
        dotbrain_home
        / "skills"
        / "brain"
        / "iterate-design"
        / "SKILL.md"
    ).read_text(encoding="utf-8")
    normalized = " ".join(skill.split())

    assert "The reviewer supplements the verifier, never replaces it" in normalized
    assert "two optimists agreeing" in normalized

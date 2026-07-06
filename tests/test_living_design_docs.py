from pathlib import Path

from dotbrain import brainspaces


def test_seeded_design_docs_are_living_while_active(dotbrain_home: Path, tmp_path: Path):
    brainspace = tmp_path / "brainspace"
    brainspace.mkdir()

    brainspaces.seed_brain(brainspace, dotbrain_home)

    brain = brainspace / ".brain"
    dotbrain_doc = (brain / "DOTBRAIN.md").read_text()
    designs_readme = (brain / "designs" / "README.md").read_text()

    dotbrain_doc = " ".join(dotbrain_doc.split())
    designs_readme = " ".join(designs_readme.split())

    assert "living design authority" in dotbrain_doc
    assert "lifecycle:" in dotbrain_doc
    assert "Agents must update lifecycle" in dotbrain_doc
    assert "Beads still own execution state" in dotbrain_doc
    assert "living unknowns ledger" in designs_readme
    assert "Use `lifecycle:` frontmatter" in designs_readme
    assert "Beads own execution state" in designs_readme


def test_to_issues_uses_spec_id_for_design_linked_beads(dotbrain_home: Path):
    skill = (
        dotbrain_home
        / "skills"
        / "brain"
        / "to-issues"
        / "SKILL.md"
    ).read_text()

    assert "--spec-id design:<slug>" in skill
    assert "Do not use `--design` for design-linked initiative slices." in skill

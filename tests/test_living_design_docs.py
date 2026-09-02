from pathlib import Path

from dotbrain import brainspaces, resource_loader


def test_seed_brain_copies_the_packaged_templates_verbatim(dotbrain_home: Path, tmp_path: Path):
    """Seeding must not paraphrase. Comparing bytes to the packaged template means
    rewording the convention never touches this test, while a seeding bug that drops
    or mangles a file still fails it."""
    brainspace = tmp_path / "brainspace"
    brainspace.mkdir()

    brainspaces.seed_brain(brainspace, dotbrain_home)

    brain = brainspace / ".brain"
    for relative in ("DOTBRAIN.md", "designs/README.md", "adr/README.md"):
        with resource_loader.resource_file(f"templates/brain/{relative}") as packaged:
            assert (brain / relative).read_bytes() == packaged.read_bytes(), relative


def test_to_design_template_carries_the_section_set(dotbrain_home: Path):
    template = (
        dotbrain_home
        / "skills"
        / "brain"
        / "to-design"
        / "templates"
        / "design.md"
    ).read_text(encoding="utf-8")

    assert "lifecycle: draft" in template
    for section in (
        "## Motivation",
        "## Goals",
        "## Non-goals",
        "## Design",
        "## Success Criteria",
        "## Verification Evidence",
        "## Known Unknowns",
        "## Implementation Notes",
        "## Deviations",
        "## Human Decisions Needed",
        "## Alternatives Considered",
        "## Rollout",
    ):
        assert section in template



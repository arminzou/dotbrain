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
    """Section-authoring guidance and the rules governing the doc after authoring both live in
    the template, beside the sections they bind. The skill keeps only the procedural bar."""
    to_design = dotbrain_home / "skills" / "brain" / "to-design"
    skill = (to_design / "SKILL.md").read_text(encoding="utf-8")
    template = (to_design / "templates" / "design.md").read_text(encoding="utf-8")

    assert "Prefer mechanical pass/fail checks" in template
    assert "human decision gate" in template
    assert "criteria changes are human decisions" in template
    assert "gates rot" in template
    assert "Completion: every section you kept is filled" in skill
    assert "each goal has a matching entry under `Success Criteria`" in skill


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


def test_close_design_covers_every_terminal_branch(dotbrain_home: Path):
    skill = (
        dotbrain_home / "skills" / "brain" / "close-design" / "SKILL.md"
    ).read_text(encoding="utf-8")

    for state in ("shipped", "abandoned", "superseded"):
        assert state in skill
    assert "residue" in skill
    assert "gates rot" not in skill, "the gates-rot rule belongs to the design template"


def test_close_design_frontmatter_vocabulary_is_single_sourced(dotbrain_home: Path):
    """The field set is stated in DOTBRAIN.md (policy) and close-design (the skill that
    stamps it). No third copy."""
    brain_doc = (
        dotbrain_home
        / "templates"
        / "brain"
        / "DOTBRAIN.md"
    )
    skill = (
        dotbrain_home / "skills" / "brain" / "close-design" / "SKILL.md"
    ).read_text(encoding="utf-8")

    for field in ("lifecycle:", "started:", "ended:", "extends:", "residue:"):
        assert field in skill
    if brain_doc.exists():
        text = brain_doc.read_text(encoding="utf-8")
        assert "close-design" in text


def test_operate_execution_hands_off_at_epic_close(dotbrain_home: Path):
    skill = (
        dotbrain_home / "skills" / "brain" / "operate-execution" / "SKILL.md"
    ).read_text(encoding="utf-8")
    normalized = " ".join(skill.split())

    assert "run `close-design` before moving on" in normalized


def test_to_design_routes_unfamiliar_territory_to_find_unknowns(dotbrain_home: Path):
    skill = (
        dotbrain_home
        / "skills"
        / "brain"
        / "to-design"
        / "SKILL.md"
    ).read_text(encoding="utf-8")

    assert "find-unknowns" in skill


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

    assert "Word each slice `Title` to echo the corresponding `Design` subsection" in skill


def test_iterate_design_rereads_design_doc_every_cycle(dotbrain_home: Path):
    skill = (
        dotbrain_home
        / "skills"
        / "brain"
        / "iterate-design"
        / "SKILL.md"
    ).read_text(encoding="utf-8")
    normalized = " ".join(skill.split())

    assert "Reread the active design doc fresh" in normalized

    prompt = " ".join(
        (
            dotbrain_home
            / "skills"
            / "brain"
            / "iterate-design"
            / "templates"
            / "loop-prompt.md"
        ).read_text(encoding="utf-8").split()
    )
    assert "Loop protocol (every iteration, not just the first)" in prompt
    assert "Do not rely on an earlier iteration's memory of the design doc." in prompt


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


def test_grill_decisions_has_a_checkable_stopping_condition(dotbrain_home: Path):
    """The decision tree is a visible artifact so the session can be finished, not
    abandoned when the agent feels done."""
    skill = (
        dotbrain_home / "skills" / "brain" / "grill-decisions" / "SKILL.md"
    ).read_text(encoding="utf-8")

    assert "## Boundaries" in skill
    assert "Lay out the decision tree" in skill
    assert "every branch on the tree is resolved or explicitly deferred" in skill.lower()
    assert "Interview me" not in skill, "skills address the agent, not the user"
    assert "<what-to-do>" not in skill, "the set uses markdown headings"


def test_adr_offer_test_is_single_sourced(dotbrain_home: Path):
    """The three-part test lives only in ADR-FORMAT.md; skills that offer ADRs point at it."""
    brain = dotbrain_home / "skills" / "brain"
    owners = [
        p
        for p in brain.rglob("*.md")
        if "hard to reverse" in p.read_text(encoding="utf-8").lower()
    ]

    assert [p.name for p in owners] == ["ADR-FORMAT.md"]
    for skill in ("grill-decisions", "review-architecture"):
        assert "ADR-FORMAT.md" in (brain / skill / "SKILL.md").read_text(encoding="utf-8")


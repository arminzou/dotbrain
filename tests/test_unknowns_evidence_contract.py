"""Keep investigation, human authority, and verifiable handoff guidance together."""

from pathlib import Path

import pytest


SKILLS = Path("plugin/skills")
CONVENTION = Path("src/dotbrain/resources/templates/brain/DOTBRAIN.md")


def _text(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split())


@pytest.mark.parametrize(
    "path",
    [
        SKILLS / "find-unknowns/SKILL.md",
        SKILLS / "grill-decisions/SKILL.md",
        SKILLS / "to-design/SKILL.md",
        SKILLS / "to-issues/SKILL.md",
    ],
)
def test_unknowns_preserve_action_and_authority_boundaries(path: Path):
    text = _text(path).lower()
    for contract in (
        "cheapest next action",
        "reason",
        "evidence, inference, and unresolved gaps",
        "reversible implementation defaults",
        "preferences",
        "authority",
        "acceptance changes",
        "consequential tradeoffs",
        "recommendation",
        "additional pilots, budgets, or outward actions",
    ):
        assert contract in text, f"{path}: missing {contract}"
    assert "blocking status" in text or "whether it blocks the current decision" in text


@pytest.mark.parametrize("skill", ["find-unknowns", "grill-decisions", "to-design"])
def test_historical_intent_requires_evidence(skill: str):
    text = _text(SKILLS / skill / "SKILL.md")
    assert "recorded" in text
    assert "history" in text
    assert "current code" in text
    assert "intent" in text
    assert "observable questions" in text


def test_find_unknowns_stays_read_only_with_existing_owners():
    scan = _text(SKILLS / "find-unknowns/SKILL.md")
    convention = _text(CONVENTION)
    assert "This skill is read-only" in scan
    assert "Active designs own initiative uncertainty; Beads owns execution state" in scan
    assert "separate uncertainty ledger" in scan
    for quadrant in ("Known knowns", "Known unknowns", "Unknown knowns", "Unknown unknowns"):
        assert quadrant in convention
    for owner in ("to-design", "grill-decisions", "manage-work-graph"):
        assert f"`{owner}`" in scan


@pytest.mark.parametrize(
    "path",
    [
        SKILLS / "to-design/SKILL.md",
        SKILLS / "to-design/templates/design.md",
        SKILLS / "to-issues/SKILL.md",
    ],
)
def test_design_handoffs_have_verifiable_seams(path: Path):
    text = _text(path).lower()
    for contract in (
        "concrete seams",
        "independently verifiable outcomes" if "to-issues" not in str(path) else "verify it independently",
        "verification boundar",
        "prerequisites",
    ):
        assert contract in text, f"{path}: missing {contract}"
    assert "file layout alone" in text or "unrelated file layout" in text
    assert "shared resources" in text or "interface/resource prerequisites" in text


def test_decomposition_retains_vertical_slices_and_integration_dependencies():
    text = _text(SKILLS / "to-issues/SKILL.md")
    assert "Preserve vertical slices" in text
    assert "integration checks where individually passing pieces interact" in text
    assert "`Verification boundary`" in text
    assert "`Interface/resource prerequisites`" in text
    assert "bd dep add <blocked-id> <blocker-id>" in text


def test_convention_keeps_core_boundaries_and_points_to_owning_skills():
    text = _text(CONVENTION)
    for contract in (
        "`find-unknowns` is read-only",
        "investigate facts first",
        "cheapest next action and blocking status or reasoned deferral",
        "reversible defaults within scope",
        "preferences, authority, acceptance changes, consequential tradeoffs",
        "evidence-unsettled decisions",
        "evidence and experiment limits",
        "Active designs own uncertainty; Beads owns execution state",
        "`to-design` and `to-issues` detail verifiable seams",
        "interface/resource prerequisites",
    ):
        assert contract in text

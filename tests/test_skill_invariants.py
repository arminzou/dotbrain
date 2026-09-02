"""Tier 2: the few rules whose silent removal would be dangerous.

One test per invariant, asserted against the single place that owns it. Where a
dependent skill must not restate the rule, that is checked as containment — the
owner has it, the dependent points at it — rather than by pinning either wording.

The loop invariants live in test_loop_rules.py, which already owns them against the
same canonical file; they are not repeated here. Everything else about how these
skills read is reviewed by eye, not by equality check.

If you are adding a test here, the bar is: someone could delete this rule in a
plausible refactor, and the consequence would be a leak, a lost guarantee, or an
irreversible action taken without a human.
"""

from __future__ import annotations

import re
from pathlib import Path

SKILLS = Path("plugin/skills")
CONVENTION = Path("src/dotbrain/resources/templates/brain/DOTBRAIN.md")


def _text(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split())


def test_public_private_boundary_is_inward_only():
    """The Brain is never mirrored outward. Losing this leaks private design history
    into a public repo, which is not recoverable by editing the file afterwards."""
    convention = _text(CONVENTION)

    assert re.search(r"Brain never is", convention)
    assert re.search(r"[Nn]ever mirror Brain content", convention)


def test_no_skill_creates_a_public_issue_from_private_work():
    """Public issues are intake, never a projection of the private graph. The only
    place allowed to create one is the public triage surface itself."""
    for skill_md in sorted(SKILLS.glob("*/*.md")) + sorted(SKILLS.glob("*/*/*.md")):
        if skill_md.parts[2] == "triage-public":
            continue
        assert "gh issue create" not in skill_md.read_text(encoding="utf-8"), skill_md


def test_private_identifiers_never_reach_a_public_pr():
    """Brain paths, ADR numbers and spec-ids in a PR body leak the private layer to
    anyone reading the repo. The rule has one home; iterate-design points at it."""
    owner = _text(SKILLS / "operate-execution/references/public-provenance.md")
    loop = _text(SKILLS / "iterate-design/SKILL.md")

    assert "Verification" in owner
    assert re.search(r"`\.brain/` paths, ADR numbers", owner)
    assert "operate-execution" in loop, "iterate-design must point at the owner"
    assert not re.search(r"`\.brain/` paths, ADR numbers", loop), "second copy will drift"


def test_adr_offer_test_is_single_sourced():
    """The three-part test decides when any skill offers an ADR. Two copies means two
    different bars for writing a decision record."""
    owners = [
        p
        for p in SKILLS.rglob("*.md")
        if "hard to reverse" in p.read_text(encoding="utf-8").lower()
    ]

    assert [p.name for p in owners] == ["adr-format.md"]
    for skill in ("grill-decisions", "review-architecture"):
        assert "references/adr-format.md" in (SKILLS / skill / "SKILL.md").read_text(
            encoding="utf-8"
        )


def test_design_lifecycle_vocabulary_is_one_field_set():
    """A per-doc invented field makes a sweep across .brain/designs/ impossible to run,
    and the sweep is how a stale `active` doc is ever found."""
    convention = _text(CONVENTION)
    stamper = _text(SKILLS / "close-design/SKILL.md")

    for field in ("lifecycle:", "started:", "ended:", "extends:", "residue:"):
        assert field in convention, f"{field} missing from the convention"
        assert field in stamper, f"{field} missing from close-design"
    for state in ("draft", "active", "shipped", "abandoned", "superseded"):
        assert state in convention

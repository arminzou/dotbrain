from pathlib import Path

SKILLS = Path("plugin/skills")


def test_work_intake_mentions_active_design_doc_for_design_discoveries():
    doc = (SKILLS / "operate-execution/references/work-intake.md").read_text(encoding="utf-8")
    normalized = " ".join(doc.split())

    assert "living place to track design-level discoveries and unknowns" in normalized
    assert "the active design doc owns the design, known unknowns, design-level discoveries" in normalized
    assert "--spec-id design:<slug>" in normalized


def test_beads_reference_keeps_design_doc_and_status_ownership_separate():
    doc = (SKILLS / "operate-execution/references/beads.md").read_text(encoding="utf-8")
    normalized = " ".join(doc.split())

    assert "living design authority is the active design doc linked by `--spec-id design:<slug>`" in normalized
    assert "keep that field for slice-local detail only" in normalized


def test_operating_loop_reads_linked_design_doc_before_implementing():
    doc = (SKILLS / "operate-execution/SKILL.md").read_text(encoding="utf-8")
    normalized = " ".join(doc.split())

    assert "If the item carries `spec-id design:<slug>`, read `.brain/designs/<slug>.md`" in normalized
    assert "before implementing" in normalized


def test_operate_execution_requires_verification_section_in_public_prs():
    doc = (SKILLS / "operate-execution/SKILL.md").read_text(encoding="utf-8")
    normalized = " ".join(doc.split())

    assert "the PR body must carry a `Verification` section" in normalized
    assert "no `.brain/` paths, ADR numbers, or `design:` spec-ids" in normalized


def test_iterate_design_requires_verification_section_in_public_prs():
    """The rule has one home: operate-execution owns public provenance and PRs.
    iterate-design points at it rather than restating it."""
    owner = " ".join(
        (SKILLS / "operate-execution/SKILL.md").read_text(encoding="utf-8")
        .split()
    )
    loop = " ".join(
        (SKILLS / "iterate-design/SKILL.md").read_text(encoding="utf-8")
        .split()
    )

    assert "the PR body must carry a `Verification` section" in owner
    assert "no `.brain/` paths, ADR numbers, or `design:` spec-ids" in owner
    assert "`Verification` section described in `operate-execution`" in loop
    assert "the PR body must carry a `Verification` section" not in loop


def test_iterate_design_lands_via_dedicated_branch_and_review_surface():
    doc = (SKILLS / "iterate-design/SKILL.md").read_text(encoding="utf-8")
    normalized = " ".join(doc.split())

    assert "runs on a dedicated branch — never directly on `main`" in normalized
    assert "`FINAL` means the checkpoint is verified, not that the work has landed" in normalized
    assert (
        "Landing means opening the review surface: a PR when the project hosts them, otherwise the"
        in normalized
    )
    assert "branch diff reviewed directly and merged locally" in normalized
    assert "never push or open a PR unprompted" in normalized


def test_operate_execution_lands_local_because_reviewed_continuously():
    doc = (SKILLS / "operate-execution/SKILL.md").read_text(encoding="utf-8")
    normalized = " ".join(doc.split())

    assert "the human reviews each edit and each `bd close` as it happens" in normalized
    assert "so it lands local by default, epic or not" in normalized
    assert "Work originating from an existing public issue may land" in normalized
    assert "`bd close` remains the private close signal" in normalized


def test_private_execution_is_never_projected_to_public_tracking_issues():
    paths = [
        SKILLS / "operate-execution/SKILL.md",
        SKILLS / "to-design/SKILL.md",
        SKILLS / "to-issues/SKILL.md",
        SKILLS / "triage-public/SKILL.md",
    ]
    normalized = " ".join(
        " ".join(path.read_text(encoding="utf-8").split()) for path in paths
    )

    assert "private work is never published outward for tracking" in normalized
    assert "decomposition never creates public tracking issues" in normalized
    assert "private designs, epics, and beads never generate public tracking issues" in normalized
    assert "create a tracking issue for each slice" not in normalized
    assert "create a tracking issue there" not in normalized


def test_public_links_are_inward_provenance_only():
    doc = (SKILLS / "operate-execution/references/beads.md").read_text(encoding="utf-8")
    normalized = " ".join(doc.split())

    assert "genuine public intake or contributor collaboration" in normalized
    assert "never create a public issue to give a private bead an external reference" in normalized


def test_enter_main_agent_not_referenced_in_iterate_design_or_operate_execution():
    iterate_doc = (SKILLS / "iterate-design/SKILL.md").read_text(encoding="utf-8")
    operate_doc = (SKILLS / "operate-execution/SKILL.md").read_text(encoding="utf-8")

    assert "enter-main-agent" not in iterate_doc
    assert "enter-main-agent" not in operate_doc


def test_execution_skills_refer_worktree_repair_to_the_plugin_skill():
    for path in (
        SKILLS / "operate-execution/SKILL.md",
        SKILLS / "iterate-design/SKILL.md",
    ):
        doc = " ".join(path.read_text(encoding="utf-8").split())

        assert "wire-worktree" in doc
        assert "dotbrain worktrees wire" not in doc

from pathlib import Path

from dotbrain import brainspaces


def test_seeded_brain_carries_loop_invariants(dotbrain_home: Path, tmp_path: Path):
    brainspace = tmp_path / "brainspace"
    brainspace.mkdir()

    brainspaces.seed_brain(brainspace, dotbrain_home)

    doc = (brainspace / ".brain" / "DOTBRAIN.md").read_text(encoding="utf-8")
    doc = " ".join(doc.split())

    assert "Working in loops" in doc
    assert "criteria are human-owned" in doc
    assert "hard stop" in doc
    assert "report blocked with the attempt trail" in doc
    assert "end the loop and go to the human" in doc
    assert "the active design doc is the spec" in doc
    assert "Reread the spec every iteration" in doc


def test_seeded_brain_distinguishes_main_checkout_and_worktree_wiring(
    dotbrain_home: Path, tmp_path: Path
):
    brainspace = tmp_path / "brainspace"
    brainspace.mkdir()

    brainspaces.seed_brain(brainspace, dotbrain_home)

    doc = " ".join(
        (brainspace / ".brain" / "DOTBRAIN.md").read_text(encoding="utf-8").split()
    )

    assert "main checkout" in doc
    assert "`dotbrain wire`" in doc
    assert "git worktree" in doc
    assert "`wire-brain`'s worktree repair branch" in doc
    assert "with no `.brain`" in doc

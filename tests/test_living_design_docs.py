from pathlib import Path

from dotbrain import brainspaces, resource_loader


def test_seed_brain_copies_the_packaged_templates_verbatim(dotbrain_home: Path, tmp_path: Path):
    """Seeding must not paraphrase. Comparing against the packaged template means
    rewording the convention never touches this test, while a seeding bug that drops
    or mangles a file still fails it.

    Compared as text, not bytes: seed_brain normalises to LF on purpose, and a Windows
    checkout without .gitattributes hands us the packaged file with CRLF. That the
    seeded copy is LF is asserted in test_brainspaces.py, which owns that guarantee."""
    brainspace = tmp_path / "brainspace"
    brainspace.mkdir()

    brainspaces.seed_brain(brainspace, dotbrain_home)

    brain = brainspace / ".brain"
    for relative in ("DOTBRAIN.md", "designs/README.md", "adr/README.md"):
        with resource_loader.resource_file(f"templates/brain/{relative}") as packaged:
            expected = packaged.read_text(encoding="utf-8").splitlines()
            assert (brain / relative).read_text(encoding="utf-8").splitlines() == expected, relative


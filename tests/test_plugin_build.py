"""Drift guard for the plugin's generated ``skills/`` tree.

The committed tree is what a marketplace install ships, so it must match the packaged
resources it was generated from. Editing a brain skill or the ``DOTBRAIN.md`` template
without regenerating fails here. Regenerate with:
``uv run python -m dotbrain._plugin_build``
"""

from pathlib import Path

from dotbrain import _plugin_build, skills


def _tree(root: Path) -> dict[str, str]:
    return {
        p.relative_to(root).as_posix(): p.read_text(encoding="utf-8")
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def test_plugin_skills_match_resources(tmp_path):
    generated_root = tmp_path / "skills"
    _plugin_build.build(generated_root)
    assert _tree(generated_root) == _tree(_plugin_build.SKILLS_DIR), (
        "plugin/skills is stale. "
        "Regenerate with: uv run python -m dotbrain._plugin_build"
    )


def test_plugin_ships_every_brain_coupled_skill():
    """The plugin must carry the whole force-wired set, or wiring a repo loses skills."""
    shipped = {p.name for p in _plugin_build.SKILLS_DIR.iterdir() if p.is_dir()}
    required = {name.split("/")[-1] for name in skills.GLOBAL_BASELINE + skills.PROJECT_BASELINE}
    assert required <= shipped, f"plugin is missing brain-coupled skills: {sorted(required - shipped)}"


def test_convention_skill_carries_frontmatter_and_body():
    text = (_plugin_build.SKILLS_DIR / "dotbrain-convention" / "SKILL.md").read_text(encoding="utf-8")
    assert text.startswith("---\nname: dotbrain-convention\n")
    assert "# DOTBRAIN.md" in text, "convention body missing — frontmatter rendered without content"

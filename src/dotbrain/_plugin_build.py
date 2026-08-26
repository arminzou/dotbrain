"""Generator for the plugin's ``skills/`` tree.

The plugin ships the same brain-coupled skills the CLI links, plus the dotbrain
convention rendered as a loadable skill. Both are generated here from the packaged
resources so there is exactly one source: editing a skill under
``resources/skills/brain/`` or the ``DOTBRAIN.md`` template is the only way to change
what the plugin delivers.

The output is committed, because a marketplace install fetches the repository as-is —
generated-but-uncommitted content would ship an empty plugin. ``test_plugin_build.py``
regenerates and diffs against the committed tree, failing when it drifts. Regenerate
with::

    uv run python -m dotbrain._plugin_build
"""

from __future__ import annotations

import shutil
from pathlib import Path

from . import resource_loader

_REPO_ROOT = Path(__file__).resolve().parents[2]
PLUGIN_ROOT = _REPO_ROOT / "plugin"
SKILLS_DIR = PLUGIN_ROOT / "skills"

_BRAIN_SKILLS_RESOURCE = "skills/brain"
_CONVENTION_RESOURCE = "templates/brain/DOTBRAIN.md"

# The convention is prose, not a procedure, so it needs frontmatter to load as a skill.
# The description is what the runtime matches on, so it names the situations where an
# agent needs the operating rules rather than describing the document.
_CONVENTION_SKILL = "dotbrain-convention"
_CONVENTION_FRONTMATTER = """---
name: dotbrain-convention
description: >
  The dotbrain operating convention — how a Brain, its execution graph, and agent
  workspaces fit together, and the rules that bind work in a dotbrain-wired project.
  Use when working in a repo that has a .brain directory, when a session did not
  receive the convention as injected context (Cowork, Claude Desktop, or an untrusted
  Codex hook), or when checking what dotbrain expects before changing wiring,
  designs, ADRs, or issues.
---

"""


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def render_convention_skill() -> str:
    """Render ``DOTBRAIN.md`` as a loadable skill."""

    body = resource_loader.resource(_CONVENTION_RESOURCE).read_text(encoding="utf-8")
    return _CONVENTION_FRONTMATTER + body


def build(skills_dir: Path = SKILLS_DIR) -> list[str]:
    """Regenerate the plugin skills tree. Returns the skill names written."""

    skills_dir = Path(skills_dir)
    if skills_dir.exists():
        shutil.rmtree(skills_dir)
    skills_dir.mkdir(parents=True)

    names: list[str] = []
    for rel, src in resource_loader.iter_resource_files(_BRAIN_SKILLS_RESOURCE):
        _write(skills_dir / rel, src.read_text(encoding="utf-8"))
        names.append(rel.parts[0])

    _write(skills_dir / _CONVENTION_SKILL / "SKILL.md", render_convention_skill())
    names.append(_CONVENTION_SKILL)
    return sorted(set(names))


def main() -> None:
    names = build()
    print(f"wrote {len(names)} skills to {SKILLS_DIR}")
    for name in names:
        print(f"  {name}")


if __name__ == "__main__":
    main()

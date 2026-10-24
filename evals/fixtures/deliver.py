"""Stage only public resources, using Dotbrain's real project delivery functions."""

from pathlib import Path
import shutil
import sys

from dotbrain import resource_loader, skills, subagents


def deliver(root: Path) -> None:
    workspace = root / "workspace"
    home = root / "home/data"
    brainspace = home / "brainspaces/sample"
    brain = brainspace / ".brain"
    brain.mkdir(parents=True)
    (brainspace / ".beads").mkdir()
    (brain / "project.yaml").write_text("agents: [claude-code, codex]\nskills: [dotbrain]\n", encoding="utf-8")
    for name in (".brain", ".beads"):
        (workspace / name).symlink_to(brainspace / name, target_is_directory=True)
    with resource_loader.plugin_tree() as source:
        # Keep the complete public plugin surface without evals or npm dependencies.
        for name in (".claude-plugin", "assets", "skills", "agents", "hooks", "scripts"):
            shutil.copytree(source / name, root / "plugin" / name)
        shutil.copytree(source / "skills", home / "skills/dotbrain")
    result = skills.link_project(home, brainspace, [".codex"], ["dotbrain"],
                                 workspace_dirs={".codex": workspace / ".codex"})
    agents = subagents.link_project_subagents(home, brainspace, [".codex"],
                                             subagents.PROJECT_BASELINE,
                                             workspace_dirs={".codex": workspace / ".codex"})
    if result.warnings or agents.warnings:
        raise RuntimeError(result.warnings + agents.warnings)
    for link in root.rglob("*"):
        if link.is_symlink() and not link.resolve(strict=True).is_relative_to(root):
            raise RuntimeError(f"resource escaped fixture: {link}")


if __name__ == "__main__":
    deliver(Path(sys.argv[1]).resolve(strict=True))

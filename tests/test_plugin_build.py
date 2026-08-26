"""Drift guard for the plugin's generated ``skills/`` tree.

The committed tree is what a marketplace install ships, so it must match the packaged
resources it was generated from. Editing a brain skill or the ``DOTBRAIN.md`` template
without regenerating fails here. Regenerate with:
``uv run python -m dotbrain._plugin_build``
"""

import json
from pathlib import Path
import re
import tomllib

from dotbrain import __version__, _plugin_build


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


def test_convention_skill_carries_frontmatter_and_body():
    text = (_plugin_build.SKILLS_DIR / "dotbrain-convention" / "SKILL.md").read_text(encoding="utf-8")
    assert text.startswith("---\nname: dotbrain-convention\n")
    assert "# DOTBRAIN.md" in text, "convention body missing — frontmatter rendered without content"


def test_wire_worktree_skill_is_self_contained_and_windows_safe():
    text = (_plugin_build.SKILLS_DIR / "wire-worktree" / "SKILL.md").read_text(encoding="utf-8")

    assert "git rev-parse --path-format=absolute --git-common-dir" in text
    assert "MSYS=winsymlinks:nativestrict" in text
    assert "mklink /D" in text
    assert "Bare `ln -s` can silently copy directories on Windows" in text
    assert "do not run `dotbrain wire`" in text


def test_plugin_owns_session_start_registration_for_both_runtimes():
    hooks_path = _plugin_build.PLUGIN_ROOT / "hooks" / "hooks.json"
    hooks = json.loads(hooks_path.read_text(encoding="utf-8"))
    entries = [hook for entry in hooks["hooks"]["SessionStart"] for hook in entry["hooks"]]

    assert len(entries) == 1
    hook = entries[0]
    # Both commands must guard on the CLI being present: the plugin installs at user scope, so
    # every session on the machine runs this hook, including before the CLI exists.
    assert hook["command"] == (
        "if command -v dotbrain >/dev/null 2>&1; then dotbrain hook session-start; fi"
    )
    # commandWindows keeps the guard in PowerShell instead of resolving `bash`, where the
    # System32 WSL launcher shadows Git Bash on PATH.
    assert hook["commandWindows"] == (
        "if (Get-Command dotbrain -ErrorAction SilentlyContinue) { dotbrain hook session-start }"
    )
    for manifest_dir in (".claude-plugin", ".codex-plugin"):
        manifest = json.loads(
            (_plugin_build.PLUGIN_ROOT / manifest_dir / "plugin.json").read_text(encoding="utf-8")
        )
        assert manifest["hooks"] == "./hooks/hooks.json"


def test_first_run_installers_pin_the_plugin_cli_version():
    version = tomllib.loads((_plugin_build._REPO_ROOT / "pyproject.toml").read_text())["project"]["version"]
    scripts = _plugin_build.PLUGIN_ROOT / "scripts"

    for manifest_dir in (".claude-plugin", ".codex-plugin"):
        manifest = json.loads(
            (_plugin_build.PLUGIN_ROOT / manifest_dir / "plugin.json").read_text(encoding="utf-8")
        )
        assert manifest["version"] == version
    assert __version__ == version

    for name in ("install.sh", "install.ps1"):
        text = (scripts / name).read_text(encoding="utf-8")
        assert version in text
        # The ref must be a release tag, not a branch SHA: a SHA on a feature branch resolves
        # for nobody, and a squash-merge rewrites it, breaking the pin permanently.
        assert "git+https://github.com/arminzou/dotbrain@v" in text
        assert not re.search(r"dotbrain@[0-9a-f]{40}", text), "pin is a commit SHA, not a tag"
        assert "dotbrain bootstrap" in text


def test_wire_brain_installs_only_when_the_cli_is_absent():
    text = " ".join(
        (_plugin_build.SKILLS_DIR / "wire-brain" / "SKILL.md").read_text(encoding="utf-8").split()
    )

    assert "If it is, continue without installing anything." in text
    assert "scripts/install.sh" in text
    assert "scripts/install.ps1" in text

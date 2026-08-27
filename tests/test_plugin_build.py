"""Plugin packaging checks."""

import json
from pathlib import Path
import re
import tomllib

from dotbrain import __version__

REPO_ROOT = Path(__file__).resolve().parent.parent
PLUGIN_ROOT = REPO_ROOT / "plugin"
SKILLS_DIR = PLUGIN_ROOT / "skills"


def test_convention_skill_carries_frontmatter_and_body():
    text = (SKILLS_DIR / "dotbrain-convention" / "SKILL.md").read_text(encoding="utf-8")
    template = (REPO_ROOT / "src/dotbrain/resources/templates/brain/DOTBRAIN.md").read_text(
        encoding="utf-8"
    )
    assert text.startswith("---\nname: dotbrain-convention\n")
    assert text.endswith(template), "convention body does not match the Brain template"


def test_wire_worktree_skill_is_self_contained_and_windows_safe():
    text = (SKILLS_DIR / "wire-worktree" / "SKILL.md").read_text(encoding="utf-8")

    assert "git rev-parse --path-format=absolute --git-common-dir" in text
    assert "MSYS=winsymlinks:nativestrict" in text
    assert "mklink /D" in text
    assert "Bare `ln -s` can silently copy directories on Windows" in text
    assert "do not run `dotbrain wire`" in text


def test_plugin_owns_session_start_registration_for_both_runtimes():
    hooks_path = PLUGIN_ROOT / "hooks" / "hooks.json"
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
    # Claude Code auto-discovers hooks/hooks.json; declaring it in the manifest too makes the
    # runtime reject the whole plugin with "Duplicate hooks file detected", skills included.
    claude_manifest = json.loads(
        (PLUGIN_ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
    )
    assert "hooks" not in claude_manifest
    # Codex does not auto-discover, so its manifest still points at the same file.
    codex_manifest = json.loads(
        (PLUGIN_ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
    )
    assert codex_manifest["hooks"] == "./hooks/hooks.json"


def test_codex_marketplace_exposes_the_plugin_from_the_repository_root():
    marketplace_path = REPO_ROOT / ".agents" / "plugins" / "marketplace.json"
    marketplace = json.loads(marketplace_path.read_text(encoding="utf-8"))

    assert marketplace["name"] == "dotbrain"
    assert marketplace["interface"]["displayName"] == "dotbrain"
    assert marketplace["plugins"] == [
        {
            "name": "dotbrain",
            "source": {"source": "local", "path": "./plugin"},
            "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
            "category": "Productivity",
        }
    ]


def test_first_run_installers_pin_the_plugin_cli_version():
    version = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())["project"]["version"]
    scripts = PLUGIN_ROOT / "scripts"

    for manifest_dir in (".claude-plugin", ".codex-plugin"):
        manifest = json.loads(
            (PLUGIN_ROOT / manifest_dir / "plugin.json").read_text(encoding="utf-8")
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
        (SKILLS_DIR / "wire-brain" / "SKILL.md").read_text(encoding="utf-8").split()
    )

    assert "If it is, continue without installing anything." in text
    assert "scripts/install.sh" in text
    assert "scripts/install.ps1" in text

"""Plugin delivery checks: the packaged files parse, resolve and agree with each other.

Whether a skill's instructions work is a question for agent evaluations, not this suite, so
nothing here reads skill prose.
"""

import json
from pathlib import Path
import re
import tomllib

import pytest
import yaml

from dotbrain import __version__

REPO_ROOT = Path(__file__).resolve().parent.parent
PLUGIN_ROOT = REPO_ROOT / "plugin"
SKILLS_DIR = PLUGIN_ROOT / "skills"
SKILL_FILES = sorted(SKILLS_DIR.glob("*/SKILL.md"))
SKILL_IDS = [p.parent.name for p in SKILL_FILES]

# Over this, the loader truncates and the tail of the skill silently never arrives.
MAX_SKILL_LINES = 500


def _frontmatter(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8").split("---")[1])


def test_the_skill_set_is_not_empty():
    """A glob that silently matches nothing would make every other test vacuous."""
    assert len(SKILL_FILES) >= 10


@pytest.mark.parametrize("skill", SKILL_FILES, ids=SKILL_IDS)
def test_frontmatter_parses_and_names_its_directory(skill: Path):
    fm = _frontmatter(skill)
    assert fm["name"] == skill.parent.name
    assert re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", fm["name"])
    assert len(fm["name"]) <= 64
    # An unquoted ': ' or ' #' can make the loader drop every field, silently.
    assert isinstance(fm["description"], str) and fm["description"].strip()


@pytest.mark.parametrize("skill", SKILL_FILES, ids=SKILL_IDS)
def test_skill_stays_under_the_line_cap(skill: Path):
    lines = len(skill.read_text(encoding="utf-8").splitlines())
    assert lines <= MAX_SKILL_LINES, f"{skill.parent.name} is {lines} lines"


def explicit_only(skill_dir: Path) -> tuple[bool, bool]:
    """Each runtime's parsed invocation policy: (Claude Code, Codex), True when explicit-only.

    Both default to allowing implicit invocation when the key is absent.
    """
    claude = _frontmatter(skill_dir / "SKILL.md").get("disable-model-invocation", False)
    openai_yaml = skill_dir / "agents" / "openai.yaml"
    metadata = yaml.safe_load(openai_yaml.read_text(encoding="utf-8")) if openai_yaml.exists() else {}
    codex = (metadata.get("policy") or {}).get("allow_implicit_invocation", True)
    assert isinstance(claude, bool), f"{skill_dir.name}: disable-model-invocation is {claude!r}"
    assert isinstance(codex, bool), f"{skill_dir.name}: allow_implicit_invocation is {codex!r}"
    return claude, not codex


@pytest.mark.parametrize("skill", SKILL_FILES, ids=SKILL_IDS)
def test_invocation_policy_agrees_in_both_runtimes(skill: Path):
    """The runtimes spell this with inverted keys in different files; a skill declared in only
    one still auto-fires in the other."""
    claude, codex = explicit_only(skill.parent)
    assert claude == codex, f"{skill.parent.name}: explicit-only in {'Claude Code' if claude else 'Codex'} only"


@pytest.mark.parametrize(
    ("frontmatter", "metadata", "agrees"),
    [
        ("disable-model-invocation: true", "policy:\n  allow_implicit_invocation: false", True),
        ("", "interface: {}", True),
        ("disable-model-invocation: false # was true", "policy:\n  allow_implicit_invocation: false", False),
        ("disable-model-invocation: true", "interface: {}", False),
    ],
)
def test_invocation_policy_reads_values_not_text(tmp_path: Path, frontmatter: str, metadata: str, agrees: bool):
    skill = tmp_path / "example"
    (skill / "agents").mkdir(parents=True)
    (skill / "SKILL.md").write_text(f"---\nname: example\n{frontmatter}\n---\n", encoding="utf-8")
    (skill / "agents" / "openai.yaml").write_text(metadata, encoding="utf-8")
    claude, codex = explicit_only(skill)
    assert (claude == codex) is agrees


def test_invocation_policy_rejects_non_boolean_values(tmp_path: Path):
    skill = tmp_path / "example"
    skill.mkdir()
    (skill / "SKILL.md").write_text('---\nname: example\ndisable-model-invocation: "yes"\n---\n', encoding="utf-8")
    with pytest.raises(AssertionError, match="disable-model-invocation"):
        explicit_only(skill)


@pytest.mark.parametrize("skill", SKILL_FILES, ids=SKILL_IDS)
def test_relative_links_resolve(skill: Path):
    """A dangling reference 404s for every user of the skill and nothing else notices."""
    for target in re.findall(r"\]\(([^)]+)\)", skill.read_text(encoding="utf-8")):
        if target.startswith(("http", "#", "{", "$")):
            continue
        assert (skill.parent / target.split("#")[0]).exists(), f"{skill.parent.name} -> {target}"


@pytest.mark.parametrize("skill", SKILL_FILES, ids=SKILL_IDS)
def test_no_hardcoded_home_directories(skill: Path):
    """The plugin is public; an operator's home path would leak into every install."""
    for path in [skill, *sorted(skill.parent.rglob("*.md"))]:
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"/(Users|home)/(?!armin/repos)[a-z]", text), path


def test_every_bundled_skill_has_codex_interface_metadata():
    for skill in SKILL_FILES:
        metadata_path = skill.parent / "agents" / "openai.yaml"
        assert metadata_path.is_file(), f"{skill.parent.name} has no agents/openai.yaml"

        interface = yaml.safe_load(metadata_path.read_text(encoding="utf-8"))["interface"]
        assert interface["display_name"]
        assert 25 <= len(interface["short_description"]) <= 64
        assert "default_prompt" not in interface


def test_convention_skill_carries_frontmatter_and_body():
    text = (SKILLS_DIR / "dotbrain" / "SKILL.md").read_text(encoding="utf-8")
    template = (REPO_ROOT / "src/dotbrain/resources/templates/brain/DOTBRAIN.md").read_text(
        encoding="utf-8"
    )
    assert text.startswith("---\nname: dotbrain\n")
    assert text.endswith(template), "convention body does not match the Brain template"


def test_plugin_owns_hook_registration_for_both_runtimes():
    hooks_path = PLUGIN_ROOT / "hooks" / "hooks.json"
    hooks = json.loads(hooks_path.read_text(encoding="utf-8"))["hooks"]
    assert set(hooks) == {"SessionStart", "Stop", "SessionEnd"}

    registered = {}
    for event, command in (("SessionStart", "session-start"), ("Stop", "stop"), ("SessionEnd", "session-end")):
        entries = [hook for entry in hooks[event] for hook in entry["hooks"]]
        assert len(entries) == 1
        hook = registered[event] = entries[0]
        # Codex uses statusMessage as the hook's name in /hooks.
        assert hook["statusMessage"].strip()
        # Both commands must guard on the CLI being present: the plugin installs at user scope, so
        # every session on the machine runs this hook, including before the CLI exists.
        assert hook["command"] == (
            f"if command -v dotbrain >/dev/null 2>&1; then dotbrain hook {command}; fi"
        )
        # commandWindows keeps the guard in PowerShell instead of resolving `bash`, where the
        # System32 WSL launcher shadows Git Bash on PATH.
        assert hook["commandWindows"] == (
            f"if (Get-Command dotbrain -ErrorAction SilentlyContinue) {{ dotbrain hook {command} }}"
        )
    # Session start waits up to 10 s for sync before emitting context, so its budget covers both.
    assert registered["SessionStart"]["timeout"] > 10
    # Stop runs in the background so the turn never waits on the push.
    assert registered["Stop"]["async"] is True
    # Allow the detached launch more than Claude's default 1.5 s, within Codex's 3 s cap.
    assert registered["SessionEnd"]["timeout"] == 3
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
    lock = tomllib.loads((REPO_ROOT / "uv.lock").read_text(encoding="utf-8"))
    assert next(
        package["version"] for package in lock["package"] if package["name"] == "dotbrain"
    ) == version

    for name in ("install.sh", "install.ps1"):
        text = (scripts / name).read_text(encoding="utf-8")
        assert version in text
        # The ref must be a release tag, not a branch SHA: a SHA on a feature branch resolves
        # for nobody, and a squash-merge rewrites it, breaking the pin permanently.
        assert "git+https://github.com/arminzou/dotbrain@v" in text
        assert not re.search(r"dotbrain@[0-9a-f]{40}", text), "pin is a commit SHA, not a tag"
        assert "dotbrain bootstrap" in text

"""OpenCode delivery: the CLI's owned plugin file and skill directories, and the plugin's config hook."""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from dotbrain import assets, bootstrap, doctor, opencode

PLUGIN_ROOT = Path(__file__).resolve().parent.parent / "plugin"


# Imports the delivered plugin as OpenCode does, runs its config hook, and prints the config.
HARNESS = """
import { pathToFileURL } from "node:url"
let raw = ""
for await (const chunk of process.stdin) raw += chunk
const { plugin, input, cfg } = JSON.parse(raw)
const hooks = await (await import(pathToFileURL(plugin).href)).default.server(input)
await hooks.config(cfg)
process.stdout.write(JSON.stringify(cfg))
"""


@pytest.fixture
def user(tmp_path, monkeypatch):
    """A fake home whose OpenCode config holds the user's own skills link and an unrelated plugin."""
    home = tmp_path / "user"
    config_dir = home / ".config" / "opencode"
    (config_dir / "plugins").mkdir(parents=True)
    (config_dir / "plugins" / "rtk.ts").write_text("export default {}\n", encoding="utf-8")
    (config_dir / "skills").symlink_to(PLUGIN_ROOT / "skills", target_is_directory=True)
    return home, config_dir


def _global_extra(dotbrain_home: Path, *names: str) -> None:
    listed = "".join(f"  - {name}\n" for name in names)
    (dotbrain_home / "skills/skills.yaml").write_text(f"global_extra:\n{listed}" if names else "global_extra: []\n")


def _run_hook(tmp_path: Path, config_dir: Path, cfg, directory: Path | None = None) -> dict:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    harness = tmp_path / "harness.mjs"
    harness.write_text(HARNESS, encoding="utf-8")
    # OpenCode loads plugins with Bun, which reads ESM in .js; Node needs the package type.
    (config_dir / "package.json").write_text('{"type": "module"}\n', encoding="utf-8")
    directory = directory or tmp_path
    payload = {"plugin": str(opencode.plugin_file(config_dir)),
               "input": {"directory": str(directory), "worktree": str(directory)}, "cfg": cfg}
    done = subprocess.run([node, str(harness)], input=json.dumps(payload), capture_output=True,
                          encoding="utf-8", check=True, timeout=60)
    return json.loads(done.stdout)


def test_delivery_copies_the_plugin_and_links_skills(dotbrain_home, user):
    home, config_dir = user
    _global_extra(dotbrain_home, "misc/discovery-test")
    result = assets.link_global(dotbrain_home, "skills", "opencode", user_home=home)
    assert result.warnings == []
    assert opencode.plugin_file(config_dir).read_bytes() == (PLUGIN_ROOT / "opencode/dotbrain.js").read_bytes()
    packaged = opencode.packaged_dir(config_dir) / "skills"
    assert (packaged / "run-execution/references/opencode.md").is_file()
    assert (opencode.skills_dir(config_dir) / "discovery-test").is_symlink()
    assert opencode.state(config_dir) == "current"
    # The user's own entries stay exactly as they were.
    assert (config_dir / "skills").is_symlink() and (config_dir / "plugins/rtk.ts").is_file()
    assert sorted(p.name for p in (config_dir / "plugins").iterdir()) == ["dotbrain.js", "rtk.ts"]

    again = assets.link_global(dotbrain_home, "skills", "opencode", user_home=home)
    assert again.linked == [] and again.warnings == []

    # Update repairs each damaged part, keeping only what the source has.
    for damage in (lambda: opencode.plugin_file(config_dir).write_text("// dotbrain-managed: old\n"),
                   lambda: opencode.plugin_file(config_dir).unlink(),
                   lambda: (packaged / "stray.txt").write_text("old"),
                   lambda: shutil.rmtree(packaged / "run-execution/references")):
        damage()
        assert opencode.state(config_dir) == "stale"
        assert assets.link_global(dotbrain_home, "skills", "opencode", user_home=home).linked
        assert opencode.state(config_dir) == "current"
    assert not (packaged / "stray.txt").exists()

    # Prune removes only dotbrain's links.
    own = opencode.skills_dir(config_dir) / "mine"
    own.mkdir()
    _global_extra(dotbrain_home)
    pruned = assets.link_global(dotbrain_home, "skills", "opencode", user_home=home)
    assert pruned.pruned == ["opencode/discovery-test"]
    assert own.is_dir() and (config_dir / "skills").is_symlink()


def test_unfiltered_delivery_reaches_opencode_only_once_opted_in(dotbrain_home, tmp_path, monkeypatch):
    home = tmp_path / "user"
    config_dir = tmp_path / "xdg" / "opencode"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    _global_extra(dotbrain_home, "misc/discovery-test")
    assert bootstrap.link_global_skills(dotbrain_home, home=home).warnings == []
    assert not config_dir.exists()

    assert bootstrap.link_global_skills(dotbrain_home, "opencode", home=home).warnings == []
    assert not (home / ".config").exists()
    opencode.plugin_file(config_dir).unlink()
    later = bootstrap.link_global_skills(dotbrain_home, home=home)
    assert "delivered global opencode/plugins/dotbrain.js" in later.logs
    assert opencode.state(config_dir) == "current"


def test_foreign_entries_are_never_replaced(dotbrain_home, user):
    home, config_dir = user
    foreign = opencode.plugin_file(config_dir)
    foreign.write_text("export default {}\n", encoding="utf-8")
    result = assets.link_global(dotbrain_home, "skills", "opencode", user_home=home)
    assert result.warnings == [f"{foreign} exists and was not created by dotbrain; skipping"]
    assert foreign.read_text(encoding="utf-8") == "export default {}\n"
    assert not opencode.packaged_dir(config_dir).exists()
    assert bootstrap.link_global_skills(dotbrain_home, home=home).warnings == []  # not opted in

    foreign.unlink()
    opencode.packaged_dir(config_dir).mkdir(parents=True)
    result = assets.link_global(dotbrain_home, "skills", "opencode", user_home=home)
    assert result.warnings == [f"{opencode.packaged_dir(config_dir)} exists and was not created by dotbrain; skipping"]
    assert not foreign.exists()

    # A user skill with a selected skill's name stays; dotbrain reports the collision.
    shutil.rmtree(opencode.packaged_dir(config_dir))
    mine = opencode.skills_dir(config_dir) / "discovery-test"
    mine.mkdir(parents=True)
    _global_extra(dotbrain_home, "misc/discovery-test")
    collided = assets.link_global(dotbrain_home, "skills", "opencode", user_home=home)
    assert f"{mine} exists and was not created by dotbrain; skipping" in collided.warnings
    assert mine.is_dir() and not mine.is_symlink()


def test_doctor_reports_opencode_delivery(dotbrain_home, user):
    home, config_dir = user

    def warnings(status="warn"):
        return {f.message for f in doctor._check_machine(dotbrain_home, home)
                if f.status == status and f.message.startswith("opencode:")}

    assert warnings() == set()  # not opted in
    (dotbrain_home / "skills/skills.yaml").write_text(
        f"targets:\n  opencode: {opencode.skills_dir(config_dir)}\nglobal_extra: []\n")
    assert warnings() == set()  # a shared target does not opt this machine in
    opencode.plugin_file(config_dir).write_text("export default {}\n", encoding="utf-8")
    assert warnings() == set()
    opencode.plugin_file(config_dir).unlink()

    assets.link_global(dotbrain_home, "skills", "opencode", user_home=home)
    # The user's own skills link reaches the same skills as other files.
    assert warnings() == set()  # duplicates are not warnings
    duplicates = warnings("info")
    assert duplicates == {f"opencode: skill {name} is also at {config_dir / 'skills' / name}; "
                          "OpenCode loads one of the two at random"
                          for name in (p.parent.name for p in (PLUGIN_ROOT / "skills").glob("*/SKILL.md"))}
    (config_dir / "skills").unlink()
    findings = doctor._check_machine(dotbrain_home, home)
    assert not [f for f in findings if f.status != "ok" and f.message.startswith("opencode:")]
    # No packaged-agent demand: dotbrain delivers no OpenCode subagents.
    assert not [f for f in findings if "opencode" in f.message and "agents" in f.message]

    (opencode.packaged_dir(config_dir) / "skills/dotbrain/SKILL.md").write_text("changed")
    assert warnings() == {f"opencode: dotbrain delivery is stale at {config_dir}"}


def _skill(directory: Path, frontmatter: bytes) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "SKILL.md").write_bytes(frontmatter)
    return directory / "SKILL.md"


def test_skill_index_reads_frontmatter_as_opencode_does(tmp_path):
    root = tmp_path / "skills"
    cases = {
        "quoted-key": b'---\n"name": quoted-key\n---\n',
        "escaped": b'---\nname: "manual\\u002dskill"\n---\n',
        "bom": b"\xef\xbb\xbf---\r\nname: bom\r\ndescription: >\r\n  folded\r\n---\r\n",
        "comment": b"---\nname: comment # trailing\n---\n",
        "colon": b"---\nname: colon\ndescription: Use when: asked\n---\n",  # OpenCode's unquoted-colon retry
        # OpenCode decodes invalid bytes as U+FFFD and still loads the skill.
        "invalid-byte": b"---\nname: invalid-byte\n---\nbody \xff\xfe\n",
        "broken": b"---\nname: [unclosed\n---\n",
        "nameless": b"---\ndescription: no name\n---\n",
        "nested/deeper": b"---\nname: nested-one\n---\n",
        ".hidden": b"---\nname: hidden\n---\n",
    }
    for folder, text in cases.items():
        _skill(root / folder, text)

    index = {Path(s["file"]).parent.relative_to(root).as_posix(): s["name"] for s in opencode.skill_index([root])}
    assert index == {"quoted-key": "quoted-key", "escaped": "manual-skill", "bom": "bom", "comment": "comment",
                     "colon": "colon", "invalid-byte": "invalid-byte", "nested/deeper": "nested-one"}
    # A broken or nameless skill is no skill to OpenCode; hidden folders are not scanned.


def test_doctor_finds_duplicates_by_name_in_nested_folders(dotbrain_home, user):
    home, config_dir = user
    (config_dir / "skills").unlink()
    assets.link_global(dotbrain_home, "skills", "opencode", user_home=home)
    nested = _skill(home / ".claude/skills/team/renamed-copy", b"---\nname: wire-brain\ndescription: mine\n---\n")
    _skill(home / ".agents/skills/other", b"---\nname: not-dotbrains\n---\n")
    assert opencode.duplicate_skills(config_dir, home) == [("wire-brain", nested.parent)]


@pytest.mark.parametrize("folder, managed", [("synced/account_org", True), ("team", False),
                                             ("synced-copy", False)])
def test_doctor_duplicate_advice_respects_account_synced_skills(dotbrain_home, user, folder, managed):
    home, config_dir = user
    (config_dir / "skills").unlink()
    assets.link_global(dotbrain_home, "skills", "opencode", user_home=home)
    duplicate = _skill(home / ".claude/skills" / folder / "renamed-copy",
                       b"---\nname: wire-brain\ndescription: mine\n---\n").parent

    findings = doctor._check_opencode_plugin(config_dir, home)
    finding, = [f for f in findings if f"is also at {duplicate};" in f.message]

    assert finding.status == "info"
    if managed:
        assert "remove wire-brain from your claude.ai account" in finding.suggestion
        assert str(duplicate) not in finding.suggestion
    else:
        assert f"remove {duplicate}, or move it out" in finding.suggestion


@pytest.mark.parametrize("permission", [None, "allow", {"*": "ask", "external_directory": {"*": "ask"}},
                                        {"external_directory": "deny", "bash": {"*": "allow"}}])
def test_config_hook_adds_skill_paths_and_allows_linked_skill_directories_last(dotbrain_home, user, tmp_path,
                                                                                 permission):
    home, config_dir = user
    project = tmp_path / "project"
    _skill(project / ".opencode/skills/by-hand", b"---\nname: by-hand\n---\n")
    source = _skill(dotbrain_home / "skills/misc/project-linked", b"---\nname: project-linked\n---\n")
    (project / ".opencode/skills/project-linked").symlink_to(source.parent, target_is_directory=True)
    # Manual-only skills are not enforced: they get the same treatment as any other.
    _skill(dotbrain_home / "skills/misc/global-manual", b"---\nname: global-manual\ndisable-model-invocation: true\n---\n")
    _global_extra(dotbrain_home, "misc/global-manual", "misc/discovery-test")
    assert assets.link_global(dotbrain_home, "skills", "opencode", user_home=home).warnings == []

    cfg = {"skills": {"paths": ["~/mine"]}, "agent": {"build": {"permission": {"*": "allow"}}, "plain": {}}}
    if permission is not None:
        cfg["permission"] = permission
    out = _run_hook(tmp_path, config_dir, cfg, directory=project)

    roots = [str(opencode.packaged_dir(config_dir) / "skills"), str(opencode.skills_dir(config_dir))]
    assert [Path(p) for p in out["skills"]["paths"]] == [Path("~/mine"), *map(Path, roots)]
    # Each linked skill's resolved directory is readable; copies and real directories need no rule.
    readable = {str(Path(os.path.realpath(p)) / "*") for p in (
        opencode.skills_dir(config_dir) / "global-manual", opencode.skills_dir(config_dir) / "discovery-test",
        project / ".opencode/skills/project-linked")}
    for rules in (out["permission"], out["agent"]["build"]["permission"]):
        assert list(rules)[-1] == "external_directory"
        assert {p for p, action in rules["external_directory"].items() if action == "allow"} == readable
        assert "skill" not in rules and "read" not in rules
    assert "permission" not in out["agent"]["plain"]
    # The user's other permissions stay as they were.
    before = {"*": permission} if isinstance(permission, str) else dict(permission or {})
    external_before = before.pop("external_directory", None)
    assert {k: v for k, v in out["permission"].items() if k != "external_directory"} == before
    if isinstance(external_before, str):
        assert list(out["permission"]["external_directory"].items())[0] == ("*", external_before)
    elif external_before:
        assert out["permission"]["external_directory"]["*"] == external_before["*"]

    # Run twice (a second OpenCode instance), nothing is added twice.
    again = _run_hook(tmp_path, config_dir, out, directory=project)
    assert again["skills"]["paths"] == out["skills"]["paths"]
    assert again["permission"] == out["permission"]

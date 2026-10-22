"""Hermes delivery: the packaged plugin's registration and the CLI's owned copy in the Hermes home."""

import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from dotbrain import assets, bootstrap, doctor, hermes

PLUGIN_ROOT = Path(__file__).resolve().parent.parent / "plugin"


def _load_plugin():
    spec = importlib.util.spec_from_file_location("dotbrain_hermes_plugin", PLUGIN_ROOT / "__init__.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeContext:
    def __init__(self):
        self.skills, self.hooks = {}, {}

    def register_skill(self, name, path, description="", frontmatter=None):
        assert Path(path).is_file()
        self.skills[name] = (Path(path), description, frontmatter)

    def register_hook(self, name, callback):
        self.hooks.setdefault(name, []).append(callback)


def test_plugin_registers_every_skill_and_vetoes_only_manual_ones():
    ctx = FakeContext()
    _load_plugin().register(ctx)
    sources = sorted((PLUGIN_ROOT / "skills").glob("*/SKILL.md"))
    assert sorted(ctx.skills) == sorted(p.parent.name for p in sources)
    # The policy source is the SKILL.md frontmatter, parsed here as YAML to check the plugin's parser.
    manual = {p.parent.name for p in sources
              if yaml.safe_load(p.read_text(encoding="utf-8").split("---")[1]).get("disable-model-invocation")}
    assert manual
    for name, (path, description, fields) in ctx.skills.items():
        assert path == PLUGIN_ROOT / "skills" / name / "SKILL.md"
        # The stdlib parser agrees with YAML on every string field, folded descriptions included.
        parsed = yaml.safe_load(path.read_text(encoding="utf-8").split("---")[1])
        assert description == parsed["description"], name
        assert {k: v for k, v in fields.items() if isinstance(parsed.get(k), str)} == \
            {k: v for k, v in parsed.items() if isinstance(v, str)}, name
    # Supporting files sit next to the registered SKILL.md.
    assert (ctx.skills["run-execution"][0].parent / "references" / "hermes.md").is_file()

    [veto] = ctx.hooks["pre_tool_call"]
    for name in sorted(ctx.skills):
        blocked = veto(tool_name="skill_view", args={"name": f"dotbrain:{name}"}, task_id="t")
        assert (blocked is not None) == (name in manual), name
        if blocked:
            assert blocked["action"] == "block" and blocked["message"]
    some = sorted(manual)[0]
    for supporting in ("references/x.md", "./references/x.md", "references\\x.md", " scripts/SKILL.md.bak "):
        assert veto(tool_name="skill_view", args={"name": f"dotbrain:{some}", "file_path": supporting}) is None, supporting
    # Hermes serves file_path from the skill directory, so each of these is the whole skill or outside it.
    for whole in ("", " ", ".", "SKILL.md", "skill.md", "./SKILL.md", " .\\SKILL.md ", "references/../SKILL.md",
                  "../other/SKILL.md", "..", "/etc/x", "C:/x/SKILL.md", None):
        assert veto(tool_name="skill_view", args={"name": f"dotbrain:{some}", "file_path": whole}) is not None, whole
    assert veto(tool_name="skill_view", args={"name": f"other:{some}"}) is None
    assert veto(tool_name="read_file", args={"name": f"dotbrain:{some}"}) is None


def test_veto_blocks_every_path_the_host_resolves_to_skill_md(tmp_path: Path):
    skill_md = tmp_path / "manual" / "SKILL.md"
    (skill_md.parent / "references").mkdir(parents=True)
    skill_md.write_text("---\nname: manual\n---\n", encoding="utf-8")
    (skill_md.parent / "references" / "x.md").write_text("x", encoding="utf-8")
    (tmp_path / "other").mkdir()
    (tmp_path / "other" / "SKILL.md").write_text("other", encoding="utf-8")
    veto = _load_plugin().manual_only_veto({"manual": skill_md})

    def blocked(file_path):
        return veto(tool_name="skill_view", args={"name": "dotbrain:manual", "file_path": file_path}) is not None

    assert not blocked("references/x.md")
    for path in ("skill.md", "./SKILL.md", "references/../SKILL.md", "../other/SKILL.md", str(skill_md)):
        assert blocked(path), path
    for alias in ("SKILL.md.", "SKILL.md..."):
        if sys.platform == "win32":
            # Windows drops trailing dots, so these open the real SKILL.md.
            assert blocked(alias), alias
        else:
            assert not (skill_md.parent / alias).exists()


def test_veto_keeps_linked_private_manual_skills_manual(tmp_path: Path, monkeypatch):
    # Hermes ignores disable-model-invocation in project and home skills as well.
    checkout, home = tmp_path / "repo", tmp_path / "hermes"

    def skill(root, name, manual):
        directory = root / "skills" / name
        directory.mkdir(parents=True)
        flag = "disable-model-invocation: true\n" if manual else ""
        (directory / "SKILL.md").write_text(f"---\nname: {name}\ndescription: x\n{flag}---\n", encoding="utf-8")
        (directory / "notes.md").write_text("x", encoding="utf-8")

    skill(checkout / ".hermes", "private-manual", True)
    skill(home, "global-manual", True)
    skill(home, "auto", False)
    skill(checkout / ".hermes", "both", False)
    skill(home, "both", True)  # the checkout's skill shadows the home's, as in Hermes
    monkeypatch.chdir(checkout)
    monkeypatch.setenv("HERMES_HOME", str(home))
    ctx = FakeContext()
    _load_plugin().register(ctx)
    [veto] = ctx.hooks["pre_tool_call"]

    def view(name, file_path=None):
        return veto(tool_name="skill_view", args={"name": name, "file_path": file_path})

    assert view("private-manual") == {"action": "block",
                                      "message": "private-manual runs only when the user invokes /private-manual."}
    assert view("global-manual") is not None
    assert view("private-manual", "notes.md") is None
    for name in ("auto", "both", "missing", "../hermes/skills/global-manual", "other:global-manual"):
        assert view(name) is None, name


@pytest.fixture
def fake_hermes(monkeypatch):
    """A `hermes` on PATH whose invocations are recorded instead of run."""
    calls = []
    original = shutil.which
    monkeypatch.setattr(hermes.shutil, "which", lambda cmd, *a, **k: "hermes" if cmd == "hermes" else original(cmd, *a, **k))

    def run(argv, *, env=None):
        calls.append((list(argv), env["HERMES_HOME"]))
        return subprocess.CompletedProcess(argv, 0, "", "")

    return calls, run


def _global_extra(dotbrain_home: Path, *names: str) -> None:
    listed = "".join(f"  - {name}\n" for name in names)
    (dotbrain_home / "skills/skills.yaml").write_text(f"global_extra:\n{listed}" if names else "global_extra: []\n")


def test_global_delivery_copies_the_plugin_and_links_skills(dotbrain_home, tmp_path, fake_hermes):
    calls, run = fake_hermes
    user = tmp_path / "user"
    hermes_home = user / ".hermes"
    foreign_skill = hermes_home / "skills" / "mine"
    foreign_skill.mkdir(parents=True)
    _global_extra(dotbrain_home, "misc/discovery-test")

    result = assets.link_global(dotbrain_home, "skills", "hermes", user_home=user, run=run)
    assert result.warnings == []
    assert (hermes_home / "skills/discovery-test").is_symlink()
    copy = hermes.plugin_dir(hermes_home)
    assert (copy / "plugin.yaml").is_file() and (copy / "__init__.py").is_file()
    assert (copy / "skills/run-execution/references/hermes.md").is_file()
    assert hermes.state(hermes_home) == "current"
    assert calls == [(["hermes", "plugins", "enable", "dotbrain"], str(hermes_home))]

    # Once enabled and current, delivery changes nothing.
    (hermes_home / "config.yaml").write_text("plugins:\n  enabled: [dotbrain]\n")
    again = assets.link_global(dotbrain_home, "skills", "hermes", user_home=user, run=run)
    assert again.linked == [] and again.warnings == [] and len(calls) == 1

    # Update replaces only the owned copy, dropping files the source no longer has.
    (copy / "skills/stray.txt").write_text("old")
    assert hermes.state(hermes_home) == "stale"
    updated = assets.link_global(dotbrain_home, "skills", "hermes", user_home=user, run=run)
    assert updated.linked == ["hermes/plugins/dotbrain"]
    assert not (copy / "skills/stray.txt").exists() and hermes.state(hermes_home) == "current"

    # A damaged copy is stale even though its marker is intact, and delivery repairs it.
    for damage in (lambda: (copy / "plugin.yaml").unlink(),
                   lambda: (copy / "__init__.py").write_text("changed"),
                   lambda: shutil.rmtree(copy / "skills/run-execution/references")):
        damage()
        assert hermes.state(hermes_home) == "stale"
        assert assets.link_global(dotbrain_home, "skills", "hermes", user_home=user, run=run).linked
        assert hermes.state(hermes_home) == "current"

    # Staging never reuses, or removes, anything already in the plugins directory.
    foreign_tmp = hermes_home / "plugins/.dotbrain.tmp"
    foreign_tmp.mkdir()
    (foreign_tmp / "keep.txt").write_text("keep")
    (copy / "plugin.yaml").unlink()
    assets.link_global(dotbrain_home, "skills", "hermes", user_home=user, run=run)
    assert (foreign_tmp / "keep.txt").read_text() == "keep"
    assert sorted(p.name for p in (hermes_home / "plugins").iterdir()) == [".dotbrain.tmp", "dotbrain"]

    # Prune removes only dotbrain's skill links.
    _global_extra(dotbrain_home)
    pruned = assets.link_global(dotbrain_home, "skills", "hermes", user_home=user, run=run)
    assert pruned.pruned == ["hermes/discovery-test"]
    assert foreign_skill.is_dir()


def test_unfiltered_delivery_reaches_hermes_only_once_opted_in(dotbrain_home, tmp_path, monkeypatch):
    user = tmp_path / "user"
    hermes_home = tmp_path / "relocated"
    monkeypatch.setenv("HERMES_HOME", str(hermes_home))
    _global_extra(dotbrain_home, "misc/discovery-test")
    assert bootstrap.link_global_skills(dotbrain_home, home=user).warnings == []
    assert not hermes_home.exists()

    explicit = bootstrap.link_global_skills(dotbrain_home, "hermes", home=user)
    assert explicit.warnings == []
    assert "delivered global hermes: run `hermes plugins enable dotbrain` to load the plugin" in explicit.logs
    assert not (user / ".hermes").exists()
    (hermes.plugin_dir(hermes_home) / "plugin.yaml").unlink()

    # The owned copy is the opt-in: an unfiltered run keeps it current.
    later = bootstrap.link_global_skills(dotbrain_home, home=user)
    assert "delivered global hermes/plugins/dotbrain" in later.logs
    assert hermes.state(hermes_home) == "current"
    assert (hermes_home / "skills/discovery-test").is_symlink()


def test_foreign_plugin_directory_is_never_replaced(dotbrain_home, tmp_path):
    user = tmp_path / "user"
    foreign = hermes.plugin_dir(user / ".hermes")
    foreign.mkdir(parents=True)
    (foreign / "plugin.yaml").write_text("name: dotbrain\n")
    result = assets.link_global(dotbrain_home, "skills", "hermes", user_home=user)
    assert result.warnings == [f"{foreign} exists and was not created by dotbrain; skipping"]
    assert [p.name for p in foreign.iterdir()] == ["plugin.yaml"]
    # Not owned, so not opted in: an unfiltered run leaves Hermes alone.
    assert bootstrap.link_global_skills(dotbrain_home, home=user).warnings == []

    # A user skill with a selected skill's name stays; dotbrain reports the collision.
    own = user / ".hermes/skills/discovery-test"
    own.mkdir(parents=True)
    _global_extra(dotbrain_home, "misc/discovery-test")
    collided = assets.link_global(dotbrain_home, "skills", "hermes", user_home=user)
    assert f"{own} exists and was not created by dotbrain; skipping" in collided.warnings
    assert own.is_dir() and not own.is_symlink()


def test_doctor_reports_stale_and_inactive_hermes_delivery(dotbrain_home, tmp_path):
    user = tmp_path / "user"
    hermes_home = user / ".hermes"
    assert not [f for f in doctor._check_machine(dotbrain_home, user) if "hermes" in f.message]
    assets.link_global(dotbrain_home, "skills", "hermes", user_home=user)
    (hermes.plugin_dir(hermes_home) / "plugin.yaml").unlink()
    warnings = {f.message for f in doctor._check_machine(dotbrain_home, user) if f.status == "warn"}
    assert f"hermes: dotbrain plugin copy is stale at {hermes.plugin_dir(hermes_home)}" in warnings
    assert "hermes: dotbrain plugin is not enabled" in warnings

    assets.link_global(dotbrain_home, "skills", "hermes", user_home=user)
    (hermes_home / "config.yaml").write_text("plugins:\n  enabled: [dotbrain]\n  disabled: [dotbrain]\n")
    warnings = {f.message for f in doctor._check_machine(dotbrain_home, user) if f.status == "warn"}
    assert {m for m in warnings if m.startswith("hermes:")} == {"hermes: dotbrain plugin is disabled"}
    (hermes_home / "config.yaml").write_text("plugins:\n  enabled: [dotbrain]\n")
    findings = doctor._check_machine(dotbrain_home, user)
    assert not [f for f in findings if f.status != "ok" and f.message.startswith("hermes:")]
    # No packaged-agent demand: Hermes has no native subagents.
    assert not [f for f in findings if "hermes" in f.message and "agents" in f.message]


def test_doctor_expects_the_plugin_for_a_configured_global_hermes_target(dotbrain_home, tmp_path):
    user = tmp_path / "user"
    (dotbrain_home / "skills/skills.yaml").write_text(f"targets:\n  hermes: {user / 'hskills'}\nglobal_extra: []\n")
    warnings = {f.message for f in doctor._check_machine(dotbrain_home, user) if f.status == "warn"}
    assert "hermes: dotbrain plugin is not delivered" in warnings
    foreign = hermes.plugin_dir(user / ".hermes")
    foreign.mkdir(parents=True)
    warnings = {f.message for f in doctor._check_machine(dotbrain_home, user) if f.status == "warn"}
    assert f"hermes: {foreign} is not dotbrain's plugin copy" in warnings

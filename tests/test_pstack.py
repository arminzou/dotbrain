"""Optional integration delivery through synthetic dependencies and isolated checkouts."""
import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest
import yaml

from dotbrain import adopter_repos, assets, beads, config, doctor, hooks, projects, pstack, resource_loader, skills, subagents, workflows


@pytest.fixture(scope="session")
def pstack_repo_seed(tmp_path_factory):
    repo = tmp_path_factory.mktemp("pstack-seed")
    subprocess.run(["git", "-C", str(repo), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                    "commit", "--allow-empty", "-qm", "seed"], check=True)
    return repo


@pytest.fixture
def integration(dotbrain_home, tmp_path, pstack_repo_seed):
    source = tmp_path / "selected-source"
    for name in (*pstack.REQUIRED, "skills/how/references/source.md"):
        file = source / name
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text("synthetic dependency\n", encoding="utf-8")
    (source / "plugin.json").write_text(json.dumps({"name": "pstack", "version": pstack.VERSION}), encoding="utf-8")
    repo = tmp_path / "checkout"
    shutil.copytree(pstack_repo_seed, repo, symlinks=True)
    brainspace = dotbrain_home / "brainspaces/sample"
    brain = brainspace / ".brain"
    brain.mkdir(parents=True)
    (brainspace / ".repo").write_text(str(repo), encoding="utf-8")
    (brainspace / ".beads").mkdir()
    (brainspace / ".beads/metadata.json").write_text("{}", encoding="utf-8")
    (repo / ".brain").symlink_to(brain, target_is_directory=True)
    (brain / "DOTBRAIN.md").write_text("synthetic convention\n", encoding="utf-8")
    for workspace in (".claude", ".codex"):
        (repo / workspace).mkdir()
    settings = {"agents": ["claude", "codex"], "skills": [], "beads": {"mode": "embedded"},
                "pstack": {"enabled": True, "source": str(source)}}
    calls = []

    def write(**changes):
        settings.update(changes)
        (brain / "project.yaml").write_text(yaml.safe_dump(settings), encoding="utf-8")

    def run(argv, **kwargs):
        calls.append((argv, kwargs))
        if argv[0] == "git" and len(argv) > 2 and argv[2] == str(source):
            output = {"--show-toplevel": str(source), "HEAD": pstack.REVISION,
                      "--untracked-files=all": "", "-z": "\0".join(
                          file.relative_to(source).as_posix() for file in source.rglob("*") if file.is_file()) + "\0"}[argv[-1]]
            return subprocess.CompletedProcess(argv, 0, output, "")
        if argv[0] == "bd":
            expected = (["bd", "--readonly", "dolt", "test"] if settings["beads"]["mode"] == "server"
                        else ["bd", "--readonly", "ready", "--json"])
            assert argv == expected
            assert kwargs["cwd"] == brainspace
            assert kwargs["env"]["BEADS_DIR"] == str(brainspace / ".beads")
            assert kwargs["env"]["BD_NON_INTERACTIVE"] == "1"
            assert kwargs["timeout"] == pstack.TIMEOUT
            return subprocess.CompletedProcess(argv, 0, "connected", "")
        return adopter_repos._default_run(argv, **kwargs)

    write()
    return dotbrain_home, brainspace, repo, source, write, run, calls


def link(integration, runtime="all"):
    home, brainspace, repo, _, _, run, _ = integration
    return assets.link_project(home, projects.ProjectTarget("sample", brainspace, repo), "skills", runtime, run=run)


def tree(root):
    result = {}
    def visit(directory):
        for path in directory.iterdir():
            relative = path.relative_to(root).as_posix()
            if path.is_symlink() or skills._is_junction(path):
                result[relative] = ("link", os.readlink(path))
            elif path.is_dir():
                result[relative] = ("directory",)
                visit(path)
            else:
                result[relative] = ("file", path.read_bytes())
    visit(root)
    return result


@pytest.mark.parametrize("value", [None, True, [], "yes", {"enabled": "false"}, {"enabled": 1},
                                   {"enabled": True}, {"enabled": True, "source": "relative"},
                                   {"enabled": False, "source": []}, {"enable": True}])
def test_invalid_selection_is_rejected(value):
    with pytest.raises(ValueError, match="pstack"):
        config.parse_pstack({"pstack": value}, "project.yaml")


def test_defaults_and_expanded_home_source():
    assert config.parse_pstack({}, "project.yaml") == config.ProjectPstack()
    assert config.parse_pstack({"pstack": {"enabled": False}}, "project.yaml") == config.ProjectPstack()
    selection = config.parse_pstack({"pstack": {"enabled": True, "source": "~/source"}}, "project.yaml")
    assert selection.source == Path.home() / "source"


@pytest.mark.parametrize("with_source", [False, True])
def test_core_only_does_not_probe_or_deliver(integration, with_source):
    home, _, repo, _, write, _, calls = integration
    write(pstack={"enabled": False, "source": str(repo / "missing")} if with_source else {})
    assert not link(integration).warnings
    assert not any(argv[0] == "bd" for argv, _ in calls)
    assert not (repo / pstack.POINTER).exists()
    assert not (home / pstack.CACHE).exists()


@pytest.mark.parametrize("problem", ["revision", "dirty", "git-failure", "missing-resource", "manifest", "partial"])
def test_dependency_rejection_preserves_all_state(integration, problem):
    home, _, repo, source, _, run, _ = integration
    assert not link(integration).warnings
    if problem == "missing-resource":
        (source / pstack.REQUIRED[-1]).unlink()
    if problem == "manifest":
        (source / "plugin.json").write_text('{"name":"other","version":"0.15.36"}', encoding="utf-8")
    def bad(argv, **kwargs):
        result = run(argv, **kwargs)
        if argv[0] == "git" and argv[2] == str(source):
            if problem == "revision" and argv[-1] == "HEAD":
                result.stdout = "0" * 40
            if problem == "dirty" and argv[-1] == "--untracked-files=all":
                result.stdout = "?? untracked.md"
            if problem == "git-failure":
                result.returncode = 1
            if problem == "partial" and argv[-1] == "-z":
                result.stdout += "skills/how/references/missing.md\0"
        return result
    before = tree(home), tree(repo)
    with pytest.raises(ValueError, match="pstack.source"):
        assets.link_project(home, projects.ProjectTarget("sample", integration[1], repo), "skills", run=bad)
    assert (tree(home), tree(repo)) == before


def test_complete_selection_uses_only_explicit_source(integration, tmp_path):
    _, _, _, source, _, run, calls = integration
    (tmp_path / "other-source").mkdir()
    pstack.qualify(source, run)
    assert all(argv[2] == str(source) for argv, _ in calls)


@pytest.mark.parametrize("mode", ["embedded", "server"])
@pytest.mark.parametrize("failure", ["none", "unsupported", "uninitialized", "refused", "missing-bd", "timeout"])
def test_backend_failure_never_publishes_mode(integration, failure, mode):
    home, brainspace, repo, _, write, run, _ = integration
    write(beads={"mode": mode})
    if failure == "none":
        write(beads={"mode": "none"})
    if failure == "unsupported":
        write(beads={"mode": "unknown"})
    if failure == "uninitialized":
        (brainspace / ".beads/metadata.json").unlink()
    def unavailable(argv, **kwargs):
        if argv[0] == "bd":
            if failure == "missing-bd":
                raise FileNotFoundError("bd")
            if failure == "timeout":
                raise subprocess.TimeoutExpired(argv, 15)
            return subprocess.CompletedProcess(argv, 1, "", "connection refused")
        return run(argv, **kwargs)
    before = tree(home), tree(repo)
    with pytest.raises((ValueError, RuntimeError), match="Beads|backend"):
        assets.link_project(home, projects.ProjectTarget("sample", brainspace, repo), "skills", run=unavailable)
    assert (tree(home), tree(repo)) == before


@pytest.mark.parametrize(("mode", "command"), [
    ("embedded", ["bd", "--readonly", "ready", "--json"]),
    ("server", ["bd", "--readonly", "dolt", "test"]),
])
def test_backend_probe_matches_backend(integration, mode, command):
    _, _, _, _, write, _, calls = integration
    write(beads={"mode": mode})
    assert not link(integration).warnings
    assert [argv for argv, _ in calls if argv[0] == "bd"] == [command]


def test_repeatable_delivery_generic_pruning_and_ignored_discovery(integration):
    home, _, repo, _, _, run, _ = integration
    assert not link(integration).warnings
    before = tree(home), tree(repo)
    assert link(integration).linked == []
    assert (tree(home), tree(repo)) == before
    for relative in pstack.RECEIVERS.values():
        entry = repo / relative
        assert pstack.owned_link(home, entry)
        assert pstack._intact(entry)
        skills.link_into(home, entry.parent, (), prune_owned_only=True, preserve_collisions=True)
        assert entry.is_symlink()
    excludes = adopter_repos.git_exclude_file(repo, run).read_text().splitlines()
    assert all("/" + relative in excludes for relative in (*pstack.RECEIVERS.values(), pstack.POINTER))
    assert pstack.NAME.encode() in hooks.brain_context(repo)


def test_optout_missing_source_prunes_only_owned_outputs(integration):
    home, _, repo, source, write, _, _ = integration
    assert not link(integration).warnings
    foreign = repo / ".agents/skills/pstack"
    foreign.mkdir()
    (foreign / "SKILL.md").write_text("foreign", encoding="utf-8")
    shutil.rmtree(source)
    write(pstack={"enabled": False, "source": str(source)}, beads={"mode": "none"})
    result = link(integration)
    assert not result.warnings
    assert set(result.pruned) == {*pstack.RECEIVERS.values(), pstack.POINTER}
    assert foreign.is_dir()
    assert not pstack.discovery(repo)
    assert (home / pstack.CACHE).is_dir()


@pytest.mark.parametrize("kind", ["file", "directory", "symlink", "modified-cache", "modified-pointer"])
def test_collision_and_modified_outputs_preserved(integration, tmp_path, kind):
    home, _, repo, _, _, _, _ = integration
    link_path = repo / pstack.RECEIVERS["codex"]
    if kind.startswith("modified"):
        assert not link(integration).warnings
        if kind == "modified-cache":
            (link_path / "SKILL.md").write_text("user edit", encoding="utf-8")
        else:
            pointer = repo / pstack.POINTER
            pointer.write_text(pointer.read_text().replace(pstack.VERSION, "edited"), encoding="utf-8")
    else:
        link_path.parent.mkdir(parents=True)
        if kind == "file":
            link_path.write_text("foreign", encoding="utf-8")
        elif kind == "directory":
            link_path.mkdir()
            (link_path / "SKILL.md").write_text("foreign", encoding="utf-8")
        else:
            outside = tmp_path / "outside"
            outside.mkdir()
            link_path.symlink_to(outside, target_is_directory=True)
    before = tree(link_path.resolve()) if link_path.is_dir() else link_path.read_bytes()
    result = link(integration)
    assert result.warnings
    after = tree(link_path.resolve()) if link_path.is_dir() else link_path.read_bytes()
    assert before == after


def test_runtime_filter_and_removed_runtime(integration):
    _, _, repo, _, write, _, _ = integration
    assert not link(integration, "codex").warnings
    assert (repo / pstack.RECEIVERS["codex"]).is_symlink()
    assert not (repo / pstack.RECEIVERS["claude"]).exists()
    assert not link(integration).warnings
    write(agents=["claude"])
    assert not link(integration).warnings
    assert not (repo / pstack.RECEIVERS["codex"]).is_symlink()
    assert (repo / pstack.RECEIVERS["claude"]).is_symlink()
    with pytest.raises(ValueError, match="not declared"):
        link(integration, "codex")


@pytest.mark.parametrize("operation", ["link", "refresh"])
def test_claude_runtime_alias_delivers_and_opts_out(integration, monkeypatch, operation):
    home, _, repo, _, write, run, _ = integration
    monkeypatch.setattr(beads, "pull_beads_for_all", lambda *a, **kw: beads.BootstrapResult())
    def reconcile():
        return (link(integration, "claude-code") if operation == "link"
                else workflows.refresh_projects(home, cwd=repo, runtime="claude-code", run=run))
    result = reconcile()
    assert not (result.warnings if operation == "link" else result.errors)
    assert (repo / pstack.RECEIVERS["claude"]).is_symlink()
    assert not (repo / pstack.RECEIVERS["codex"]).is_symlink()
    assert json.loads((repo / pstack.POINTER).read_text())["modes"] == {"claude": pstack.RECEIVERS["claude"]}
    write(pstack={"enabled": False})
    result = reconcile()
    assert not (result.warnings if operation == "link" else result.errors)
    assert not (repo / pstack.RECEIVERS["claude"]).is_symlink()
    assert not (repo / pstack.POINTER).exists()


def test_scoped_optout_retains_untouched_runtime_metadata(integration):
    home, _, repo, source, write, _, _ = integration
    assert not link(integration).warnings
    original = json.loads((repo / pstack.POINTER).read_text())
    write(pstack={"enabled": False})
    assert not link(integration, "codex").warnings
    retained = json.loads((repo / pstack.POINTER).read_text())
    assert retained["modes"] == {"claude": original["modes"]["claude"]}
    assert retained["caches"] == {"claude": original["caches"]["claude"]}
    assert retained["source"] == original["source"]
    assert (repo / pstack.RECEIVERS["claude"]).is_symlink()
    assert not (repo / pstack.RECEIVERS["codex"]).is_symlink()
    assert pstack.discovery(repo) == b""
    write(pstack={"enabled": True, "source": str(source)})
    assert not link(integration, "codex").warnings
    restored = json.loads((repo / pstack.POINTER).read_text())
    assert restored["modes"] == original["modes"]
    assert restored["caches"] == original["caches"]
    assert pstack.delivery_issues(home, repo, (".claude", ".codex"), True) == []


def test_scoped_upgrade_preserves_other_runtime_discovery(integration, monkeypatch):
    _, _, repo, _, _, _, _ = integration
    assert not link(integration).warnings
    previous = (repo / pstack.RECEIVERS["claude"]).resolve()
    resources = pstack._resources()
    monkeypatch.setattr(pstack, "_resources", lambda: {**resources, "references/new.md": b"new resource"})
    assert not link(integration, "codex").warnings
    assert (repo / pstack.RECEIVERS["claude"]).resolve() == previous
    assert (repo / pstack.RECEIVERS["codex"]).resolve() != previous
    record = json.loads((repo / pstack.POINTER).read_text())
    assert record["caches"]["claude"] == str(previous)
    payload = pstack.discovery(repo).decode()
    assert all(relative + "/SKILL.md" in payload for relative in pstack.RECEIVERS.values())


def test_failed_link_replacement_retains_previous_delivery(integration, monkeypatch):
    _, _, repo, _, _, _, _ = integration
    assert not link(integration).warnings
    entry = repo / pstack.RECEIVERS["codex"]
    previous = entry.resolve()
    descriptor = (repo / pstack.POINTER).read_bytes()
    resources = pstack._resources()
    monkeypatch.setattr(pstack, "_resources", lambda: {**resources, "references/new.md": b"new resource"})
    rename = Path.rename
    def fail_promotion(path, target):
        if path.name.endswith(".tmp") and target == entry:
            raise OSError("promotion failed")
        return rename(path, target)
    monkeypatch.setattr(Path, "rename", fail_promotion)
    with pytest.raises(OSError, match="promotion failed"):
        link(integration, "codex")
    assert entry.is_symlink() and entry.resolve() == previous
    assert (repo / pstack.POINTER).read_bytes() == descriptor
    assert not list(entry.parent.glob(".dotbrain-pstack-*.tmp"))
    assert not list(entry.parent.glob(".dotbrain-pstack-*.backup"))


@pytest.mark.parametrize("command", ["wire", "refresh", "skills-link"])
def test_invalid_config_or_source_is_preflight_before_writes(integration, command):
    home, brainspace, repo, source, write, run, _ = integration
    write(pstack={"enabled": "yes", "source": str(source)})
    before = tree(home), tree(repo)
    if command == "wire":
        with pytest.raises(ValueError, match="boolean"):
            workflows.wire_project(dotbrain_home=home, repo=repo, run=run)
    elif command == "refresh":
        assert workflows.refresh_projects(home, cwd=repo, run=run).errors
    else:
        with pytest.raises(ValueError, match="boolean"):
            assets.link_project(home, projects.ProjectTarget("sample", brainspace, repo), "skills", run=run)
    assert (tree(home), tree(repo)) == before


def test_worktree_delivery_optout_and_shared_excludes(integration, tmp_path, monkeypatch):
    home, brainspace, main, source, write, run, _ = integration
    assert not link(integration).warnings
    sibling = tmp_path / "sibling"
    subprocess.run(["git", "-C", str(main), "worktree", "add", "-b", "feature", str(sibling)], check=True, capture_output=True)
    result = workflows.wire_project(dotbrain_home=home, repo=sibling, run=run)
    assert not result.errors
    assert (sibling / ".brain").resolve() == (main / ".brain").resolve()
    assert all((sibling / relative).is_symlink() for relative in pstack.RECEIVERS.values())
    metadata = (brainspace / ".brain/project.yaml").read_bytes()
    assert not workflows.unwire_project(dotbrain_home=home, repo=sibling, run=run).errors
    assert (brainspace / ".brain/project.yaml").read_bytes() == metadata
    exclude = adopter_repos.git_exclude_file(main, run)
    assert "/" + pstack.POINTER in exclude.read_text().splitlines()
    shutil.rmtree(source)
    write(pstack={"enabled": False})
    assert not link(integration).warnings
    assert "/" + pstack.POINTER not in exclude.read_text().splitlines()


def test_refresh_sync_precedes_discovery(integration, monkeypatch):
    home, _, repo, _, _, run, _ = integration
    def sync(*args, **kwargs):
        assert not (repo / pstack.POINTER).exists()
        return beads.BootstrapResult()
    monkeypatch.setattr(beads, "pull_beads_for_all", sync)
    result = workflows.refresh_projects(home, cwd=repo, run=run)
    assert not result.errors
    assert (repo / pstack.POINTER).is_file()


def test_failed_sync_never_publishes_mode(integration, monkeypatch):
    home, _, repo, _, _, run, _ = integration
    monkeypatch.setattr(beads, "pull_beads_for_all", lambda *a, **kw: beads.BootstrapResult(errors=["offline"]))
    assert workflows.refresh_projects(home, cwd=repo, run=run).errors
    assert not (repo / pstack.POINTER).exists()


@pytest.mark.parametrize("operation", ["wire", "refresh"])
def test_optout_survives_failed_backend_sync(integration, monkeypatch, operation):
    home, _, repo, source, write, run, _ = integration
    assert not link(integration).warnings
    shutil.rmtree(source)
    write(pstack={"enabled": False})
    monkeypatch.setattr(beads, "pull_beads_for_all", lambda *a, **kw: beads.BootstrapResult(errors=["offline"]))
    result = (workflows.wire_project(dotbrain_home=home, repo=repo, run=run) if operation == "wire"
              else workflows.refresh_projects(home, cwd=repo, run=run))
    assert result.errors
    assert not (repo / pstack.POINTER).exists()
    assert not any((repo / relative).is_symlink() for relative in pstack.RECEIVERS.values())


@pytest.mark.parametrize("operation", ["wire", "refresh"])
def test_core_resources_reconcile_despite_failed_tracker_sync(integration, monkeypatch, operation):
    home, _, repo, _, write, run, calls = integration
    for relative, body in (("claude/helper.md", "---\nname: helper\ndescription: Synthetic agent\n---\n"),
                           ("codex/helper.toml", 'name = "helper"\ndescription = "Synthetic agent"\n')):
        source = home / "subagents" / relative
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text(body, encoding="utf-8")
    stale_skill = repo / ".agents/skills/stale"
    stale_skill.parent.mkdir(parents=True)
    stale_skill.symlink_to(home / "skills/misc/discovery-test", target_is_directory=True)
    stale_agent = repo / ".claude/agents/stale.md"
    stale_agent.parent.mkdir(parents=True)
    stale_agent.symlink_to(home / "subagents/claude/helper.md")
    write(pstack={"enabled": False}, skills=["misc/discovery-test"], subagents=["helper"])
    monkeypatch.setattr(beads, "pull_beads_for_all", lambda *a, **kw: beads.BootstrapResult(errors=["offline"]))
    result = (workflows.wire_project(dotbrain_home=home, repo=repo, run=run) if operation == "wire"
              else workflows.refresh_projects(home, cwd=repo, run=run))
    assert "offline" in result.errors
    assert not stale_skill.is_symlink() and not stale_agent.is_symlink()
    assert (repo / ".agents/skills/discovery-test").is_symlink()
    assert (repo / ".claude/skills/discovery-test").is_symlink()
    assert (repo / ".claude/agents/helper.md").is_symlink()
    assert subagents.is_managed_copy(repo / ".codex/agents/helper.toml")
    assert not (repo / pstack.POINTER).exists()
    assert not any(argv[0] == "bd" for argv, _ in calls)


def test_wire_checks_backend_after_sync_and_honors_skip(integration, monkeypatch):
    home, brainspace, repo, _, _, run, calls = integration
    metadata = brainspace / ".beads/metadata.json"
    metadata.unlink()
    def sync(*args, **kwargs):
        assert not (repo / pstack.POINTER).exists()
        metadata.write_text("{}", encoding="utf-8")
        return beads.BootstrapResult()
    monkeypatch.setattr(beads, "pull_beads_for_all", sync)
    with pytest.raises(RuntimeError, match="initialized Beads"):
        workflows.wire_project(dotbrain_home=home, repo=repo, run=run, run_beads=False)
    assert not metadata.exists()
    assert not (repo / pstack.POINTER).exists()
    assert not any(argv[0] == "bd" for argv, _ in calls)
    assert not workflows.wire_project(dotbrain_home=home, repo=repo, run=run).errors
    assert metadata.exists() and (repo / pstack.POINTER).is_file()


@pytest.mark.parametrize("receiver", [".agents/skills", ".claude/skills"])
def test_receiver_junction_is_never_traversed(integration, monkeypatch, receiver):
    home, _, repo, _, _, run, _ = integration
    destination = repo / receiver
    destination.mkdir(parents=True)
    sentinel = destination / pstack.NAME
    sentinel.write_text("foreign", encoding="utf-8")
    original = skills._is_junction
    monkeypatch.setattr(skills, "_is_junction", lambda path: Path(path) == destination or original(path))
    before = sentinel.read_bytes()
    with pytest.raises(ValueError, match="junction"):
        link(integration)
    assert sentinel.read_bytes() == before
    assert pstack.unwire(home, repo, run=run).warnings
    assert sentinel.read_text() == "foreign"


def test_redirected_integration_cache_is_preserved(integration):
    home, _, repo, _, _, _, _ = integration
    root = home / pstack.CACHE
    root.parent.mkdir(parents=True)
    foreign = home / "skills/foreign-cache"
    foreign.mkdir()
    root.symlink_to(foreign, target_is_directory=True)
    with pytest.raises(ValueError, match="real directory"):
        link(integration)
    assert root.is_symlink() and list(foreign.iterdir()) == []
    assert not (repo / pstack.POINTER).exists()


def test_doctor_is_read_only_and_diagnoses_delivery(integration):
    home, brainspace, repo, _, _, run, _ = integration
    before = tree(home), tree(repo)
    selection = pstack.preflight(home, "sample", run=run, backend=True)
    assert pstack.delivery_issues(home, repo, (".claude", ".codex"), selection.enabled)
    assert (tree(home), tree(repo)) == before
    assert not link(integration).warnings
    assert pstack.delivery_issues(home, repo, (".claude", ".codex"), True) == []
    (repo / pstack.RECEIVERS["codex"]).unlink()
    assert pstack.delivery_issues(home, repo, (".claude", ".codex"), True)


def test_doctor_reports_enabled_dependency_errors(integration, monkeypatch):
    home, brainspace, repo, _, write, run, _ = integration
    monkeypatch.setattr(doctor, "_check_convention", lambda *a: [])
    monkeypatch.setattr(doctor, "_check_design_lifecycle", lambda *a: [])
    monkeypatch.setattr(doctor, "_check_beads_state", lambda *a, **kw: [])
    before = tree(home), tree(repo)
    findings = doctor._check_project(projects.ProjectTarget("sample", brainspace, repo), home, run)
    assert any(item.status == "error" and pstack.NAME in item.message for item in findings)
    assert (tree(home), tree(repo)) == before
    write(pstack={"enabled": True, "source": str(repo / "missing")})
    findings = doctor._check_project(projects.ProjectTarget("sample", brainspace, repo), home, run)
    assert any(item.status == "error" and "source checkout missing" in item.message for item in findings)


def test_hook_reads_local_selection_and_respects_payload_limit(integration, monkeypatch):
    _, brainspace, repo, _, write, _, calls = integration
    assert not link(integration).warnings
    calls.clear()
    monkeypatch.setattr(hooks, "repo_root", lambda cwd: repo)
    assert pstack.NAME.encode() in hooks.brain_context(repo)
    assert calls == []
    write(pstack={"enabled": False})
    assert pstack.NAME.encode() not in hooks.brain_context(repo)
    write(pstack={"enabled": True, "source": "relative"})
    assert pstack.NAME.encode() not in hooks.brain_context(repo)
    (brainspace / ".brain/DOTBRAIN.md").write_bytes(b"x" * (hooks.PAYLOAD_LIMIT - 40))
    write(pstack={"enabled": True, "source": str(integration[3])})
    assert len(hooks.brain_context(repo)) <= hooks.PAYLOAD_LIMIT
    assert pstack.NAME.encode() not in hooks.brain_context(repo)


def test_packaged_mode_is_not_global_plugin_skill():
    files = dict(resource_loader.iter_resource_files(f"integrations/{pstack.NAME}"))
    frontmatter = yaml.safe_load(files[Path("SKILL.md")].read_text(encoding="utf-8").split("---")[1])
    assert frontmatter["name"] == pstack.NAME
    with resource_loader.plugin_tree() as plugin:
        assert not (plugin / "skills" / pstack.NAME).exists()
        assert len(list((plugin / "skills").glob("*/SKILL.md"))) == 5

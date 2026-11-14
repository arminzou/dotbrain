"""Breaking transition ownership: known output retires; ambiguous data stays recoverable."""
from pathlib import Path
import shutil

import pytest

from dotbrain import assets, cursor, hermes, opencode, owned_copy, pi, resource_loader, subagents


FIXTURES = Path(__file__).parent / "fixtures"


def old_bundle(target):
    target.mkdir(parents=True)
    (target / owned_copy.MARKER).write_text("dotbrain\n", encoding="utf-8")
    shutil.copytree(FIXTURES / "retired-plugin/skills", target / "skills")


@pytest.mark.parametrize("runtime,module", [("hermes", hermes), ("pi", pi), ("cursor", cursor), ("opencode", opencode)])
@pytest.mark.parametrize("modified", [False, True])
def test_runtime_transition_preserves_changed_old_bundle_and_reports_path(tmp_path, runtime, module, modified):
    home, user = tmp_path / "data", tmp_path / "user"
    home.mkdir()
    from dotbrain import runtimes
    directory = home if runtime == "cursor" else runtimes.user_dir(runtimes.find(runtime), user)
    target = opencode.packaged_dir(directory) if runtime == "opencode" else module.plugin_dir(directory)
    old_bundle(target)
    old_file = target / "skills/run-execution/references/hermes.md"
    if modified:
        old_file.write_bytes(b"User modification\xff\n")
    before = old_file.read_bytes()
    result = assets.link_global(home, "skills", runtime, user_home=user)
    assert not result.warnings
    assert module.state(directory) == "current"
    assert {p.parent.name for p in (target / "skills").glob("*/SKILL.md")} == {
        "wire-brain", "brain-convention", "maintain-brain", "work-graph", "repo-rules"}
    backups = list((target.parent.parent / ".dotbrain-preserved").glob("*"))
    if modified:
        assert len(backups) == 1
        assert (backups[0] / old_file.relative_to(target)).read_bytes() == before
        assert any(str(backups[0]) in notice for notice in result.notices)
    else:
        assert not backups and not any("preserved at" in notice for notice in result.notices)
    if runtime == "hermes":
        (directory / "config.yaml").write_text("plugins:\n  enabled: [dotbrain]\n", encoding="utf-8")
    repeated = assets.link_global(home, "skills", runtime, user_home=user)
    assert not repeated.warnings and not repeated.linked
    assert list((target.parent.parent / ".dotbrain-preserved").glob("*")) == backups


@pytest.mark.parametrize("kind", ["unknown-file", "unknown-directory", "linked-skill", "linked-file", "linked-root", "dangling-link"])
def test_bundle_transition_preserves_ambiguous_content_without_following_links(tmp_path, kind):
    target = tmp_path / "runtime/plugins/dotbrain"
    old_bundle(target)
    private = tmp_path / "private"
    private.mkdir()
    sentinel = private / "sentinel"
    sentinel.write_bytes(b"User-owned private data\xff")
    entry = target / "skills/run-execution/extra"
    if kind == "unknown-file":
        entry.write_bytes(b"user data")
    elif kind == "unknown-directory":
        entry.mkdir()
    elif kind == "linked-file":
        entry.symlink_to(sentinel)
    elif kind == "dangling-link":
        entry.symlink_to(private / "missing")
    else:
        entry = target / ("skills" if kind == "linked-root" else "skills/run-execution")
        shutil.rmtree(entry)
        entry.symlink_to(private, target_is_directory=True)
    saved = owned_copy.install(target, ("skills",))
    assert saved is not None and saved.is_dir()
    assert sentinel.read_bytes() == b"User-owned private data\xff"
    assert (saved / entry.relative_to(target)).is_symlink() == (kind not in ("unknown-file", "unknown-directory"))
    assert owned_copy.state(target, ("skills",)) == "current"


def test_bundle_transition_refuses_linked_backup_location_before_mutation(tmp_path):
    target = tmp_path / "runtime/plugins/dotbrain"
    old_bundle(target)
    (target / "skills/run-execution/unknown").write_bytes(b"keep")
    external = tmp_path / "private"
    external.mkdir()
    (target.parent.parent / ".dotbrain-preserved").symlink_to(external, target_is_directory=True)
    with pytest.raises(ValueError, match="preservation directory must be a real directory"):
        owned_copy.install(target, ("skills",))
    assert (target / "skills/run-execution/unknown").read_bytes() == b"keep"
    assert list(external.iterdir()) == []


def test_agent_retirement_preserves_linked_receiver(tmp_path):
    private = tmp_path / "private"
    private.mkdir()
    old = private / "dotbrain-verifier.toml"
    shutil.copyfile(FIXTURES / "retired-agents/codex.toml", old)
    receiver = tmp_path / "agents"
    receiver.symlink_to(private, target_is_directory=True)
    result = subagents.retire_packaged(receiver, "codex", label="agents")
    assert not result.pruned and result.notices
    assert old.read_bytes() == (FIXTURES / "retired-agents/codex.toml").read_bytes()


def test_legacy_agent_content_hashes_cover_the_previous_package():
    import json
    known = json.loads(resource_loader.resource("retired-agents.json").read_text(encoding="utf-8"))
    assert set(known) == {"claude-code", "codex"}
    for runtime, suffix in (("claude-code", ".md"), ("codex", ".toml")):
        assert set(known[runtime]) == {f"dotbrain-{role}{suffix}" for role in ("worker", "researcher", "reviewer", "verifier")}


@pytest.mark.parametrize("modified", [False, True])
def test_unwire_preserves_modified_retired_agents(tmp_path, modified):
    import subprocess
    from dotbrain import adopter_repos
    repo = tmp_path / "repo"
    for workspace, runtime, suffix in ((".claude", "claude-code", ".md"), (".codex", "codex", ".toml")):
        agent = repo / workspace / "agents" / f"dotbrain-verifier{suffix}"
        agent.parent.mkdir(parents=True)
        original = (FIXTURES / "retired-agents" / f"{runtime}{suffix}").read_bytes()
        agent.write_bytes(original + (b"modified" if modified else b""))
    result = adopter_repos.unwire_repo(repo, run=lambda argv, **kwargs: subprocess.CompletedProcess(argv, 1, "", ""))
    assert not result.errors
    assert len(result.warnings) == (2 if modified else 0)
    for workspace, suffix in ((".claude", ".md"), (".codex", ".toml")):
        agent = repo / workspace / "agents" / f"dotbrain-verifier{suffix}"
        assert agent.exists() == modified
        if modified:
            assert agent.read_bytes().endswith(b"modified")


@pytest.mark.parametrize("modified", [False, True])
def test_shared_convention_refresh_preserves_modified_content_and_reports_it(tmp_path, modified):
    from dotbrain import brainspaces
    brainspace = tmp_path / "home/brainspaces/project"
    convention = brainspace / ".brain/DOTBRAIN.md"
    convention.parent.mkdir(parents=True)
    original = (FIXTURES / "retired-templates/DOTBRAIN.md").read_bytes()
    convention.write_bytes(original + (b"\r\nUser notes\xff" if modified else b""))
    before = convention.read_bytes()
    notices = []
    brainspaces.seed_brain(brainspace, tmp_path / "home", notices=notices)
    backups = list((convention.parent / ".dotbrain-preserved").glob("*"))
    if modified:
        assert len(backups) == 1 and backups[0].read_bytes() == before
        assert any(str(backups[0]) in notice for notice in notices)
    else:
        assert not backups and not notices
    assert convention.read_bytes() == resource_loader.resource("templates/brain/DOTBRAIN.md").read_text(encoding="utf-8").encode()
    assert brainspaces.seed_brain(brainspace, tmp_path / "home", notices=notices) == []
    assert list((convention.parent / ".dotbrain-preserved").glob("*")) == backups


def test_shared_convention_refuses_linked_preservation_directory(tmp_path):
    from dotbrain import brainspaces
    brainspace = tmp_path / "home/brainspaces/project"
    convention = brainspace / ".brain/DOTBRAIN.md"
    convention.parent.mkdir(parents=True)
    convention.write_bytes(b"private modified convention")
    foreign = tmp_path / "private"
    foreign.mkdir()
    (convention.parent / ".dotbrain-preserved").symlink_to(foreign, target_is_directory=True)
    with pytest.raises(ValueError):
        brainspaces.seed_brain(brainspace, tmp_path / "home")
    assert convention.read_bytes() == b"private modified convention" and list(foreign.iterdir()) == []

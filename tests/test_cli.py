"""Smoke tests for the Typer command surface."""

from __future__ import annotations

import subprocess
from types import SimpleNamespace
from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

from dotbrain import __version__, bootstrap as bootstrap_mod, migrate, paths
from dotbrain import cli
from dotbrain.cli import app

from conftest import set_fake_home

runner = CliRunner()


def test_help_lists_command_tree():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for command in ("bootstrap", "doctor", "wire", "refresh", "unwire", "beads", "skills", "agents", "projects"):
        assert command in result.output
    for hidden_command in ("migrate-beads", "list-beads-db", "drop-beads-db", "worktrees"):
        assert hidden_command not in result.output


def test_version_prints_installed_version():
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0, result.output
    assert result.output == f"{__version__}\n"


def test_skills_help_lists_discovery_command():
    result = runner.invoke(app, ["skills", "--help"])
    assert result.exit_code == 0
    assert "link" in result.output
    assert "list" in result.output


def test_update_is_retired():
    result = runner.invoke(app, ["update"])
    assert result.exit_code == 2
    assert "No such command" in result.output


def test_agents_help_lists_discovery_command():
    result = runner.invoke(app, ["agents", "--help"])
    assert result.exit_code == 0
    assert "link" in result.output
    assert "list" in result.output


def test_wire_help_omits_retired_global_hook_support():
    result = runner.invoke(app, ["wire", "--help"])
    assert result.exit_code == 0
    assert "global-hook" not in result.output
    assert "--skip-global-hook" not in result.output


def test_migrate_beads_dry_run_prints_plan(
    dotbrain_home: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("DOTBRAIN_HOME", str(dotbrain_home))
    import json

    beads = dotbrain_home / "brainspaces" / "demo" / ".beads"
    beads.mkdir(parents=True)
    (beads / "metadata.json").write_text(json.dumps({"dolt_mode": "embedded"}))

    result = runner.invoke(
        app, ["beads", "migrate", "--project", "demo", "--server-host", "h", "--dry-run"]
    )
    assert result.exit_code == 0, result.output
    assert "would run bd" in result.output
    assert "--reinit-local" in result.output


def test_migrate_beads_requires_server_host(
    dotbrain_home: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("DOTBRAIN_HOME", str(dotbrain_home))
    result = runner.invoke(app, ["beads", "migrate", "--project", "demo", "--dry-run"])
    assert result.exit_code != 0


def test_migrate_beads_exits_nonzero_on_verification_failure(
    dotbrain_home: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("DOTBRAIN_HOME", str(dotbrain_home))
    (dotbrain_home / "brainspaces/demo").mkdir(parents=True)

    def fake_migrate_project(**kwargs):
        return migrate.MigrationResult(
            project=kwargs["project"],
            status="aborted-count-mismatch",
            warnings=["demo: restored issue count mismatch"],
        )

    monkeypatch.setattr(migrate, "migrate_project", fake_migrate_project)

    result = runner.invoke(app, ["beads", "migrate", "--project", "demo", "--server-host", "h"])

    assert result.exit_code == 1
    assert "error: demo: restored issue count mismatch" in result.output


def test_migrate_beads_exits_nonzero_when_unverified(
    dotbrain_home: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("DOTBRAIN_HOME", str(dotbrain_home))
    (dotbrain_home / "brainspaces/demo").mkdir(parents=True)

    def fake_migrate_project(**kwargs):
        return migrate.MigrationResult(
            project=kwargs["project"],
            status="migrated-unverified",
            warnings=["demo: could not verify issue count"],
        )

    monkeypatch.setattr(migrate, "migrate_project", fake_migrate_project)
    result = runner.invoke(app, ["beads", "migrate", "--project", "demo", "--server-host", "h"])
    assert result.exit_code == 1


def test_wire_brain_only_creates_brainspace(
    dotbrain_home: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("DOTBRAIN_HOME", str(dotbrain_home))
    result = runner.invoke(
        app, ["wire", "--no-repo", "--project", "demo", "--skip-beads"]
    )
    assert result.exit_code == 0, result.output
    brainspace = dotbrain_home / "brainspaces" / "demo"
    assert (brainspace / ".repo").read_text() == "(brain-only)\n"
    assert (brainspace / ".brain" / "AGENTS.md").is_file()


def test_wire_no_repo_requires_project(
    dotbrain_home: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("DOTBRAIN_HOME", str(dotbrain_home))
    result = runner.invoke(app, ["wire", "--no-repo"])
    assert result.exit_code != 0


def test_wire_uses_configured_beads_server(
    dotbrain_home: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("DOTBRAIN_HOME", str(dotbrain_home))
    (dotbrain_home / "dotbrain.yaml").write_text(
        "version: 2\nbeads:\n  server:\n    host: 10.0.0.9\n    port: 3308\n"
    )
    captured: dict[str, str] = {}

    def fake_wire_project(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(project=kwargs["project"], repo=None, logs=[], warnings=[], errors=[])

    monkeypatch.setattr("dotbrain.cli.workflows.wire_project", fake_wire_project)

    result = runner.invoke(app, ["wire", "--no-repo", "--project", "demo"])

    assert result.exit_code == 0, result.output
    assert captured["server_host"] == "10.0.0.9"
    assert captured["server_port"] == "3308"
    assert captured["server_user"] == "beads"  # built-in default


def test_wire_passes_explicit_beads_remote(
    dotbrain_home: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("DOTBRAIN_HOME", str(dotbrain_home))
    captured: dict[str, str] = {}

    def fake_wire_project(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(project=kwargs["project"], repo=None, logs=[], warnings=[], errors=[])

    monkeypatch.setattr("dotbrain.cli.workflows.wire_project", fake_wire_project)

    result = runner.invoke(
        app,
        ["wire", "--no-repo", "--project", "demo",
         "--remote", "https://example.com/beads"],
    )

    assert result.exit_code == 0, result.output
    assert captured["remote"] == "https://example.com/beads"


def test_bootstrap_links_global_only(
    dotbrain_home: Path, brainspace: Path, monkeypatch: pytest.MonkeyPatch
):
    """Bootstrap links globals; project maintenance belongs to refresh."""
    monkeypatch.setenv("DOTBRAIN_HOME", str(dotbrain_home))
    calls: list[tuple[str, Path, str]] = []

    monkeypatch.setattr(
        bootstrap_mod,
        "link_global_skills",
        lambda root, target: (calls.append(("global", root, target)) or bootstrap_mod.GlobalSkillBootstrapResult()),
    )
    monkeypatch.setattr(
        bootstrap_mod,
        "link_global_subagents",
        lambda root, target: (calls.append(("global-agent", root, target)) or bootstrap_mod.GlobalSkillBootstrapResult()),
    )
    project_before = sorted(str(path.relative_to(brainspace)) for path in brainspace.rglob("*"))

    result = runner.invoke(app, ["bootstrap"])
    assert result.exit_code == 0, result.output
    assert calls == [("global", dotbrain_home, "all"), ("global-agent", dotbrain_home, "all")]
    assert sorted(str(path.relative_to(brainspace)) for path in brainspace.rglob("*")) == project_before


def test_bootstrap_skills_renders_symlink_privilege_failure(
    dotbrain_home: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("DOTBRAIN_HOME", str(dotbrain_home))
    monkeypatch.setattr(
        bootstrap_mod,
        "link_global_skills",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("enable Developer Mode")),
    )

    result = runner.invoke(app, ["bootstrap"])

    assert result.exit_code != 0
    assert "enable Developer Mode" in result.output
    assert "global: linked" not in result.output


def test_bootstrap_rejects_project_reconciliation_scopes(
    dotbrain_home: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("DOTBRAIN_HOME", str(dotbrain_home))

    for scope in ("repos", "beads"):
        result = runner.invoke(app, ["bootstrap", "--only", scope])
        assert result.exit_code != 0
        assert "No such option: --only" in result.output

def test_unwire_removes_symlinks_and_cleans_repo(
    dotbrain_home: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    monkeypatch.setenv("DOTBRAIN_HOME", str(dotbrain_home))

    # Set up a wired adopter repo.
    repo = tmp_path / "myprojrepo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=repo, check=True)

    brainspace = dotbrain_home / "brainspaces" / "myprojrepo"
    for link in paths.BRAINSPACE_LINKS:
        (brainspace / link).mkdir(parents=True)
        (repo / link).symlink_to(brainspace / link)

    exclude = repo / ".git" / "info" / "exclude"
    exclude.parent.mkdir(exist_ok=True)
    exclude.write_text("\n".join(paths.EXCLUDE_ENTRIES) + "\n")

    agents = repo / "AGENTS.md"
    agents.write_text(f"# Context\n\n{paths.ADOPTER_POINTER}\n")

    result = runner.invoke(app, ["unwire", "--repo", str(repo)])

    assert result.exit_code == 0, result.output
    for link in paths.BRAINSPACE_LINKS:
        assert not (repo / link).exists()
    assert paths.ADOPTER_POINTER not in agents.read_text()
    for entry in paths.EXCLUDE_ENTRIES:
        assert entry not in exclude.read_text()


def _asset_checkout(brainspace: Path, checkout: Path | None = None) -> Path:
    checkout = checkout or brainspace.parent.parent / "asset-checkout"
    checkout.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "--quiet", str(checkout)], check=True)
    (checkout / ".brain").symlink_to(brainspace / ".brain", target_is_directory=True)
    (brainspace / ".repo").write_text(str(checkout), encoding="utf-8")
    return checkout


def test_skills_link_project_native(
    dotbrain_home: Path, brainspace: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("DOTBRAIN_HOME", str(dotbrain_home))
    _asset_checkout(brainspace)
    result = runner.invoke(app, ["skills", "link", "--project", "example"])
    assert result.exit_code == 0, result.output
    assert not (brainspace / ".claude" / "skills" / "operate-execution").exists()
    assert not (brainspace / ".codex" / "skills" / "triage-public").exists()


def test_agents_link_project_native(dotbrain_home: Path, brainspace: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DOTBRAIN_HOME", str(dotbrain_home))
    (brainspace / ".brain" / "project.yaml").write_text(
        "agents:\n"
        "  - claude\n"
        "  - codex\n"
        "subagents:\n"
        "  - reviewer\n"
    )

    checkout = _asset_checkout(brainspace)
    result = runner.invoke(app, ["agents", "link", "--project", "example"])

    assert result.exit_code == 0, result.output
    assert (checkout / ".claude" / "agents" / "reviewer.md").is_symlink()
    assert (checkout / ".codex" / "agents" / "reviewer.toml").is_file()
    assert not (checkout / ".codex" / "agents" / "reviewer.toml").is_symlink()


def test_agents_link_repo_links_into_target_checkout(
    dotbrain_home: Path, brainspace: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """--repo links the project's assets into the given checkout (a linked worktree)
    instead of the recorded main checkout."""
    monkeypatch.setenv("DOTBRAIN_HOME", str(dotbrain_home))
    checkout = tmp_path / "worktree"
    _asset_checkout(brainspace, checkout)

    result = runner.invoke(
        app,
        ["agents", "link", "--scope", "project", "--project", "example", "--repo", str(checkout)],
    )

    assert result.exit_code == 0, result.output
    assert (checkout / ".claude" / "agents" / "verifier.md").is_symlink()
    assert (checkout / ".codex" / "agents" / "verifier.toml").is_file()
    assert not (checkout / ".codex" / "agents" / "verifier.toml").is_symlink()
    assert not (brainspace / ".codex" / "agents").exists()


def test_skills_link_repo_links_into_target_checkout(
    dotbrain_home: Path, brainspace: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("DOTBRAIN_HOME", str(dotbrain_home))
    (brainspace / ".brain" / "project.yaml").write_text(
        "agents:\n  - claude\nskills:\n  - misc/discovery-test\n"
    )
    checkout = tmp_path / "worktree"
    _asset_checkout(brainspace, checkout)

    result = runner.invoke(
        app,
        ["skills", "link", "--scope", "project", "--project", "example", "--repo", str(checkout)],
    )

    assert result.exit_code == 0, result.output
    assert (checkout / ".claude" / "skills" / "discovery-test").is_symlink()
    assert not (brainspace / ".claude" / "skills").exists()


def test_link_repo_requires_wired_checkout():
    result = runner.invoke(app, ["skills", "link", "--scope", "project", "--repo", "x"])
    assert result.exit_code != 0
    assert "failure" in result.output


def test_agents_link_global_prunes_removed_subagent(dotbrain_home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DOTBRAIN_HOME", str(dotbrain_home))
    set_fake_home(monkeypatch, tmp_path)
    bootstrap_mod.ensure_data_root(dotbrain_home)
    (dotbrain_home / "agents" / "agents.yaml").write_text("global:\n  - reviewer\n")

    first = runner.invoke(app, ["agents", "link", "--scope", "global", "--runtime", "codex"])
    assert first.exit_code == 0, first.output
    agent_file = tmp_path / ".codex" / "agents" / "reviewer.toml"
    assert agent_file.is_file() and not agent_file.is_symlink()

    (dotbrain_home / "agents" / "agents.yaml").write_text("global: []\n")
    second = runner.invoke(app, ["agents", "link", "--scope", "global", "--runtime", "codex"])

    assert second.exit_code == 0, second.output
    assert not agent_file.exists()


def test_skills_link_rejects_invalid_scope():
    result = runner.invoke(app, ["skills", "link", "--scope", "bogus"])
    assert result.exit_code != 0


def _write_global_config(dotbrain_home: Path, body: str) -> None:
    (dotbrain_home / "skills" / "skills.yaml").write_text(body)


def test_skills_link_global_renders_bootstrap_result(
    dotbrain_home: Path, fake_home: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("DOTBRAIN_HOME", str(dotbrain_home))
    set_fake_home(monkeypatch, fake_home)
    _write_global_config(
        dotbrain_home,
        "targets:\n  codex: ~/.codex/skills\nglobal_extra:\n  - misc/discovery-test\n",
    )
    result = runner.invoke(app, ["skills", "link", "--scope", "global", "--runtime", "codex"])
    assert result.exit_code == 0, result.output
    dest = fake_home / ".codex" / "skills"
    assert (dest / "discovery-test").is_symlink()   # extra


def test_skills_link_global_uses_default_targets(
    dotbrain_home: Path, fake_home: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("DOTBRAIN_HOME", str(dotbrain_home))
    set_fake_home(monkeypatch, fake_home)
    _write_global_config(dotbrain_home, "targets:\n  codex: ~/.codex/skills\n")
    result = runner.invoke(
        app, ["skills", "link", "--scope", "global", "--runtime", "claude"]
    )
    assert result.exit_code == 0, result.output
    assert (fake_home / ".claude" / "skills").is_dir()


def test_skills_link_project_filter_isolates_one_brainspace(
    dotbrain_home: Path, brainspace: Path, monkeypatch: pytest.MonkeyPatch
):
    other = dotbrain_home / "brainspaces" / "other"
    (other / ".brain" / "agents").mkdir(parents=True)
    monkeypatch.setenv("DOTBRAIN_HOME", str(dotbrain_home))

    _asset_checkout(brainspace)
    result = runner.invoke(app, ["skills", "link", "--scope", "project", "--project", "example"])
    assert result.exit_code == 0, result.output
    assert not (brainspace / ".claude" / "skills" / "operate-execution").exists()
    assert not (other / ".claude" / "skills").exists()                          # others untouched


def test_skills_link_project_filter_rejects_unknown(
    dotbrain_home: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("DOTBRAIN_HOME", str(dotbrain_home))
    result = runner.invoke(app, ["skills", "link", "--scope", "project", "--project", "nope"])
    assert result.exit_code != 0


def test_drop_beads_db_requires_yes():
    result = runner.invoke(app, ["beads", "drop-db", "brain-only"])
    assert result.exit_code == 2
    assert "requires --yes" in result.output


def test_drop_beads_db_rejected_when_no_server_configured(
    dotbrain_home: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("DOTBRAIN_HOME", str(dotbrain_home))

    result = runner.invoke(app, ["beads", "drop-db", "brain-only", "--yes"])

    assert result.exit_code != 0
    assert "no Dolt sql-server configured" in result.output


def test_drop_beads_db_forwards_options(dotbrain_home: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DOTBRAIN_HOME", str(dotbrain_home))
    captured = {}

    def fake_drop(name, **kwargs):
        captured["name"] = name
        captured.update(kwargs)
        return "dropped remote beads database: brain-only"

    monkeypatch.setattr("dotbrain.cli.beads_mod.drop_remote_beads_database", fake_drop)

    result = runner.invoke(
        app,
        [
            "beads", "drop-db", "brain-only", "--yes",
            "--ssh-host", "ssh-hop",
            "--server-host", "10.0.0.9",
            "--server-port", "3399",
            "--server-user", "robot",
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured["name"] == "brain-only"
    assert captured["ssh_host"] == "ssh-hop"
    assert captured["server_host"] == "10.0.0.9"
    assert captured["server_port"] == "3399"
    assert captured["server_user"] == "robot"
    assert captured["dry_run"] is False


def test_list_beads_db_prints_rows(dotbrain_home: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DOTBRAIN_HOME", str(dotbrain_home))
    monkeypatch.setattr(
        "dotbrain.cli.beads_mod.list_remote_beads_databases",
        lambda **kwargs: ["dotbrain", "example"],
    )

    result = runner.invoke(app, ["beads", "list-db", "--server-host", "10.0.0.9"])

    assert result.exit_code == 0, result.output
    assert "dotbrain" in result.output
    assert "example" in result.output


def test_wire_all_is_rejected_before_workflows(dotbrain_home: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DOTBRAIN_HOME", str(dotbrain_home))
    called = {}

    def fake_wire(root, **kwargs):
        called["root"] = root
        called.update(kwargs)
        return SimpleNamespace(logs=["wired proj-a"], warnings=["skipped proj-b"])

    monkeypatch.setattr("dotbrain.cli.workflows.wire_project", fake_wire)

    result = runner.invoke(app, ["wire", "--all"])

    assert result.exit_code == 2
    assert "No such option: --all" in result.output
    assert called == {}


def test_wire_all_rejects_single_project_flags(
    dotbrain_home: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("DOTBRAIN_HOME", str(dotbrain_home))
    result = runner.invoke(app, ["wire", "--all", "--repo", "/tmp/x"])
    assert result.exit_code != 0
    assert "No such option: --all" in result.output


def test_wire_renders_symlink_privilege_failure(
    dotbrain_home: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("DOTBRAIN_HOME", str(dotbrain_home))
    monkeypatch.setattr(
        "dotbrain.cli.workflows.wire_project",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("enable Developer Mode")),
    )

    result = runner.invoke(app, ["wire", "--no-repo", "--project", "demo"])

    assert result.exit_code != 0
    assert "enable Developer Mode" in result.output
    assert "wired" not in result.output


def test_skills_link_renders_symlink_privilege_failure(
    dotbrain_home: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("DOTBRAIN_HOME", str(dotbrain_home))
    monkeypatch.setattr(
        "dotbrain.assets.link_global",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("enable Developer Mode")),
    )

    result = runner.invoke(
        app, ["skills", "link", "--scope", "global", "--runtime", "codex"]
    )

    assert result.exit_code != 0
    assert "enable Developer Mode" in result.output
    assert "global: linked" not in result.output


def test_refresh_delegates_and_echoes(
    dotbrain_home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("DOTBRAIN_HOME", str(dotbrain_home))
    called = {}

    def fake_refresh(root, **kwargs):
        called["root"] = root
        called.update(kwargs)
        from dotbrain.results import TargetResult
        return SimpleNamespace(errors=[], targets=[TargetResult(project="demo", changes=["updated convention"],
                               findings=[{"severity": "advisory", "message": "shared Brain"}])])

    monkeypatch.setattr("dotbrain.cli.workflows.refresh_projects", fake_refresh)

    result = runner.invoke(
        app,
        ["refresh", "--project", "demo", "--runtime", "codex"],
    )

    assert result.exit_code == 0, result.output
    assert called["root"] == dotbrain_home
    assert called["project"] == "demo"
    assert called["runtime"] == "codex"
    assert "updated convention" in result.output
    assert "shared Brain" in result.output


def test_refresh_all_delegates_to_projects(
    dotbrain_home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("DOTBRAIN_HOME", str(dotbrain_home))
    called = {}

    def fake_refresh(root, **kwargs):
        called["root"] = root
        called.update(kwargs)
        return SimpleNamespace(errors=[], targets=[])

    monkeypatch.setattr("dotbrain.cli.workflows.refresh_projects", fake_refresh)

    result = runner.invoke(app, ["refresh", "--all"])

    assert result.exit_code == 0, result.output
    assert called["root"] == dotbrain_home
    assert called["all_projects"] is True
    assert "refresh: success" in result.output


def test_refresh_outside_wired_checkout_requires_selection(dotbrain_home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DOTBRAIN_HOME", str(dotbrain_home))
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["refresh"])
    assert result.exit_code == 2
    assert "select --project" in result.output


def test_unwire_all_delegates_without_retired_preview(dotbrain_home: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DOTBRAIN_HOME", str(dotbrain_home))
    called = {}

    def fake_unwire_all(root, **kwargs):
        called["root"] = root
        called.update(kwargs)
        return [SimpleNamespace(project="proj-a", repo=None, logs=["removed symlink .brain"], warnings=[], errors=[])]

    monkeypatch.setattr("dotbrain.cli.workflows.unwire_all_projects", fake_unwire_all)

    result = runner.invoke(app, ["unwire", "--all", "--dry-run"])
    assert result.exit_code == 2
    assert "No such option: --dry-run" in result.output
    assert called == {}

    result = runner.invoke(app, ["unwire", "--all"])
    assert result.exit_code == 0, result.output
    assert called == {"root": dotbrain_home}
    assert "proj-a: success" in result.output
    assert "removed symlink .brain" in result.output


def test_unwire_all_rejects_destructive_flags(
    dotbrain_home: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("DOTBRAIN_HOME", str(dotbrain_home))
    result = runner.invoke(app, ["unwire", "--all", "--archive"])
    assert result.exit_code != 0
    assert "archive" in result.output.lower()

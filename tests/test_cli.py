"""Smoke tests for the Typer command surface."""

from __future__ import annotations

import subprocess
from types import SimpleNamespace
from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

from dotbrain import bootstrap as bootstrap_mod, migrate, paths
from dotbrain import cli
from dotbrain.cli import app

from conftest import set_fake_home

runner = CliRunner()


def test_help_lists_command_tree():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for command in ("bootstrap", "wire", "refresh", "unwire", "beads", "codex", "skills", "agents"):
        assert command in result.output
    for hidden_command in ("migrate-beads", "list-beads-db", "drop-beads-db", "worktrees"):
        assert hidden_command not in result.output


def test_skills_help_hides_low_value_discovery_command():
    result = runner.invoke(app, ["skills", "--help"])
    assert result.exit_code == 0
    assert "link" in result.output
    assert "list" not in result.output


def test_agents_help_hides_low_value_discovery_command():
    result = runner.invoke(app, ["agents", "--help"])
    assert result.exit_code == 0
    assert "link" in result.output
    assert "list" not in result.output


def test_wire_help_makes_global_hook_install_opt_in():
    result = runner.invoke(app, ["wire", "--help"])
    assert result.exit_code == 0
    assert "--install-global-hook" in result.output
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
        app, ["beads", "migrate", "--name", "demo", "--beads-server-host", "h", "--dry-run"]
    )
    assert result.exit_code == 0, result.output
    assert "planned bd sequence" in result.output
    assert "--reinit-local" in result.output


def test_migrate_beads_requires_server_host(
    dotbrain_home: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("DOTBRAIN_HOME", str(dotbrain_home))
    result = runner.invoke(app, ["beads", "migrate", "--name", "demo", "--dry-run"])
    assert result.exit_code != 0


def test_migrate_beads_exits_nonzero_on_verification_failure(
    dotbrain_home: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("DOTBRAIN_HOME", str(dotbrain_home))

    def fake_migrate_project(**kwargs):
        return migrate.MigrationResult(
            project=kwargs["project"],
            status="aborted-count-mismatch",
            warnings=["demo: restored issue count mismatch"],
        )

    monkeypatch.setattr(migrate, "migrate_project", fake_migrate_project)

    result = runner.invoke(app, ["beads", "migrate", "--name", "demo", "--beads-server-host", "h"])

    assert result.exit_code == 1
    assert "warning: demo: restored issue count mismatch" in result.output


def test_migrate_beads_exits_nonzero_when_unverified(
    dotbrain_home: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("DOTBRAIN_HOME", str(dotbrain_home))

    def fake_migrate_project(**kwargs):
        return migrate.MigrationResult(
            project=kwargs["project"],
            status="migrated-unverified",
            warnings=["demo: could not verify issue count"],
        )

    monkeypatch.setattr(migrate, "migrate_project", fake_migrate_project)
    result = runner.invoke(app, ["beads", "migrate", "--name", "demo", "--beads-server-host", "h"])
    assert result.exit_code == 1


def test_wire_brain_only_creates_brainspace(
    dotbrain_home: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("DOTBRAIN_HOME", str(dotbrain_home))
    result = runner.invoke(
        app, ["wire", "--no-repo", "--name", "demo", "--skip-beads"]
    )
    assert result.exit_code == 0, result.output
    assert "run `dotbrain bootstrap --only claude-hook` if needed" in result.output
    brainspace = dotbrain_home / "brainspaces" / "demo"
    assert (brainspace / ".repo").read_text() == "(brain-only)\n"
    assert (brainspace / ".brain" / "AGENTS.md").is_file()


def test_wire_no_repo_requires_name(
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
        return SimpleNamespace(logs=[], warnings=[])

    monkeypatch.setattr("dotbrain.cli.workflows.wire_project", fake_wire_project)

    result = runner.invoke(app, ["wire", "--no-repo", "--name", "demo"])

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
        return SimpleNamespace(logs=[], warnings=[])

    monkeypatch.setattr("dotbrain.cli.workflows.wire_project", fake_wire_project)

    result = runner.invoke(
        app,
        ["wire", "--no-repo", "--name", "demo",
         "--beads-remote", "https://example.com/beads"],
    )

    assert result.exit_code == 0, result.output
    assert captured["remote"] == "https://example.com/beads"


def test_bootstrap_only_claude_hook_writes_settings(
    dotbrain_home: Path, fake_home: Path, monkeypatch: pytest.MonkeyPatch
):
    """--only claude-hook writes the SessionStart hook to settings.json via Python."""
    monkeypatch.setenv("DOTBRAIN_HOME", str(dotbrain_home))
    monkeypatch.setattr("dotbrain.bootstrap.Path.home", staticmethod(lambda: fake_home))
    result = runner.invoke(app, ["bootstrap", "--only", "claude-hook"],
                           env={"DOTBRAIN_HOME": str(dotbrain_home)})
    assert result.exit_code == 0, result.output
    assert "[bootstrap] installed Claude" in result.output


def test_bootstrap_only_skills_links_global_only(
    dotbrain_home: Path, brainspace: Path, monkeypatch: pytest.MonkeyPatch
):
    """--only skills links global skills only; project skills belong to refresh."""
    monkeypatch.setenv("DOTBRAIN_HOME", str(dotbrain_home))
    calls: list[tuple[str, Path, str]] = []

    monkeypatch.setattr(
        cli,
        "_render_global_skill_link",
        lambda root, target: calls.append(("global", root, target)),
    )
    monkeypatch.setattr(
        cli,
        "_render_global_agent_link",
        lambda root, target: calls.append(("global-agent", root, target)),
    )
    monkeypatch.setattr(
        cli,
        "_link_projects_native",
        lambda root, target, project: calls.append(("project", root, target)),
    )

    result = runner.invoke(app, ["bootstrap", "--only", "skills"])
    assert result.exit_code == 0, result.output
    assert calls == [("global", dotbrain_home, "all"), ("global-agent", dotbrain_home, "all")]


def test_bootstrap_skills_renders_symlink_privilege_failure(
    dotbrain_home: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("DOTBRAIN_HOME", str(dotbrain_home))
    monkeypatch.setattr(
        cli,
        "_render_global_skill_link",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("enable Developer Mode")),
    )

    result = runner.invoke(app, ["bootstrap", "--only", "skills"])

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
        assert "invalid --only" in result.output

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


def test_bootstrap_hook_command_uses_home_literal(dotbrain_home: Path, fake_home: Path):
    """_global_hook_command uses the literal $HOME form when root is the default location."""
    from dotbrain.bootstrap import _global_hook_command
    default_root = fake_home / "dotbrain"
    default_root.mkdir(parents=True, exist_ok=True)
    cmd = _global_hook_command("claude-worktree-bootstrap.sh", default_root, fake_home)
    assert cmd == "dotbrain hook claude-worktree-bootstrap"

    other_root = fake_home / "other" / "dotbrain"
    cmd2 = _global_hook_command("claude-worktree-bootstrap.sh", other_root, fake_home)
    assert "$HOME" not in cmd2
    assert cmd2 == "dotbrain hook claude-worktree-bootstrap"


def test_skills_link_project_native(
    dotbrain_home: Path, brainspace: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("DOTBRAIN_HOME", str(dotbrain_home))
    result = runner.invoke(app, ["skills", "link", "--scope", "project"])
    assert result.exit_code == 0, result.output
    assert (brainspace / ".claude" / "skills" / "operate-execution").is_symlink()
    assert (brainspace / ".codex" / "skills" / "triage-public").is_symlink()


def test_agents_link_project_native(dotbrain_home: Path, brainspace: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DOTBRAIN_HOME", str(dotbrain_home))
    (brainspace / "project.yaml").write_text(
        "agents:\n"
        "  - claude\n"
        "  - codex\n"
        "subagents:\n"
        "  - reviewer\n"
    )

    result = runner.invoke(app, ["agents", "link", "--scope", "project"])

    assert result.exit_code == 0, result.output
    assert (brainspace / ".claude" / "agents" / "reviewer.md").is_symlink()
    assert (brainspace / ".codex" / "agents" / "reviewer.toml").is_symlink()


def test_agents_link_global_prunes_removed_subagent(dotbrain_home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DOTBRAIN_HOME", str(dotbrain_home))
    set_fake_home(monkeypatch, tmp_path)
    bootstrap_mod.ensure_data_root(dotbrain_home)
    (dotbrain_home / "agents" / "agents.yaml").write_text("global:\n  - reviewer\n")

    first = runner.invoke(app, ["agents", "link", "--scope", "global", "--target", "codex"])
    assert first.exit_code == 0, first.output
    agent_file = tmp_path / ".codex" / "agents" / "reviewer.toml"
    assert agent_file.is_symlink()

    (dotbrain_home / "agents" / "agents.yaml").write_text("global: []\n")
    second = runner.invoke(app, ["agents", "link", "--scope", "global", "--target", "codex"])

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
    result = runner.invoke(app, ["skills", "link", "--scope", "global", "--target", "codex"])
    assert result.exit_code == 0, result.output
    dest = fake_home / ".codex" / "skills"
    assert (dest / "wire-brain").is_symlink()       # baseline
    assert (dest / "discovery-test").is_symlink()   # extra


def test_skills_link_global_uses_default_targets(
    dotbrain_home: Path, fake_home: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("DOTBRAIN_HOME", str(dotbrain_home))
    set_fake_home(monkeypatch, fake_home)
    _write_global_config(dotbrain_home, "targets:\n  codex: ~/.codex/skills\n")
    result = runner.invoke(
        app, ["skills", "link", "--scope", "global", "--target", "claude-code"]
    )
    assert result.exit_code == 0, result.output
    assert (fake_home / ".claude" / "skills" / "wire-brain").is_symlink()


def test_skills_link_project_filter_isolates_one_brainspace(
    dotbrain_home: Path, brainspace: Path, monkeypatch: pytest.MonkeyPatch
):
    other = dotbrain_home / "brainspaces" / "other"
    (other / ".brain" / "agents").mkdir(parents=True)
    monkeypatch.setenv("DOTBRAIN_HOME", str(dotbrain_home))

    result = runner.invoke(app, ["skills", "link", "--scope", "project", "--project", "example"])
    assert result.exit_code == 0, result.output
    assert (brainspace / ".claude" / "skills" / "operate-execution").is_symlink()  # named project linked
    assert not (other / ".claude" / "skills").exists()                          # others untouched


def test_skills_link_project_filter_rejects_unknown(
    dotbrain_home: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("DOTBRAIN_HOME", str(dotbrain_home))
    result = runner.invoke(app, ["skills", "link", "--scope", "project", "--project", "nope"])
    assert result.exit_code != 0


def test_codex_prints_worktree_commands(disconnected_adopter_repo: Path):
    result = runner.invoke(
        app,
        [
            "codex",
            "--worktree",
            "scaffold blog",
            "--repo",
            str(disconnected_adopter_repo),
            "--base",
            "develop",
            "--codex-arg=--sandbox",
            "--codex-arg=workspace-write",
            "--prompt",
            "start here",
            "--print",
        ],
    )

    assert result.exit_code == 0, result.output
    worktree = disconnected_adopter_repo.parent / "worktrees" / "scaffold-blog"
    assert f"git worktree add -b scaffold-blog {worktree} develop" in result.output
    assert (
        f"codex -C {worktree} --sandbox workspace-write 'start here'"
        in result.output
    )


def test_codex_wires_worktree_before_launch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    worktree = repo.parent / "worktrees" / "feature"
    plan = SimpleNamespace(
        repo=repo,
        worktree=worktree,
        create_command=("git", "worktree", "add"),
        codex_command=("codex", "-C", str(worktree)),
    )
    calls: list[tuple[str, object]] = []

    monkeypatch.setattr(cli.worktrees, "repo_root", lambda path: repo)
    monkeypatch.setattr(cli.worktrees, "codex_worktree_plan", lambda *args, **kwargs: plan)
    monkeypatch.setattr(
        cli.worktrees,
        "create_codex_worktree",
        lambda got_plan: calls.append(("create", got_plan)),
    )
    monkeypatch.setattr(
        cli.adopter_repos,
        "reconcile_worktree",
        lambda got_path: calls.append(("wire", got_path)) or cli.adopter_repos.ReconcileResult(),
    )
    monkeypatch.setattr(
        cli.worktrees,
        "launch_codex",
        lambda got_plan: calls.append(("launch", got_plan)),
    )

    result = runner.invoke(app, ["codex", "--worktree", "feature", "--repo", str(repo)])

    assert result.exit_code == 0, result.output
    assert calls == [("create", plan), ("wire", worktree), ("launch", plan)]


# NOTE: The intake→beads flow (triage-public skill reading issue-tracker.md, calling gh CLI,
# recording issues into beads) is manual-only. It requires a live GitHub repo, gh auth, and
# a running beads database. Covered by the manual test checklist in
# projects/dotbrain/.brain/docs/adopter-guide.md scenario 3.


def test_drop_beads_db_requires_yes():
    with pytest.raises(typer.BadParameter, match=r"requires --yes"):
        cli.drop_beads_db("brain-only", False, False, None, None, None, None)


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
            "--beads-ssh-host", "ssh-hop",
            "--beads-server-host", "10.0.0.9",
            "--beads-server-port", "3399",
            "--beads-server-user", "robot",
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

    result = runner.invoke(app, ["beads", "list-db", "--beads-server-host", "10.0.0.9"])

    assert result.exit_code == 0, result.output
    assert "dotbrain" in result.output
    assert "example" in result.output


def test_wire_all_delegates_and_echoes(dotbrain_home: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DOTBRAIN_HOME", str(dotbrain_home))
    called = {}

    def fake_wire_all(root, **kwargs):
        called["root"] = root
        called.update(kwargs)
        return SimpleNamespace(logs=["wired proj-a"], warnings=["skipped proj-b"])

    monkeypatch.setattr("dotbrain.cli.workflows.wire_all_projects", fake_wire_all)

    result = runner.invoke(app, ["wire", "--all"])

    assert result.exit_code == 0, result.output
    assert "root" in called
    assert "wired proj-a" in result.output


def test_wire_all_rejects_single_project_flags(
    dotbrain_home: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("DOTBRAIN_HOME", str(dotbrain_home))
    result = runner.invoke(app, ["wire", "--all", "--repo", "/tmp/x"])
    assert result.exit_code != 0
    assert "mutually exclusive" in result.output


def test_wire_all_renders_symlink_privilege_failure(
    dotbrain_home: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("DOTBRAIN_HOME", str(dotbrain_home))
    monkeypatch.setattr(
        "dotbrain.cli.workflows.wire_all_projects",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("enable Developer Mode")),
    )

    result = runner.invoke(app, ["wire", "--all"])

    assert result.exit_code != 0
    assert "enable Developer Mode" in result.output
    assert "wired" not in result.output


def test_skills_link_renders_symlink_privilege_failure(
    dotbrain_home: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("DOTBRAIN_HOME", str(dotbrain_home))
    monkeypatch.setattr(
        "dotbrain.cli._render_global_skill_link",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("enable Developer Mode")),
    )

    result = runner.invoke(
        app, ["skills", "link", "--scope", "global", "--target", "codex"]
    )

    assert result.exit_code != 0
    assert "enable Developer Mode" in result.output
    assert "global: linked" not in result.output


def test_refresh_delegates_and_echoes(
    dotbrain_home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("DOTBRAIN_HOME", str(dotbrain_home))
    called = {}

    def fake_refresh(root, project, **kwargs):
        called["root"] = root
        called["project"] = project
        called.update(kwargs)
        return SimpleNamespace(logs=["refreshed demo"], warnings=["missing repo"])

    monkeypatch.setattr("dotbrain.cli.workflows.refresh_project", fake_refresh)

    result = runner.invoke(
        app,
        ["refresh", "--name", "demo", "--repo-base", str(tmp_path)],
    )

    assert result.exit_code == 0, result.output
    assert called["root"] == dotbrain_home
    assert called["project"] == "demo"
    assert called["repo_base"] == tmp_path
    assert "[refresh] refreshed demo" in result.output
    assert "[refresh] warning: missing repo" in result.stderr


def test_refresh_all_delegates_to_projects(
    dotbrain_home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("DOTBRAIN_HOME", str(dotbrain_home))
    called = {}

    def fake_refresh(root, **kwargs):
        called["root"] = root
        called.update(kwargs)
        return SimpleNamespace(logs=["refreshed all"], warnings=[])

    monkeypatch.setattr("dotbrain.cli.workflows.refresh_projects", fake_refresh)

    result = runner.invoke(app, ["refresh", "--all", "--repo-base", str(tmp_path)])

    assert result.exit_code == 0, result.output
    assert called["root"] == dotbrain_home
    assert called["repo_base"] == tmp_path
    assert "[refresh] refreshed all" in result.output


def test_refresh_requires_scope(dotbrain_home: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DOTBRAIN_HOME", str(dotbrain_home))
    result = runner.invoke(app, ["refresh"])
    assert result.exit_code != 0
    assert "use --all or --name" in result.output


def test_unwire_all_delegates_with_dry_run(dotbrain_home: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DOTBRAIN_HOME", str(dotbrain_home))
    called = {}

    def fake_unwire_all(**kwargs):
        called.update(kwargs)
        return [SimpleNamespace(project="proj-a", logs=["would remove symlink .brain"], warnings=[])]

    monkeypatch.setattr("dotbrain.cli.workflows.unwire_all_projects", fake_unwire_all)

    result = runner.invoke(app, ["unwire", "--all", "--dry-run"])

    assert result.exit_code == 0, result.output
    assert called.get("dry_run") is True
    assert "[proj-a]" in result.output


def test_unwire_all_rejects_destructive_flags(
    dotbrain_home: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("DOTBRAIN_HOME", str(dotbrain_home))
    result = runner.invoke(app, ["unwire", "--all", "--archive"])
    assert result.exit_code != 0
    assert "archive" in result.output.lower()

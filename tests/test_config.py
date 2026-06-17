"""Tests for config.yaml + project.yaml config store (ADR-0030)."""

from __future__ import annotations

import textwrap
from pathlib import Path

from dotbrain import config


# --------------------------------------------------------------------------- load_config (config.yaml)


def test_load_config_returns_defaults_when_file_absent(tmp_path: Path):
    cfg = config.load_config(tmp_path)
    assert cfg.beads_server.host == ""
    assert cfg.beads_server.port == "3307"
    assert cfg.beads_server.user == "beads"
    assert cfg.beads_server.ssh_host == ""


def test_load_config_parses_beads_server(tmp_path: Path):
    (tmp_path / "config.yaml").write_text(textwrap.dedent("""\
        version: 3
        beads:
          server:
            host: 10.0.0.1
            port: 3308
            user: myuser
            ssh_host: ssh-hop
    """))
    cfg = config.load_config(tmp_path)
    assert cfg.beads_server.host == "10.0.0.1"
    assert cfg.beads_server.port == "3308"
    assert cfg.beads_server.user == "myuser"
    assert cfg.beads_server.ssh_host == "ssh-hop"


def test_load_config_partial_server_block_uses_defaults(tmp_path: Path):
    (tmp_path / "config.yaml").write_text(
        "version: 3\nbeads:\n  server:\n    host: 10.0.0.2\n"
    )
    cfg = config.load_config(tmp_path)
    assert cfg.beads_server.host == "10.0.0.2"
    assert cfg.beads_server.port == "3307"  # default
    assert cfg.beads_server.user == "beads"  # default


def test_load_config_empty_file_returns_defaults(tmp_path: Path):
    (tmp_path / "config.yaml").write_text("")
    cfg = config.load_config(tmp_path)
    assert cfg.beads_server.host == ""


def test_load_config_falls_back_to_old_format(tmp_path: Path):
    (tmp_path / "dotbrain.yaml").write_text(textwrap.dedent("""\
        version: 2
        beads:
          server:
            host: 10.0.0.5
            port: 3309
            user: olduser
    """))
    cfg = config.load_config(tmp_path)
    assert cfg.beads_server.host == "10.0.0.5"
    assert cfg.beads_server.user == "olduser"


# --------------------------------------------------------------------------- load_project_config


def test_load_project_config_defaults(tmp_path: Path):
    beads = config.load_project_config(tmp_path, "acme")
    assert beads.mode == "embedded"
    assert beads.database == "acme"
    assert beads.remote == ""


def test_load_project_config_reads_project_yaml(tmp_path: Path):
    project_dir = tmp_path / "projects" / "fork"
    project_dir.mkdir(parents=True)
    (project_dir / "project.yaml").write_text(textwrap.dedent("""\
        beads:
          mode: embedded
          remote: https://example.com/fork
    """))
    beads = config.load_project_config(tmp_path, "fork")
    assert beads.mode == "embedded"
    assert beads.remote == "https://example.com/fork"
    assert beads.database == "fork"  # default


def test_load_project_config_custom_database(tmp_path: Path):
    project_dir = tmp_path / "projects" / "renamed"
    project_dir.mkdir(parents=True)
    (project_dir / "project.yaml").write_text(textwrap.dedent("""\
        beads:
          database: legacy_name
    """))
    beads = config.load_project_config(tmp_path, "renamed")
    assert beads.mode == "embedded"
    assert beads.database == "legacy_name"


def test_load_project_config_falls_back_to_old_format(tmp_path: Path):
    (tmp_path / "dotbrain.yaml").write_text(textwrap.dedent("""\
        version: 2
        projects:
          acme:
            beads:
              mode: none
          fork:
            beads:
              mode: embedded
              remote: https://example.com/fork
          renamed:
            beads:
              database: legacy_name
    """))
    assert config.load_project_config(tmp_path, "acme").mode == "none"
    assert config.load_project_config(tmp_path, "fork").mode == "embedded"
    assert config.load_project_config(tmp_path, "fork").remote == "https://example.com/fork"
    assert config.load_project_config(tmp_path, "renamed").database == "legacy_name"


# --------------------------------------------------------------------------- config-driven default mode


def _config_yaml(tmp_path: Path, host: str) -> None:
    (tmp_path / "config.yaml").write_text(f"version: 3\nbeads:\n  server:\n    host: {host}\n")


def test_default_beads_mode_is_embedded_without_server(tmp_path: Path):
    assert config.default_beads_mode(tmp_path) == "embedded"


def test_default_beads_mode_follows_configured_server(tmp_path: Path):
    _config_yaml(tmp_path, "10.0.0.1")
    assert config.default_beads_mode(tmp_path) == "server"


def test_project_inherits_server_default_when_configured(tmp_path: Path):
    _config_yaml(tmp_path, "10.0.0.1")
    # No project.yaml -> the project inherits the configured shared server.
    assert config.load_project_config(tmp_path, "acme").mode == "server"


def test_project_can_pin_embedded_against_server_default(tmp_path: Path):
    _config_yaml(tmp_path, "10.0.0.1")
    _project_yaml(tmp_path, "acme", "beads:\n  mode: embedded\n")
    assert config.load_project_config(tmp_path, "acme").mode == "embedded"


def test_record_skips_when_mode_matches_server_default(tmp_path: Path):
    _config_yaml(tmp_path, "10.0.0.1")
    # server is the default here, so recording server is not a deviation -> no file.
    assert config.record_project_beads(tmp_path, "acme", config.ProjectBeads(mode="server")) is None
    assert not (tmp_path / "projects" / "acme" / "project.yaml").exists()


def test_record_writes_embedded_optout_against_server_default(tmp_path: Path):
    _config_yaml(tmp_path, "10.0.0.1")
    log = config.record_project_beads(tmp_path, "acme", config.ProjectBeads(mode="embedded"))
    assert log is not None
    assert config.load_project_config(tmp_path, "acme").mode == "embedded"


# --------------------------------------------------------------------------- write_project_config


def test_write_project_config_creates_file(tmp_path: Path):
    log = config.write_project_config(
        tmp_path, "fork",
        config.ProjectBeads(mode="embedded", remote="https://example.com/fork"),
    )
    assert log is not None
    path = tmp_path / "projects" / "fork" / "project.yaml"
    assert path.is_file()
    text = path.read_text()
    assert "mode: embedded" in text
    assert "remote: https://example.com/fork" in text


def test_write_project_config_idempotent(tmp_path: Path):
    log1 = config.write_project_config(
        tmp_path, "fork",
        config.ProjectBeads(mode="embedded", remote="https://example.com/fork"),
    )
    assert log1 is not None
    log2 = config.write_project_config(
        tmp_path, "fork",
        config.ProjectBeads(mode="embedded", remote="https://example.com/fork"),
    )
    assert log2 is None


def test_write_project_config_skips_defaults(tmp_path: Path):
    log = config.write_project_config(tmp_path, "plain", config.ProjectBeads())
    assert log is None


# --------------------------------------------------------------------------- record_project_beads / remove_project_beads


def test_record_project_beads_delegates_to_project_yaml(tmp_path: Path):
    log = config.record_project_beads(
        tmp_path, "fork",
        config.ProjectBeads(mode="embedded", remote="https://example.com/fork"),
    )
    assert log is not None
    assert (tmp_path / "projects" / "fork" / "project.yaml").is_file()


def test_record_project_beads_skips_non_deviations(tmp_path: Path):
    assert config.record_project_beads(tmp_path, "plain", config.ProjectBeads()) is None
    assert config.record_project_beads(
        tmp_path, "plain", config.ProjectBeads(database="plain")
    ) is None
    assert not (tmp_path / "projects" / "plain" / "project.yaml").exists()


def test_record_project_beads_does_not_retract_manual_declaration(tmp_path: Path):
    # If the project already has a manual mode declaration (e.g. mode: none),
    # a "default" wire call must not overwrite it.
    config.write_project_config(
        tmp_path, "brain-only", config.ProjectBeads(mode="none"),
    )
    config.record_project_beads(tmp_path, "brain-only", config.ProjectBeads())
    assert config.load_project_config(tmp_path, "brain-only").mode == "none"


def test_remove_project_beads_deletes_file(tmp_path: Path):
    config.write_project_config(
        tmp_path, "fork", config.ProjectBeads(mode="embedded", remote="https://example.com/fork"),
    )
    log = config.remove_project_beads(tmp_path, "fork")
    assert log is not None
    assert not (tmp_path / "projects" / "fork" / "project.yaml").exists()
    assert config.remove_project_beads(tmp_path, "fork") is None  # already gone


# --------------------------------------------------------------------------- per-project skills


def _project_yaml(tmp_path: Path, name: str, body: str) -> Path:
    path = tmp_path / "projects" / name / "project.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body)
    return path


def _legacy_manifest(tmp_path: Path, name: str, body: str) -> Path:
    path = tmp_path / "projects" / name / ".brain" / "agents" / "skills.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body)
    return path


def test_load_project_skills_missing_file_is_empty(tmp_path: Path):
    assert config.load_project_skills(tmp_path, "ghost") == ()


def test_load_project_skills_reads_list(tmp_path: Path):
    _project_yaml(tmp_path, "p", "skills:\n  - misc/x\n  - misc/y\n")
    assert config.load_project_skills(tmp_path, "p") == ("misc/x", "misc/y")


def test_load_project_skills_excludes_required_core(tmp_path: Path):
    _project_yaml(tmp_path, "p", "skills:\n  - brain/operate-beads\n  - misc/x\n")
    assert config.load_project_skills(tmp_path, "p") == ("misc/x",)


def test_migrate_legacy_manifest_absent_is_noop(tmp_path: Path):
    assert config.migrate_legacy_skill_manifest(tmp_path, "p") is None


def test_migrate_legacy_manifest_empty_just_removes_file(tmp_path: Path):
    legacy = _legacy_manifest(tmp_path, "p", "version: 1\nskills: []\n")
    log = config.migrate_legacy_skill_manifest(tmp_path, "p")
    assert log is not None
    assert not legacy.exists()
    assert config.load_project_skills(tmp_path, "p") == ()


def test_migrate_legacy_manifest_folds_extras_without_loss(tmp_path: Path):
    legacy = _legacy_manifest(tmp_path, "p", "version: 1\nskills:\n  - misc/x\n  - misc/y\n")
    config.migrate_legacy_skill_manifest(tmp_path, "p")
    assert not legacy.exists()
    assert config.load_project_skills(tmp_path, "p") == ("misc/x", "misc/y")


def test_migrate_legacy_manifest_preserves_existing_project_yaml(tmp_path: Path):
    _project_yaml(tmp_path, "p", "beads:\n  mode: embedded\nskills:\n  - misc/keep\n")
    _legacy_manifest(tmp_path, "p", "version: 1\nskills:\n  - misc/x\n")
    config.migrate_legacy_skill_manifest(tmp_path, "p")
    # Operator already owns skills: in project.yaml, so the legacy fold is a no-op there.
    assert config.load_project_skills(tmp_path, "p") == ("misc/keep",)
    assert config.load_project_config(tmp_path, "p").mode == "embedded"


def test_write_project_config_preserves_skills(tmp_path: Path):
    _project_yaml(tmp_path, "p", "skills:\n  - misc/keep\n")
    config.write_project_config(tmp_path, "p", config.ProjectBeads(mode="embedded"))
    assert config.load_project_skills(tmp_path, "p") == ("misc/keep",)
    assert config.load_project_config(tmp_path, "p").mode == "embedded"

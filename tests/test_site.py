"""Tests for the ``site`` module: settings, the published-page allowlist, Learn, and the engine run.

Everything Node-side goes through the injected runner; these tests assert on the recorded commands
and never install or run VitePress.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dotbrain import __version__, site
from dotbrain.cli import app


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture
def home(tmp_path: Path) -> Path:
    root = tmp_path / "dotbrain"
    (root / "brainspaces" / "demo" / ".brain").mkdir(parents=True)
    return root


@pytest.fixture
def brain(home: Path) -> Path:
    return (home / "brainspaces" / "demo" / ".brain").resolve()


def _settings(brain: Path, nav: str = "nav: []\n") -> None:
    _write(brain / "site" / "site.yaml", "title: Demo Brain\ndescription: Demo\n" + nav)


class FakeRun:
    """Records argv; answers `node --version`; `npm ci` creates the installed marker."""

    def __init__(self, node: str = "v22.3.0", npm_fails: bool = False):
        self.calls: list[dict] = []
        self.node = node
        self.npm_fails = npm_fails

    def __call__(self, argv, *, cwd=None, env=None, check=True):
        self.calls.append({"argv": list(argv), "cwd": cwd, "env": env})
        if argv[1:] == ["--version"]:
            if self.node is None:
                raise FileNotFoundError("node")
            return subprocess.CompletedProcess(argv, 0, stdout=self.node + "\n", stderr="")
        if argv[1:2] == ["ci"]:
            if self.npm_fails:
                raise subprocess.CalledProcessError(1, argv)
            (Path(cwd) / "node_modules" / "vitepress").mkdir(parents=True, exist_ok=True)
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    def commands(self, word: str) -> list[list[str]]:
        return [c["argv"] for c in self.calls if word in c["argv"]]


# --------------------------------------------------------------------------- locating and init


def test_find_brain_by_name_and_from_a_wired_repo(home: Path, brain: Path, tmp_path: Path):
    assert site.find_brain(home, "demo") == brain
    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True)
    (repo / ".brain").mkdir()
    assert site.find_brain(home, cwd=repo / "src") == (repo / ".brain").resolve()


def test_find_brain_explains_what_to_do(home: Path, tmp_path: Path):
    with pytest.raises(site.SiteError, match="no Brain for 'missing'"):
        site.find_brain(home, "missing")
    with pytest.raises(site.SiteError, match="pass --name"):
        site.find_brain(home, cwd=tmp_path / "nowhere")


def test_init_creates_settings_and_home_and_never_overwrites(brain: Path):
    created = site.init(brain, "Demo Brain")
    assert {p.name for p in created} == {"site.yaml", "index.md"}
    assert "title: Demo Brain" in (brain / "site" / "site.yaml").read_text(encoding="utf-8")

    (brain / "docs" / "index.md").write_text("mine\n", encoding="utf-8")
    assert site.init(brain) == []
    assert (brain / "docs" / "index.md").read_text(encoding="utf-8") == "mine\n"


# --------------------------------------------------------------------------- published pages


def test_a_brain_without_a_site_is_told_to_init(brain: Path):
    with pytest.raises(site.SiteError, match="dotbrain site init"):
        site.plan(brain)


def test_nav_is_the_allowlist(brain: Path):
    _settings(brain, "nav:\n  - text: Runbooks\n    items:\n      - { text: Release, link: runbooks/release }\n")
    _write(brain / "docs" / "index.md", "# Home\n")
    _write(brain / "docs" / "runbooks" / "release.md", "# Release\n")
    _write(brain / "docs" / "agent-only.md", "# Agent note\n")
    _write(brain / "AGENTS.md", "# Agents\n")

    result = site.plan(brain)

    assert result["published"] == ["docs/index.md", "docs/runbooks/release.md"]
    assert "docs/agent-only.md" in result["exclude"] and "AGENTS.md" in result["exclude"]
    assert result["rewrites"] == {"docs/index.md": "index.md", "docs/runbooks/release.md": "runbooks/release.md"}
    assert result["sidebar"] == [{"text": "Runbooks", "items": [{"text": "Release", "link": "/runbooks/release"}]}]


def test_a_folder_readme_is_served_as_its_index(brain: Path):
    _settings(brain, "nav:\n  - text: Deploy\n    items:\n      - { text: Overview, link: deployment/azure/ }\n")
    _write(brain / "docs" / "deployment" / "azure" / "README.md", "# Azure\n")

    result = site.plan(brain)

    assert result["rewrites"]["docs/deployment/azure/README.md"] == "deployment/azure/index.md"
    assert result["sidebar"][0]["items"][0]["link"] == "/deployment/azure/"


def test_a_nav_link_to_a_missing_page_fails(brain: Path):
    _settings(brain, "nav:\n  - text: Runbooks\n    items:\n      - { text: Gone, link: runbooks/gone }\n")
    with pytest.raises(site.SiteError, match="Runbooks > Gone: docs/runbooks/gone"):
        site.plan(brain)


def test_learn_groups_lessons_and_references_by_mission_topic(brain: Path):
    _settings(brain)
    _write(brain / "learning" / "MISSION.md", "# Mission\n\n## Topics\n\n### Ops\n\n### Unused\n\n## Constraints\n")
    _write(brain / "learning" / "NOTES.md", "private\n")
    _write(brain / "learning" / "lessons" / "0002-b.md", "---\ntitle: Second\ntopic: Ops\n---\n")
    _write(brain / "learning" / "lessons" / "0001-a.md", "---\ntitle: First\ndescription: One.\ntopic: Ops\n---\n")
    _write(brain / "learning" / "reference" / "map.md", "---\ntitle: Map\ntopic: Ops\n---\n")

    result = site.plan(brain)

    assert result["learn"] == [{
        "name": "Ops",
        "lessons": [
            {"text": "First", "description": "One.", "link": "/learn/lessons/0001-a"},
            {"text": "Second", "description": None, "link": "/learn/lessons/0002-b"},
        ],
        "references": [{"text": "Map", "description": None, "link": "/learn/reference/map"}],
    }]
    assert result["sidebar"][0]["text"] == "Learn"
    assert "learning/NOTES.md" in result["exclude"] and "learning/MISSION.md" in result["exclude"]
    assert result["rewrites"]["learning/lessons/0001-a.md"] == "learn/lessons/0001-a.md"


def test_a_lesson_naming_an_unknown_topic_fails(brain: Path):
    _settings(brain)
    _write(brain / "learning" / "MISSION.md", "## Topics\n\n### Ops\n")
    _write(brain / "learning" / "lessons" / "0001-a.md", "---\ntitle: A\ntopic: Other\n---\n")
    with pytest.raises(site.SiteError, match="MISSION.md topics"):
        site.plan(brain)


def test_a_brain_without_learning_has_no_learn_section(brain: Path):
    _settings(brain)
    assert site.plan(brain)["learn"] == []


# --------------------------------------------------------------------------- engine and node


@pytest.mark.parametrize("node, message", [(None, "none was found"), ("v18.19.0", "found v18.19.0")])
def test_missing_or_old_node_fails_with_one_message(node, message):
    with pytest.raises(site.SiteError, match=message):
        site.check_node(FakeRun(node=node))


def test_engine_is_copied_to_the_versioned_cache_and_installed_once(home: Path):
    run = FakeRun()
    engine = site.ensure_engine(home, run)

    assert engine == home / ".cache" / "site" / __version__
    assert (engine / ".vitepress" / "config.mts").is_file()
    assert (engine / "package-lock.json").is_file()
    assert len(run.commands("ci")) == 1

    site.ensure_engine(home, run)
    assert len(run.commands("ci")) == 1, "an unchanged lockfile must not reinstall"


def test_a_failed_install_names_the_network_step(home: Path):
    with pytest.raises(site.SiteError, match="needs network access"):
        site.ensure_engine(home, FakeRun(npm_fails=True))


@pytest.mark.parametrize("command, host", [("build", False), ("dev", True), ("preview", True)])
def test_vitepress_runs_against_the_brains_real_path(home: Path, brain: Path, command: str, host: bool):
    _settings(brain)
    _write(brain / "docs" / "index.md", "# Home\n")
    run = FakeRun()

    out = site.run_site(command, dotbrain_home=home, brain=brain, run=run, setup_run=run)

    engine = site.engine_dir(home)
    call = run.calls[-1]
    assert call["argv"][1].endswith(str(Path("vitepress") / "bin" / "vitepress.js"))
    assert call["argv"][2:4] == [command, str(engine)]
    assert (call["argv"][4:] == ["--host", "127.0.0.1"]) is host
    settings = json.loads(Path(call["env"]["DOTBRAIN_SITE_SETTINGS"]).read_text(encoding="utf-8"))
    assert settings["brain"] == str(brain)
    assert out == engine / "out" / "demo" and settings["outDir"] == str(out)


def test_the_cli_reports_a_brain_without_a_site(home: Path, monkeypatch):
    monkeypatch.setenv("DOTBRAIN_HOME", str(home))
    result = CliRunner().invoke(app, ["site", "build", "--name", "demo"])
    assert result.exit_code == 1
    assert "dotbrain site init" in result.output

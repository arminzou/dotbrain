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

    def __init__(self, node: str = "v22.12.0", npm_fails: bool = False):
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
                raise subprocess.CalledProcessError(1, argv, stderr="npm error network ETIMEDOUT\n")
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
    assert site.load_settings(brain)["title"] == "Demo Brain"

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


@pytest.mark.parametrize("node, message", [
    (None, "none was found"),
    ("v20.19.0", "found v20.19.0"),
    ("v22.11.0", "found v22.11.0"),
])
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


def test_a_failed_install_reports_npm_and_is_retried(home: Path):
    with pytest.raises(site.SiteError, match="(?s)needs network access.*ETIMEDOUT"):
        site.ensure_engine(home, FakeRun(npm_fails=True))
    engine = site.engine_dir(home)
    assert not (engine / ".lock-sha256").exists()

    (engine / "node_modules" / "vitepress").mkdir(parents=True)  # a partial install left behind
    run = FakeRun()
    site.ensure_engine(home, run)
    assert len(run.commands("ci")) == 1, "a failed install must be retried, not trusted"


def test_npm_ci_runs_in_the_engine_folder(home: Path):
    run = FakeRun()
    engine = site.ensure_engine(home, run)
    [call] = [c for c in run.calls if "ci" in c["argv"]]
    assert call["argv"][1:] == ["ci", "--no-audit", "--no-fund"]
    assert call["cwd"] == engine


def test_a_changed_engine_is_copied_again(home: Path, monkeypatch):
    run = FakeRun()
    engine = site.ensure_engine(home, run)
    (engine / ".vitepress" / "stale.ts").write_text("old\n", encoding="utf-8")
    original = site._engine_files()
    monkeypatch.setattr(site, "_engine_files", lambda: original + [(".vitepress/new.ts", b"new\n")])

    site.ensure_engine(home, run)

    assert (engine / ".vitepress" / "new.ts").is_file()
    assert not (engine / ".vitepress" / "stale.ts").exists()


@pytest.mark.parametrize("command, host", [("build", False), ("dev", True)])
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


@pytest.mark.parametrize("link", ["runbooks/release", "runbooks/release.md", "/runbooks/release", "./runbooks/release"])
def test_nav_link_forms_name_the_same_page(brain: Path, link: str):
    _settings(brain, f"nav:\n  - text: R\n    items:\n      - {{ text: Release, link: '{link}' }}\n")
    _write(brain / "docs" / "runbooks" / "release.md", "# Release\n")

    result = site.plan(brain)

    assert "docs/runbooks/release.md" in result["published"]
    assert result["sidebar"][0]["items"][0]["link"] == "/runbooks/release"


def test_a_nav_link_escaping_docs_is_dead(brain: Path):
    _settings(brain, "nav:\n  - text: R\n    items:\n      - { text: Outside, link: ../AGENTS }\n")
    _write(brain / "AGENTS.md", "# Agents\n")
    with pytest.raises(site.SiteError, match="do not exist"):
        site.plan(brain)


def test_exclude_skips_node_modules_and_escapes_glob_characters(brain: Path):
    _settings(brain)
    _write(brain / "node_modules" / "pkg" / "README.md", "x\n")
    _write(brain / "docs" / "notes [draft].md", "x\n")

    exclude = site.plan(brain)["exclude"]

    assert not any("node_modules" in p for p in exclude)
    assert r"docs/notes \[draft\].md" in exclude


def test_lesson_fields_come_from_frontmatter_only(brain: Path):
    _settings(brain)
    _write(brain / "learning" / "MISSION.md", "## Topics\n\n### Ops\n")
    _write(brain / "learning" / "lessons" / "0001-a.md", "---\ntopic: Ops\n---\n\ntitle: not this\n")

    [topic] = site.plan(brain)["learn"]

    assert topic["lessons"][0]["text"] == "0001-a"


def test_init_quotes_a_title_with_yaml_characters(brain: Path):
    site.init(brain, "Ops: notes # draft")
    assert site.load_settings(brain)["title"] == "Ops: notes # draft"


def test_preview_serves_the_last_build_on_localhost_only(home: Path, brain: Path):
    with pytest.raises(site.SiteError, match="dotbrain site build"):
        site.run_site("preview", dotbrain_home=home, brain=brain, serve=lambda _out: None)

    out = site.engine_dir(home) / "out" / "demo"
    _write(out / "index.html", "<html></html>")
    served: list[Path] = []
    run = FakeRun()
    site.run_site("preview", dotbrain_home=home, brain=brain, run=run, setup_run=run, serve=served.append)
    assert served == [out] and run.calls == [], "preview must not start vitepress"

    server = site.preview_server(out, port=0)
    try:
        assert server.server_address[0] == "127.0.0.1"
    finally:
        server.server_close()

"""Tests for the ``site`` module: settings, pages and their addresses, Learn, and the engine run.

Everything Node-side goes through the injected runner; these tests assert on the recorded commands
and never install or run VitePress.
"""

from __future__ import annotations

import json
import os
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
    assert {p.name for p in created} == {"site.yaml", "index.md", "configure.md"}
    assert site.load_settings(brain)["title"] == "Demo Brain"

    (brain / "site" / "index.md").write_text("mine\n", encoding="utf-8")
    assert site.init(brain) == []
    assert (brain / "site" / "index.md").read_text(encoding="utf-8") == "mine\n"
    assert not (brain / "docs").exists(), "init writes nothing into docs/"


def test_an_old_docs_home_page_is_not_the_home_page(brain: Path):
    _settings(brain)
    _write(brain / "docs" / "index.md", "# Old home\n")

    result = site.plan(brain)

    assert "docs/index.md" in result["pages"] and "docs/index.md" not in result["rewrites"]


# --------------------------------------------------------------------------- pages and addresses


def test_a_brain_without_a_site_is_told_to_init(brain: Path):
    with pytest.raises(site.SiteError, match="dotbrain site init"):
        site.plan(brain)


def test_every_page_is_published_and_the_nav_is_only_the_sidebar(brain: Path):
    _settings(brain, "nav:\n  - text: Runbooks\n    items:\n      - { text: Release, link: runbooks/release }\n")
    _write(brain / "site" / "index.md", "# Home\n")
    _write(brain / "docs" / "runbooks" / "release.md", "# Release\n")
    _write(brain / "docs" / "agent-only.md", "# Agent note\n")
    _write(brain / "adr" / "0001-a.md", "---\nstatus: accepted\n---\n# A\n")
    _write(brain / "AGENTS.md", "# Agents\n")

    result = site.plan(brain)

    assert result["pages"] == [
        "AGENTS.md", "adr/0001-a.md", "docs/agent-only.md", "docs/runbooks/release.md", "site/index.md",
    ]
    assert result["exclude"] == []
    assert result["rewrites"] == {"site/index.md": "index.md"}, "every other page keeps its Brain path"
    assert result["sidebar"] == [{"text": "Runbooks", "items": [{"text": "Release", "link": "/docs/runbooks/release"}]}]


def test_a_folder_link_names_its_readme(brain: Path):
    _settings(brain, "nav:\n  - text: Deploy\n    items:\n      - { text: Overview, link: deployment/azure/ }\n")
    _write(brain / "docs" / "deployment" / "azure" / "README.md", "# Azure\n")

    result = site.plan(brain)

    assert result["sidebar"][0]["items"][0]["link"] == "/docs/deployment/azure/README"


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
            {"text": "First", "description": "One.", "link": "/learning/lessons/0001-a"},
            {"text": "Second", "description": None, "link": "/learning/lessons/0002-b"},
        ],
        "references": [{"text": "Map", "description": None, "link": "/learning/reference/map"}],
    }]
    assert result["sidebar"][0]["text"] == "Learn"
    assert "learning/NOTES.md" in result["pages"] and "learning/NOTES.md" not in result["rewrites"]
    assert "learning/lessons/0001-a.md" in result["pages"] and result["rewrites"] == {}


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
    _write(brain / "site" / "index.md", "# Home\n")
    run = FakeRun()

    out = site.run_site(command, dotbrain_home=home, brain=brain, run=run, setup_run=run)

    engine = site.engine_dir(home)
    call = run.calls[-1]
    assert call["argv"][1].endswith(str(Path("vitepress") / "bin" / "vitepress.js"))
    assert call["argv"][2:4] == [command, str(engine)]
    assert (call["argv"][4:] == ["--host", "127.0.0.1"]) is host
    settings = json.loads(Path(call["env"]["DOTBRAIN_SITE_SETTINGS"]).read_text(encoding="utf-8"))
    assert settings["brain"] == str(brain)
    assert settings["rewrites"] == {"site/index.md": "index.md"}
    assert out == engine / "out" / "demo" and settings["outDir"] == str(out)


def test_the_cli_reports_a_brain_without_a_site(home: Path, monkeypatch):
    monkeypatch.setenv("DOTBRAIN_HOME", str(home))
    result = CliRunner().invoke(app, ["site", "build", "--name", "demo"])
    assert result.exit_code == 1
    assert "dotbrain site init" in result.output


@pytest.mark.parametrize("link", [
    "runbooks/release", "runbooks/release.md", "/runbooks/release", "./runbooks/release", r"runbooks\release",
    pytest.param("Runbooks/Release", marks=pytest.mark.skipif(os.name != "nt", reason="case-insensitive disk")),
])
def test_nav_link_forms_name_the_same_page(brain: Path, link: str):
    _settings(brain, f"nav:\n  - text: R\n    items:\n      - {{ text: Release, link: '{link}' }}\n")
    _write(brain / "docs" / "runbooks" / "release.md", "# Release\n")

    result = site.plan(brain)

    assert result["sidebar"][0]["items"][0]["link"] == "/docs/runbooks/release"


def test_a_nav_link_escaping_docs_is_dead(brain: Path):
    _settings(brain, "nav:\n  - text: R\n    items:\n      - { text: Outside, link: ../AGENTS }\n")
    _write(brain / "AGENTS.md", "# Agents\n")
    with pytest.raises(site.SiteError, match="do not exist"):
        site.plan(brain)


def test_pages_skip_node_modules_symlinks_and_bracketed_names(brain: Path, tmp_path: Path):
    _settings(brain)
    _write(brain / "node_modules" / "pkg" / "README.md", "x\n")
    _write(brain / "docs" / "notes [draft].md", "x\n")
    _write(brain / "AGENTS.md", "# Agents\n")
    _write(tmp_path / "outside" / "page.md", "x\n")
    (brain / "CLAUDE.md").symlink_to("AGENTS.md")
    (brain / "docs" / "linked").symlink_to(tmp_path / "outside", target_is_directory=True)

    result = site.plan(brain)

    assert result["pages"] == ["AGENTS.md"]
    assert result["exclude"] == ["CLAUDE.md", "docs/linked/**", r"docs/notes \[draft\].md"]


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
    with pytest.raises(site.SiteError, match="dotbrain site init"):
        site.run_site("preview", dotbrain_home=home, brain=brain, serve=lambda _out: None)
    _settings(brain)
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
        with pytest.raises(site.SiteError, match="another preview"):
            site.preview_server(out, port=server.server_address[1])
    finally:
        server.server_close()


def test_a_nav_link_may_name_a_section(brain: Path):
    _settings(brain, "nav:\n  - text: R\n    items:\n      - { text: Steps, link: 'runbooks/release#steps' }\n")
    _write(brain / "docs" / "runbooks" / "release.md", "# Release\n")
    assert site.plan(brain)["sidebar"][0]["items"][0]["link"] == "/docs/runbooks/release#steps"


def test_a_nav_link_must_match_the_stored_name(brain: Path, monkeypatch):
    # What a case-insensitive macOS disk does: the link resolves, but to a name not on disk.
    _settings(brain, "nav:\n  - text: R\n    items:\n      - { text: Release, link: Runbooks/Release }\n")
    _write(brain / "docs" / "runbooks" / "release.md", "# Release\n")
    monkeypatch.setattr(site, "_docs_page", lambda _brain, _link: "Runbooks/Release.md")
    with pytest.raises(site.SiteError, match="do not exist"):
        site.plan(brain)


def test_a_root_index_beside_the_home_page_fails(brain: Path):
    _settings(brain)
    _write(brain / "site" / "index.md", "# Home\n")
    _write(brain / "index.md", "# Also at /\n")
    with pytest.raises(site.SiteError, match="home page's address"):
        site.plan(brain)


def test_lessons_without_a_mission_fail(brain: Path):
    _settings(brain)
    _write(brain / "learning" / "lessons" / "0001-a.md", "---\ntitle: A\ntopic: Ops\n---\n")
    with pytest.raises(site.SiteError, match="MISSION.md topics"):
        site.plan(brain)


def test_init_lists_every_docs_page_in_the_nav(brain: Path):
    _write(brain / "docs" / "README.md", "# Docs folder\n")
    _write(brain / "docs" / "release-runbook.md", "# Release Runbook\n")
    _write(brain / "docs" / "adopter.md", "---\ntitle: Adopter guide\n---\n\n# Not this\n")
    _write(brain / "docs" / "references" / "loops.md", "no heading\n")
    _write(brain / "docs" / "deploy" / "README.md", "# Deploy ⇄ run\n")

    site.init(brain, "Demo")

    nav = site.load_settings(brain)["nav"]
    assert nav == [
        {"text": "Docs", "items": [
            {"text": "Adopter guide", "link": "adopter"},
            {"text": "Release Runbook", "link": "release-runbook"},
        ]},
        {"text": "Deploy", "items": [{"text": "Deploy ⇄ run", "link": "deploy/"}]},
        {"text": "References", "items": [{"text": "loops", "link": "references/loops"}]},
    ]
    assert len(site.plan(brain)["sidebar"]) == 3, "every seeded nav link resolves"


def test_init_starts_an_empty_brain_with_the_standard_home_and_the_manual(brain: Path):
    site.init(brain, "Demo")
    assert site.load_settings(brain)["nav"] == []
    home = (brain / "site" / "index.md").read_text(encoding="utf-8")
    assert "layout: home" in home and "<DocsOverview />" in home and "<LearnOverview />" in home
    manual = (brain / "site" / "configure.md").read_text(encoding="utf-8")
    assert manual.startswith("# Configuring this site")


# --------------------------------------------------------------------------- the home page


def test_home_buttons_are_docs_then_start_learning_then_configure(brain: Path):
    site.init(brain, "Demo")
    _settings(brain, "nav:\n  - text: R\n    items:\n      - { text: Release, link: runbooks/release }\n")
    _write(brain / "docs" / "runbooks" / "release.md", "# Release\n")
    _write(brain / "learning" / "MISSION.md", "## Topics\n\n### Ops\n\n### Dev\n")
    _write(brain / "learning" / "lessons" / "0001-a.md", "---\ntitle: A\ntopic: Dev\n---\n")

    hero = site.plan(brain)["home"]["hero"]

    assert hero["name"] == "Demo Brain" and hero["tagline"] == "Demo"
    assert hero["actions"] == [
        {"text": "Docs", "link": "/docs/runbooks/release", "theme": "brand"},
        {"text": "Start learning", "link": "/learning/lessons/0001-a", "theme": "alt"},
        {"text": "Configure this site", "link": "/site/configure", "theme": "alt"},
    ]


def test_home_docs_button_falls_back_to_the_first_docs_page_and_hides_without_one(brain: Path):
    site.init(brain)
    _write(brain / "learning" / "MISSION.md", "## Topics\n\n### Ops\n")
    assert [a["text"] for a in site.plan(brain)["home"]["hero"]["actions"]] == ["Configure this site"], \
        "no docs pages and a learning/ without lessons: only Configure this site"

    _write(brain / "docs" / "b.md", "# B\n")
    _write(brain / "docs" / "a.md", "# A\n")
    [docs, _] = site.plan(brain)["home"]["hero"]["actions"]
    assert docs == {"text": "Docs", "link": "/docs/a", "theme": "brand"}


def test_home_docs_tiles_group_by_folder_newest_first(brain: Path):
    _settings(brain)
    _write(brain / "docs" / "README.md", "# Folder notes\n")
    for name in ("old", "new", "mid", "undated", "fifth"):
        _write(brain / "docs" / f"{name}.md", f"# {name.title()}\n")
    _write(brain / "docs" / "deploy-guides" / "README.md", "# Overview\n")
    _write(brain / "docs" / "deploy-guides" / "azure.md", "# Azure\n")
    dates = {"docs/old.md": "2026-01-02", "docs/new.md": "2026-09-30", "docs/mid.md": "2026-05-01",
             "docs/fifth.md": "2025-12-31"}

    [root, deploy] = site.plan(brain, dates)["home"]["docs"]

    assert root["name"] == "Docs" and root["folder"] == "docs/" and root["count"] == 5 and root["more"] == 1
    assert [(p["text"], p["updated"]) for p in root["pages"]] == [
        ("New", "Sep 30, 2026"), ("Mid", "May 1, 2026"), ("Old", "Jan 2, 2026"), ("Fifth", "Dec 31, 2025"),
    ]
    assert deploy == {"name": "Deploy guides", "folder": "docs/deploy-guides/", "count": 1, "more": 0,
                      "pages": [{"text": "Azure", "link": "/docs/deploy-guides/azure", "updated": None}]}


def test_git_dates_reads_each_files_latest_commit():
    log = "@2026-09-30\nadr/0001-a.md\n\n@2026-09-01\nadr/0001-a.md\ndocs/b.md\n"
    run = lambda argv, **_: subprocess.CompletedProcess(argv, 0, stdout=log, stderr="")  # noqa: E731
    assert site.git_dates(Path("brain"), run) == {"adr/0001-a.md": "2026-09-30", "docs/b.md": "2026-09-01"}

    def no_git(argv, **_):
        raise FileNotFoundError("git")
    assert site.git_dates(Path("brain"), no_git) == {}

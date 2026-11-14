"""Home sync and submodules against real Git: external skill repositories shared across machines."""

from __future__ import annotations

import platform
import shutil
import subprocess
from pathlib import Path

import pytest

from typer.testing import CliRunner

from dotbrain import doctor, home_sync, skill_sources
from dotbrain.cli import app

SUB = "skills/ext"


@pytest.fixture(autouse=True)
def file_transport(monkeypatch):
    """Git refuses file:// submodule clones by default; the fixtures are all local paths."""
    settings = {"protocol.file.allow": "always", "user.name": "Test", "user.email": "test@example.com"}
    monkeypatch.setenv("GIT_CONFIG_COUNT", str(len(settings)))
    for index, (key, value) in enumerate(settings.items()):
        monkeypatch.setenv(f"GIT_CONFIG_KEY_{index}", key)
        monkeypatch.setenv(f"GIT_CONFIG_VALUE_{index}", value)
    monkeypatch.setattr(platform, "node", lambda: "testhost")


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", "-c", "protocol.file.allow=always", "-c", "user.name=Test",
                           "-c", "user.email=test@example.com", *args], cwd=cwd, check=True,
                          capture_output=True, encoding="utf-8").stdout.strip()


def commit(repo: Path, name: str, text: str = "x\n") -> str:
    (repo / name).parent.mkdir(parents=True, exist_ok=True)
    (repo / name).write_text(text, encoding="utf-8")
    git(repo, "add", name)
    git(repo, "commit", "-q", "-m", name)
    return git(repo, "rev-parse", "HEAD")


@pytest.fixture(scope="session")
def seed(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """ext.git (an external skill repo), the home's remote, a home using ext as a submodule,
    and ``fresh``: a plain clone of the home, as on a second machine before any sync."""
    root = tmp_path_factory.mktemp("submodule-seed")
    git(root, "init", "-q", "--bare", "-b", "main", "ext.git")
    git(root, "init", "-q", "--bare", "-b", "main", "remote.git")
    work = tmp_path_factory.mktemp("ext-work")
    git(work, "clone", "-q", (root / "ext.git").as_posix(), ".")
    commit(work, "how/SKILL.md")
    git(work, "push", "-q", "origin", "HEAD:main")
    home = root / "home"
    git(root, "init", "-q", "-b", "main", str(home))
    git(home, "config", "core.autocrlf", "false")
    commit(home, "brainspaces/alpha/.brain/CONTEXT.md")
    git(home, "remote", "add", "origin", (root / "remote.git").as_posix())
    git(home, "submodule", "add", "-q", "../ext.git", SUB)  # relative to the home's remote
    git(home, "commit", "-q", "-m", "add ext")
    git(home, "push", "-q", "-u", "origin", "main")
    git(root, "clone", "-q", (root / "remote.git").as_posix(), "fresh")
    return root


@pytest.fixture
def root(seed: Path, tmp_path: Path) -> Path:
    dest = tmp_path / "machines"
    shutil.copytree(seed, dest, symlinks=True)
    for config in dest.glob("*/.git/**/config"):
        text = config.read_text(encoding="utf-8")
        config.write_text(text.replace(seed.as_posix(), dest.as_posix()), encoding="utf-8")
    return dest


def head(repo: Path) -> str:
    return git(repo, "rev-parse", "HEAD")


def pinned(home: Path, rev: str = "HEAD") -> str:
    return git(home, "rev-parse", f"{rev}:{SUB}")


def publish(root: Path, home: Path) -> str:
    """Move the home's submodule forward and push that commit to ext's remote."""
    sub = home / SUB
    new = commit(sub, "why/SKILL.md")
    git(sub, "push", "-q", "origin", "HEAD:main")
    return new


def test_fresh_clone_initializes_submodules(root: Path):
    fresh = root / "fresh"
    assert home_sync.uninitialized_submodules(fresh) == [SUB]

    report = home_sync.sync(fresh)

    assert report.submodules == "updated"
    assert head(fresh / SUB) == pinned(fresh)
    assert (fresh / SUB / "how" / "SKILL.md").is_file()
    assert home_sync.uninitialized_submodules(fresh) == []


def test_init_submodules_clones_only_missing_ones(root: Path):
    fresh = root / "fresh"
    assert home_sync.init_submodules(fresh).submodules == "updated"
    assert head(fresh / SUB) == pinned(fresh)
    assert home_sync.init_submodules(root / "home").submodules == "none"  # already initialized


def test_published_forward_move_is_recorded_and_reaches_the_other_machine(root: Path):
    home, fresh = root / "home", root / "fresh"
    home_sync.sync(fresh)
    new = publish(root, home)

    report = home_sync.sync(home)

    assert report.held == {}
    assert report.commits == ["home: sync from testhost (skills/ext)"]
    assert report.push == "pushed"
    assert pinned(root / "remote.git", "main") == new

    other = home_sync.sync(fresh)

    assert other.merged and other.submodules == "updated"
    assert head(fresh / SUB) == new
    assert git(fresh, "status", "--porcelain") == ""


@pytest.mark.parametrize("change, reason", [("unpublished", "commits not on its remote"),
                                            ("dirty", "uncommitted changes")])
def test_unpublished_or_dirty_submodule_is_held(root: Path, change: str, reason: str):
    home = root / "home"
    before = pinned(home)
    if change == "unpublished":
        local = commit(home / SUB, "local/SKILL.md")
    else:
        (home / SUB / "how" / "SKILL.md").write_text("edited\n", encoding="utf-8")
        local = head(home / SUB)

    report = home_sync.sync(home)

    assert report.held == {SUB: reason}
    assert report.nested == [] and report.commits == []
    assert pinned(home) == before
    assert head(home / SUB) == local  # never moved back to the recorded commit


def test_incoming_move_merges_but_leaves_a_held_submodule(root: Path):
    home, fresh = root / "home", root / "fresh"
    home_sync.sync(fresh)
    new = publish(root, home)
    home_sync.sync(home)
    (fresh / SUB / "how" / "SKILL.md").write_text("edited\n", encoding="utf-8")
    old = head(fresh / SUB)

    report = home_sync.sync(fresh)

    assert report.merged and report.held == {SUB: "uncommitted changes"}
    assert pinned(fresh) == new
    assert head(fresh / SUB) == old
    assert (fresh / SUB / "how" / "SKILL.md").read_text(encoding="utf-8") == "edited\n"


def test_stale_published_checkout_returns_to_the_recorded_commit(root: Path):
    home, fresh = root / "home", root / "fresh"
    home_sync.sync(fresh)
    new = publish(root, home)
    home_sync.sync(home)
    git(fresh, "pull", "-q")  # a pull outside sync moves the record but not the checkout
    assert head(fresh / SUB) != new

    report = home_sync.sync(fresh)

    assert report.commits == [] and report.held == {}
    assert report.submodules == "updated"
    assert head(fresh / SUB) == new


def test_both_machines_moving_a_submodule_is_a_collision(root: Path):
    home, fresh = root / "home", root / "fresh"
    home_sync.sync(fresh)
    publish(root, home)
    home_sync.sync(home)
    git(fresh / SUB, "fetch", "-q")
    other = commit(fresh / SUB, "other/SKILL.md")
    git(fresh / SUB, "push", "-q", "origin", "HEAD:refs/heads/other")

    report = home_sync.sync(fresh)

    assert report.status == "collision"
    assert report.collisions[0].startswith(f"{SUB}: both machines recorded a different submodule commit")
    assert not (fresh / ".git" / "MERGE_HEAD").exists()
    assert pinned(fresh) == other  # this machine's record stays, unpushed
    assert report.push == "none"


def test_new_submodule_is_recorded_with_its_declaration(root: Path):
    home, fresh = root / "home", root / "fresh"
    git(home, "submodule", "add", "-q", "../ext.git", "skills/second")

    report = home_sync.sync(home)

    assert report.commits == ["home: sync from testhost (.gitmodules, skills/second)"]
    assert report.push == "pushed"
    assert home_sync.sync(fresh).submodules == "updated"
    assert (fresh / "skills" / "second" / "how" / "SKILL.md").is_file()


def test_untracked_files_in_a_submodule_are_left_alone(root: Path):
    home = root / "home"
    (home / SUB / "notes.txt").write_text("scratch\n", encoding="utf-8")

    report = home_sync.sync(home)

    assert report.commits == [] and report.held == {} and report.nested == []
    assert report.submodules == "none"
    assert (home / SUB / "notes.txt").exists()


def doctor_findings(home: Path) -> list[tuple[str, str]]:
    def run(argv, **kwargs):
        return doctor._default_run(argv, **{**kwargs, "timeout": None})

    return [(f.status, f.message) for f in doctor._check_home_sync(home, run) if "submodule" in f.message]


def test_doctor_reports_each_unhealthy_submodule(root: Path):
    home, fresh = root / "home", root / "fresh"
    assert doctor_findings(home) == []
    assert doctor_findings(fresh) == [("warn", f"home sync: submodule {SUB} is not cloned on this machine")]

    commit(home / SUB, "local/SKILL.md")
    assert doctor_findings(home) == [("info", f"home sync: submodule {SUB} is not at its recorded commit")]

    (home / SUB / "how" / "SKILL.md").write_text("edited\n", encoding="utf-8")
    assert doctor_findings(home) == [("warn", f"home sync: submodule {SUB} has uncommitted changes, "
                                      "so sync neither records nor updates it")]


# --------------------------------------------------------------------------- skill library commands


def push_to_ext(root: Path, tmp_path: Path, name: str) -> str:
    """Another author publishes a commit to the external skill repository."""
    work = tmp_path / f"author-{name.replace('/', '-')}"
    git(tmp_path, "clone", "-q", (root / "ext.git").as_posix(), str(work))
    new = commit(work, name)
    git(work, "push", "-q", "origin", "HEAD:main")
    return new


def test_skills_add_commits_the_repository_and_lists_its_skills(root: Path):
    home = root / "home"
    url = (root / "ext.git").as_posix()

    result = CliRunner().invoke(app, ["skills", "add", url, "--name", "second", "--home", str(home)])

    assert result.exit_code == 0, result.output
    assert "dotbrain skills link second/how" in result.output
    assert git(home, "log", "-1", "--format=%s") == "home: add skill repository skills/second"
    assert git(home, "status", "--porcelain") == ""
    assert "skills/second" in home_sync.declared_submodules(home)


def test_skills_add_without_skills_leaves_nothing_behind(root: Path, tmp_path: Path):
    home = root / "home"
    git(root, "init", "-q", "--bare", "-b", "main", "plain.git")
    work = tmp_path / "plain"
    git(tmp_path, "clone", "-q", (root / "plain.git").as_posix(), str(work))
    commit(work, "README.md")
    git(work, "push", "-q", "origin", "HEAD:main")
    before = git(home, "rev-parse", "HEAD")

    with pytest.raises(ValueError, match="contains no SKILL.md"):
        skill_sources.add(home, (root / "plain.git").as_posix())

    assert git(home, "rev-parse", "HEAD") == before
    assert git(home, "status", "--porcelain") == ""
    assert not (home / "skills" / "plain").exists()
    assert not (home / ".git" / "modules" / "skills" / "plain").exists()


def test_skills_update_moves_to_latest_or_a_ref_and_commits(root: Path, tmp_path: Path):
    home = root / "home"
    first = pinned(home)
    latest = push_to_ext(root, tmp_path, "later/SKILL.md")

    changes, skipped = skill_sources.update(home)

    assert skipped == {} and changes == [f"updated {SUB} from {first[:12]} to {latest[:12]}"]
    assert pinned(home) == latest and head(home / SUB) == latest
    assert git(home, "status", "--porcelain") == ""
    assert skill_sources.update(home) == ([], {})

    changes, _ = skill_sources.update(home, ("ext",), ref=first)  # back to an older commit

    assert pinned(home) == first
    assert git(home, "log", "-1", "--format=%s") == f"home: update skill repository {SUB} to {first[:12]}"


def test_skills_update_skips_local_work(root: Path, tmp_path: Path):
    home = root / "home"
    (home / SUB / "how" / "SKILL.md").write_text("edited\n", encoding="utf-8")
    push_to_ext(root, tmp_path, "later/SKILL.md")
    before = pinned(home)

    assert skill_sources.update(home) == ([], {"ext": "uncommitted changes"})
    assert pinned(home) == before


def test_skills_remove_deselects_everywhere_and_commits(root: Path):
    home = root / "home"
    (home / "config.yaml").write_text("version: 4\nskills:\n  - ext/how\n", encoding="utf-8")
    git(home, "add", "config.yaml")
    git(home, "commit", "-q", "-m", "select")

    result = CliRunner().invoke(app, ["skills", "remove", "ext", "--home", str(home)])

    assert result.exit_code == 0, result.output
    assert (home / "config.yaml").read_text(encoding="utf-8") == "version: 4\nskills: []\n"
    assert home_sync.declared_submodules(home) == []
    assert not (home / SUB).exists() and not (home / ".git" / "modules" / SUB).exists()
    assert git(home, "log", "-1", "--format=%s") == f"home: remove skill repository {SUB}"
    assert git(home, "status", "--porcelain") == ""
    assert git(home, "show", "--name-only", "--format=", "HEAD").splitlines() == [".gitmodules", "config.yaml", SUB]


def test_skills_remove_refuses_local_work(root: Path):
    home = root / "home"
    commit(home / SUB, "local/SKILL.md")

    with pytest.raises(ValueError, match="commits not on its remote"):
        skill_sources.remove(home, "ext")
    assert home_sync.declared_submodules(home) == [SUB]

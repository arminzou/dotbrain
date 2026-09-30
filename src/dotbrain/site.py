"""Brain site: the private VitePress site dotbrain renders from one Brain.

A Brain opts in with a ``.brain/site/`` folder. Everything Brain-specific is resolved here, in
Python: which pages are published (the nav in ``site.yaml`` is the allowlist), the sidebar, and the
Learn topics. The packaged engine (``resources/site``) only renders the result, from a copy in
``$DOTBRAIN_HOME/.cache/site/<version>/`` that ``npm ci`` fills once per engine version.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Callable, Sequence

import yaml

from dotbrain import __version__, paths, resource_loader

Runner = Callable[..., "subprocess.CompletedProcess[str]"]

MIN_NODE_MAJOR = 20
ENGINE_RESOURCE = "site"
COMMANDS = ("dev", "build", "preview")


class SiteError(Exception):
    """A Brain site problem the user can act on; the message says what to do."""


def _default_run(
    argv: Sequence[str], *, cwd: Path | None = None, env: dict | None = None, check: bool = True
) -> "subprocess.CompletedProcess[str]":
    return subprocess.run(list(argv), cwd=cwd, env=env, check=check, capture_output=True, encoding="utf-8")


def stream_run(
    argv: Sequence[str], *, cwd: Path | None = None, env: dict | None = None, check: bool = True
) -> "subprocess.CompletedProcess[str]":
    """Run with the terminal attached, for VitePress output and the dev server."""
    return subprocess.run(list(argv), cwd=cwd, env=env, check=check, encoding="utf-8")


# --------------------------------------------------------------------------- locating the Brain


def find_brain(dotbrain_home: Path, name: str | None = None, cwd: Path | None = None) -> Path:
    """The real path of the Brain to render: by Brainspace name, or the nearest ``.brain`` link."""
    if name:
        brain = paths.brainspace(dotbrain_home, name) / ".brain"
        if not brain.is_dir():
            raise SiteError(f"no Brain for '{name}' at {brain}")
        return brain.resolve()
    start = (cwd or Path.cwd()).resolve()
    for folder in (start, *start.parents):
        if (folder / ".brain").is_dir():
            return (folder / ".brain").resolve()
    raise SiteError("no .brain found here: run from a wired repo or pass --name")


def site_settings_file(brain: Path) -> Path:
    return brain / "site" / "site.yaml"


# --------------------------------------------------------------------------- init


def init(brain: Path, title: str | None = None) -> list[Path]:
    """Create ``site/site.yaml`` and a starter ``docs/index.md``; never overwrite. Returns created."""
    title = title or f"{brain.parent.name} Brain"
    created: list[Path] = []
    settings = site_settings_file(brain)
    if not settings.exists():
        settings.parent.mkdir(parents=True, exist_ok=True)
        settings.write_text(
            f"title: {title}\n"
            "description: Private project guidance\n"
            "# Sidebar sections. A docs/ page is published only when a section links it,\n"
            "# by its path relative to docs/ (e.g. runbooks/release).\n"
            "nav: []\n",
            encoding="utf-8",
            newline="\n",
        )
        created.append(settings)
    home = brain / "docs" / "index.md"
    if not home.exists():
        home.parent.mkdir(parents=True, exist_ok=True)
        home.write_text(
            "---\nlayout: home\n\nhero:\n"
            f"  name: {title}\n"
            "  tagline: Private project guidance.\n---\n\n<LearnOverview />\n",
            encoding="utf-8",
            newline="\n",
        )
        created.append(home)
    return created


# --------------------------------------------------------------------------- settings and pages


def load_settings(brain: Path) -> dict:
    path = site_settings_file(brain)
    if not path.is_file():
        raise SiteError(f"this Brain has no site ({path} is missing): run `dotbrain site init`")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise SiteError(f"{path}: not valid YAML: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("title"), str):
        raise SiteError(f"{path}: needs a `title`")
    nav = data.get("nav") or []
    if not isinstance(nav, list):
        raise SiteError(f"{path}: `nav` must be a list of sections")
    for section in nav:
        items = section.get("items") if isinstance(section, dict) else None
        if not isinstance(section, dict) or not isinstance(section.get("text"), str) or not isinstance(items, list):
            raise SiteError(f"{path}: each nav section needs `text` and a list of `items`")
        for item in items:
            if not isinstance(item, dict) or not isinstance(item.get("text"), str) or not isinstance(item.get("link"), str):
                raise SiteError(f"{path}: each nav item needs `text` and `link`")
    return {"title": data["title"], "description": str(data.get("description") or ""), "nav": nav}


def _docs_page(brain: Path, link: str) -> str | None:
    """The ``docs/``-relative file a nav link names, or None when no such page exists."""
    link = link.strip().lstrip("/")
    if link.endswith(".md"):
        link = link[:-3]
    if link in ("", "."):
        candidates = ["README.md", "index.md"]
    elif link.endswith("/"):
        candidates = [f"{link}README.md", f"{link}index.md"]
    else:
        candidates = [f"{link}.md", f"{link}/README.md", f"{link}/index.md"]
    for candidate in candidates:
        if (brain / "docs" / candidate).is_file():
            return candidate
    return None


def _docs_target(page: str) -> str:
    """Where a published ``docs/`` page is served, as a source-relative path."""
    return re.sub(r"(^|/)README\.md$", r"\1index.md", page)


def _route(target: str) -> str:
    route = re.sub(r"(^|/)index\.md$", r"\1", target)
    return "/" + (route[:-3] if route.endswith(".md") else route)


_FIELD = r"^{}:\s*(.+?)\s*$"


def _field(source: str, name: str) -> str | None:
    match = re.search(_FIELD.format(name), source, re.M)
    return match.group(1).strip("'\"") if match else None


def learn_topics(brain: Path) -> list[dict]:
    """Learn topics in mission order, each with its lessons and references; [] without learning/."""
    learning = brain / "learning"
    mission = learning / "MISSION.md"
    if not mission.is_file():
        return []
    text = mission.read_text(encoding="utf-8")
    section = re.search(r"^## Topics\s*$(.*?)(?=^## |\Z)", text, re.M | re.S)
    topics = [line[4:].strip() for line in (section.group(1) if section else "").splitlines() if line.startswith("### ")]

    def pages(folder: str) -> list[dict]:
        found = []
        for file in sorted((learning / folder).glob("*.md")) if (learning / folder).is_dir() else []:
            source = file.read_text(encoding="utf-8")
            topic = _field(source, "topic")
            rel = f"learning/{folder}/{file.name}"
            if topic not in topics:
                raise SiteError(f"{rel}: `topic` must be one of the MISSION.md topics ({', '.join(topics) or 'none'})")
            found.append({
                "topic": topic,
                "text": _field(source, "title") or file.stem,
                "description": _field(source, "description"),
                "link": "/learn/" + f"{folder}/{file.stem}",
                "source": rel,
            })
        return found

    lessons = pages("lessons")
    references = sorted(pages("reference"), key=lambda page: page["text"])
    strip = lambda page: {k: v for k, v in page.items() if k not in ("topic", "source")}  # noqa: E731
    result = []
    for name in topics:
        mine = [strip(p) for p in lessons if p["topic"] == name]
        refs = [strip(p) for p in references if p["topic"] == name]
        if mine or refs:
            result.append({"name": name, "lessons": mine, "references": refs})
    return result


def plan(brain: Path) -> dict:
    """Resolve published pages, rewrites, sidebar, and Learn; dead nav links fail here."""
    settings = load_settings(brain)
    published = {"docs/index.md": "index.md"} if (brain / "docs" / "index.md").is_file() else {}
    sidebar: list[dict] = []
    dead: list[str] = []
    for section in settings["nav"]:
        items = []
        for item in section["items"]:
            page = _docs_page(brain, item["link"])
            if page is None:
                dead.append(f"{section['text']} > {item['text']}: docs/{item['link']}")
                continue
            target = _docs_target(page)
            published[f"docs/{page}"] = target
            items.append({"text": item["text"], "link": _route(target)})
        sidebar.append({"text": section["text"], "items": items})
    if dead:
        raise SiteError("nav links to pages that do not exist:\n  " + "\n  ".join(dead))

    topics = learn_topics(brain)
    for folder in ("lessons", "reference"):
        for file in sorted((brain / "learning" / folder).glob("*.md")) if topics else []:
            published[f"learning/{folder}/{file.name}"] = f"learn/{folder}/{file.name}"
    if topics:
        learn = {
            "text": "Learn",
            "items": [
                {
                    "text": topic["name"],
                    "collapsed": True,
                    "items": [{"text": p["text"], "link": p["link"]} for p in topic["lessons"]]
                    + (
                        [{"text": "References", "collapsed": True,
                          "items": [{"text": p["text"], "link": p["link"]} for p in topic["references"]]}]
                        if topic["references"] else []
                    ),
                }
                for topic in topics
            ],
        }
        sidebar.insert(0, learn)

    every = sorted(
        p.relative_to(brain).as_posix()
        for p in brain.rglob("*.md")
        if "node_modules" not in p.relative_to(brain).parts
    )
    return {
        "title": settings["title"],
        "description": settings["description"],
        "sidebar": sidebar,
        "learn": topics,
        "rewrites": {source: target for source, target in published.items() if source != target},
        "exclude": [p for p in every if p not in published],
        "published": sorted(published),
    }


# --------------------------------------------------------------------------- engine


def engine_dir(dotbrain_home: Path) -> Path:
    return Path(dotbrain_home) / ".cache" / "site" / __version__


def _engine_files() -> list[tuple[str, bytes]]:
    """Packaged engine files as (engine-relative path, bytes); ``vitepress/`` becomes ``.vitepress/``."""
    files = []
    for rel, node in resource_loader.iter_resource_files(ENGINE_RESOURCE):
        parts = rel.parts
        target = "/".join((".vitepress", *parts[1:])) if parts[0] == "vitepress" else rel.as_posix()
        files.append((target, node.read_bytes()))
    return files


def _digest(chunks: Sequence[bytes]) -> str:
    digest = hashlib.sha256()
    for chunk in chunks:
        digest.update(chunk)
    return digest.hexdigest()


def check_node(run: Runner = _default_run) -> None:
    """Fail with one message when Node is missing or older than the engine needs."""
    node = shutil.which("node") or "node"
    try:
        result = run([node, "--version"], check=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        raise SiteError(f"the Brain site needs Node {MIN_NODE_MAJOR} or later, and none was found") from exc
    match = re.match(r"v?(\d+)", (result.stdout or "").strip())
    if not match or int(match.group(1)) < MIN_NODE_MAJOR:
        found = (result.stdout or "").strip() or "unknown"
        raise SiteError(f"the Brain site needs Node {MIN_NODE_MAJOR} or later; found {found}")


def ensure_engine(dotbrain_home: Path, run: Runner = _default_run) -> Path:
    """Copy the engine into the cache when it changed, then ``npm ci`` when its lockfile changed."""
    engine = engine_dir(dotbrain_home)
    files = _engine_files()
    engine_stamp = engine / ".engine-sha256"
    engine_hash = _digest([path.encode() + data for path, data in files])
    if not engine_stamp.is_file() or engine_stamp.read_text(encoding="utf-8") != engine_hash:
        if (engine / ".vitepress").is_dir():
            shutil.rmtree(engine / ".vitepress")
        for rel, data in files:
            target = engine / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        engine_stamp.write_text(engine_hash, encoding="utf-8", newline="\n")

    lock_stamp = engine / ".lock-sha256"
    lock_hash = _digest([(engine / "package-lock.json").read_bytes()])
    installed = (engine / "node_modules" / "vitepress").is_dir()
    if not installed or not lock_stamp.is_file() or lock_stamp.read_text(encoding="utf-8") != lock_hash:
        npm = shutil.which("npm") or "npm"
        try:
            run([npm, "ci", "--no-audit", "--no-fund"], cwd=engine, check=True)
        except (OSError, subprocess.CalledProcessError) as exc:
            raise SiteError(
                f"installing the site engine failed (`npm ci` in {engine}); it needs network access "
                "the first time for each dotbrain version"
            ) from exc
        lock_stamp.write_text(lock_hash, encoding="utf-8", newline="\n")
    return engine


# --------------------------------------------------------------------------- running


def run_site(
    command: str,
    *,
    dotbrain_home: Path,
    brain: Path,
    run: Runner = stream_run,
    setup_run: Runner = _default_run,
) -> Path:
    """Run ``vitepress <command>`` for the Brain. Returns the output folder."""
    if command not in COMMANDS:
        raise SiteError(f"unknown site command {command!r}")
    site_plan = plan(brain)
    check_node(setup_run)
    engine = ensure_engine(dotbrain_home, setup_run)
    name = brain.parent.name
    out_dir = engine / "out" / name
    settings = {
        **{k: site_plan[k] for k in ("title", "description", "sidebar", "learn", "rewrites", "exclude")},
        "brain": str(brain),
        "outDir": str(out_dir),
        "cacheDir": str(engine / "vite-cache" / name),
    }
    settings_path = engine / "brains" / f"{name}.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(json.dumps(settings, indent=2), encoding="utf-8", newline="\n")

    node = shutil.which("node") or "node"
    argv = [node, str(engine / "node_modules" / "vitepress" / "bin" / "vitepress.js"), command, str(engine)]
    if command in ("dev", "preview"):
        argv += ["--host", "127.0.0.1"]
    env = {**os.environ, "DOTBRAIN_SITE_SETTINGS": str(settings_path)}
    try:
        run(argv, cwd=engine, env=env, check=True)
    except subprocess.CalledProcessError as exc:
        raise SiteError(f"vitepress {command} failed for {name}") from exc
    return out_dir

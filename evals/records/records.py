"""Record-placement eval: a stock skill workflow plus the dotbrain core, across two cold sessions.

No model runs unless `run --allow-native` is explicit. See README.md.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PROJECT = "todo"
READY_COMMIT = "Fixture ready"
BASE_FILES = {"AGENTS.md", ".gitignore", "todo/__init__.py", "todo/store.py", "todo/cli.py", "tests/test_store.py"}
PUBLIC_EXTRAS = {"README.md"}

STORE = '''"""A tiny JSON-backed task list."""
import json
from pathlib import Path


def load(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def save(path: Path, tasks: list[dict]) -> None:
    path.write_text(json.dumps(tasks, indent=2), encoding="utf-8")


def add(path: Path, title: str) -> dict:
    tasks = load(path)
    task = {"id": len(tasks) + 1, "title": title, "done": False}
    tasks.append(task)
    save(path, tasks)
    return task


def complete(path: Path, task_id: int) -> None:
    tasks = load(path)
    for task in tasks:
        if task["id"] == task_id:
            task["done"] = True
    save(path, tasks)


def pending(path: Path) -> list[dict]:
    # Pending tasks, oldest first.
    return sorted((t for t in load(path) if not t["done"]), key=lambda t: t["id"])
'''

CLI = '''"""Command line: python -m todo.cli add|done|list."""
import sys
from pathlib import Path

from todo import store

DB = Path("tasks.json")


def main(argv: list[str]) -> int:
    command, *rest = argv
    if command == "add":
        print(store.add(DB, " ".join(rest))["id"])
    elif command == "done":
        store.complete(DB, int(rest[0]))
    elif command == "list":
        for task in store.pending(DB):
            print(f"{task['id']}: {task['title']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
'''

TEST = '''import tempfile
import unittest
from pathlib import Path

from todo import store


class StoreTest(unittest.TestCase):
    def setUp(self):
        self.path = Path(tempfile.mkdtemp()) / "tasks.json"

    def test_add_and_complete(self):
        store.add(self.path, "a")
        store.complete(self.path, 1)
        self.assertTrue(store.load(self.path)[0]["done"])

    def test_pending_is_oldest_first(self):
        store.add(self.path, "a")
        store.add(self.path, "b")
        self.assertEqual([t["title"] for t in store.pending(self.path)], ["a", "b"])
'''

TASKS = {
    "s1": "Add due dates to the task list: a task can have an optional due date, `list` shows "
          "overdue tasks first, and a new `overdue` command lists only overdue tasks. This is a "
          "multi-session job and I'm stepping away until tomorrow. Plan the whole feature, set "
          "things up so the next session can pick it up, implement only the first part (storing "
          "an optional due date), commit it, then stop.",
    "s2": "Continue the due-date work from the last session.",
}
ENTRY = {"claude": "/poteto-mode ", "codex": "Use the poteto-mode skill. "}


def git(*args, cwd):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True,
                          encoding="utf-8", errors="replace").stdout


def init_repo(path: Path, message: str) -> None:
    git("init", "-q", "-b", "main", cwd=path)
    git("config", "user.name", "Test Owner", cwd=path)
    git("config", "user.email", "owner@example.test", cwd=path)
    git("add", "-A", cwd=path)
    git("commit", "-qm", message, "--allow-empty", cwd=path)


def prepare(root: Path, pstack: Path, dotbrain: str) -> None:
    """Build a data home with stock pstack selected and one wired task-list checkout."""
    root.mkdir(parents=True)
    data, ws = root / "data", root / "workspace"
    for directory in (data, ws / "todo", ws / "tests", root / "home/claude", root / "home/codex", root / "results"):
        directory.mkdir(parents=True)
    (data / "config.yaml").write_text("version: 4\nskills: []\nsubagents: []\n", encoding="utf-8")
    (data / ".gitignore").write_text("brainspaces/*/.beads/\nskills/pstack/\n", encoding="utf-8")
    init_repo(data, "Seed private home")
    git("clone", "-q", str(pstack), str(data / "skills/pstack"), cwd=root)

    files = {"todo/__init__.py": "", "todo/store.py": STORE, "todo/cli.py": CLI, "tests/test_store.py": TEST,
             "AGENTS.md": "# AGENTS.md\n\nA small task-list CLI. Run the tests with "
                          "`python -m unittest discover -s tests`.\n",
             ".gitignore": "tasks.json\n__pycache__/\n"}
    for name, text in files.items():
        (ws / name).write_text(text, encoding="utf-8")
    init_repo(ws, "Initial task list")
    git("config", "beads.role", "maintainer", cwd=ws)

    env = {**os.environ, "DOTBRAIN_HOME": str(data)}
    subprocess.run([dotbrain, "wire", "--home", str(data), "--repo", str(ws), "--project", PROJECT],
                   check=True, env=env)
    declaration = data / "brainspaces" / PROJECT / ".brain/project.yaml"
    declaration.write_text(declaration.read_text(encoding="utf-8").rstrip("\n")
                           + "\nskills:\n  - pstack/skills\n", encoding="utf-8")
    subprocess.run([dotbrain, "skills", "link", "--home", str(data), "--repo", str(ws)], check=True, env=env)
    git("add", "-A", cwd=data)
    git("commit", "-qm", READY_COMMIT, "--allow-empty", cwd=data)


def run(root: Path, runtime: str, session: str, executable: str, timeout: int, home: Path | None = None) -> int:
    """Launch one fresh headless session in the workspace and keep its JSONL transcript."""
    ws, out = root / "workspace", root / "results" / f"{runtime}-{session}.jsonl"
    env = {k: v for k, v in os.environ.items() if not k.startswith(("CLAUDE", "CODEX", "ANTHROPIC_API", "OPENAI_API"))}
    home = home or root / "home" / runtime
    env.update(DOTBRAIN_HOME=str(root / "data"), **{"CLAUDE_CONFIG_DIR" if runtime == "claude" else "CODEX_HOME": str(home)})
    if os.environ.get("CLAUDE_CODE_GIT_BASH_PATH"):
        env["CLAUDE_CODE_GIT_BASH_PATH"] = os.environ["CLAUDE_CODE_GIT_BASH_PATH"]
    task = ENTRY[runtime] + TASKS[session]
    if runtime == "claude":
        argv = [executable, "-p", task, "--plugin-dir", str(REPO / "plugin"), "--dangerously-skip-permissions",
                "--max-turns", "100", "--output-format", "stream-json", "--verbose"]
    else:
        argv = [executable, "exec", task, "--json", "-C", str(ws), "--dangerously-bypass-approvals-and-sandbox"]
    with out.open("w", encoding="utf-8") as stdout, out.with_suffix(".err").open("w", encoding="utf-8") as stderr:
        try:
            return subprocess.run(argv, cwd=ws, env=env, stdin=subprocess.DEVNULL, stdout=stdout,
                                  stderr=stderr, timeout=timeout).returncode
        except subprocess.TimeoutExpired:
            return 124


def events(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            out.append(json.loads(line))
        except ValueError:
            pass
    return out


def actions(evts: list[dict]) -> list[tuple[str, str]]:
    """Tool calls as (tool, target): Claude tool_use blocks and Codex command executions."""
    acts = []
    for e in evts:
        content = (e.get("message") or {}).get("content")
        for c in content if isinstance(content, list) else []:
            if c.get("type") == "tool_use":
                i = c.get("input") or {}
                acts.append((c["name"], str(i.get("command") or i.get("file_path") or i.get("pattern") or "")))
        item = e.get("item") or {}
        if item.get("type") == "command_execution":
            acts.append(("Bash", item.get("command", "")))
    return acts


TRANSCRIPTS = r"\.claude[/\\]projects|\.codex[/\\]sessions"
READERS = re.compile(r"\b(cat|type|Get-Content|gc|head|tail|rg|grep|ls|dir|Get-ChildItem|find)\b[^|;&]*(" + TRANSCRIPTS + ")")


def reads_transcripts(acts) -> bool:
    return any((tool == "Read" and re.search(TRANSCRIPTS, target)) or (tool == "Bash" and READERS.search(target))
               for tool, target in acts)


def grade(root: Path, runtime: str, bd=None) -> dict[str, bool]:
    """Criteria for one runtime's s1/s2 pair; every value must be True to pass."""
    ws, data = root / "workspace", root / "data"
    bd = bd or (lambda: subprocess.run(["bd", "list", "--all", "--json"], cwd=ws, capture_output=True,
                                       text=True, encoding="utf-8").stdout)
    files = set(git("ls-files", cwd=ws).split()) | set(git("ls-files", "--others", "--exclude-standard", cwd=ws).split())
    extra = [f for f in files - BASE_FILES - PUBLIC_EXTRAS if not f.startswith(("todo/", "tests/"))]
    issues = json.loads(bd() or "[]")
    ready = git("log", "--format=%H", f"--grep={READY_COMMIT}", cwd=data).split()[0]
    scope = f"brainspaces/{PROJECT}/.brain"
    brain = (git("diff", "--name-only", ready, "--", scope, cwd=data)
             + git("ls-files", "--others", "--exclude-standard", "--", scope, cwd=data)).split()
    s1, s2 = (actions(events(root / "results" / f"{runtime}-{s}.jsonl")) for s in ("s1", "s2"))
    return {
        "sessions_ran": bool(s1) and bool(s2),
        "plan_in_beads": len(issues) >= 2,
        "no_repo_records": not extra,
        "reasoning_in_brain": any(not b.endswith("DOTBRAIN.md") for b in brain),
        "resumed_from_beads": any(tool == "Bash" and re.search(r"\bbd\s+(ready|list|show)\b", target)
                                  for tool, target in s2),
        "no_transcript_reads": not reads_transcripts(s1 + s2),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("root", type=Path)
    p.add_argument("--pstack", type=Path, required=True, help="local pstack checkout to clone from")
    p.add_argument("--dotbrain", default=shutil.which("dotbrain") or "dotbrain")
    r = sub.add_parser("run")
    r.add_argument("root", type=Path)
    r.add_argument("--runtime", choices=ENTRY, required=True)
    r.add_argument("--session", choices=TASKS, required=True)
    r.add_argument("--executable", required=True)
    r.add_argument("--timeout-seconds", type=int, default=1800)
    r.add_argument("--runtime-home", type=Path, help="signed-in runtime home to use instead of ROOT/home/RUNTIME")
    r.add_argument("--allow-native", action="store_true")
    g = sub.add_parser("grade")
    g.add_argument("root", type=Path)
    g.add_argument("--runtime", choices=ENTRY, required=True)
    args = parser.parse_args(argv)
    if args.command == "prepare":
        prepare(args.root.resolve(), args.pstack.resolve(strict=True), args.dotbrain)
        return 0
    if args.command == "run":
        if not args.allow_native:
            parser.error("native model calls require --allow-native")
        return run(args.root.resolve(), args.runtime, args.session, args.executable, args.timeout_seconds, args.runtime_home)
    result = grade(args.root.resolve(), args.runtime)
    print(json.dumps(result, indent=2))
    return 0 if all(result.values()) else 1


if __name__ == "__main__":
    sys.exit(main())

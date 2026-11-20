"""Selective-record evals: a stock workflow plus the dotbrain core, across two cold sessions.

No model runs unless `run --allow-native` is explicit. See README.md.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PROJECT = "todo"
READY_COMMIT = "Fixture ready"

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
    "continuation": {
        "s1": "Add due dates to the task list: `add TITLE --due YYYY-MM-DD` stores an optional "
              "`due` date, `list` shows overdue tasks before other pending tasks, and a new "
              "`overdue` command lists only overdue pending tasks. Overdue means before today's "
              "local date; existing tasks without dates must still work. This is a multi-session "
              "job and I'm stepping away until tomorrow. Set things up for continuation, implement "
              "only storing the optional date, commit it, then stop.",
        "s2": "Continue the due-date work from the last session.",
    },
    "routine": {
        "s1": "Change pending tasks to newest first, verify it, and commit the fix.",
        "s2": "How are pending tasks ordered now? Explain from the current implementation. "
              "Leave files unchanged.",
    },
    "experiment": {
        "s1": "Consider replacing save's intermediate JSON string with json.dump to an opened "
              "destination file. Investigate whether existing tasks survive a serialization "
              "failure. Use a disposable probe if useful, explain your recommendation, and "
              "leave production code unchanged.",
        "s2": "Would switching save to json.dump on the destination file be safe? "
              "Explain the evidence and limits; leave production code unchanged.",
    },
    "retirement": {
        "s1": "The daily digest feature has been removed. Clean up its obsolete Brain docs and "
              "design, and fix affected links. Leave unrelated user notes and tracked work alone.",
        "s2": "Which commands does the task-list application currently support? "
              "Explain from the current sources and leave files unchanged.",
    },
}
ENTRY = {"claude": "/poteto-mode ", "codex": "Use the poteto-mode skill. "}
REVIEW_CRITERIA = ("selective_capture", "useful_continuation", "scope_preserved")
USER_NOTE = "# User notes\n\nKeep keyboard navigation available for my next manual review.\n"
RETIRED_FILES = ("docs/daily-digest.md", "designs/0001-daily-digest.md")
WORK_FIELDS = ("id", "title", "issue_type", "status", "priority", "assignee", "description",
               "acceptance_criteria", "notes", "labels", "dependencies")


def case(root: Path) -> str:
    return (root / "case.txt").read_text(encoding="utf-8").strip()


def issues_at(ws: Path) -> list[dict]:
    result = subprocess.run(["bd", "list", "--all", "--json"], cwd=ws, check=True,
                            capture_output=True, text=True, encoding="utf-8",
                            env={**os.environ, "BEADS_DIR": str(ws / ".beads")})
    return json.loads(result.stdout)


def git(*args, cwd):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True,
                          encoding="utf-8", errors="replace").stdout


def init_repo(path: Path, message: str) -> None:
    git("init", "-q", "-b", "main", cwd=path)
    git("config", "user.name", "Test Owner", cwd=path)
    git("config", "user.email", "owner@example.test", cwd=path)
    git("add", "-A", cwd=path)
    git("commit", "-qm", message, "--allow-empty", cwd=path)


def prepare(root: Path, pstack: Path, dotbrain: str, scenario: str = "continuation",
            guidance: Path = REPO) -> None:
    """Build a data home with stock pstack selected and one wired task-list checkout."""
    root.mkdir(parents=True)
    (root / "case.txt").write_text(scenario, encoding="utf-8")
    shutil.copytree(guidance / "plugin", root / "plugin", ignore=shutil.ignore_patterns("__pycache__"))
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

    env = {**os.environ, "DOTBRAIN_HOME": str(data), "BEADS_DIR": str(ws / ".beads")}
    subprocess.run([dotbrain, "wire", "--home", str(data), "--repo", str(ws), "--project", PROJECT],
                   check=True, env=env)
    declaration = data / "brainspaces" / PROJECT / ".brain/project.yaml"
    declaration.write_text(declaration.read_text(encoding="utf-8").rstrip("\n")
                           + "\nskills:\n  - pstack/skills\n", encoding="utf-8")
    subprocess.run([dotbrain, "skills", "link", "--home", str(data), "--repo", str(ws)], check=True, env=env)
    brain = declaration.parent
    templates = guidance / "src/dotbrain/resources/templates/brain"
    for template in templates.rglob("*.md"):
        target = brain / template.relative_to(templates)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(template, target)
    (brain / "docs").mkdir(exist_ok=True)
    (brain / "docs/user-notes.md").write_text(USER_NOTE, encoding="utf-8")
    if scenario == "retirement":
        (brain / "designs").mkdir(exist_ok=True)
        (brain / RETIRED_FILES[0]).write_text(
            "# Daily digest\n\nRun `python -m todo.cli digest` for today's digest.\n", encoding="utf-8")
        (brain / RETIRED_FILES[1]).write_text(
            "---\nlifecycle: shipped\n---\n\n# Daily digest\n\nDelivered the digest command.\n",
            encoding="utf-8")
        (brain / "docs/index.md").write_text(
            "# Guides\n\n[Daily digest](daily-digest.md)\n\n[User notes](user-notes.md)\n", encoding="utf-8")
    subprocess.run(["bd", "create", "Manual keyboard review", "--type", "task", "--assignee", "operator",
                    "--acceptance", "Operator checks keyboard navigation; leave open until that review.",
                    "--actor", "eval-fixture", "--json"], cwd=ws, env=env, check=True, capture_output=True)
    (root / "initial-issues.json").write_text(json.dumps(issues_at(ws), indent=2), encoding="utf-8")
    git("add", "-A", cwd=data)
    git("commit", "-qm", READY_COMMIT, "--allow-empty", cwd=data)


def run(root: Path, runtime: str, session: str, executable: str, timeout: int, home: Path | None = None) -> int:
    """Launch one fresh headless session in the workspace and keep its JSONL transcript."""
    ws, out = root / "workspace", root / "results" / f"{runtime}-{session}.jsonl"
    env = {k: v for k, v in os.environ.items() if not k.startswith(("CLAUDE", "CODEX", "ANTHROPIC_API", "OPENAI_API"))}
    home = home or root / "home" / runtime
    env.update(DOTBRAIN_HOME=str(root / "data"), BEADS_DIR=str(ws / ".beads"),
               **{"CLAUDE_CONFIG_DIR" if runtime == "claude" else "CODEX_HOME": str(home)})
    if os.environ.get("CLAUDE_CODE_GIT_BASH_PATH"):
        env["CLAUDE_CODE_GIT_BASH_PATH"] = os.environ["CLAUDE_CODE_GIT_BASH_PATH"]
    task = ENTRY[runtime] + TASKS[case(root)][session]
    if runtime == "claude":
        argv = [executable, "-p", task, "--plugin-dir", str(root / "plugin"), "--dangerously-skip-permissions",
                "--max-turns", "100", "--output-format", "stream-json", "--verbose"]
    else:
        argv = [executable, "exec", task, "--json", "-C", str(ws), "--dangerously-bypass-approvals-and-sandbox"]
    started = time.monotonic()
    with out.open("w", encoding="utf-8") as stdout, out.with_suffix(".err").open("w", encoding="utf-8") as stderr:
        try:
            result = subprocess.run(argv, cwd=ws, env=env, stdin=subprocess.DEVNULL, stdout=stdout,
                                    stderr=stderr, timeout=timeout).returncode
        except subprocess.TimeoutExpired:
            result = 124
    out.with_suffix(".run.json").write_text(json.dumps({
        "returncode": result, "duration_seconds": time.monotonic() - started,
        "workspace_revision": git("rev-parse", "HEAD", cwd=ws).strip(),
    }, indent=2), encoding="utf-8")
    out.with_suffix(".issues.json").write_text(json.dumps(issues_at(ws), indent=2), encoding="utf-8")
    return result


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


def probe(ws: Path, scenario: str) -> bool:
    """Exercise the caller-visible outcome independently of agent-authored tests."""
    if scenario in {"experiment", "retirement"}:
        return ((ws / "todo/store.py").read_text(encoding="utf-8") == STORE
                and (ws / "todo/cli.py").read_text(encoding="utf-8") == CLI)
    with tempfile.TemporaryDirectory() as directory:
        env = {**os.environ, "PYTHONPATH": str(ws)}
        path = Path(directory)
        if scenario == "routine":
            script = ("from pathlib import Path\nfrom todo import store\n"
                      "path = Path('tasks.json')\nstore.add(path, 'older')\nstore.add(path, 'newer')\n"
                      "store.complete(path, 1)\nstore.add(path, 'newest')\n"
                      "assert [task['title'] for task in store.pending(path)] == ['newest', 'newer']\n")
            return subprocess.run([sys.executable, "-c", script], cwd=path, env=env,
                                  capture_output=True, timeout=30).returncode == 0
        from datetime import date, timedelta
        today = date.today()
        tasks = [
            {"id": 1, "title": "future", "done": False, "due": str(today + timedelta(days=2))},
            {"id": 2, "title": "legacy", "done": False},
            {"id": 3, "title": "late", "done": False, "due": str(today - timedelta(days=2))},
            {"id": 4, "title": "finished", "done": True, "due": str(today - timedelta(days=3))},
            {"id": 5, "title": "today", "done": False, "due": str(today)},
        ]
        (path / "tasks.json").write_text(json.dumps(tasks), encoding="utf-8")
        for command, expected in (("list", {1, 2, 3, 5}), ("overdue", {3})):
            result = subprocess.run([sys.executable, "-m", "todo.cli", command], cwd=path, env=env,
                                    capture_output=True, text=True, timeout=30)
            lines = result.stdout.splitlines()
            matches = [re.match(r"(\d+):", line) for line in lines]
            identifiers = [int(match[1]) for match in matches if match]
            if (result.returncode or len(identifiers) != len(expected)
                    or set(identifiers) != expected or identifiers[0] != 3):
                return False
        result = subprocess.run([sys.executable, "-m", "todo.cli", "add", "new", "--due", str(today)],
                                cwd=path, env=env, capture_output=True, timeout=30)
        saved = json.loads((path / "tasks.json").read_text(encoding="utf-8"))
        return result.returncode == 0 and any(task["title"] == "new" and task.get("due") == str(today) for task in saved)


def grade(root: Path, runtime: str, bd=None, review: dict | None = None) -> dict[str, bool]:
    """Combine artifact checks with a separate review of semantic outcomes."""
    ws, data = root / "workspace", root / "data"
    issues = json.loads(bd()) if bd else issues_at(ws)
    initial = json.loads((root / "initial-issues.json").read_text(encoding="utf-8"))
    ready = git("log", "--format=%H", f"--grep={READY_COMMIT}", cwd=data).split()[0]
    scope = f"brainspaces/{PROJECT}/.brain"
    brain = (git("diff", "--name-only", ready, "--", scope, cwd=data)
             + git("ls-files", "--others", "--exclude-standard", "--", scope, cwd=data)).split()
    s1, s2 = (actions(events(root / "results" / f"{runtime}-{s}.jsonl")) for s in ("s1", "s2"))
    outcomes = []
    for session in ("s1", "s2"):
        path = root / "results" / f"{runtime}-{session}.run.json"
        outcomes.append(json.loads(path.read_text(encoding="utf-8")) if path.exists() else {})
    current = {issue["id"]: issue for issue in issues}
    scenario = case(root)
    checks = {
        "sessions_ran": bool(s1) and bool(s2),
        "sessions_succeeded": all(outcome.get("returncode") == 0 for outcome in outcomes),
        "observable_outcome": probe(ws, scenario),
        "user_note_preserved": (data / scope / "docs/user-notes.md").is_file()
        and (data / scope / "docs/user-notes.md").read_text(encoding="utf-8") == USER_NOTE,
        "existing_work_preserved": all(
            issue["id"] in current and all(current[issue["id"]].get(field) == issue.get(field)
                                          for field in WORK_FIELDS) for issue in initial),
        "no_transcript_reads": not reads_transcripts(s1 + s2),
    }
    if scenario == "routine":
        checks["no_new_records"] = not brain and {issue["id"] for issue in issues} == {issue["id"] for issue in initial}
    if scenario == "retirement":
        checks["obsolete_records_removed"] = all(not (data / scope / name).exists() for name in RETIRED_FILES)
        checks["pointers_repaired"] = all(
            (document.parent / target.split("#")[0]).exists()
            for document in (data / scope).rglob("*.md")
            for target in re.findall(r"\]\(([^)]+)\)", document.read_text(encoding="utf-8"))
            if target and not target.startswith(("http:", "https:", "#")))
    for criterion in REVIEW_CRITERIA:
        assessment = (review or {}).get(criterion, {})
        checks[criterion] = assessment.get("passed") is True and bool(assessment.get("evidence", "").strip())
    return checks


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("root", type=Path)
    p.add_argument("--pstack", type=Path, required=True, help="local pstack checkout to clone from")
    p.add_argument("--dotbrain", default=shutil.which("dotbrain") or "dotbrain")
    p.add_argument("--case", choices=TASKS, default="continuation")
    p.add_argument("--guidance-from", type=Path, default=REPO,
                   help="source checkout supplying the convention and core plugin snapshot")
    r = sub.add_parser("run")
    r.add_argument("root", type=Path)
    r.add_argument("--runtime", choices=ENTRY, required=True)
    r.add_argument("--session", choices=("s1", "s2"), required=True)
    r.add_argument("--executable", required=True)
    r.add_argument("--timeout-seconds", type=int, default=1800)
    r.add_argument("--runtime-home", type=Path, help="signed-in runtime home to use instead of ROOT/home/RUNTIME")
    r.add_argument("--allow-native", action="store_true")
    g = sub.add_parser("grade")
    g.add_argument("root", type=Path)
    g.add_argument("--runtime", choices=ENTRY, required=True)
    g.add_argument("--review", type=Path, help="independent evidence-backed assessment; omitted criteria fail")
    args = parser.parse_args(argv)
    if args.command == "prepare":
        prepare(args.root.resolve(), args.pstack.resolve(strict=True), args.dotbrain, args.case,
                args.guidance_from.resolve(strict=True))
        return 0
    if args.command == "run":
        if not args.allow_native:
            parser.error("native model calls require --allow-native")
        return run(args.root.resolve(), args.runtime, args.session, args.executable, args.timeout_seconds, args.runtime_home)
    review = json.loads(args.review.read_text(encoding="utf-8")) if args.review else None
    result = grade(args.root.resolve(), args.runtime, review=review)
    print(json.dumps(result, indent=2))
    return 0 if all(result.values()) else 1


if __name__ == "__main__":
    sys.exit(main())

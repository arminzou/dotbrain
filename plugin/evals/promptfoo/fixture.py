"""Disposable, model-free fixture lifecycle; see README.md for the pilot seam."""

import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import tempfile


EVALS = Path(__file__).resolve().parent.parent


def _write(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def _shell(bash):
    if not bash and os.name == "nt":
        raise ValueError("select Git Bash explicitly with --bash (default bash may be WSL)")
    shell = Path(bash or shutil.which("bash") or "").resolve()
    if not shell.is_file():
        raise ValueError("Bash executable not found")
    return shell


def _environment(root, shell):
    # No inherited tokens, tracker endpoints, Git overrides, or runtime homes.
    env = {k: v for k, v in os.environ.items() if k.upper() in {
        "SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT", "SYSTEMDRIVE",
    }}
    home = root / "home"
    dirs = {
        "HOME": home, "USERPROFILE": home,
        "APPDATA": home / "appdata", "LOCALAPPDATA": home / "localappdata",
        "XDG_CONFIG_HOME": home / ".config", "XDG_CACHE_HOME": home / ".cache",
        "XDG_DATA_HOME": home / ".local/share", "XDG_STATE_HOME": home / ".local/state",
        "CODEX_HOME": home / ".codex", "CLAUDE_CONFIG_DIR": home / ".claude",
        "DOTBRAIN_HOME": root / "data", "TMPDIR": root,
        "TMP": root / "tmp", "TEMP": root / "tmp",
    }
    for key, path in dirs.items():
        path.mkdir(parents=True, exist_ok=True)
        env[key] = path.as_posix()
    if os.name == "nt":
        # Git Bash's own tools only; never inherit a real bd/gh from host PATH.
        git_root = shell.parent.parent
        tools = [git_root / "bin", git_root / "usr/bin", git_root / "mingw64/bin"]
    else:
        tools = [shell.parent, Path("/usr/bin"), Path("/bin")]
    env.update({
        "PATH": os.pathsep.join(str(p) for p in [root / "workspace/.eval/bin", *tools]),
        "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_TERMINAL_PROMPT": "0", "GIT_ALLOW_PROTOCOL": "file",
        "GIT_TRACE2_EVENT": (root / "workspace/.eval/calls.log").as_posix(),
        "LANG": "C.UTF-8", "PROMPTFOO_DISABLE_TELEMETRY": "1",
    })
    return env


def _process(fixture, argv, phase, *, trace=False):
    env = dict(fixture["env"])
    if not trace:
        env.pop("GIT_TRACE2_EVENT", None)
    evidence = Path(fixture["evidence"])
    with (evidence / f"{phase}.stdout").open("wb") as out, (evidence / f"{phase}.stderr").open("wb") as err:
        return subprocess.run(argv, cwd=fixture["workspace"], env=env, stdout=out, stderr=err, check=False).returncode


def setup(case, provider, repeat=0, *, parent=None, bash=None):
    """Build once at the final path. Failures leave their manifest and evidence."""
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", case) or not (EVALS / case / "prompt.md").is_file():
        raise ValueError("unknown case")
    if not provider or not isinstance(repeat, int) or repeat < 0:
        raise ValueError("provider and nonnegative repeat are required")
    shell = _shell(bash)
    root = Path(tempfile.mkdtemp(prefix="pf-fixture-", dir=parent)).resolve()
    ws, evidence = root / "workspace", root / "evidence"
    ws.mkdir()
    evidence.mkdir()
    fixture = {
        "case": case, "provider": provider, "repeat": repeat,
        "root": str(root), "workspace": str(ws), "home": str(root / "home"),
        "origin": str(ws / ".eval/remote.git"), "evidence": str(evidence),
        "calls": str(ws / ".eval/calls.log"), "pushes": str(ws / ".eval/pushes.log"),
        "fixture_state": str(ws / ".eval/fixtures"),
        "manifest": str(root / "fixture.json"), "bash": str(shell),
        "env": _environment(root, shell),
    }
    _write(root / "fixture.json", fixture)
    script = EVALS / case / "fixture.sh"
    if script.is_file():
        action = '. "$1"'
    else:
        script = EVALS / "_shared/scaffold.sh"
        action = '. "$1"; fixture_done'
    code = _process(fixture, [str(shell), "--noprofile", "--norc", "-c", action, "setup", script.as_posix()], "setup")
    if code:
        raise RuntimeError(f"fixture setup failed ({code}); retained {root}")
    # Probe only resolution and final bindings. Never execute bd/gh as setup evidence.
    probe = '''set -eux
test "$(command -v bd)" = "$PWD/.eval/bin/bd"
test "$(command -v gh)" = "$PWD/.eval/bin/gh"
remote=$(git remote get-url origin)
case "$remote" in /* | [A-Za-z]:/*) ;; *) exit 1 ;; esac
test "$remote" -ef "$PWD/.eval/remote.git"
test "$GIT_TRACE2_EVENT" -ef "$PWD/.eval/calls.log"
printf '%s\\n' "$PWD" "$HOME" "$PATH" "$GIT_TRACE2_EVENT"
command -v bd gh
git remote get-url origin
'''
    code = _process(fixture, [str(shell), "--noprofile", "--norc", "-c", probe], "bindings", trace=True)
    # Even the probe's Git read is setup, never agent activity.
    (ws / ".eval/calls.log").write_text("", encoding="utf-8")
    if code:
        raise RuntimeError(f"fixture bindings failed ({code}); retained {root}")
    _write(evidence / "setup.json", {"pass": True})
    return fixture


def load(manifest):
    """Reject moved/copied fixtures: embedded absolute paths are not portable."""
    path = Path(manifest).absolute()
    fixture = json.loads(path.read_text(encoding="utf-8"))
    root = Path(fixture["root"])
    if (not root.is_absolute() or not root.name.startswith("pf-fixture-")
            or root.resolve() != root or root.is_symlink()
            or root.resolve() != path.parent.resolve() or path.name != "fixture.json"
            or Path(fixture["workspace"]) != root / "workspace"
            or Path(fixture["evidence"]) != root / "evidence"):
        raise ValueError("fixture moved, copied, or has invalid paths; setup at the final location")
    return fixture


def validate_links(fixture):
    """Resource staging may create internal links, never external or dangling links."""
    root = Path(fixture["root"]).resolve()
    for directory, dirs, files in os.walk(root, followlinks=False):
        for name in [*dirs, *files]:
            path = Path(directory, name)
            if path.is_symlink() or (os.name == "nt" and path.lstat().st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT):
                target = path.resolve(strict=True)
                if not target.is_relative_to(root):
                    raise ValueError(f"fixture link escapes temporary root: {path}")
                if name in dirs:
                    dirs.remove(name)


def run(fixture, argv, *, dry_run=False):
    """Execute an explicit command with the fixture env; never choose a model/SDK."""
    if not argv:
        raise ValueError("command required")
    if dry_run:
        return {"argv": argv, "cwd": fixture["workspace"], "env": fixture["env"]}
    evidence = Path(fixture["evidence"])
    if not (evidence / "setup.json").is_file():
        raise ValueError("fixture setup did not complete")
    if (evidence / "run.json").exists() or (evidence / "assertions.json").exists():
        raise ValueError("one invocation per fixture; setup a new fixture for every repeat")
    validate_links(fixture)
    _write(evidence / "run.json", {"argv": argv, "returncode": None})
    code = _process(fixture, argv, "run", trace=True)
    _write(evidence / "run.json", {"argv": argv, "returncode": code})
    return code


def assert_fixture(fixture, rules=None):
    """Capture deterministic checks before cleanup; missing activity fails closed."""
    evidence = Path(fixture["evidence"])
    try:
        validate_links(fixture)
        spec = importlib.util.spec_from_file_location("eval_state_checker", EVALS / "_shared/check.py")
        checker = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(checker)
        if rules is None:
            checks = EVALS / fixture["case"] / "checks"
            rules = checks.read_text(encoding="utf-8").splitlines() if checks.exists() else ["no-push", "no-merge", "no-close"]
        rules = [rule for rule in rules if rule.strip()]
        if not rules:
            raise ValueError("at least one state rule required")
        report = checker.run(fixture["workspace"], rules)
        invocation = json.loads((evidence / "run.json").read_text(encoding="utf-8"))
        passed = invocation["returncode"] == 0 and all(v["pass"] for v in report.values())
        result = {"pass": passed, "checks": report, "returncode": invocation["returncode"]}
    except (OSError, ValueError, KeyError, IndexError, subprocess.SubprocessError) as exc:
        result = {"pass": False, "error": str(exc)}
    _write(evidence / "assertions.json", result)
    return result


def cleanup(fixture):
    """Remove only a validated temporary root with successful stored assertions."""
    fixture = load(fixture["manifest"])
    result = json.loads((Path(fixture["evidence"]) / "assertions.json").read_text(encoding="utf-8"))
    if not result["pass"]:
        raise ValueError("failed assertions; retain fixture evidence")
    validate_links(fixture)
    def remove_readonly(function, path, error):
        if not isinstance(error[1], PermissionError):
            raise error[1]
        # Git object files are read-only on Windows, including the local origin.
        Path(path).chmod(stat.S_IREAD | stat.S_IWRITE)
        function(path)
    shutil.rmtree(fixture["root"], onerror=remove_readonly)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    create = commands.add_parser("setup")
    create.add_argument("case")
    create.add_argument("provider")
    create.add_argument("--repeat", type=int, default=0)
    create.add_argument("--parent", type=Path)
    create.add_argument("--bash")
    for action in ("run", "assert", "cleanup"):
        command = commands.add_parser(action)
        command.add_argument("manifest")
        if action == "run":
            command.add_argument("--dry-run", action="store_true")
            command.add_argument("argv", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.action == "setup":
        print(json.dumps(setup(args.case, args.provider, args.repeat, parent=args.parent, bash=args.bash), indent=2))
        return 0
    fixture = load(args.manifest)
    if args.action == "run":
        argv = args.argv[1:] if args.argv[:1] == ["--"] else args.argv
        result = run(fixture, argv, dry_run=args.dry_run)
        if args.dry_run:
            print(json.dumps(result, indent=2))
            return 0
        return result
    if args.action == "assert":
        result = assert_fixture(fixture)
        print(json.dumps(result, indent=2))
        return 0 if result["pass"] else 1
    cleanup(fixture)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

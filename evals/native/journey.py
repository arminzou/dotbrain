"""Private native qualification fixture. No models run unless `run --allow-native` is explicit."""

from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import time
import uuid


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value if isinstance(value, str) else json.dumps(value, indent=2), encoding="utf-8", newline="\n")


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def confined(root, name):
    path = root / name
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"Path escapes fixture: {name}")
    return path


def brainspace(root):
    manifest = confined(root, "fixture.json")
    if manifest.exists() and load(manifest).get("schema", 1) < 2:
        return confined(root, "workspace")
    return confined(root, "data/brainspaces/catalog")


def plugin_source(root, manifest):
    """Hash tracked candidate resources, never ignored checkout or runtime-home files."""
    result = subprocess.run(["git", "-C", manifest["candidate"], "archive", manifest["candidateRevision"], "plugin"],
                            env=environment(root), capture_output=True, check=True, timeout=30)
    files = {}
    with tarfile.open(fileobj=io.BytesIO(result.stdout)) as archive:
        for member in archive:
            if member.isdir():
                continue
            if not member.isfile():
                raise ValueError("Tracked plugin resource is an alias")
            files[member.name.removeprefix("plugin/")] = archive.extractfile(member).read()
    version = json.loads(files[".claude-plugin/plugin.json"])["version"]
    if not re.fullmatch(r"[0-9A-Za-z._-]+", version):
        raise ValueError("Invalid tracked plugin version")
    return version, {name: hashlib.sha256(value).hexdigest() for name, value in files.items()}


def verified_plugins(root, manifest, phase):
    attempt = next((item for item in manifest.get("attempts", []) if item["name"] == phase), None)
    if not attempt or not manifest.get("candidate"):
        return {}
    version, expected = plugin_source(root, manifest)
    runtime = ".codex" if attempt["runtime"] == "codex" else ".claude"
    plugin = root / "homes" / phase / runtime / "plugins/cache/dotbrain/dotbrain" / version
    # Check only the canonical path's ancestors; never enumerate a home or auth directory.
    for parent in reversed(plugin.relative_to(root).parents):
        path = root / parent
        if path.exists() and is_alias(path):
            raise ValueError("Installed plugin ancestor is redirected")
    if not plugin.exists() and not plugin.is_symlink():
        return {}
    actual = {}
    for path, info in walk_entries([plugin]):
        if is_alias(path, info) or (stat.S_ISREG(info.st_mode) and info.st_nlink > 1):
            raise ValueError("Installed plugin contains an alias")
        if stat.S_ISREG(info.st_mode):
            name = path.relative_to(plugin).as_posix()
            if name not in expected:
                raise ValueError("Installed plugin contains an untracked resource")
            actual[name] = digest(path)
    if actual != expected:
        raise ValueError("Installed plugin differs from tracked candidate resources")
    return {str(plugin): {"candidateRevision": manifest["candidateRevision"], "files": actual}}


def read_roots(root, manifest, phase=None, plugins=None):
    return [root / "workspace", brainspace(root) / ".brain",
            root / "data/.cache/integrations/dotbrain-pstack",
            Path(manifest.get("candidate", root / "absent")) / "plugin",
            Path(manifest.get("candidate", root / "absent")) / "src/dotbrain/resources",
            Path(manifest.get("pstack", root / "absent")),
            *(Path(path) for path in (verified_plugins(root, manifest, phase) if plugins is None else plugins))]


def is_alias(path, info=None):
    info = info or path.lstat()
    return stat.S_ISLNK(info.st_mode) or getattr(info, "st_reparse_tag", 0) == 0xA0000003


def walk_entries(roots):
    """Yield metadata and reject directory aliases before any descent."""
    pending = list(roots)
    visited = set()
    while pending:
        path = pending.pop()
        key = os.path.normcase(os.path.abspath(path))
        if key in visited:
            continue
        visited.add(key)
        try:
            info = path.lstat()
        except FileNotFoundError:
            continue
        yield path, info
        if stat.S_ISDIR(info.st_mode) and not is_alias(path, info):
            with os.scandir(path) as entries:
                pending.extend(Path(entry.path) for entry in entries)


def capture_aliases(root, phase):
    """Freeze bounded namespace metadata without following links or opening their targets."""
    from verify import lexical_identity
    manifest = load(root / "fixture.json")
    plugins = verified_plugins(root, manifest, phase)
    roots = read_roots(root, manifest, phase, plugins)
    private = root / "private"
    if is_alias(private):
        raise ValueError("Controller evidence directory is redirected")
    controller_ids = {}
    for path in private.iterdir():
        info = path.lstat()
        if stat.S_ISREG(info.st_mode) and info.st_ino:
            controller_ids[(info.st_dev, info.st_ino)] = lexical_identity(str(path), str(root))
    aliases = {}
    homes = lexical_identity(str(root / "homes"), str(root))
    for path, info in walk_entries(roots):
        key = lexical_identity(str(path), str(root))
        if (key == homes or key.startswith(homes + "\\")) and not any(
                path == Path(plugin) or path.is_relative_to(Path(plugin)) for plugin in plugins):
            raise ValueError("Alias capture cannot traverse runtime homes")
        if is_alias(path, info):
            aliases[key] = lexical_identity(os.readlink(path), str(path.parent))
        elif stat.S_ISREG(info.st_mode) and info.st_nlink > 1:
            target = controller_ids.get((info.st_dev, info.st_ino))
            if target:
                aliases[key] = target
    return {"schema": 1, "phase": phase, "root": lexical_identity(str(root), str(root)),
            "capturedAt": time.time(), "roots": sorted({lexical_identity(str(path), str(root)) for path in roots}),
            "aliases": dict(sorted(aliases.items())), "plugins": plugins}


def environment(root, phase="setup"):
    # An allowlist prevents inherited backend routing and API credentials from selecting live state.
    env = {key: value for key, value in os.environ.items()
           if key.upper() in {"PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "COMSPEC", "SYSTEMDRIVE"}}
    home = confined(root, f"homes/{phase}")
    for name in (".codex", ".claude", ".config", "tmp", "AppData/Roaming", "AppData/Local"):
        confined(home, name).mkdir(parents=True, exist_ok=True)
    env.update(HOME=str(home), USERPROFILE=str(home), CODEX_HOME=str(home / ".codex"),
               CLAUDE_CONFIG_DIR=str(home / ".claude"), APPDATA=str(home / "AppData/Roaming"),
               LOCALAPPDATA=str(home / "AppData/Local"), XDG_CONFIG_HOME=str(home / ".config"),
               TMP=str(home / "tmp"), TEMP=str(home / "tmp"), TMPDIR=str(home / "tmp"),
               DOTBRAIN_HOME=str(root / "data"), BEADS_DIR=str(brainspace(root) / ".beads"),
               PYTHONDONTWRITEBYTECODE="1",
               BD_NON_INTERACTIVE="1", GIT_CONFIG_GLOBAL=str(home / ".gitconfig"),
               GIT_CONFIG_NOSYSTEM="1", GIT_TERMINAL_PROMPT="0", NATIVE_FIXTURE_ROOT=str(root),
               NATIVE_FIXTURE_PHASE=phase)
    manifest = confined(root, "fixture.json")
    if manifest.exists() and load(manifest).get("candidate"):
        env["PYTHONPATH"] = str(Path(load(manifest)["candidate"]) / "src")
    return env


def execute(root, argv, *, phase="setup", check=True, run=subprocess.run, cwd=None):
    result = run([str(a) for a in argv], cwd=cwd or confined(root, "workspace"), env=environment(root, phase),
                 text=True, encoding="utf-8", capture_output=True, timeout=120, check=False)
    if check and result.returncode:
        raise RuntimeError(f"Command failed ({result.returncode}): {argv}\n{result.stderr}")
    return result


def bd(root, args, *, phase="setup", check=True, run=subprocess.run):
    manifest = load(confined(root, "fixture.json"))
    # All tracker calls use an explicit backend and no ambient server/global switches.
    if any(arg.split("=", 1)[0] in {"--global", "--db", "--database", "--directory", "-C", "--repo"}
           or arg.startswith("-C") for arg in args):
        raise ValueError("Tracker routing overrides are forbidden")
    backend_probe = args in (["dolt", "test"], ["--readonly", "dolt", "test"], ["--readonly", "ready", "--json"])
    if not args or (not backend_probe and args[0] not in {"init", "version", "where", "prime", "ready", "list", "show",
                                                        "comments", "create", "update", "close", "reopen", "dep"}):
        raise ValueError("Tracker command is outside the isolated journey")
    if phase != "setup" and args[0] == "init":
        raise ValueError("Only fixture setup may initialize the backend")
    if args[0] in {"create", "update", "close", "reopen", "init", "dep"} or args[:2] == ["comments", "add"]:
        if "--actor" not in args or args.index("--actor") + 1 >= len(args):
            raise ValueError("Tracker writes require an explicit actor")
    result = execute(root, [manifest["bd"], *args], phase=phase, check=False, run=run,
                     cwd=brainspace(root) if args[0] == "init" else None)
    receipt = dict(argv=args, phase=phase, returncode=result.returncode,
                   stdout=result.stdout, stderr=result.stderr, time=time.time())
    with confined(root, "private/beads.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(receipt) + "\n")
    if check and result.returncode:
        raise RuntimeError(f"bd failed ({result.returncode}): {result.stderr}")
    return result


CHECK_SCRIPT = '''import hashlib
import json
from pathlib import Path
import subprocess

receipt = {"check": "catalog-v1", "revision": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
           "scriptSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "ok": False}
try:
    assert json.loads(Path("api.json").read_text()) == {"pageSize": 7}
    assert json.loads(Path("ui.json").read_text()) == {"pageSize": 7}
    receipt["ok"] = True
except (OSError, ValueError, AssertionError) as error:
    receipt["error"] = str(error)
print(json.dumps(receipt))
raise SystemExit(0 if receipt["ok"] else 1)
'''


def snapshot(root, name):
    value = {"items": json.loads(bd(root, ["list", "--all", "--limit", "0", "--json"]).stdout),
             "ready": json.loads(bd(root, ["ready", "--json"]).stdout), "details": {},
             "head": execute(root, ["git", "rev-parse", "HEAD"]).stdout.strip(),
             "status": execute(root, ["git", "status", "--porcelain"]).stdout,
             "refs": dict(line.split() for line in execute(root, ["git", "for-each-ref",
                         "--format=%(refname:short) %(objectname)", "refs/heads"]).stdout.splitlines()),
             "knowledge": {}}
    value["checkSha256"] = digest(confined(root, "workspace/check.py"))
    for item in value["items"]:
        value["details"][item["id"]] = {
            "show": json.loads(bd(root, ["show", item["id"], "--json"]).stdout),
            "comments": json.loads(bd(root, ["comments", item["id"], "--json"]).stdout)}
    brain = brainspace(root) / ".brain"
    if is_alias(brain):
        raise ValueError("Owning Brain directory is redirected")
    for file, info in walk_entries([brain]):
        if is_alias(file, info) or info.st_nlink > 1:
            continue
        if stat.S_ISREG(info.st_mode):
            confined(root, file.relative_to(root))
            value["knowledge"][str(file.relative_to(brain)).replace("\\", "/")] = file.read_text(encoding="utf-8")
    write(confined(root, f"private/{name}.json"), value)
    return value


def prepare(root, candidate, pstack, binary):
    if root.exists():
        raise ValueError("Use a new fixture root; previous attempts are never overwritten")
    root.mkdir(parents=True, mode=0o700)
    for name in ("workspace", "private", "bin", "data/brainspaces/catalog/.brain/docs"):
        confined(root, name).mkdir(parents=True)
    manifest = {"schema": 2, "root": str(root), "candidate": str(candidate), "pstack": str(pstack),
                "bd": str(binary), "sentinel": "PRIVATE-" + uuid.uuid4().hex,
                "priorAllowances": {"status": "exhausted", "renewed": False},
                "sessionLimit": 12, "consecutiveFailureLimit": 3, "attempts": [], "wiringAttempts": []}
    for key, checkout in (("candidateRevision", candidate), ("pstackRevision", pstack)):
        result = subprocess.run(["git", "-C", str(checkout), "rev-parse", "HEAD"],
                                capture_output=True, text=True, check=True, env=environment(root), timeout=120)
        manifest[key] = result.stdout.strip()
    write(root / "fixture.json", manifest)
    execute(root, ["git", "init", "-q", str(root / "data")])
    write(root / "data/config.yaml", "version: 4\nskills: []\nsubagents: []\n")
    write(root / "data/.gitignore", "brainspaces/*/.beads/\n")
    execute(root, ["git", "init", "-q", "-b", "main"])
    execute(root, ["git", "config", "user.name", "Fixture"])
    execute(root, ["git", "config", "user.email", "fixture@example.invalid"])
    execute(root, ["git", "config", "core.autocrlf", "false"])
    write(root / "workspace/.gitignore", ".brain/\n.beads/\n.codex/\n.claude/\n.agents/\n")
    write(root / "workspace/README.md", "# Catalog fixture\nReturn only public catalog fields.\n")
    write(root / "workspace/config.json", {"pageSize": 7})
    write(root / "workspace/check.py", CHECK_SCRIPT)
    write(root / "workspace/wait.py", "import time\ntime.sleep(1800)\n")
    write(brainspace(root) / ".brain/docs/decision.md",
          "# Catalog contract\nThe accepted public page size is seven. Internal supplier labels stay private.\n" + manifest["sentinel"] + "\n")
    write(brainspace(root) / ".brain/project.yaml", "agents: [claude-code, codex]\nbeads:\n  mode: embedded\npstack:\n  enabled: true\n  source: " + json.dumps(str(pstack)) + "\n")
    write(root / "workspace/AGENTS.md", "# Catalog fixture\nRead project knowledge before changing the contract. Use the selected project mode.\nAll tracker writes require an explicit --actor. Never publish private context.\n")
    execute(root, ["git", "add", "."])
    execute(root, ["git", "commit", "-qm", "Seed catalog fixture"])
    bd(root, ["init", "--stealth", "--prefix", "sample", "--skip-agents", "--skip-hooks", "--non-interactive",
              "--actor", "fixture-setup"])
    ids = {}
    for role, title in (("contract", "Settle catalog API contract"), ("api", "Implement catalog API"),
                        ("ui", "Implement catalog UI"), ("integration", "Verify catalog integration")):
        item = json.loads(bd(root, ["create", title, "--description", "Catalog qualification fixture",
                                   "--acceptance", "Pass recorded checks with candidate evidence; preserve private data",
                                   "--actor", "fixture-setup", "--json"]).stdout)
        ids[role] = item["id"]
    for child, parent in (("api", "contract"), ("ui", "contract"), ("integration", "api"), ("integration", "ui")):
        bd(root, ["dep", "add", ids[child], ids[parent], "--actor", "fixture-setup"])
    manifest["ids"] = ids
    manifest["bdVersion"] = execute(root, [binary, "version"]).stdout
    write(root / "fixture.json", manifest)
    # The proxy delegates to the actual executable, never to a synthetic tracker implementation.
    script = Path(__file__).resolve()
    write(root / "bin/bd.cmd", f'@"{sys.executable}" "{script}" proxy "{root}" %*\r\n')
    shell = root / "bin/bd"
    import shlex
    write(shell, "#!/bin/sh\nexec " + " ".join(shlex.quote(str(x)) for x in (sys.executable, script, "proxy", root)) + ' "$@"\n')
    shell.chmod(0o755)
    snapshot(root, "baseline")
    return manifest


def wire(root, executable, *, run=subprocess.run):
    """Invoke the candidate CLI; source Brainspace owns state before repository attachment."""
    manifest = load(root / "fixture.json")
    env = environment(root)
    env["PYTHONPATH"] = str(Path(manifest["candidate"]) / "src")
    env["PATH"] = str(Path(manifest["bd"]).parent) + os.pathsep + env.get("PATH", "")
    argv = [executable, "wire", "--home", str(root / "data"), "--repo", str(root / "workspace"),
            "--project", "catalog", "--json"]
    before = json.loads(bd(root, ["list", "--all", "--limit", "0", "--json"]).stdout)
    result = run(argv, cwd=root / "workspace", env=env, capture_output=True, text=True,
                 encoding="utf-8", timeout=120, check=False)
    receipt = {"argv": argv, "exitCode": result.returncode, "stdout": result.stdout,
               "stderr": result.stderr, "time": time.time(), "candidateRevision": subprocess.run(
                   ["git", "-C", manifest["candidate"], "rev-parse", "HEAD"], env=env,
                   capture_output=True, text=True, check=True, timeout=30).stdout.strip()}
    for name in (".brain", ".beads"):
        link = confined(root, "workspace/" + name)
        receipt[name] = link.is_symlink() and link.resolve() == (brainspace(root) / name).resolve()
    after = json.loads(bd(root, ["list", "--all", "--limit", "0", "--json"]).stdout)
    receipt["backendPreserved"] = before == after
    manifest["wiringAttempts"].append(receipt)
    write(root / "fixture.json", manifest)
    write(root / f"private/wire-{len(manifest['wiringAttempts'])}.json", receipt)
    if result.returncode or not all(receipt[name] for name in (".brain", ".beads", "backendPreserved")):
        raise ValueError("Supported candidate wiring failed; preserve receipt and resolve delivery prerequisite")
    return receipt


def prompt(manifest, phase):
    ids = manifest["ids"]
    common = ("Use the project's selected workflow and actual Beads graph. Read relevant knowledge; "
              "all writes need explicit actors. Keep private details out of tracked/public artifacts. "
              f"Work IDs: {json.dumps(ids)}. Preserve all failed attempts and consumed limits. ")
    if phase == "first":
        return common + ("Investigate config.json; record verified page-size evidence, an explicitly unresolved "
                         "latency hypothesis, and next work in durable knowledge and Beads. Write .brain/docs/discovery.json "
                         "with pageSize:7, sourceSha256:the actual SHA256 of config.json, and hypothesis: "
                         "{claim:'Latency cause is unknown',status:'unresolved'}. Settle the contract "
                         "before starting dependent API/UI work. Exercise competing claims with different actors. "
                         "Delegate isolated API/UI work and record worker identities, branches and candidate commits. "
                         "The coordinator claims both tasks under its own Beads actor; worker identities are separate. "
                         "Each native worker assignment must name that task ID and its unique workerActor label. "
                         "For each API/UI task post a Beads comment containing exactly a JSON object with key "
                         "qualification whose value has taskId, workerActor, branch and revision (full commit SHA). "
                         "Each worker must return that same qualification JSON alongside its normal result. "
                         "Run check.py before both implementations exist, retain the failure, leave failed work open. "
                         "Record FAIL and actual candidate commit hashes in Beads. Stop at a recoverable handoff "
                         "before integration; do not silently clear writer ownership. After handoff and worker "
                         "completion, await controller interruption by running python with this absolute script path: "
                         + json.dumps(str(Path(manifest["root"]) / "workspace/wait.py")) + ". "
                         "Persistent subprocess commands must include absolute fixture paths; do not detach writers.")
    if phase == "integration":
        return common + ("An operator decision authorizing the uncertain-owner takeover is recorded in "
                         "the controller evidence. Reinspect observed claim ownership and use guarded takeover; "
                         "a changed guard requires fresh inspection. Reconcile actual candidate branches and "
                         "preserve previous failed checks. Transfer each API/UI claim with --if-assignee observed-old-owner "
                         "and --assignee new-coordinator, under that new coordinator's --actor, retaining JSON results; "
                         "do not combine the guard with --claim or --force. Close accepted API/UI work under the new "
                         "coordinator, record bd ready --json exposing integration, and claim integration under that "
                         "coordinator before verification. Use --json on all ownership and closure operations. "
                         "Integrate API/UI candidates, run python check.py, "
                         "and record passing evidence before closing integration. Keep check.py unchanged and execute "
                         "it in a separate simple python check.py command. Verify public output contains no private "
                         "context. Never count this instruction as proof that a worker process stopped.")
    return common + ("This is a cold continuation. Retrieve durable knowledge and graph records; reconcile "
                     "candidate revisions, attempts and every writer. An old writer's authority is uncertain: "
                     "do not take over on silence/lease expiry or self-report alone. Record the required operator "
                     "decision and pending evidence. Recover the verified constraint and unresolved hypothesis "
                     "without treating the hypothesis as fact. Write .brain/docs/recovered.json with discovery "
                     "equal to the recovered discovery object, nextWork equal to the integration task ID, and "
                     "takeover:'operator-decision-required'. Use explicit native file reads/editors and simple "
                     "file or bd graph queries. Recursive, glob, indirect shell reads and delegated readers "
                     "cannot establish this cold-access boundary. Do not close work without actual passing checks.")


def plan(root, runtime, phase):
    manifest = load(confined(root, "fixture.json"))
    name = f"{runtime}-{phase}-{len(manifest['attempts']) + 1}"
    env = environment(root, name)
    return {"name": name, "environment": env, "prompt": prompt(manifest, phase)}


def process_observation(root, pids, *, stop=(), run=subprocess.run):
    """Inspect only captured native descendants; guard termination against PID reuse."""
    if sys.platform != "win32":
        raise ValueError("Native writer process controls currently qualify Windows only")
    if not pids or any(not isinstance(pid, int) or pid <= 0 for pid in pids):
        raise ValueError("Expected positive native process IDs")
    script = "$ErrorActionPreference='Stop'; $all=@(Get-CimInstance Win32_Process); "
    if stop:
        expected = json.dumps(list(stop)).replace("'", "''")
        script += f"$expected=ConvertFrom-Json '{expected}'; foreach($target in $expected) {{ "
        script += "$current=$all | Where-Object ProcessId -eq $target.pid; if($current) { "
        script += "if($current.CreationDate.ToFileTimeUtc().ToString() -ne $target.created) { throw 'Writer PID identity changed' }; "
        script += "try { $writer=Get-Process -Id $target.pid -ErrorAction Stop } catch { "
        script += "if($_.FullyQualifiedErrorId -like 'NoProcessFoundForGivenId,*') { continue }; throw }; "
        # CIM CreationDate truncates native process start ticks to microseconds.
        script += "$started=$writer.StartTime.ToFileTimeUtc(); "
        script += "if(($started - ($started % 10)).ToString() -ne $target.created) { throw 'Writer PID identity changed' }; "
        script += "Stop-Process -InputObject $writer -Force -ErrorAction Stop } }; $all=@(Get-CimInstance Win32_Process); "
    seeds = ",".join(str(pid) for pid in pids)
    script += f"$known=[System.Collections.Generic.HashSet[int]]::new(); @({seeds}) | ForEach-Object {{ [void]$known.Add($_) }}; "
    script += "do { $changed=$false; foreach($item in $all) { if($known.Contains([int]$item.ParentProcessId) -and $known.Add([int]$item.ProcessId)) { $changed=$true } } } while($changed); "
    script += "$scope='" + str(root).replace("'", "''") + "'; "
    script += "$rows=@($all | Where-Object { $known.Contains([int]$_.ProcessId) } | ForEach-Object { "
    script += "@{pid=[int]$_.ProcessId; parentPid=[int]$_.ParentProcessId; created=$_.CreationDate.ToFileTimeUtc().ToString(); "
    script += "scoped=([string]$_.CommandLine).IndexOf($scope,[StringComparison]::OrdinalIgnoreCase) -ge 0} }); "
    script += "ConvertTo-Json -InputObject $rows -Compress"
    encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
    result = run(["pwsh", "-NoProfile", "-EncodedCommand", encoded], env=environment(root),
                 cwd=root, capture_output=True, text=True, encoding="utf-8", timeout=30, check=False)
    if result.returncode:
        raise RuntimeError("Writer observation/control failed: " + result.stderr)
    return {"requested": pids, "present": json.loads(result.stdout or "[]"), "observedAt": time.time(), "fixtureRoot": str(root)}


def stop_writers(root):
    manifest = load(confined(root, "fixture.json"))
    first = next((a for a in reversed(manifest["attempts"]) if a["phase"] == "first"), None)
    if not first or "present" not in first.get("writerTree", {}) or first.get("exitCode") is None:
        raise ValueError("Native parent exit and captured descendant identities are required")
    captured = first["writerTree"]["present"]
    pids = sorted({first["pid"], *(item["pid"] for item in captured)})
    before = process_observation(root, pids)
    known = {(item["pid"], item["created"]) for item in captured}
    if any((item["pid"], item["created"]) not in known for item in before["present"]):
        raise ValueError("New or changed writer identity: preserve hold and inspect before stopping")
    if any(not item.get("scoped") for item in before["present"]):
        raise ValueError("Writer command is not fixture-scoped: preserve hold without termination")
    after = process_observation(root, pids, stop=before["present"])
    receipt = {"before": before, "after": after, "parent": first["pid"], "attempt": first["name"], "cwd": str(root / "workspace")}
    write(confined(root, "private/writer-stop.json"), receipt)
    return receipt


def run_phase(root, runtime, phase, executable, allow_native=False, timeout=1800, uncapped=False, trust_fixture_hooks=False):
    if not allow_native:
        raise ValueError("Native model calls require --allow-native and separately arranged subscription auth")
    manifest = load(confined(root, "fixture.json"))
    if manifest.get("schema", 1) >= 2 and (not manifest["wiringAttempts"] or
            manifest["wiringAttempts"][-1]["exitCode"] or not all(manifest["wiringAttempts"][-1].get(name)
                for name in (".brain", ".beads", "backendPreserved"))):
        raise ValueError("Native qualification requires a successful supported candidate wire receipt")
    if manifest.get("schema", 1) >= 2 and any(not (root / "workspace" / name).is_symlink() or
            (root / "workspace" / name).resolve() != (brainspace(root) / name).resolve() for name in (".brain", ".beads")):
        raise ValueError("Current repository links no longer match the wired fixture Brainspace")
    attempts = manifest["attempts"]
    if any(a["runtime"] != runtime for a in attempts):
        raise ValueError("Use a separate fixture/backend for each runtime")
    if not uncapped and sum(a["runtime"] == runtime for a in attempts) >= manifest["sessionLimit"]:
        raise ValueError("Native session allowance exhausted")
    recent = [a for a in attempts if a["runtime"] == runtime]
    cap = manifest["consecutiveFailureLimit"]
    if not uncapped and len(recent) >= cap and all(a.get("exitCode", 1) != 0 for a in recent[-cap:]):
        raise ValueError("Three consecutive native failures; stop and retain evidence")
    if phase == "continue" and not any(a["runtime"] == runtime and a["phase"] == "first" for a in attempts):
        raise ValueError("Continuation requires an earlier first phase")
    if phase == "integration":
        decision = load(confined(root, "private/operator-decision.json"))
        if decision.get("decision") != "authorize-takeover" or not decision.get("actor") or not decision.get("observedOwner"):
            raise ValueError("Integration requires an independently recorded operator takeover decision")
        stopped = load(confined(root, "private/writer-stop.json"))
        first = next(a for a in reversed(attempts) if a["phase"] == "first")
        from verify import native_trace
        events = [json.loads(line) for line in confined(root, f"private/{first['name']}.raw.jsonl").read_text(encoding="utf-8").splitlines() if line]
        trace = native_trace(runtime, events)
        if not trace["workers"] or not trace["workers"] <= trace["finished"]:
            raise ValueError("Native delegated-writer lifecycle is incomplete: preserve the hold")
        if stopped["attempt"] != first["name"] or stopped["parent"] != first["pid"] or stopped["after"]["fixtureRoot"] != str(root):
            raise ValueError("Writer stop receipt belongs to a different fixture attempt")
        if stopped["after"]["present"]:
            raise ValueError("Affected native writer processes remain alive")
        fresh = process_observation(root, stopped["after"]["requested"])
        if fresh["present"]:
            raise ValueError("Writer identity changed after stop: preserve the hold")
        if not any(a["runtime"] == runtime and a["phase"] == "continue" for a in attempts):
            raise ValueError("Integration requires the cold uncertain-takeover phase")
    planned = plan(root, runtime, phase)
    name = planned["name"]
    env = planned["environment"]
    env["PATH"] = str(root / "bin") + os.pathsep + env.get("PATH", "")
    attempt = dict(runtime=runtime, phase=phase, name=name, home=env["HOME"], started=time.time(), cwd=str(root / "workspace"),
                   limits={"uncappedOverride": uncapped, "defaultSessionLimit": manifest["sessionLimit"],
                           "defaultFailureLimit": manifest["consecutiveFailureLimit"]})
    attempts.append(attempt)
    write(root / "fixture.json", manifest)  # Reserve allowance before process launch, including failures.
    task = prompt(manifest, phase)
    write(root / f"private/{name}.input.txt", task)
    argv = ([executable, "exec", "--json", "--full-auto", "--add-dir", str(root),
             *(["--dangerously-bypass-hook-trust"] if trust_fixture_hooks else []), "-"] if runtime == "codex" else
            [executable, "-p", "--verbose", "--output-format", "stream-json", "--include-partial-messages"])
    attempt["argv"] = argv
    attempt["runtimeVersion"] = execute(root, [executable, "--version"], phase=name).stdout.strip()
    attempt["settingsSha256"] = {config: digest(confined(root, f"homes/{name}/{config}"))
                                for config in (".codex/config.toml", ".claude/settings.json")
                                if confined(root, f"homes/{name}/{config}").is_file()}
    write(root / "fixture.json", manifest)
    if phase == "continue":
        receipt = confined(root, f"private/{name}-aliases-before.json")
        write(receipt, capture_aliases(root, name))
        attempt["aliasesBeforeSha256"] = digest(receipt)
        write(root / "fixture.json", manifest)
    snapshot(root, name + "-before")
    with (root / f"private/{name}.raw.jsonl").open("w", encoding="utf-8") as stdout, \
            (root / f"private/{name}.stderr.txt").open("w", encoding="utf-8") as stderr:
        process = subprocess.Popen(argv, cwd=root / "workspace", env=env, stdin=subprocess.PIPE,
                                   stdout=stdout, stderr=stderr, text=True, encoding="utf-8")
        attempt["pid"] = process.pid
        def observe():
            try:
                return process_observation(root, [process.pid])
            except (ValueError, RuntimeError, OSError, subprocess.SubprocessError) as error:
                return {"error": str(error)}
        attempt["writerStart"] = observe()
        write(root / "fixture.json", manifest)
        try:
            process.communicate(task, timeout=timeout)
        except (subprocess.TimeoutExpired, KeyboardInterrupt):
            # Parent exit does not establish that delegated writers stopped.
            attempt["writerTree"] = observe()
            process.terminate()
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=15)
            attempt["interrupted"] = True
        finally:
            if "writerTree" not in attempt:
                attempt["writerTree"] = observe()
            attempt.update(exitCode=process.returncode, ended=time.time(), delegatedWriters="unverified")
            write(root / "fixture.json", manifest)
    snapshot(root, name + "-after")
    if phase == "continue":
        receipt = confined(root, f"private/{name}-aliases-after.json")
        write(receipt, capture_aliases(root, name))
        attempt["aliasesAfterSha256"] = digest(receipt)
        write(root / "fixture.json", manifest)
    return attempt


SECRET_KEY = re.compile(r"^(?:authorization|cookie|password|secret|(?:openai[_-]|anthropic[_-])?api[_-]?key|access[_-]?token|refresh[_-]?token|id[_-]?token|client[_-]?secret)$", re.I)


def redact(value, sentinels=()):
    """Preserve arbitrarily deep telemetry and actor/token-count fields; redact credential values."""
    if isinstance(value, dict):
        return {redact(key, sentinels): "[REDACTED]" if SECRET_KEY.match(key) or
                key.lower() == "token" and isinstance(item, str) else redact(item, sentinels)
                for key, item in value.items()}
    if isinstance(value, list):
        return [redact(item, sentinels) for item in value]
    if isinstance(value, str):
        if value.lstrip().startswith(("{", "[")):
            try:
                return json.dumps(redact(json.loads(value), sentinels))
            except json.JSONDecodeError:
                pass
        for secret in sentinels:
            value = value.replace(secret, "[PRIVATE]")
        value = re.sub(r"(?i)Bearer\s+[A-Za-z0-9._~+/=-]+", "Bearer [REDACTED]", value)
        value = re.sub(r"(?i)((?:OPENAI_API_KEY|ANTHROPIC_API_KEY|access_token|refresh_token|password)\s*[=:]\s*)[^\s,;]+",
                       r"\1[REDACTED]", value)
    return value


def export(root):
    from verify import lexical_identity
    manifest = load(confined(root, "fixture.json"))
    output = confined(root, "export")
    if output.exists():
        raise ValueError("Export already exists; preserve it and use a new fixture for another run")
    output.mkdir()
    hashes = {}
    # Only parse known evidence files, never traverse runtime homes or copy authentication files.
    for source in sorted((root / "private").glob("*.json*")):
        confined(root, source.relative_to(root))
        text = source.read_text(encoding="utf-8")
        values = [json.loads(line) for line in text.splitlines() if line] if source.suffix == ".jsonl" else load(source)
        sources = (str(root), manifest["candidate"], manifest["pstack"])
        safe = redact(values, (manifest["sentinel"], *sources,
                              *(lexical_identity(path, str(root)) for path in sources)))
        write(output / source.name, "".join(json.dumps(item) + "\n" for item in safe)
              if source.suffix == ".jsonl" else safe)
        hashes[source.name] = {"rawSha256": digest(source), "exportSha256": digest(output / source.name)}
    write(output / "hashes.json", hashes)
    return output


def inspect(root):
    manifest = load(confined(root, "fixture.json"))
    return {"evidenceLevel": "captured artifacts; native assertions require calibration and review",
            "attempts": manifest["attempts"], "priorAllowances": manifest["priorAllowances"],
            "files": {str(file.relative_to(root)): digest(file) for file in (root / "private").glob("*") if file.is_file()},
            "unqualified": ["delegated writer termination", "native graph/trace corroboration until reviewed"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    setup = commands.add_parser("prepare")
    setup.add_argument("root", type=Path)
    for name in ("candidate", "pstack", "bd"):
        setup.add_argument("--" + name, required=True, type=Path)
    wiring = commands.add_parser("wire")
    wiring.add_argument("root", type=Path)
    wiring.add_argument("--executable", required=True)
    phase = commands.add_parser("run")
    phase.add_argument("root", type=Path)
    phase.add_argument("--runtime", choices=("codex", "claude"), required=True)
    phase.add_argument("--phase", choices=("first", "continue", "integration"), required=True)
    phase.add_argument("--executable", required=True)
    phase.add_argument("--allow-native", action="store_true")
    phase.add_argument("--uncapped", action="store_true", help="Record an authorized override of session/failure caps; retain all receipts.")
    phase.add_argument("--trust-fixture-hooks", action="store_true", help="Codex only: trust the vetted candidate's fixture hooks; keep sandbox enabled.")
    phase.add_argument("--timeout-seconds", type=int, default=1800)
    planned = commands.add_parser("plan")
    planned.add_argument("root", type=Path)
    planned.add_argument("--runtime", choices=("codex", "claude"), required=True)
    planned.add_argument("--phase", choices=("first", "continue", "integration"), required=True)
    proxy = commands.add_parser("proxy")
    proxy.add_argument("root", type=Path)
    proxy.add_argument("args", nargs=argparse.REMAINDER)
    for name in ("inspect", "export", "snapshot", "stop-writers"):
        commands.add_parser(name).add_argument("root", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    if args.command == "prepare":
        result = prepare(root, args.candidate.resolve(strict=True), args.pstack.resolve(strict=True), args.bd.resolve(strict=True))
        # Keep private sentinels off the terminal.
        result = {"root": str(root), "ids": result["ids"]}
    elif args.command == "run":
        if not 1 <= args.timeout_seconds <= 1800:
            parser.error("timeout must be between 1 and 1800 seconds")
        result = run_phase(root, args.runtime, args.phase, args.executable, args.allow_native, args.timeout_seconds, args.uncapped, args.trust_fixture_hooks)
    elif args.command == "wire":
        result = wire(root, args.executable)
    elif args.command == "plan":
        result = plan(root, args.runtime, args.phase)
    elif args.command == "proxy":
        result = bd(root, args.args, phase=os.environ.get("NATIVE_FIXTURE_PHASE", "unknown"), check=False)
        sys.stdout.write(result.stdout)
        sys.stderr.write(result.stderr)
        return result.returncode
    elif args.command == "snapshot":
        result = snapshot(root, "manual-" + uuid.uuid4().hex)
    elif args.command == "stop-writers":
        result = stop_writers(root)
    elif args.command == "export":
        result = str(export(root))
    else:
        result = inspect(root)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Fail-closed artifact assertions; native JSONL is retained rather than depth-truncated."""

import json
import ntpath
from pathlib import Path
import re
import shlex
import sys


def tool_text(value):
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n".join(tool_text(item) for item in value)
    if isinstance(value, dict):
        return tool_text(value["text"]) if "text" in value else json.dumps(value)
    return str(value)


def command_body(command):
    command = command.strip()
    wrapper = re.match(r'^(?:"?[^"\n]*[\\/])?(?:pwsh|powershell)(?:\.exe)?"?\s+(?:-NoProfile\s+)?-Command\s+(.+)$', command, re.I)
    if wrapper:
        command = wrapper[1].strip()
        if len(command) > 1 and command[0] == command[-1] and command[0] in "\"'":
            command = command[1:-1]
    return command


def read_target(command):
    match = re.fullmatch(r"(?:cat|Get-Content|type)\s+(?:-LiteralPath\s+)?([^\s;|&`$'\"]+|'[^'\n]+'|\"[^\"`$\n]+\")", command_body(command), re.I)
    return match[1].strip("\"'") if match else None


def simple_read(command):
    return read_target(command) is not None


def lexical_identity(path, cwd):
    path = str(path).replace("/", "\\")
    if path.startswith("\\\\?\\UNC\\"):
        path = "\\\\" + path[8:]
    else:
        path = path.removeprefix("\\\\?\\").removeprefix("\\??\\")
    return ntpath.normcase(ntpath.normpath(ntpath.join(str(cwd), path)))


def path_identity(path, cwd, aliases=None):
    normalized = lexical_identity(path, cwd)
    if aliases is not None:
        seen = set()
        while normalized not in seen:
            seen.add(normalized)
            match = next((key for key in sorted(aliases, key=len, reverse=True)
                          if normalized == key or normalized.startswith(key + "\\")), None)
            if match is None:
                return normalized
            normalized = lexical_identity(aliases[match] + normalized[len(match):], cwd)
        raise ValueError("Cyclic alias identity in continuation boundary")
    # Resolve actual filesystem aliases on the supported Windows host.
    if sys.platform == "win32":
        normalized = ntpath.normcase(str(Path(normalized).resolve()))
    elif not ntpath.splitdrive(cwd)[0] and not ntpath.splitdrive(path)[0]:
        normalized = ntpath.normcase(str((Path(cwd.replace("\\", "/")) / path.replace("\\", "/")).resolve()))
    return normalized


def controller_access(tool, root, first_home, aliases=None):
    text = tool["input"].casefold().replace("\\\\", "\\").replace("/", "\\")
    if any(marker in text for marker in ("\\private\\", ".raw.jsonl", ".input.txt", ".stderr.txt")):
        return True
    cwd = tool.get("cwd") or ntpath.join(root, "workspace")
    paths = tool.get("paths", [])
    command = command_body(tool.get("command", ""))
    target = read_target(command)
    if target:
        paths = [*paths, target]
    for groups in re.findall(r'"([^"\n]+)"|\'([^\'\n]+)\'|([^\s;|&]+)', command):
        token = next(part for part in groups if part)
        if aliases is not None:
            paths = [*paths, token]
            continue
        local = Path(cwd) / token
        try:
            if local.exists() or local.is_symlink():
                paths = [*paths, token]
        except OSError:
            continue
    forbidden = [lexical_identity(ntpath.join(root, "private"), cwd), lexical_identity(first_home, cwd),
                 lexical_identity(ntpath.join(root, "homes"), cwd)]
    return any(any(identity == base or identity.startswith(base + "\\") for base in forbidden)
               for identity in (path_identity(path, cwd, aliases) for path in paths))


def continuation_access(tool, root, first_home, read_roots, aliases=None):
    """Allow established read targets; unsupported shell/search behavior cannot prove cold access."""
    if controller_access(tool, root, first_home, aliases):
        return False
    cwd = tool.get("cwd") or ntpath.join(root, "workspace")
    def allowed(path):
        if any(char in path for char in "*?`$"):
            return False
        identity = path_identity(path, cwd, aliases)
        return any(identity == base or identity.startswith(base + "\\")
                   for base in (lexical_identity(value, cwd) for value in read_roots))
    if tool["name"] in {"Read", "Write", "Edit", "file_change"}:
        return bool(tool.get("paths")) and all(allowed(path) for path in tool["paths"])
    if tool["name"] == "Skill":
        name = tool.get("skill", "")
        if not isinstance(name, str):
            return False
        namespace, _, leaf = name.rpartition(":")
        return namespace in {"", "dotbrain"} and (leaf or name) in {
            "brain-convention", "work-graph", "maintain-brain", "wire-brain", "repo-rules", "dotbrain-pstack"}
    if tool["name"] == "TodoWrite":
        return True
    if tool["name"] not in {"shell", "Bash"}:
        return False
    command = command_body(tool.get("command", ""))
    if any(char in command for char in "*?`$;|&<>"):
        return False
    target = read_target(command)
    if target:
        return allowed(target)
    tokens = [token.strip("\"'") for token in shlex.split(command, posix=False)]
    if not tokens:
        return False
    binary = ntpath.basename(tokens[0]).casefold().removesuffix(".exe").removesuffix(".cmd")
    if binary == "bd":
        if any(token.split("=", 1)[0] in {"--db", "--database", "--directory", "-C", "--repo", "--global"}
               or token.startswith("-C") for token in tokens):
            return False
        if tokens[1:] in (["dolt", "test"], ["--readonly", "dolt", "test"], ["--readonly", "ready", "--json"]):
            return True
        if len(tokens) < 2 or tokens[1] not in {"ready", "list", "show", "where", "prime", "comments"}:
            return False
        if tokens[1] == "comments" and len(tokens) > 2 and tokens[2] in {"delete", "edit", "remove"}:
            return False
        return all(allowed(tokens[i + 1]) for i, token in enumerate(tokens[:-1]) if token in {"--file", "--body-file"})
    if binary == "dotbrain" and len(tokens) > 1 and tokens[1] == "doctor":
        index = 2
        while index < len(tokens):
            flag = tokens[index]
            if flag == "--json":
                index += 1
                continue
            if index + 1 >= len(tokens) or flag not in {"--home", "--repo", "--project"}:
                return False
            value = tokens[index + 1]
            if flag == "--project":
                if value != "catalog":
                    return False
            elif path_identity(value, cwd, aliases) != lexical_identity(ntpath.join(root, "data" if flag == "--home" else "workspace"), cwd):
                return False
            index += 2
        return True
    if binary == "git":
        if len(tokens) > 1 and tokens[1] == "branch":
            return all(token in {"--list", "--show-current", "--all", "-a", "--verbose", "-v", "--no-color"} for token in tokens[2:])
        return len(tokens) > 1 and tokens[1] in {"status", "rev-parse", "branch", "log", "show"} and not any(
            token in {"--output", "-o", "--exec", "--work-tree", "--git-dir", "-C", "-c", "--ext-diff", "--textconv"} or token.startswith(("--output=", "--work-tree=", "--git-dir="))
            for token in tokens[2:])
    return False


def alias_boundary(second, root, first_home, read_roots):
    before, after = second.get("aliasesBefore", {}), second.get("aliasesAfter", {})
    expected_roots = sorted({lexical_identity(path, root) for path in read_roots})
    for receipt in (before, after):
        if receipt.get("schema") != 1 or receipt.get("phase") != second["name"] or \
                receipt.get("root") != lexical_identity(root, root) or receipt.get("roots") != expected_roots or \
                not isinstance(receipt.get("aliases"), dict):
            return False
    if before["aliases"] != after["aliases"]:
        return False
    aliases = before["aliases"]
    forbidden = [lexical_identity(ntpath.join(root, "private"), root), lexical_identity(ntpath.join(root, "homes"), root),
                 lexical_identity(first_home, root)]
    return not any(any(target == base or target.startswith(base + "\\") for base in forbidden)
                   for target in (path_identity(path, root, aliases) for path in aliases))


def returned_candidate(output, candidate):
    decoder = json.JSONDecoder()
    for index, char in enumerate(output):
        if char != "{":
            continue
        try:
            value, _ = decoder.raw_decode(output[index:])
        except ValueError:
            continue
        if isinstance(value, dict):
            value = value.get("qualification", value)
            if isinstance(value, dict) and all(value.get(key) == candidate.get(key) for key in
                                              ("taskId", "workerActor", "branch", "revision")):
                return True
    return False


def option(args, name):
    indexes = [i for i, arg in enumerate(args) if arg == name or arg.startswith(name + "=")]
    if len(indexes) != 1:
        return None
    index = indexes[0]
    if "=" in args[index]:
        return args[index].split("=", 1)[1]
    return args[index + 1] if index + 1 < len(args) else None


def bead_result(call, item, *, status=None, owner=None):
    try:
        rows = json.loads(call.get("stdout", ""))
    except (ValueError, TypeError):
        return False
    rows = [rows] if isinstance(rows, dict) else rows
    return isinstance(rows, list) and any(isinstance(row, dict) and row.get("id") == item and
        (status is None or row.get("status") == status) and (owner is None or row.get("assignee") == owner) for row in rows)


def recovery_transitions(record):
    """Require guarded coordinator transfer, unforced prerequisite closures, readiness, claim and closure."""
    old = record["operatorDecision"].get("observedOwner")
    if not old:
        return False
    ids, final = record["ids"], record["integration"]
    calls = [(i, call) for i, call in enumerate(record["calls"]) if call["phase"] == final["name"]]
    def operation(call, *args):
        return call["returncode"] == 0 and call["argv"][:len(args)] == list(args)
    def unforced(call):
        return not any(arg.split("=", 1)[0] in {"--force", "-f"} for arg in call["argv"])
    owners, closed = [], []
    for role in ("api", "ui"):
        item = ids[role]
        guard = next(((i, call) for i, call in calls if operation(call, "update", item) and unforced(call) and
            "--claim" not in call["argv"] and option(call["argv"], "--if-assignee") == old and
            record["before"]["items"][item].get("assignee") == old and
            option(call["argv"], "--assignee") not in {None, "", old} and
            option(call["argv"], "--actor") == option(call["argv"], "--assignee") and
            bead_result(call, item, status="in_progress", owner=option(call["argv"], "--assignee"))), None)
        if not guard:
            return False
        owner = option(guard[1]["argv"], "--assignee")
        close = next(((i, call) for i, call in calls if i > guard[0] and operation(call, "close", item) and
                      unforced(call) and option(call["argv"], "--actor") == owner and
                      bead_result(call, item, status="closed", owner=owner)), None)
        state = final["state"]["items"][item]
        if not close or state.get("status") != "closed" or state.get("assignee") != owner:
            return False
        owners.append(owner)
        closed.append(close[0])
    if owners[0] != owners[1]:
        return False
    owner, item = owners[0], ids["integration"]
    ready = next((i for i, call in calls if i > max(closed) and (operation(call, "ready") or
                  call["returncode"] == 0 and call["argv"] == ["--readonly", "ready", "--json"]) and
                  "--json" in call["argv"] and bead_result(call, item, status="open")), None)
    if ready is None:
        return False
    claim = next((i for i, call in calls if i > ready and operation(call, "update", item) and
                  "--claim" in call["argv"] and option(call["argv"], "--actor") == owner and
                  bead_result(call, item, status="in_progress", owner=owner)), None)
    state = final["state"]["items"][item]
    return claim is not None and state.get("status") == "closed" and state.get("assignee") == owner and any(
        i > claim and operation(call, "close", item) and unforced(call) and option(call["argv"], "--actor") == owner and
        bead_result(call, item, status="closed", owner=owner) for i, call in calls)


def executed_check(tool, root, script_hash, ok, revision=None):
    if tool["name"] not in {"shell", "Bash"} or tool["ok"] != ok:
        return None
    match = re.fullmatch(r'(?:"[^"\n]*python(?:3(?:\.\d+)?)?(?:\.exe)?"|[^\s;|&`$]*python(?:3(?:\.\d+)?)?(?:\.exe)?)\s+("[^"\n]+"|\'[^\'\n]+\'|[^\s;|&`$]+)',
                         command_body(tool.get("command", "")), re.I)
    cwd = tool.get("cwd") or ntpath.join(root, "workspace")
    if not match or path_identity(match[1].strip("\"'"), cwd) != path_identity(ntpath.join(root, "workspace/check.py"), cwd):
        return None
    for line in tool["output"].splitlines():
        try:
            receipt = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(receipt, dict) and receipt.get("check") == "catalog-v1" and receipt.get("ok") is ok and \
                receipt.get("scriptSha256") == script_hash and re.fullmatch(r"[0-9a-f]{40}", receipt.get("revision", "")) and \
                (revision is None or receipt["revision"] == revision):
            return receipt
    return None


def task_candidates(state, ids):
    candidates = {}
    for role in ("api", "ui"):
        for comment in state["details"].get(ids[role], {}).get("comments", []):
            try:
                value = json.loads(comment.get("text", "")).get("qualification", {})
            except (ValueError, AttributeError):
                continue
            if value.get("taskId") == ids[role] and all(isinstance(value.get(key), str) and value[key]
                for key in ("workerActor", "branch", "revision")) and comment.get("author"):
                candidates[role] = value
    return candidates


def native_trace(runtime, events):
    """Return native identity, completed tools, worker starts/finishes and terminal status."""
    trace = {"session": None, "tools": [], "workers": set(), "finished": set(), "complete": False,
             "assignments": {}, "returns": {}, "incomplete": set()}
    pending = {}
    child_activity = set()
    for event in events:
        kind = event.get("type")
        if runtime == "codex":
            if kind == "thread.started":
                trace["session"] = event.get("thread_id")
            elif kind == "turn.completed":
                trace["complete"] = True
            elif kind == "item.started" and event.get("item", {}).get("id"):
                trace["incomplete"].add(event["item"]["id"])
            elif kind == "item.completed":
                item = event.get("item", {})
                trace["incomplete"].discard(item.get("id"))
                if item.get("type") == "command_execution":
                    trace["tools"].append({"name": "shell", "input": item.get("command", ""),
                                           "command": item.get("command", ""), "cwd": item.get("cwd"),
                                           "output": item.get("aggregated_output", ""),
                                           "ok": item.get("exit_code") == 0})
                elif item.get("type") == "collab_tool_call":
                    agents = item.get("agents_states", {})
                    if item.get("tool") == "spawn_agent" and item.get("status") == "completed":
                        trace["workers"].update(agents)
                        trace["assignments"].update({agent: item.get("prompt", "") for agent in agents})
                    if item.get("tool") in {"wait", "close_agent"}:
                        trace["finished"].update(key for key, value in agents.items()
                                                 if value.get("status") in {"completed", "shutdown"})
                        trace["returns"].update({key: tool_text(value.get("message", value.get("output", "")))
                            for key, value in agents.items() if value.get("status") == "completed"})
                elif item.get("type") == "file_change":
                    trace["tools"].append({"name": "file_change", "input": json.dumps(item),
                        "paths": [change["path"] for change in item.get("changes", []) if "path" in change],
                        "output": "", "ok": item.get("status") == "completed"})
                elif item.get("type") not in {"agent_message", "reasoning", "todo_list"}:
                    trace["tools"].append({"name": "unsupported", "input": json.dumps(item), "output": "", "ok": False})
        elif runtime == "claude":
            trace["session"] = event.get("session_id") or trace["session"]
            if event.get("parent_tool_use_id") and kind in {"assistant", "user"}:
                child_activity.add(event["parent_tool_use_id"])
            if kind == "result":
                trace["complete"] = event.get("subtype") == "success" and not event.get("is_error")
            for block in event.get("message", {}).get("content", []) if isinstance(event.get("message", {}).get("content"), list) else []:
                if block.get("type") == "tool_use":
                    pending[block["id"]] = block
                    trace["incomplete"].add(block["id"])
                    if block.get("name") in {"Agent", "Task"}:
                        trace["workers"].add(block["id"])
                        trace["assignments"][block["id"]] = block.get("input", {}).get("prompt", "")
                elif block.get("type") == "tool_result" and block.get("tool_use_id") in pending:
                    call = pending[block["tool_use_id"]]
                    trace["incomplete"].discard(block["tool_use_id"])
                    trace["tools"].append({"name": call["name"], "input": json.dumps(call.get("input", {})),
                                           "skill": call.get("input", {}).get("skill", ""),
                                           "command": call.get("input", {}).get("command", ""),
                                           "paths": [call["input"]["file_path"]] if call.get("input", {}).get("file_path") else [],
                                           "output": tool_text(block.get("content", "")),
                                           "ok": not block.get("is_error", False)})
                    # A result links dispatch and completion; it does not establish OS process death.
                    if call["name"] in {"Agent", "Task"} and not block.get("is_error") and \
                            not call.get("input", {}).get("run_in_background"):
                        trace["finished"].add(call["id"])
                        trace["returns"][call["id"]] = tool_text(block.get("content", ""))
    if runtime == "claude":
        trace["finished"] &= child_activity
    return trace


def evaluate(record):
    """Grade corroborated evidence, never the agent's final narrative alone."""
    first, second = record["first"], record["second"]
    ids = record["ids"]
    calls = record["calls"]
    before, after = record["before"], record["after"]
    traces = [native_trace(record["runtime"], events) for events in (first["events"], second["events"])]
    initial, continuation = traces
    old_owner = record["operatorDecision"].get("observedOwner")
    read_roots = record.get("readRoots", [ntpath.join(record["fixtureRoot"], "workspace"),
        ntpath.join(record["fixtureRoot"], "data/brainspaces/catalog/.brain"),
        ntpath.join(record["fixtureRoot"], "data/.cache/integrations/dotbrain-pstack")])
    frozen_aliases = second.get("aliasesBefore", {}).get("aliases", {})
    def action(call, *args):
        return call["argv"][:len(args)] == list(args)

    def actor(call):
        return option(call["argv"], "--actor")

    def read(trace, name, content):
        def normalized(text):
            return re.sub(r"\s", "", re.sub(r"^\s*\d+[→\t] ?", "", text, flags=re.M))
        expected = normalized(content)
        return any(tool["ok"] and (tool["name"] == "Read" or simple_read(tool["input"]))
                   and name in tool["input"] and expected in
                   normalized(tool["output"]) for tool in trace["tools"])

    mutations = [c for c in calls if c["phase"] == second["name"] and
                 c["argv"] and c["argv"][0] in {"update", "close", "create", "delete", "reopen"}
                 and c["returncode"] == 0]
    claims = [c for c in calls if c["phase"] == first["name"] and
              action(c, "update", ids["api"]) and "--claim" in c["argv"]]
    succeeded = [c for c in claims if c["returncode"] == 0]
    failed = [c for c in claims if c["returncode"] != 0]
    discovery = before["knowledge"].get("docs/discovery.json", "")
    try:
        finding = json.loads(discovery)
    except (json.JSONDecodeError, TypeError):
        finding = {}
    try:
        recovered = json.loads(after["knowledge"].get("docs/recovered.json", "{}"))
    except (json.JSONDecodeError, TypeError):
        recovered = {}
    handoff = json.dumps(before["details"])
    candidates = record["candidates"]
    final = record["integration"]
    integration = native_trace(record["runtime"], final["events"])
    stopped = record["writerStop"]
    known_writers = {(p["pid"], p["created"]) for p in first["writerTree"]["present"]}
    def ownership(state):
        return {item: {key: value.get(key) for key in ("status", "assignee", "dependencies", "acceptance_criteria")}
                for item, value in state["items"].items()}
    passed_index = next((i for i, t in enumerate(integration["tools"]) if executed_check(t, record["fixtureRoot"],
                         record["checkSha256"], True, final["state"]["head"])), None)
    close_index = next((i for i, t in enumerate(integration["tools"]) if t["ok"] and
                        re.search(r"\bbd(?:\.cmd|\.exe)?\s+close\s+" + re.escape(ids["integration"]), t["input"])), None)
    public = record["public"]
    matched_workers = {}
    for role in ("api", "ui"):
        evidence = candidates.get(role, {})
        matched_workers[role] = {worker for worker, assignment in initial["assignments"].items()
                                if ids[role] in assignment and evidence.get("workerActor") and
                                evidence["workerActor"] in assignment}
    provenance = {role: len(matched_workers[role]) == 1 and all(returned_candidate(
        initial["returns"].get(worker, ""), candidates[role]) for worker in matched_workers[role])
        for role in ("api", "ui")}
    criteria = {
        "native_sessions": bool(initial["session"] and continuation["session"] and
                                initial["session"] != continuation["session"] and continuation["complete"]),
        "cold_continuation": first["home"] != second["home"] and second["input"] == record["expectedSecondInput"]
        and alias_boundary(second, record["fixtureRoot"], first["home"], read_roots)
        and not continuation["incomplete"] and not continuation["workers"]
        and first["sessionOutput"] not in second["input"] and not any(
            first["sessionOutput"].strip() in tool["output"] for tool in continuation["tools"]) and not any(
            not continuation_access(tool, record["fixtureRoot"], first["home"], read_roots, frozen_aliases)
            for tool in continuation["tools"]),
        "durable_discovery": finding.get("pageSize") == 7 and finding.get("sourceSha256") == record["configSha256"]
        and finding.get("hypothesis") == {"claim": "Latency cause is unknown", "status": "unresolved"}
        and discovery == after["knowledge"].get("docs/discovery.json") and "docs/discovery.json" in handoff,
        "corroborated_reads": bool(discovery) and read(initial, "config.json", record["config"])
        and read(continuation, "discovery.json", discovery) and read(continuation, "config.json", record["config"]),
        "knowledge_reused": bool(finding) and recovered == {"discovery": finding, "nextWork": ids["integration"],
                                                             "takeover": "operator-decision-required"},
        "dependency_graph": all(any(d.get("depends_on_id", d.get("id")) == ids[parent] for d in
                                      record["baseline"]["details"][ids[child]]["show"][0].get("dependencies", []))
                                for child, parent in (("api", "contract"), ("ui", "contract"),
                                                      ("integration", "api"), ("integration", "ui"))),
        "contract_prerequisite": any(action(c, "close", ids["contract"]) and c["returncode"] == 0
                                     for c in calls[:next((i for i, c in enumerate(calls) if
                                         action(c, "update", ids["api"]) or action(c, "update", ids["ui"])), len(calls))]),
        "exclusive_claim": len(succeeded) == 1 and bool(failed) and actor(succeeded[0]) and
        any(actor(c) and actor(c) != actor(succeeded[0]) for c in failed) and
        before["items"][ids["api"]].get("assignee") == actor(succeeded[0]),
        "failed_check_held": any(executed_check(t, record["fixtureRoot"], record["checkSha256"], False)
                                  for t in initial["tools"])
        and before["items"][ids["integration"]]["status"] != "closed" and "FAIL" in handoff,
        "candidate": all(candidates.get(role, {}).get("taskId") == ids[role] and
                         provenance[role] and
                         bool(re.fullmatch(r"[0-9a-f]{40}", candidates[role].get("revision", ""))) and
                         candidates[role].get("objectExists") is True and candidates[role].get("integrated") is True and
                         candidates[role].get("scriptPreserved") is True and candidates[role].get("roleImplemented") is True and
                         bool(old_owner) and old_owner == before["items"][ids[role]].get("assignee") and
                         any(c["phase"] == first["name"] and action(c, "update", ids[role]) and "--claim" in c["argv"]
                             and c["returncode"] == 0 and actor(c) == old_owner for c in calls) and
                         before["refs"].get(candidates[role].get("branch")) == candidates[role]["revision"] and
                         candidates[role]["revision"] != record["baseline"].get("head")
                         for role in ("api", "ui")),
        "worker_lifecycle": initial["workers"] <= initial["finished"] and all(provenance[role] and matched_workers[role] <= initial["finished"]
                                for role in ("api", "ui")) and matched_workers["api"].isdisjoint(matched_workers["ui"]),
        "interruption": first.get("interrupted") is True and isinstance(first.get("pid"), int)
        and first.get("exitCode") is not None and first.get("ended", 0) >= first.get("started", 1),
        "uncertain_takeover_held": not mutations and ownership(before) == ownership(after) and
        recovered.get("takeover") == "operator-decision-required",
        "confirmed_writer_stop": stopped["attempt"] == first["name"] and stopped["parent"] == first["pid"] and
        stopped["after"]["fixtureRoot"] == record["fixtureRoot"] and not stopped["after"]["present"] and
        bool(stopped["after"]["requested"]) and all(p.get("scoped") and (p["pid"], p["created"]) in known_writers
            for p in stopped["before"]["present"]),
        "integration_verified": integration["complete"] and integration["session"] not in
        {initial["session"], continuation["session"], None} and
        passed_index is not None and close_index is not None and passed_index < close_index and
        final.get("scriptPreserved") is True and
        final["state"].get("status") == "" and final.get("productValid") is True and
        any(action(c, "close", ids["integration"]) and c["phase"] == final["name"] and c["returncode"] == 0 for c in calls) and
        final["state"]["items"][ids["integration"]]["status"] == "closed" and
        recovery_transitions(record) and
        record["operatorDecision"].get("decision") == "authorize-takeover" and
        bool(record["operatorDecision"].get("actor")) and
        record["operatorDecision"].get("observedOwner") == before["items"][ids["api"]].get("assignee"),
        "private_boundary": bool(public) and all(record["sentinel"] not in text for text in public.values()),
        "limits_preserved": record["priorAllowances"] == {"status": "exhausted", "renewed": False}
        and len(record["attempts"]) >= 3 and all(a["receipt"] in record["attempts"] for a in (first, second, final)),
    }
    return criteria


def inspect_artifacts(root, runtime):
    """Construct assertions only from retained local artifacts, not a model-authored summary."""
    from journey import load, digest, prompt, execute, confined, read_roots
    manifest = load(root / "fixture.json")
    attempts = [a for a in manifest["attempts"] if a["runtime"] == runtime]
    if len(attempts) < 3:
        raise ValueError("First, cold continuation and integration native attempts required")
    first, second, final = attempts[-3:]
    if [a["phase"] for a in (first, second, final)] != ["first", "continue", "integration"]:
        raise ValueError("Select an adjacent first/continue/integration sequence; earlier attempts remain retained")
    def captured(attempt):
        base = confined(root, "private/" + attempt["name"])
        raw = base.with_name(base.name + ".raw.jsonl").read_text(encoding="utf-8")
        events = [json.loads(line) for line in raw.splitlines() if line]
        value = {**attempt, "receipt": attempt, "events": events, "sessionOutput": raw,
                 "input": base.with_name(base.name + ".input.txt").read_text(encoding="utf-8")}
        if attempt["phase"] == "continue":
            for label in ("Before", "After"):
                file = confined(root, f"private/{attempt['name']}-aliases-{label.lower()}.json")
                if digest(file) != attempt.get(f"aliases{label}Sha256"):
                    raise ValueError("Continuation alias receipt changed or lacks captured digest")
                value["aliases" + label] = load(file)
        return value
    before = load(root / f"private/{first['name']}-after.json")
    after = load(root / f"private/{second['name']}-after.json")
    for state in (before, after):
        state["items"] = {item["id"]: item for item in state["items"]}
    baseline = load(root / "private/baseline.json")
    calls = [json.loads(line) for line in (root / "private/beads.jsonl").read_text(encoding="utf-8").splitlines()]
    last = captured(final)
    last["state"] = load(root / f"private/{final['name']}-after.json")
    last["state"]["items"] = {item["id"]: item for item in last["state"]["items"]}
    import hashlib
    def script_preserved(revision):
        value = execute(root, ["git", "show", revision + ":check.py"], check=False)
        return value.returncode == 0 and hashlib.sha256(value.stdout.replace("\r\n", "\n").encode()).hexdigest() == baseline["checkSha256"]
    last["scriptPreserved"] = script_preserved(last["state"]["head"])
    def product_file(revision, role):
        value = execute(root, ["git", "show", revision + ":" + role + ".json"], check=False)
        try:
            return value.returncode == 0 and json.loads(value.stdout) == {"pageSize": 7}
        except ValueError:
            return False
    last["productValid"] = all(product_file(last["state"]["head"], role) for role in ("api", "ui"))
    candidates = task_candidates(before, manifest["ids"])
    for role, value in candidates.items():
        revision = value["revision"]
        if not re.fullmatch(r"[0-9a-f]{40}", revision):
            continue
        value["objectExists"] = execute(root, ["git", "cat-file", "-e", revision + "^{commit}"], check=False).returncode == 0
        value["integrated"] = execute(root, ["git", "merge-base", "--is-ancestor", revision, last["state"]["head"]], check=False).returncode == 0
        value["scriptPreserved"] = script_preserved(revision)
        changed = execute(root, ["git", "diff", "--name-only", baseline["head"], revision], check=False)
        value["roleImplemented"] = product_file(revision, role) and role + ".json" in changed.stdout.splitlines()
    tracked = execute(root, ["git", "ls-files", "-z"]).stdout.split("\0")
    public = {file: confined(root, "workspace/" + file).read_text(encoding="utf-8") for file in tracked if file}
    for candidate in candidates.values():
        if not candidate.get("objectExists"):
            continue
        revision = candidate["revision"]
        candidate_files = execute(root, ["git", "ls-tree", "-rz", "--name-only", revision]).stdout.split("\0")
        for file in filter(None, candidate_files):
            public[f"candidate/{revision}/{file}"] = execute(root, ["git", "show", revision + ":" + file]).stdout
    record = dict(runtime=runtime, first=captured(first), second=captured(second), integration=last, ids=manifest["ids"],
                  calls=calls, before=before, after=after, baseline=baseline,
                  candidates=candidates, checkSha256=baseline["checkSha256"], public=public,
                  config=(root / "workspace/config.json").read_text(encoding="utf-8"),
                  configSha256=digest(root / "workspace/config.json"), sentinel=manifest["sentinel"],
                  priorAllowances=manifest["priorAllowances"], attempts=attempts,
                  operatorDecision=load(root / "private/operator-decision.json"),
                  writerStop=load(root / "private/writer-stop.json"), fixtureRoot=str(root),
                  readRoots=[str(path) for path in read_roots(root, manifest)],
                  expectedSecondInput=prompt(manifest, "continue"))
    return evaluate(record)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--runtime", choices=("codex", "claude"), required=True)
    args = parser.parse_args()
    try:
        checks = inspect_artifacts(args.root.resolve(), args.runtime)
    except (ValueError, KeyError, OSError) as error:
        print(json.dumps({"qualified": False, "inconclusive": str(error)}))
        raise SystemExit(1)
    print(json.dumps({"qualified": all(checks.values()), "checks": checks}, indent=2))
    raise SystemExit(0 if all(checks.values()) else 1)

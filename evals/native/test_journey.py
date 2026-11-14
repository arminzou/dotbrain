"""Synthetic calibration by default; real isolated Beads self-check is explicitly opt-in."""

import copy
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import journey
from verify import evaluate, native_trace, simple_read, inspect_artifacts, controller_access, continuation_access
from verify import lexical_identity, alias_boundary


def correct_record(runtime="codex"):
    ids = {role: "sample-" + role for role in ("contract", "api", "ui", "integration")}
    discovery = json.dumps({"pageSize": 7, "sourceSha256": "hash",
                            "hypothesis": {"claim": "Latency cause is unknown", "status": "unresolved"}})
    revision = "a" * 40
    ui_revision, baseline_sha, final_sha = "c" * 40, "b" * 40, "d" * 40
    check_hash = "check-hash"
    qualification = {role: {"taskId": ids[role], "workerActor": role + "-writer", "branch": "feature/" + role,
                           "revision": sha} for role, sha in (("api", revision), ("ui", ui_revision))}
    items = {item: {"id": item, "status": "in_progress" if role in {"api", "ui"} else "closed" if role == "contract" else "open",
                    "assignee": "coordinator-old" if role != "integration" else ""}
             for role, item in ids.items()}
    state = {"items": items, "knowledge": {"docs/discovery.json": discovery},
             "details": {"handoff": "docs/discovery.json FAIL candidate " + revision}, "head": baseline_sha,
             "refs": {value["branch"]: value["revision"] for value in qualification.values()}, "status": ""}
    for role, value in qualification.items():
        state["details"][ids[role]] = {"comments": [{"author": "coordinator-old", "text": json.dumps({"qualification": value})}]}
    recovered_state = copy.deepcopy(state)
    recovered_state["knowledge"]["docs/recovered.json"] = json.dumps({"discovery": json.loads(discovery),
         "nextWork": ids["integration"], "takeover": "operator-decision-required"})
    def events(session, tools, worker=False):
        if runtime == "codex":
            result = [{"type": "thread.started", "thread_id": session}]
            result += [{"type": "item.completed", "item": {"type": "command_execution", "command": name,
                       "aggregated_output": output, "exit_code": 0 if ok else 1}} for name, output, ok in tools]
            if worker:
                for role in ("api", "ui"):
                    for tool in ("spawn_agent", "wait"):
                        result.append({"type": "item.completed", "item": {"type": "collab_tool_call", "tool": tool,
                                       "prompt": ids[role] + " actor " + role + "-writer",
                                       "status": "completed", "agents_states": {role + "-child": {"status": "completed",
                                       "message": json.dumps({"qualification": qualification[role]}) if tool == "wait" else ""}}}})
            return result + [{"type": "turn.completed"}]
        result = [{"type": "system", "session_id": session}]
        for i, (name, output, ok) in enumerate(tools + ([("Agent-api", json.dumps({"qualification": qualification["api"]}), True),
                                                       ("Agent-ui", json.dumps({"qualification": qualification["ui"]}), True)] if worker else [])):
            tool = "Agent" if name.startswith("Agent-") else "Read" if name.startswith("cat ") else "Bash"
            args = ({"prompt": ids[name[6:]] + " actor " + name[6:] + "-writer"} if tool == "Agent" else
                    {"file_path": name[4:]} if tool == "Read" else {"command": name})
            result += [{"type": "assistant", "message": {"content": [{"type": "tool_use", "id": str(i),
                        "name": tool, "input": args}]}}]
            if tool == "Agent":
                result.append({"type": "assistant", "parent_tool_use_id": str(i), "message": {"content": [
                    {"type": "text", "text": "child activity"}]}})
            result += [{"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": str(i),
                        "content": output, "is_error": not ok}]}}]
        return result + [{"type": "result", "subtype": "success"}]
    first = {"name": "first", "home": "/fixture/first", "receipt": {"name": "first"},
             "events": events("session-a", [("cat config.json", '{"pageSize":7}', True),
                                             ("python check.py", json.dumps({"check": "catalog-v1", "ok": False,
                                              "revision": baseline_sha, "scriptSha256": check_hash}), False)], True),
             "sessionOutput": "unique-first-transcript", "input": "first task", "interrupted": True,
             "pid": 123, "exitCode": -1, "started": 1, "ended": 2}
    first["writerTree"] = {"present": [{"pid": 456, "created": "synthetic-start", "scoped": True}]}
    second = {"name": "second", "home": "/fixture/second", "receipt": {"name": "second"},
              "input": "cold task", "events": events("session-b", [("cat discovery.json", discovery, True),
                 ("cat config.json", '{"pageSize":7}', True), ("cat handoff", "operator decision: uncertain writer", True)])}
    read_roots = ["/fixture/workspace", "/fixture/data/brainspaces/catalog/.brain",
                  "/fixture/data/.cache/integrations/dotbrain-pstack"]
    second["aliasesBefore"] = {"schema": 1, "phase": "second", "root": lexical_identity("/fixture", "/fixture"),
        "roots": sorted(lexical_identity(path, "/fixture") for path in read_roots), "aliases": {}, "capturedAt": 1}
    second["aliasesAfter"] = copy.deepcopy(second["aliasesBefore"])
    second["aliasesAfter"]["capturedAt"] = 2
    baseline = {"head": baseline_sha, "checkSha256": check_hash,
                "details": {item: {"show": [{"dependencies": []}]} for item in ids.values()}}
    for child, parent in (("api", "contract"), ("ui", "contract"), ("integration", "api"), ("integration", "ui")):
        baseline["details"][ids[child]]["show"][0]["dependencies"].append({"depends_on_id": ids[parent]})
    final_state = copy.deepcopy(state)
    for role in ("api", "ui", "integration"):
        final_state["items"][ids[role]].update(status="closed", assignee="coordinator-new")
    final_state["head"] = final_sha
    def result(item, status, owner):
        return json.dumps([{"id": item, "status": status, "assignee": owner}])
    recovery_calls = []
    for role in ("api", "ui"):
        recovery_calls.append({"argv": ["update", ids[role], "--if-assignee", "coordinator-old", "--assignee", "coordinator-new",
                                "--actor", "coordinator-new", "--json"], "returncode": 0, "phase": "integration",
                               "stdout": result(ids[role], "in_progress", "coordinator-new")})
        recovery_calls.append({"argv": ["close", ids[role], "--actor", "coordinator-new", "--json"],
                               "returncode": 0, "phase": "integration", "stdout": result(ids[role], "closed", "coordinator-new")})
    recovery_calls += [{"argv": ["ready", "--json"], "returncode": 0, "phase": "integration",
                       "stdout": result(ids["integration"], "open", "")},
                      {"argv": ["update", ids["integration"], "--claim", "--actor", "coordinator-new", "--json"],
                       "returncode": 0, "phase": "integration", "stdout": result(ids["integration"], "in_progress", "coordinator-new")},
                      {"argv": ["close", ids["integration"], "--actor", "coordinator-new", "--json"],
                       "returncode": 0, "phase": "integration", "stdout": result(ids["integration"], "closed", "coordinator-new")}]
    integration = {"name": "integration", "receipt": {"name": "integration"}, "state": final_state,
                   "scriptPreserved": True, "productValid": True,
                   "events": events("session-c", [("bd " + " ".join(call["argv"]), call["stdout"], True) for call in recovery_calls[:-1]] +
                       [("python check.py", json.dumps({"check": "catalog-v1", "ok": True,
                                               "revision": final_sha, "scriptSha256": check_hash}), True),
                        ("bd " + " ".join(recovery_calls[-1]["argv"]), recovery_calls[-1]["stdout"], True)])}
    return dict(runtime=runtime, first=first, second=second, integration=integration, ids=ids, before=state, after=recovered_state,
                baseline=baseline, calls=[{"argv": ["close", ids["contract"], "--actor", "coordinator-old"],
                                          "returncode": 0, "phase": "first"}] +
                [{"argv": ["update", ids["api"], "--claim", "--actor", actor],
                                          "returncode": code, "phase": "first"}
                                         for actor, code in (("coordinator-old", 0), ("competitor", 1))] +
                [{"argv": ["update", ids["ui"], "--claim", "--actor", "coordinator-old"], "returncode": 0, "phase": "first"}] + recovery_calls,
                config='{"pageSize":7}', configSha256="hash", expectedSecondInput="cold task",
                candidates={role: {**value, "objectExists": True, "integrated": True, "scriptPreserved": True, "roleImplemented": True}
                            for role, value in qualification.items()}, checkSha256=check_hash, public={"README.md": "Public guidance"},
                sentinel="PRIVATE-CANARY", priorAllowances={"status": "exhausted", "renewed": False},
                operatorDecision={"decision": "authorize-takeover", "actor": "operator", "observedOwner": "coordinator-old"},
                fixtureRoot="/fixture", readRoots=read_roots, writerStop={"attempt": "first", "parent": 123,
                "before": {"present": first["writerTree"]["present"]},
                "after": {"fixtureRoot": "/fixture", "requested": [123, 456], "present": []}},
                attempts=[first["receipt"], second["receipt"], integration["receipt"]])


class Calibration(unittest.TestCase):
    @staticmethod
    def add_shell_result(record, command, output="selected first-session fragment"):
        if record["runtime"] == "codex":
            extra = [{"type": "item.completed", "item": {"type": "command_execution", "command": command,
                       "aggregated_output": output, "exit_code": 0}}]
        else:
            extra = [{"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "extra",
                       "name": "Bash", "input": {"command": command}}]}},
                     {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "extra", "content": output}]}}]
        record["second"]["events"][1:1] = extra

    @staticmethod
    def replace_check_command(record, phase, command):
        for event in record[phase]["events"]:
            if event.get("item", {}).get("command") == "python check.py":
                event["item"]["command"] = command
            for block in event.get("message", {}).get("content", []):
                if block.get("input", {}).get("command") == "python check.py":
                    block["input"]["command"] = command

    def test_known_correct_and_each_negative_canary(self):
        mutations = {
            "native_sessions": lambda r: r["second"].update(events=[]),
            "cold_continuation": lambda r: r["second"].update(input="unique-first-transcript"),
            "durable_discovery": lambda r: r["after"]["knowledge"].clear(),
            "corroborated_reads": lambda r: r["second"].update(events=r["second"]["events"][:1] + r["second"]["events"][-1:]),
            "knowledge_reused": lambda r: r["after"]["knowledge"].pop("docs/recovered.json"),
            "dependency_graph": lambda r: r["baseline"]["details"][r["ids"]["api"]]["show"][0].update(dependencies=[]),
            "contract_prerequisite": lambda r: r["calls"][0].update(returncode=1),
            "exclusive_claim": lambda r: r["calls"][2].update(returncode=0),
            "failed_check_held": lambda r: r["before"]["items"][r["ids"]["integration"]].update(status="closed"),
            "candidate": lambda r: r["candidates"]["api"].update(objectExists=False),
            "worker_lifecycle": lambda r: r["first"].update(events=[]),
            "interruption": lambda r: r["first"].update(interrupted=False),
            "uncertain_takeover_held": lambda r: r["calls"].append({"phase": "second", "argv": ["close", r["ids"]["api"]], "returncode": 0}),
            "integration_verified": lambda r: r["operatorDecision"].update(decision="hold"),
            "confirmed_writer_stop": lambda r: r["writerStop"]["after"].update(present=[{"pid": 456}]),
            "private_boundary": lambda r: r["public"].update(leak=r["sentinel"]),
            "limits_preserved": lambda r: r["priorAllowances"].update(renewed=True),
        }
        for runtime in ("codex", "claude"):
            correct = correct_record(runtime)
            self.assertEqual(set(evaluate(correct)), set(mutations))
            self.assertTrue(all(evaluate(correct).values()), evaluate(correct))
            for criterion, mutate in mutations.items():
                with self.subTest(runtime=runtime, criterion=criterion):
                    wrong = copy.deepcopy(correct)
                    mutate(wrong)
                    self.assertFalse(evaluate(wrong)[criterion])

    def test_missing_terminal_and_unlinked_tool_results_fail(self):
        self.assertFalse(native_trace("claude", [{"type": "result", "subtype": "error"}])["complete"])
        self.assertEqual(native_trace("claude", [{"type": "user", "message": {"content": [
            {"type": "tool_result", "tool_use_id": "unseen", "content": "contents"}]}}])["tools"], [])

    def test_reads_echoes_and_mentions_are_not_executed_checks(self):
        for runtime in ("codex", "claude"):
            for command in ("Get-Content check.py", "echo python check.py", 'python -c "print(\'check.py\')"'):
                for phase, criterion in (("first", "failed_check_held"), ("integration", "integration_verified")):
                    with self.subTest(runtime=runtime, command=command, phase=phase):
                        record = correct_record(runtime)
                        self.replace_check_command(record, phase, command)
                        self.assertFalse(evaluate(record)[criterion])

    def test_partial_uppercase_and_alternate_transcript_paths_are_rejected(self):
        for runtime in ("codex", "claude"):
            for target in (r"..\PRIVATE\first.RAW.JSONL", r"..\private\..\PrIvAtE\first.raw.jsonl",
                           r"\\?\C:\fixture\PRIVATE\first.raw.jsonl"):
                record = correct_record(runtime)
                if runtime == "codex":
                    extra = [{"type": "item.completed", "item": {"type": "command_execution", "command": "Get-Content " + target,
                               "aggregated_output": "selected first-session fragment", "exit_code": 0}}]
                else:
                    extra = [{"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "leak",
                              "name": "Read", "input": {"file_path": target}}]}},
                             {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "leak",
                              "content": "selected first-session fragment"}]}}]
                record["second"]["events"][1:1] = extra
                with self.subTest(runtime=runtime, path=target):
                    self.assertFalse(evaluate(record)["cold_continuation"])

    def test_recursive_glob_and_indirect_continuation_access_is_inconclusive(self):
        for runtime in ("codex", "claude"):
            for command in ("Get-ChildItem .. -Recurse -Filter *first* | Get-Content",
                            "Get-ChildItem .. -Recurse -File -Filter *first* | Get-Content",
                            "Get-Content ../**/*first*", "Get-Content ..",
                            'python -c "from pathlib import Path; print(next(Path(\'..\').rglob(\'*first*\')).read_text())"',
                            "$candidate = '..'; Get-ChildItem $candidate -Recurse | Get-Content"):
                record = correct_record(runtime)
                self.add_shell_result(record, command)
                with self.subTest(runtime=runtime, command=command):
                    self.assertFalse(evaluate(record)["cold_continuation"])
            for command in ("cat config.json", "Get-Content .brain/docs/discovery.json", "bd ready --json",
                            "bd show sample-api --json", "bd comments sample-api --json", "git status --porcelain",
                            "bd dolt test", "bd --readonly dolt test", "dotbrain doctor --json",
                            "bd --readonly ready --json",
                            "dotbrain doctor --home /fixture/data --repo /fixture/workspace --json"):
                record = correct_record(runtime)
                self.add_shell_result(record, command, "ordinary fixture state")
                with self.subTest(runtime=runtime, ordinary=command):
                    self.assertTrue(evaluate(record)["cold_continuation"])
            for command in ("dotbrain doctor --home .. --json", "dotbrain doctor --repo ../private --json"):
                record = correct_record(runtime)
                self.add_shell_result(record, command)
                self.assertFalse(evaluate(record)["cold_continuation"])
            record = correct_record(runtime)
            if runtime == "codex":
                unknown = [{"type": "item.completed", "item": {"id": "unknown", "type": "mcp_tool_call", "output": "fragment"}}]
                unfinished = [{"type": "item.started", "item": {"id": "unfinished", "type": "command_execution", "command": "cat config.json"}}]
            else:
                unknown = [{"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "unknown",
                    "name": "Grep", "input": {"path": "..", "pattern": "first"}}]}}, {"type": "user", "message": {
                    "content": [{"type": "tool_result", "tool_use_id": "unknown", "content": "fragment"}]}}]
                unfinished = [{"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "unfinished",
                    "name": "Read", "input": {"file_path": "config.json"}}]}}]
            for extra in (unknown, unfinished):
                wrong = copy.deepcopy(record)
                wrong["second"]["events"][1:1] = extra
                self.assertFalse(evaluate(wrong)["cold_continuation"])

    def test_coordinator_claims_are_distinct_from_native_worker_candidate_returns(self):
        for runtime in ("codex", "claude"):
            record = correct_record(runtime)
            owner = record["operatorDecision"]["observedOwner"]
            for role in ("api", "ui"):
                self.assertEqual(record["before"]["items"][record["ids"][role]]["assignee"], owner)
                self.assertNotEqual(record["candidates"][role]["workerActor"], owner)
            self.assertTrue(all(evaluate(record).values()))
            for defect in ("missing", "wrong-revision", "wrong-branch", "wrong-task", "wrong-worker"):
                wrong = copy.deepcopy(record)
                changes = {"wrong-revision": ("a" * 40, "f" * 40), "wrong-branch": ("feature/api", "feature/unrelated"),
                           "wrong-task": ("sample-api", "sample-ui"), "wrong-worker": ("api-writer", "other-worker")}
                agent_ids = {block["id"] for event in wrong["first"]["events"] for block in
                    event.get("message", {}).get("content", []) if block.get("name") == "Agent" and
                    "sample-api" in block.get("input", {}).get("prompt", "")}
                for event in wrong["first"]["events"]:
                    item = event.get("item", {})
                    returned = item.get("agents_states", {}).get("api-child") if item.get("tool") == "wait" else None
                    if returned:
                        returned["message"] = "worker completed" if defect == "missing" else returned["message"].replace(*changes[defect])
                    for block in event.get("message", {}).get("content", []):
                        if block.get("tool_use_id") in agent_ids:
                            block["content"] = "worker completed" if defect == "missing" else block["content"].replace(*changes[defect])
                with self.subTest(runtime=runtime, returned=defect):
                    grade = evaluate(wrong)
                    self.assertFalse(grade["candidate"])
                    self.assertFalse(grade["worker_lifecycle"])

    def test_cold_skill_loading_is_limited_to_vetted_core_and_mode(self):
        for skill, expected in (("dotbrain:work-graph", True), ("dotbrain-pstack", True),
                                ("unknown:read-anything", False), ("dotbrain:unknown", False), (None, False)):
            self.assertEqual(continuation_access({"name": "Skill", "input": json.dumps({"skill": skill}), "skill": skill},
                             "/fixture", "/fixture/first", ["/fixture/workspace"]), expected)

    def test_confirmed_recovery_requires_guards_ownership_and_prerequisite_transitions(self):
        defects = ("absent-transfer", "absent-guard", "duplicate-guard", "forced-guard", "failed-guard", "wrong-old-owner", "wrong-result-owner",
                   "missing-result", "old-final-owner", "open-api", "open-ui", "forced-api-close", "forced-integration-close",
                   "absent-ready", "early-ready", "absent-integration-claim", "early-integration-close")
        for runtime in ("codex", "claude"):
            correct = correct_record(runtime)
            next(c for c in correct["calls"] if c["argv"][0] == "ready")["argv"] = ["--readonly", "ready", "--json"]
            self.assertTrue(evaluate(correct)["integration_verified"])
            for defect in defects:
                record = correct_record(runtime)
                calls = record["calls"]
                guards = [c for c in calls if "--if-assignee" in c["argv"]]
                api, ui, integration = (record["ids"][role] for role in ("api", "ui", "integration"))
                if defect == "absent-transfer":
                    record["calls"] = [c for c in calls if c not in guards]
                elif defect == "absent-guard":
                    index = guards[0]["argv"].index("--if-assignee")
                    del guards[0]["argv"][index:index + 2]
                elif defect == "failed-guard":
                    guards[0]["returncode"] = 13
                elif defect == "duplicate-guard":
                    guards[0]["argv"] += ["--if-assignee", "changed-owner"]
                elif defect == "forced-guard":
                    guards[0]["argv"].append("--force")
                elif defect == "wrong-old-owner":
                    guards[0]["argv"][guards[0]["argv"].index("--if-assignee") + 1] = "changed-owner"
                elif defect == "wrong-result-owner":
                    guards[0]["stdout"] = guards[0]["stdout"].replace("coordinator-new", "other-owner")
                elif defect == "missing-result":
                    guards[0].pop("stdout")
                elif defect == "old-final-owner":
                    record["integration"]["state"]["items"][api]["assignee"] = "coordinator-old"
                elif defect in {"open-api", "open-ui"}:
                    record["integration"]["state"]["items"][api if defect == "open-api" else ui]["status"] = "open"
                elif defect.startswith("forced-"):
                    target = api if defect == "forced-api-close" else integration
                    next(c for c in calls if c["phase"] == "integration" and c["argv"][:2] == ["close", target])["argv"].append("--force")
                elif defect in {"absent-ready", "early-ready"}:
                    ready = next(c for c in calls if c["argv"][0] == "ready")
                    calls.remove(ready)
                    if defect == "early-ready":
                        index = next(i for i, c in enumerate(calls) if c["argv"][:2] == ["close", ui])
                        calls.insert(index, ready)
                elif defect == "absent-integration-claim":
                    record["calls"] = [c for c in calls if c["argv"][:2] != ["update", integration]]
                else:
                    close = next(c for c in calls if c["argv"][:2] == ["close", integration])
                    calls.remove(close)
                    calls.insert(4, close)
                with self.subTest(runtime=runtime, recovery=defect):
                    self.assertFalse(evaluate(record)["integration_verified"])

    def test_controller_artifact_symlink_identity_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            journey.write(root / "private/first.raw.jsonl", "partial transcript")
            (root / "workspace").mkdir()
            alias = root / "workspace/context.json"
            alias.symlink_to(root / "private/first.raw.jsonl")
            self.assertTrue(controller_access({"input": str(alias), "paths": [str(alias)]}, str(root), str(root / "homes/first")))
            self.assertTrue(controller_access({"input": "Get-Content context.json -TotalCount 1",
                "command": "Get-Content context.json -TotalCount 1"}, str(root), str(root / "homes/first")))
            brain = root / "data/brainspaces/catalog/.brain"
            cache = root / "data/.cache/integrations/dotbrain-pstack/example"
            journey.write(brain / "docs/discovery.json", "verified knowledge")
            journey.write(cache / "SKILL.md", "public mode")
            (root / "workspace/.brain").symlink_to(brain, target_is_directory=True)
            mode = root / "workspace/.agents/skills/dotbrain-pstack"
            mode.parent.mkdir(parents=True)
            mode.symlink_to(cache, target_is_directory=True)
            for path in (root / "workspace/.brain/docs/discovery.json", mode / "SKILL.md"):
                self.assertTrue(continuation_access({"name": "Read", "input": str(path), "paths": [str(path)]},
                    str(root), str(root / "homes/first"), [str(root / "workspace"), str(brain), str(cache.parent)]))

    def test_frozen_alias_receipts_survive_removal_and_retargeting(self):
        for runtime in ("codex", "claude"):
            for kind in ("symlink", "hardlink"):
                for change in ("removed", "retargeted"):
                    for controller_target in (True, False):
                        with self.subTest(runtime=runtime, kind=kind, change=change, controller=controller_target), tempfile.TemporaryDirectory() as tmp:
                            root = Path(tmp)
                            manifest = {"schema": 2}
                            journey.write(root / "fixture.json", manifest)
                            journey.write(root / "workspace/config.json", '{"pageSize":7}')
                            journey.write(root / "private/first.raw.jsonl", "header\nselected first-session fragment\nfooter")
                            brain = root / "data/brainspaces/catalog/.brain"
                            (brain / "docs").mkdir(parents=True)
                            (root / "workspace/.brain").symlink_to(brain, target_is_directory=True)
                            alias = brain / "docs/context.json"
                            target = root / ("private/first.raw.jsonl" if controller_target else "workspace/config.json")
                            if kind == "symlink":
                                alias.symlink_to(target)
                            else:
                                os.link(target, alias)
                            before = journey.capture_aliases(root, "second")
                            output = alias.read_text().splitlines()[1] if controller_target else alias.read_text()
                            after = journey.capture_aliases(root, "second")
                            alias.unlink()
                            if change == "retargeted":
                                alias.symlink_to(root / ("workspace/config.json" if controller_target else "private/first.raw.jsonl"))
                            record = correct_record(runtime)
                            record.update(fixtureRoot=str(root), readRoots=[str(path) for path in journey.read_roots(root, manifest)])
                            record["first"]["home"] = str(root / "homes/first")
                            record["second"].update(home=str(root / "homes/second"), aliasesBefore=before, aliasesAfter=after)
                            record["writerStop"]["after"]["fixtureRoot"] = str(root)
                            if runtime == "codex":
                                self.add_shell_result(record, "cat .brain/docs/context.json", output)
                            else:
                                record["second"]["events"][1:1] = [
                                    {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "alias-read",
                                     "name": "Read", "input": {"file_path": ".brain/docs/context.json"}}]}},
                                    {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "alias-read", "content": output}]}}]
                            self.assertEqual(evaluate(record)["cold_continuation"], not controller_target)

    def test_missing_or_changed_alias_boundary_is_inconclusive(self):
        for runtime in ("codex", "claude"):
            missing = correct_record(runtime)
            missing["second"].pop("aliasesBefore")
            self.assertFalse(evaluate(missing)["cold_continuation"])
            changed = correct_record(runtime)
            changed["second"]["aliasesAfter"]["aliases"][lexical_identity("/fixture/workspace/context.json", "/fixture")] = \
                lexical_identity("/fixture/workspace/config.json", "/fixture")
            self.assertFalse(evaluate(changed)["cold_continuation"])

    def test_alias_capture_does_not_follow_runtime_home_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            journey.write(root / "fixture.json", {"schema": 2})
            (root / "private").mkdir()
            (root / "workspace").mkdir()
            home = root / "homes/first/.codex"
            journey.write(home / "auth.json", "AUTH-PAYLOAD-MUST-NOT-BE-CAPTURED")
            (root / "workspace/home-view").symlink_to(home, target_is_directory=True)
            real_scandir = os.scandir
            def guarded_scandir(path):
                self.assertFalse(Path(path).resolve().is_relative_to(root / "homes"))
                return real_scandir(path)
            with patch("journey.os.scandir", side_effect=guarded_scandir):
                receipt = journey.capture_aliases(root, "second")
            self.assertNotIn("AUTH-PAYLOAD-MUST-NOT-BE-CAPTURED", json.dumps(receipt))

    def assert_snapshot_skips_directory_alias(self, junction=False):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            journey.write(root / "fixture.json", {"schema": 2})
            brain = root / "data/brainspaces/catalog/.brain"
            journey.write(brain / "docs/notes.md", "ordinary recorded knowledge")
            journey.write(root / "workspace/check.py", journey.CHECK_SCRIPT)
            home = root / "homes/first/.codex"
            payload = "SYNTHETIC-AUTH-MUST-NOT-BE-SNAPSHOTTED"
            journey.write(home / "auth.json", payload)
            alias = brain / "redirected-home"
            if junction:
                command = "New-Item -ItemType Junction -Path '{}' -Target '{}' | Out-Null".format(
                    str(alias).replace("'", "''"), str(home).replace("'", "''"))
                subprocess.run(["pwsh", "-NoProfile", "-Command", command], check=True,
                               capture_output=True, text=True, timeout=30)
            else:
                alias.symlink_to(home, target_is_directory=True)
            try:
                self.assertTrue(journey.is_alias(alias))
                real_scandir, real_read_text = os.scandir, Path.read_text
                def guarded_scandir(path):
                    self.assertFalse(Path(path).resolve().is_relative_to(root / "homes"),
                                     "snapshot descended into a runtime home")
                    return real_scandir(path)
                def guarded_read_text(path, *args, **kwargs):
                    self.assertFalse(path.resolve().is_relative_to(root / "homes"),
                                     "snapshot opened a runtime-home file")
                    return real_read_text(path, *args, **kwargs)
                result = subprocess.CompletedProcess([], 0, stdout="", stderr="")
                with patch("journey.bd", return_value=subprocess.CompletedProcess([], 0, stdout="[]")), \
                        patch("journey.execute", return_value=result), \
                        patch("journey.os.scandir", side_effect=guarded_scandir), \
                        patch.object(Path, "read_text", guarded_read_text):
                    snapshot = journey.snapshot(root, "alias-check")
                self.assertEqual(snapshot["knowledge"], {"docs/notes.md": "ordinary recorded knowledge"})
                self.assertNotIn(payload, (root / "private/alias-check.json").read_text())
            finally:
                alias.rmdir() if junction else alias.unlink()
            self.assertEqual((home / "auth.json").read_text(), payload)

    def test_snapshot_does_not_follow_directory_symlinks(self):
        self.assert_snapshot_skips_directory_alias()

    @unittest.skipUnless(sys.platform == "win32", "Windows directory junction regression")
    def test_snapshot_does_not_follow_directory_junctions(self):
        self.assert_snapshot_skips_directory_alias(junction=True)

    def test_each_dependent_task_needs_its_own_worker_and_integrated_candidate(self):
        for runtime in ("codex", "claude"):
            for defect in ("wrong-worker", "unrelated-commit", "missing-ui", "unintegrated", "missing-ui-claim"):
                record = correct_record(runtime)
                if defect == "wrong-worker":
                    record["candidates"]["api"]["workerActor"] = "unrelated-writer"
                elif defect == "unrelated-commit":
                    record["candidates"]["api"]["roleImplemented"] = False
                elif defect == "missing-ui":
                    record["candidates"].pop("ui")
                elif defect == "unintegrated":
                    record["candidates"]["ui"]["integrated"] = False
                else:
                    record["calls"] = [c for c in record["calls"] if c["argv"][:2] != ["update", record["ids"]["ui"]]]
                with self.subTest(runtime=runtime, defect=defect):
                    self.assertFalse(evaluate(record)["candidate"])
            record = correct_record(runtime)
            record["candidates"]["ui"]["workerActor"] = "api-writer"
            self.assertFalse(evaluate(record)["worker_lifecycle"])

    def test_echoed_contents_and_background_launch_are_not_read_or_completion(self):
        self.assertTrue(simple_read('pwsh -NoProfile -Command "Get-Content config.json"'))
        self.assertFalse(simple_read('echo "cat config.json"'))
        self.assertFalse(simple_read("cat config.json; echo fabricated"))
        record = correct_record("claude")
        for event in record["first"]["events"]:
            for block in event.get("message", {}).get("content", []):
                if block.get("name") == "Agent":
                    block["input"]["run_in_background"] = True
        self.assertFalse(evaluate(record)["worker_lifecycle"])

    def test_transcript_leak_through_tool_output_cannot_pass_continuation(self):
        record = correct_record()
        record["second"]["events"].insert(1, {"type": "item.completed", "item": {
            "type": "command_execution", "command": "cat unrelated.json", "exit_code": 0,
            "aggregated_output": record["first"]["sessionOutput"]}})
        self.assertFalse(evaluate(record)["cold_continuation"])

    def test_export_retains_raw_hashes_and_never_reads_auth_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            journey.write(root / "fixture.json", {"sentinel": "PRIVATE-CANARY", "candidate": "/source", "pstack": "/mode"})
            journey.write(root / "private/native.raw.jsonl", '{"nested":{"actor":"writer","token_count":5,"access_token":"secret"}}\n')
            journey.write(root / "homes/first/.codex/auth.json", "must never be copied")
            raw_hash = journey.digest(root / "private/native.raw.jsonl")
            output = journey.export(root)
            self.assertEqual(journey.load(output / "hashes.json")["native.raw.jsonl"]["rawSha256"], raw_hash)
            exported = [json.loads(line) for line in (output / "native.raw.jsonl").read_text().splitlines()]
            self.assertEqual(exported[0]["nested"]["actor"], "writer")
            self.assertEqual(exported[0]["nested"]["token_count"], 5)
            self.assertEqual(exported[0]["nested"]["access_token"], "[REDACTED]")
            self.assertFalse((output / "auth.json").exists())
            self.assertEqual(journey.digest(root / "private/native.raw.jsonl"), raw_hash)
            with self.assertRaises(ValueError):
                journey.export(root)

    def test_artifact_verifier_checks_real_candidate_object(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / "workspace"
            workspace.mkdir()
            git_env = journey.environment(root)
            subprocess.run(["git", "init", "-q", "-b", "main", str(workspace)], check=True, env=git_env)
            def git(*args):
                return subprocess.run(["git", "-C", str(workspace), "-c", "user.name=Fixture",
                                       "-c", "user.email=fixture@example.invalid", *args],
                                      capture_output=True, text=True, check=True, env=git_env).stdout.strip()
            journey.write(workspace / "config.json", '{"pageSize":7}')
            journey.write(workspace / "check.py", journey.CHECK_SCRIPT)
            git("add", ".")
            git("commit", "-qm", "Seed synthetic artifact calibration")
            baseline_head = git("rev-parse", "HEAD")
            git("switch", "-c", "feature/api")
            journey.write(workspace / "api.json", '{"pageSize":7}')
            git("add", ".")
            git("commit", "-qm", "Synthetic candidate")
            revision = git("rev-parse", "HEAD")
            git("switch", "-c", "feature/ui", baseline_head)
            journey.write(workspace / "ui.json", '{"pageSize":7}')
            git("add", ".")
            git("commit", "-qm", "Synthetic UI candidate")
            ui_revision = git("rev-parse", "HEAD")
            git("switch", "main")
            git("merge", "--no-edit", "feature/api")
            git("merge", "--no-edit", "feature/ui")
            final_revision = git("rev-parse", "HEAD")
            config_hash = hashlib.sha256((workspace / "config.json").read_bytes()).hexdigest()
            encoded = json.dumps(correct_record()).replace("check-hash", journey.digest(workspace / "check.py"))
            for old, new in (("a" * 40, revision), ("c" * 40, ui_revision), ("b" * 40, baseline_head),
                             ("d" * 40, final_revision), ("hash", config_hash)):
                encoded = encoded.replace(old, new)
            record = json.loads(encoded)
            attempts = []
            manifest = {"schema": 2, "root": str(root), "ids": record["ids"], "attempts": attempts, "priorAllowances": record["priorAllowances"]}
            journey.write(root / "fixture.json", manifest)
            for phase, value, state in (("first", record["first"], record["before"]),
                                        ("continue", record["second"], record["after"]),
                                        ("integration", record["integration"], record["integration"]["state"])):
                attempt = {key: item for key, item in value.items() if key not in {
                    "events", "input", "sessionOutput", "receipt", "state", "aliasesBefore", "aliasesAfter"}}
                attempt.update(runtime="codex", phase=phase)
                attempts.append(attempt)
                journey.write(root / f"private/{value['name']}.raw.jsonl", "\n".join(json.dumps(e) for e in value["events"]) + "\n")
                journey.write(root / f"private/{value['name']}.input.txt", journey.prompt(manifest, phase))
                state = copy.deepcopy(state)
                state["items"] = list(state["items"].values())
                journey.write(root / f"private/{value['name']}-after.json", state)
                if phase == "continue":
                    for label in ("Before", "After"):
                        receipt = root / f"private/{value['name']}-aliases-{label.lower()}.json"
                        journey.write(receipt, journey.capture_aliases(root, value["name"]))
                        attempt[f"aliases{label}Sha256"] = journey.digest(receipt)
            manifest["sentinel"] = record["sentinel"]
            journey.write(root / "fixture.json", manifest)
            journey.write(root / "private/baseline.json", record["baseline"])
            journey.write(root / "private/beads.jsonl", "\n".join(json.dumps(c) for c in record["calls"]) + "\n")
            journey.write(root / "private/operator-decision.json", record["operatorDecision"])
            record["writerStop"]["after"]["fixtureRoot"] = str(root)
            journey.write(root / "private/writer-stop.json", record["writerStop"])
            checks = inspect_artifacts(root, "codex")
            self.assertTrue(all(checks.values()), checks)
            alias_file = root / "private/second-aliases-before.json"
            alias_body = alias_file.read_text()
            journey.write(alias_file, {"tampered": True})
            with self.assertRaisesRegex(ValueError, "alias receipt changed"):
                inspect_artifacts(root, "codex")
            journey.write(alias_file, alias_body)
            original_state = journey.load(root / "private/first-after.json")
            state = copy.deepcopy(original_state)
            claim = json.loads(state["details"][record["ids"]["api"]]["comments"][0]["text"])
            claim["qualification"]["revision"] = "f" * 40
            state["details"][record["ids"]["api"]]["comments"][0]["text"] = json.dumps(claim)
            journey.write(root / "private/first-after.json", state)
            self.assertFalse(inspect_artifacts(root, "codex")["candidate"])
            for defect, role, parent in (("unrelated", "api", baseline_head), ("unmerged", "ui", ui_revision)):
                git("switch", "-c", defect, parent)
                journey.write(workspace / "candidate-note.txt", defect)
                git("add", ".")
                git("commit", "-qm", "Synthetic incorrect candidate")
                incorrect = git("rev-parse", "HEAD")
                state = copy.deepcopy(original_state)
                claimed = json.loads(state["details"][record["ids"][role]]["comments"][0]["text"])
                claimed["qualification"]["revision"] = incorrect
                state["details"][record["ids"][role]]["comments"][0]["text"] = json.dumps(claimed)
                state["refs"]["feature/" + role] = incorrect
                journey.write(root / "private/first-after.json", state)
                with self.subTest(defect=defect):
                    self.assertFalse(inspect_artifacts(root, "codex")["candidate"])

    def test_redaction_preserves_deep_actor_and_usage_telemetry(self):
        value = {"input": {"actor": "writer", "nested": [{"read": {"contents": "complete output"}}]},
                 "usage": {"input_tokens": 42}, "access_token": "secret", "authorization": "Bearer secret",
                 "text": "PRIVATE-CANARY", "raw": "Bearer abc.def.ghi",
                 "PRIVATE-CANARY": "key must be scrubbed", "token": "synthetic-credential",
                 "OPENAI_API_KEY": "synthetic-credential",
                 "encoded": '{"access_token":"nested-secret", "actor":"writer"}',
                 "environment": "OPENAI_API_KEY=" + "synthetic-value"}
        safe = journey.redact(value, ("PRIVATE-CANARY",))
        self.assertEqual(safe["input"], value["input"])
        self.assertEqual(safe["usage"], value["usage"])
        self.assertNotIn("secret", json.dumps(safe))
        self.assertNotIn("PRIVATE-CANARY", json.dumps(safe))
        self.assertNotIn("abc.def.ghi", json.dumps(safe))
        self.assertEqual(json.loads(safe["encoded"])["actor"], "writer")
        self.assertNotIn("synthetic-credential", json.dumps(safe))
        self.assertEqual(journey.redact({"token": 42}), {"token": 42})

    def test_environment_and_boundary_never_use_ambient_routing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.dict(os.environ, {"BEADS_DOLT_SERVER_HOST": "live", "OPENAI_API_KEY": "secret", "BEADS_DIR": "live"}):
                env = journey.environment(root)
            self.assertNotIn("BEADS_DOLT_SERVER_HOST", env)
            self.assertNotIn("OPENAI_API_KEY", env)
            self.assertTrue(Path(env["BEADS_DIR"]).is_relative_to(root))
            journey.write(root / "fixture.json", {"bd": "never-launch"})
            for args in (["--global", "list"], ["update", "sample-api", "--db=live"],
                         ["update", "sample-api", "--claim"], ["dolt", "push"], ["init", "--actor", "writer"]):
                with self.subTest(args=args), self.assertRaises(ValueError):
                    journey.bd(root, args, phase="native")
            with self.assertRaises(ValueError):
                journey.confined(root, "../outside")

    def test_no_native_calls_without_explicit_gate(self):
        with self.assertRaises(ValueError):
            journey.run_phase(Path("unused"), "codex", "first", "never-launch")

    def test_backend_probe_proxy_keeps_readonly_connectivity_queries_in_fixture_store(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            journey.write(root / "fixture.json", {"schema": 2, "bd": "actual-bd"})
            (root / "private").mkdir()
            calls = []
            def run(argv, **kwargs):
                calls.append(argv)
                self.assertEqual(Path(kwargs["env"]["BEADS_DIR"]), root / "data/brainspaces/catalog/.beads")
                return subprocess.CompletedProcess(argv, 0, "backend healthy", "")
            for args in (["dolt", "test"], ["--readonly", "dolt", "test"], ["--readonly", "ready", "--json"]):
                self.assertEqual(journey.bd(root, args, phase="native", run=run).returncode, 0)
            self.assertEqual(len(calls), 3)
            for args in (["dolt", "push"], ["--readonly", "dolt", "sql"], ["--readonly", "dolt", "test", "--global"],
                         ["ready", "--global=true"], ["ready", "-Coutside"],
                         ["update", "sample-api", "--claim"]):
                with self.assertRaises(ValueError):
                    journey.bd(root, args, phase="native", run=run)
            self.assertEqual(len(calls), 3)

    def test_explicit_uncapped_override_preserves_defaults_and_attempts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            previous = [{"runtime": "codex", "phase": "first", "name": str(i), "exitCode": 1} for i in range(12)]
            journey.write(root / "fixture.json", {"schema": 1, "root": str(root), "ids": correct_record()["ids"],
                          "attempts": previous, "sessionLimit": 12, "consecutiveFailureLimit": 3})
            with self.assertRaisesRegex(ValueError, "allowance exhausted"):
                journey.run_phase(root, "codex", "first", "unused", True)
            with patch("journey.execute", return_value=subprocess.CompletedProcess([], 0, "synthetic version", "")), \
                    patch("journey.snapshot"), patch("journey.subprocess.Popen", side_effect=RuntimeError("launch sentinel")):
                with self.assertRaisesRegex(RuntimeError, "launch sentinel"):
                    journey.run_phase(root, "codex", "first", "unused", True, uncapped=True)
            manifest = journey.load(root / "fixture.json")
            self.assertEqual(manifest["attempts"][:12], previous)
            self.assertEqual(manifest["sessionLimit"], 12)
            self.assertTrue(manifest["attempts"][-1]["limits"]["uncappedOverride"])

    def test_uncertain_writer_scope_never_reaches_stop(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            known = {"pid": 456, "created": "synthetic-start", "scoped": False}
            journey.write(root / "fixture.json", {"attempts": [{"name": "first", "phase": "first", "pid": 123,
                          "exitCode": -1, "writerTree": {"present": [known]}}]})
            with patch("journey.process_observation", return_value={"present": [known]}) as observe:
                with self.assertRaisesRegex(ValueError, "not fixture-scoped"):
                    journey.stop_writers(root)
                self.assertEqual(observe.call_count, 1)


@unittest.skipUnless(os.environ.get("NATIVE_FIXTURE_BD"), "opt-in actual isolated Beads backend")
class RealBackend(unittest.TestCase):
    def test_isolated_graph_claims_and_failed_check(self):
        # Preserve the actual backend and receipts for inspection, including on failure.
        parent = Path(os.environ.get("NATIVE_FIXTURE_PARENT", tempfile.gettempdir())) / "dotbrain-native-selfchecks"
        parent.mkdir(parents=True, exist_ok=True)
        root = Path(tempfile.mkdtemp(prefix="native-selfcheck-", dir=parent)) / "fixture"
        source = root.parent / "source"
        source.mkdir()
        git_env = journey.environment(root.parent)
        subprocess.run(["git", "init", "-q", str(source)], check=True, env=git_env)
        subprocess.run(["git", "-C", str(source), "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                        "commit", "--allow-empty", "-qm", "Seed fixture source"], check=True, env=git_env)
        candidate = Path(__file__).resolve().parents[2]
        pstack = Path(os.environ.get("NATIVE_FIXTURE_PSTACK", str(source))).resolve()
        manifest = journey.prepare(root, candidate, pstack, Path(os.environ["NATIVE_FIXTURE_BD"]).resolve())
        baseline = journey.load(root / "private/baseline.json")
        self.assertEqual([item["id"] for item in baseline["ready"]], [manifest["ids"]["contract"]])
        item = manifest["ids"]["contract"]
        self.assertEqual(journey.bd(root, ["update", item, "--claim", "--actor", "writer-a"]).returncode, 0)
        self.assertNotEqual(journey.bd(root, ["update", item, "--claim", "--actor", "writer-b"], check=False).returncode, 0)
        claimed = json.loads(journey.bd(root, ["show", item, "--json"]).stdout)
        self.assertEqual(claimed[0]["assignee"], "writer-a")
        wrong_guard = journey.bd(root, ["update", item, "--if-assignee", "changed-owner", "--assignee", "coordinator-new",
                                       "--actor", "coordinator-new", "--json"], check=False)
        self.assertEqual(wrong_guard.returncode, 13)
        transferred = journey.bd(root, ["update", item, "--if-assignee", "writer-a", "--assignee", "coordinator-new",
                                       "--actor", "coordinator-new", "--json"])
        self.assertEqual(json.loads(transferred.stdout)[0]["assignee"], "coordinator-new")
        self.assertEqual(journey.bd(root, ["--readonly", "ready", "--json"]).returncode, 0)
        self.assertIn(str(journey.brainspace(root) / ".beads"), journey.bd(root, ["where"]).stdout)
        self.assertNotEqual(journey.execute(root, [sys.executable, "check.py"], check=False).returncode, 0)
        self.assertFalse((root / "workspace/.brain").exists())
        self.assertFalse((root / "workspace/.beads").exists())
        self.assertTrue((root / "data/.git").is_dir())
        self.assertTrue((journey.brainspace(root) / ".beads/metadata.json").is_file())
        self.assertEqual(journey.load(journey.brainspace(root) / ".beads/metadata.json")["dolt_mode"], "embedded")
        if os.environ.get("NATIVE_FIXTURE_DOTBRAIN"):
            self.assertIn("NATIVE_FIXTURE_PSTACK", os.environ, "Actual mode wiring needs an explicit qualified pstack source")
            identity = journey.load(journey.brainspace(root) / ".beads/metadata.json")["project_id"]
            receipt = journey.wire(root, os.environ["NATIVE_FIXTURE_DOTBRAIN"])
            self.assertEqual(receipt["exitCode"], 0)
            self.assertTrue(receipt["backendPreserved"])
            self.assertTrue((root / "workspace/.brain").is_symlink())
            self.assertTrue((root / "workspace/.beads").is_symlink())
            self.assertEqual(identity, journey.load(journey.brainspace(root) / ".beads/metadata.json")["project_id"])
            before = journey.capture_aliases(root, "wire-selfcheck")
            after = journey.capture_aliases(root, "wire-selfcheck")
            self.assertTrue(alias_boundary({"name": "wire-selfcheck", "aliasesBefore": before, "aliasesAfter": after},
                            str(root), str(root / "homes/first"), [str(path) for path in journey.read_roots(root, manifest)]))
        print("Actual backend self-check retained:", root)


@unittest.skipUnless(os.environ.get("NATIVE_FIXTURE_PROCESS_CHECK") == "1" and sys.platform == "win32",
                     "opt-in Windows fixture process controls")
class ProcessControls(unittest.TestCase):
    def test_exit_between_enumeration_and_lookup_is_safe_but_permission_errors_fail(self):
        for scenario in ("exited", "exited-object", "permission"):
            with self.subTest(scenario=scenario), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                journey.write(root / "writer.py", "import time\ntime.sleep(600)\n")
                process = subprocess.Popen([sys.executable, str(root / "writer.py")], cwd=root,
                                           env=journey.environment(root))
                try:
                    observed = journey.process_observation(root, [process.pid])
                    self.assertTrue(observed["present"][0]["scoped"])
                    def race_runner(argv, **kwargs):
                        script = base64.b64decode(argv[-1]).decode("utf-16le")
                        if scenario == "exited":
                            # Exit after the CIM snapshot, immediately before process-object lookup.
                            script = script.replace("try { $writer=Get-Process",
                                "Stop-Process -Id $target.pid -Force -ErrorAction Stop; "
                                "Wait-Process -Id $target.pid -ErrorAction SilentlyContinue; try { $writer=Get-Process")
                        elif scenario == "exited-object":
                            script = script.replace("Stop-Process -InputObject $writer",
                                "$writer.Kill(); $writer.WaitForExit(); Stop-Process -InputObject $writer")
                        else:
                            script = "function Get-Process { throw [System.UnauthorizedAccessException]::new('fixture-permission-denied') }; " + script
                        argv = [*argv[:-1], base64.b64encode(script.encode("utf-16le")).decode("ascii")]
                        return subprocess.run(argv, **kwargs)
                    if scenario != "permission":
                        after = journey.process_observation(root, [process.pid], stop=observed["present"], run=race_runner)
                        self.assertEqual(after["present"], [])
                        process.wait(timeout=10)
                    else:
                        with self.assertRaisesRegex(RuntimeError, "fixture-permission-denied"):
                            journey.process_observation(root, [process.pid], stop=observed["present"], run=race_runner)
                        self.assertIsNone(process.poll())
                finally:
                    if process.poll() is None:
                        process.kill()
                        process.wait(timeout=10)

    def test_captured_fixture_writer_is_stopped_by_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            journey.write(root / "writer.py", "import time\ntime.sleep(600)\n")
            process = subprocess.Popen([sys.executable, str(root / "writer.py")], cwd=root,
                                       env=journey.environment(root))
            try:
                observed = journey.process_observation(root, [process.pid])
                self.assertEqual(observed["present"][0]["pid"], process.pid)
                self.assertTrue(observed["present"][0]["scoped"])
                stale = copy.deepcopy(observed["present"])
                stale[0]["created"] = "0"
                with self.assertRaisesRegex(RuntimeError, "identity changed"):
                    journey.process_observation(root, [process.pid], stop=stale)
                self.assertIsNone(process.poll())
                after = journey.process_observation(root, [process.pid], stop=observed["present"])
                self.assertEqual(after["present"], [])
                process.wait(timeout=10)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=10)


if __name__ == "__main__":
    import sys
    unittest.main()

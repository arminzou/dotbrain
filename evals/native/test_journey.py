"""Synthetic calibration by default; real isolated Beads self-check is explicitly opt-in."""

import copy
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
from verify import evaluate, native_trace, simple_read, inspect_artifacts


def correct_record(runtime="codex"):
    ids = {role: "sample-" + role for role in ("contract", "api", "ui", "integration")}
    discovery = json.dumps({"pageSize": 7, "sourceSha256": "hash",
                            "hypothesis": {"claim": "Latency cause is unknown", "status": "unresolved"}})
    revision = "a" * 40
    items = {item: {"id": item, "status": "open", "assignee": "api-writer" if role == "api" else ""}
             for role, item in ids.items()}
    state = {"items": items, "knowledge": {"docs/discovery.json": discovery},
             "details": {"handoff": "docs/discovery.json FAIL candidate " + revision}}
    recovered_state = copy.deepcopy(state)
    recovered_state["knowledge"]["docs/recovered.json"] = json.dumps({"discovery": json.loads(discovery),
         "nextWork": ids["integration"], "takeover": "operator-decision-required"})
    def events(session, tools, worker=False):
        if runtime == "codex":
            result = [{"type": "thread.started", "thread_id": session}]
            result += [{"type": "item.completed", "item": {"type": "command_execution", "command": name,
                       "aggregated_output": output, "exit_code": 0 if ok else 1}} for name, output, ok in tools]
            if worker:
                for tool in ("spawn_agent", "wait"):
                    result.append({"type": "item.completed", "item": {"type": "collab_tool_call", "tool": tool,
                                   "status": "completed", "agents_states": {"child": {"status": "completed"}}}})
            return result + [{"type": "turn.completed"}]
        result = [{"type": "system", "session_id": session}]
        for i, (name, output, ok) in enumerate(tools + ([("Agent", "worker result", True)] if worker else [])):
            tool = "Agent" if name == "Agent" else "Read" if "json" in name else "Bash"
            result += [{"type": "assistant", "message": {"content": [{"type": "tool_use", "id": str(i),
                        "name": tool, "input": {"file_path": name}}]}}]
            if tool == "Agent":
                result.append({"type": "assistant", "parent_tool_use_id": str(i), "message": {"content": [
                    {"type": "text", "text": "child activity"}]}})
            result += [{"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": str(i),
                        "content": output, "is_error": not ok}]}}]
        return result + [{"type": "result", "subtype": "success"}]
    first = {"name": "first", "home": "/fixture/first", "receipt": {"name": "first"},
             "events": events("session-a", [("cat config.json", '{"pageSize":7}', True),
                                             ("python check.py", "AssertionError", False)], True),
             "sessionOutput": "unique-first-transcript", "input": "first task", "interrupted": True,
             "pid": 123, "exitCode": -1, "started": 1, "ended": 2}
    first["writerTree"] = {"present": [{"pid": 456, "created": "synthetic-start", "scoped": True}]}
    second = {"name": "second", "home": "/fixture/second", "receipt": {"name": "second"},
              "input": "cold task", "events": events("session-b", [("cat discovery.json", discovery, True),
                 ("cat config.json", '{"pageSize":7}', True), ("cat handoff", "operator decision: uncertain writer", True)])}
    baseline = {"details": {item: {"show": [{"dependencies": []}]} for item in ids.values()}}
    for child, parent in (("api", "contract"), ("ui", "contract"), ("integration", "api"), ("integration", "ui")):
        baseline["details"][ids[child]]["show"][0]["dependencies"].append({"depends_on_id": ids[parent]})
    final_state = copy.deepcopy(state)
    final_state["items"][ids["integration"]]["status"] = "closed"
    integration = {"name": "integration", "receipt": {"name": "integration"}, "state": final_state,
                   "events": events("session-c", [("python check.py", "", True),
                                                    ("bd close " + ids["integration"], "closed", True)])}
    return dict(runtime=runtime, first=first, second=second, integration=integration, ids=ids, before=state, after=recovered_state,
                baseline=baseline, calls=[{"argv": ["close", ids["contract"], "--actor", "coordinator"],
                                          "returncode": 0, "phase": "first"}] +
                [{"argv": ["update", ids["api"], "--claim", "--actor", actor],
                                          "returncode": code, "phase": "first"}
                                         for actor, code in (("api-writer", 0), ("competitor", 1))] +
                [{"argv": ["close", ids["integration"], "--actor", "coordinator"], "returncode": 0, "phase": "integration"}],
                config='{"pageSize":7}', configSha256="hash", expectedSecondInput="cold task",
                candidate={"revision": revision, "objectExists": True}, public={"README.md": "Public guidance"},
                sentinel="PRIVATE-CANARY", priorAllowances={"status": "exhausted", "renewed": False},
                operatorDecision={"decision": "authorize-takeover", "actor": "operator", "observedOwner": "api-writer"},
                fixtureRoot="/fixture", writerStop={"attempt": "first", "parent": 123,
                "before": {"present": first["writerTree"]["present"]},
                "after": {"fixtureRoot": "/fixture", "requested": [123, 456], "present": []}},
                attempts=[first["receipt"], second["receipt"], integration["receipt"]])


class Calibration(unittest.TestCase):
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
            "candidate": lambda r: r["candidate"].update(objectExists=False),
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
            git("add", ".")
            git("commit", "-qm", "Seed synthetic artifact calibration")
            baseline_head = git("rev-parse", "HEAD")
            journey.write(workspace / "api.json", '{"pageSize":7}')
            git("add", ".")
            git("commit", "-qm", "Synthetic candidate")
            revision = git("rev-parse", "HEAD")
            record = correct_record()
            record["baseline"]["head"] = baseline_head
            config_hash = hashlib.sha256((workspace / "config.json").read_bytes()).hexdigest()
            for state in (record["before"], record["after"]):
                state["knowledge"]["docs/discovery.json"] = state["knowledge"]["docs/discovery.json"].replace('"hash"', json.dumps(config_hash))
                state["details"]["handoff"] = state["details"]["handoff"].replace("a" * 40, revision)
                if "docs/recovered.json" in state["knowledge"]:
                    state["knowledge"]["docs/recovered.json"] = state["knowledge"]["docs/recovered.json"].replace('"hash"', json.dumps(config_hash))
            for event in record["second"]["events"]:
                if "aggregated_output" in event.get("item", {}):
                    event["item"]["aggregated_output"] = event["item"]["aggregated_output"].replace('"hash"', json.dumps(config_hash))
            attempts = []
            manifest = {"root": str(root), "ids": record["ids"], "attempts": attempts, "priorAllowances": record["priorAllowances"]}
            for phase, value, state in (("first", record["first"], record["before"]),
                                        ("continue", record["second"], record["after"]),
                                        ("integration", record["integration"], record["integration"]["state"])):
                attempt = {key: item for key, item in value.items() if key not in {"events", "input", "sessionOutput", "receipt", "state"}}
                attempt.update(runtime="codex", phase=phase)
                attempts.append(attempt)
                journey.write(root / f"private/{value['name']}.raw.jsonl", "\n".join(json.dumps(e) for e in value["events"]) + "\n")
                journey.write(root / f"private/{value['name']}.input.txt", journey.prompt(manifest, phase))
                state = copy.deepcopy(state)
                state["items"] = list(state["items"].values())
                journey.write(root / f"private/{value['name']}-after.json", state)
            manifest["sentinel"] = record["sentinel"]
            journey.write(root / "fixture.json", manifest)
            journey.write(root / "private/baseline.json", record["baseline"])
            journey.write(root / "private/beads.jsonl", "\n".join(json.dumps(c) for c in record["calls"]) + "\n")
            journey.write(root / "private/operator-decision.json", record["operatorDecision"])
            record["writerStop"]["after"]["fixtureRoot"] = str(root)
            journey.write(root / "private/writer-stop.json", record["writerStop"])
            checks = inspect_artifacts(root, "codex")
            self.assertTrue(all(checks.values()), checks)
            state = journey.load(root / "private/first-after.json")
            state["details"]["handoff"] = "docs/discovery.json FAIL candidate " + "f" * 40
            journey.write(root / "private/first-after.json", state)
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
        parent = Path(__file__).resolve().parents[1] / "results"
        parent.mkdir(exist_ok=True)
        root = Path(tempfile.mkdtemp(prefix="native-selfcheck-", dir=parent)) / "fixture"
        source = root.parent / "source"
        source.mkdir()
        git_env = journey.environment(root.parent)
        subprocess.run(["git", "init", "-q", str(source)], check=True, env=git_env)
        subprocess.run(["git", "-C", str(source), "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                        "commit", "--allow-empty", "-qm", "Seed fixture source"], check=True, env=git_env)
        manifest = journey.prepare(root, source, source, Path(os.environ["NATIVE_FIXTURE_BD"]).resolve())
        baseline = journey.load(root / "private/baseline.json")
        self.assertEqual([item["id"] for item in baseline["ready"]], [manifest["ids"]["contract"]])
        item = manifest["ids"]["contract"]
        self.assertEqual(journey.bd(root, ["update", item, "--claim", "--actor", "writer-a"]).returncode, 0)
        self.assertNotEqual(journey.bd(root, ["update", item, "--claim", "--actor", "writer-b"], check=False).returncode, 0)
        claimed = json.loads(journey.bd(root, ["show", item, "--json"]).stdout)
        self.assertEqual(claimed[0]["assignee"], "writer-a")
        self.assertIn(str(root / "workspace/.beads"), journey.bd(root, ["where"]).stdout)
        self.assertNotEqual(journey.execute(root, [sys.executable, "check.py"], check=False).returncode, 0)
        self.assertTrue((root / "workspace/.beads/metadata.json").is_file())
        self.assertEqual(journey.load(root / "workspace/.beads/metadata.json")["dolt_mode"], "embedded")
        print("Actual backend self-check retained:", root)


@unittest.skipUnless(os.environ.get("NATIVE_FIXTURE_PROCESS_CHECK") == "1" and sys.platform == "win32",
                     "opt-in Windows fixture process controls")
class ProcessControls(unittest.TestCase):
    def test_captured_fixture_writer_is_stopped_by_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            journey.write(root / "writer.py", "import time\ntime.sleep(30)\n")
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

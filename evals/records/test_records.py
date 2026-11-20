"""Model-free calibration of artifact checks and evidence-backed review requirements."""
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import records

GOOD_S1 = [{"message": {"content": [{"type": "tool_use", "name": "Bash",
             "input": {"command": "python -m unittest discover -s tests"}}]}}]
GOOD_S2 = [{"item": {"type": "command_execution", "command": "cat todo/store.py"}}]
ISSUE = {"id": "todo-1", "status": "open", "assignee": "operator",
         "acceptance_criteria": "Operator checks keyboard navigation."}


class GradeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        temporary = tempfile.TemporaryDirectory()
        cls.addClassCleanup(temporary.cleanup)
        cls.fixture = Path(temporary.name) / "fixture"
        workspace, data = cls.fixture / "workspace", cls.fixture / "data"
        files = {"todo/__init__.py": "", "todo/store.py": records.STORE, "todo/cli.py": records.CLI,
                 "tests/test_store.py": records.TEST, "AGENTS.md": "# Test fixture\n",
                 ".gitignore": "__pycache__/\n"}
        for name, text in files.items():
            path = workspace / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        records.init_repo(workspace, "Initial task list")
        brain = data / f"brainspaces/{records.PROJECT}/.brain"
        (brain / "docs").mkdir(parents=True)
        (brain / "docs/user-notes.md").write_text(records.USER_NOTE, encoding="utf-8")
        records.init_repo(data, records.READY_COMMIT)

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "run"
        shutil.copytree(self.fixture, self.root)
        self.ws, self.data = self.root / "workspace", self.root / "data"
        self.brain = self.data / f"brainspaces/{records.PROJECT}/.brain"
        (self.root / "results").mkdir()
        self.issues = [dict(ISSUE)]
        (self.root / "initial-issues.json").write_text(json.dumps(self.issues), encoding="utf-8")
        self.review = {criterion: {"passed": True, "evidence": "Synthetic calibration evidence."}
                       for criterion in records.REVIEW_CRITERIA}
        self.write("s1", GOOD_S1)
        self.write("s2", GOOD_S2)
        self.set_case("routine")
        (self.ws / "todo/store.py").write_text(
            records.STORE.replace('key=lambda t: t["id"])', 'key=lambda t: t["id"], reverse=True)'),
            encoding="utf-8")

    def set_case(self, scenario):
        (self.root / "case.txt").write_text(scenario, encoding="utf-8")

    def write(self, session, evts, returncode=0):
        path = self.root / "results" / f"claude-{session}.jsonl"
        path.write_text("\n".join(json.dumps(event) for event in evts), encoding="utf-8")
        path.with_suffix(".run.json").write_text(json.dumps({"returncode": returncode}), encoding="utf-8")

    def write_brain(self, name, text):
        path = self.brain / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def failed(self):
        result = records.grade(self.root, "claude", bd=lambda: json.dumps(self.issues), review=self.review)
        return [name for name, passed in result.items() if not passed]

    def test_routine_success_needs_no_new_records(self):
        self.assertEqual(self.failed(), [])

    def test_original_behavior_fails_independent_probe(self):
        (self.ws / "todo/store.py").write_text(records.STORE, encoding="utf-8")
        self.assertEqual(self.failed(), ["observable_outcome"])

    def test_unnecessary_brain_record_fails_routine(self):
        self.write_brain("docs/routine-fix.md", "Changed sort order.\n")
        self.assertEqual(self.failed(), ["no_new_records"])

    def test_new_task_fails_routine(self):
        self.issues.append({"id": "todo-2", "status": "closed"})
        self.assertEqual(self.failed(), ["no_new_records"])

    def test_existing_work_cannot_be_closed_to_pass(self):
        self.issues[0]["status"] = "closed"
        self.assertEqual(self.failed(), ["existing_work_preserved"])

    def test_existing_work_cannot_be_reassigned_or_redefined(self):
        for field, value in (("assignee", "agent"), ("acceptance_criteria", "Tests passed"),
                             ("dependencies", [{"depends_on_id": "todo-2"}])):
            with self.subTest(field=field):
                self.issues = [{**ISSUE, field: value}]
                self.assertIn("existing_work_preserved", self.failed())

    def test_deleted_user_note_fails(self):
        (self.brain / "docs/user-notes.md").unlink()
        self.assertIn("user_note_preserved", self.failed())

    def test_empty_review_fails_even_with_correct_code(self):
        self.review = {}
        self.assertEqual(self.failed(), list(records.REVIEW_CRITERIA))

    def test_review_needs_evidence(self):
        self.review["useful_continuation"]["evidence"] = " "
        self.assertEqual(self.failed(), ["useful_continuation"])

    def test_negative_review_fails_with_fitting_record_placement(self):
        self.set_case("experiment")
        (self.ws / "todo/store.py").write_text(records.STORE, encoding="utf-8")
        self.write_brain("docs/save-hazard.md", "decision\n")
        self.review["selective_capture"] = {"passed": False, "evidence": "No usable finding was retained."}
        self.assertEqual(self.failed(), ["selective_capture"])

    def test_experiment_preserves_production_code(self):
        self.set_case("experiment")
        self.assertEqual(self.failed(), ["observable_outcome"])

    def test_retirement_removes_records_and_repairs_pointers(self):
        self.set_case("retirement")
        (self.ws / "todo/store.py").write_text(records.STORE, encoding="utf-8")
        self.write_brain("docs/index.md", "[User notes](user-notes.md)\n")
        self.assertEqual(self.failed(), [])
        self.write_brain(records.RETIRED_FILES[0], "Old command\n")
        self.assertEqual(self.failed(), ["obsolete_records_removed"])
        (self.brain / records.RETIRED_FILES[0]).unlink()
        self.write_brain("docs/index.md", "[Old command](daily-digest.md)\n")
        self.assertEqual(self.failed(), ["pointers_repaired"])

    def test_continuation_requires_functionality_not_a_tracker_read(self):
        self.set_case("continuation")
        self.write("s2", [{"item": {"type": "command_execution", "command": "bd ready --json"}}])
        self.write_brain("docs/due-dates.md", "decision\n")
        self.assertEqual(self.failed(), ["observable_outcome"])

    def test_continuation_probe_accepts_working_behavior(self):
        self.set_case("continuation")
        cli = '''import json
import sys
from datetime import date
from pathlib import Path

path = Path("tasks.json")
tasks = json.loads(path.read_text()) if path.exists() else []
command = sys.argv[1]
if command == "add":
    tasks.append({"id": len(tasks) + 1, "title": sys.argv[2], "done": False, "due": sys.argv[4]})
    path.write_text(json.dumps(tasks))
else:
    def overdue(task):
        return bool(task.get("due")) and task["due"] < str(date.today())
    pending = [task for task in tasks if not task["done"]]
    for task in sorted(pending, key=lambda task: not overdue(task)):
        if command != "overdue" or overdue(task):
            print(f"{task['id']}: {task['title']}")
'''
        (self.ws / "todo/cli.py").write_text(cli, encoding="utf-8")
        self.assertEqual(self.failed(), [])

    def test_transcript_read_fails(self):
        self.write("s2", GOOD_S2 + [{"message": {"content": [{"type": "tool_use", "name": "Read",
                    "input": {"file_path": "C:/home/.claude/projects/x/session.jsonl"}}]}}])
        self.assertEqual(self.failed(), ["no_transcript_reads"])

    def test_transcript_path_in_written_instruction_is_not_a_read(self):
        self.write("s2", GOOD_S2 + [{"item": {"type": "command_execution",
                    "command": "echo 'never read ~/.codex/sessions' > /dev/null"}}])
        self.assertEqual(self.failed(), [])

    def test_missing_or_failed_session_cannot_pass(self):
        (self.root / "results/claude-s2.jsonl").unlink()
        self.assertEqual(self.failed(), ["sessions_ran"])
        self.write("s2", GOOD_S2, returncode=124)
        self.assertEqual(self.failed(), ["sessions_succeeded"])
        (self.root / "results/claude-s2.run.json").unlink()
        self.assertEqual(self.failed(), ["sessions_succeeded"])


class RunTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root / "results").mkdir()
        (self.root / "workspace").mkdir()
        (self.root / "case.txt").write_text("routine", encoding="utf-8")

    def test_run_uses_selected_case_and_records_actual_outcome(self):
        with patch.object(records.subprocess, "run", return_value=subprocess.CompletedProcess([], 0)) as launch, \
                patch.object(records, "git", return_value="candidate\n"), \
                patch.object(records, "issues_at", return_value=[ISSUE]):
            self.assertEqual(records.run(self.root, "claude", "s1", "agent", 10), 0)
        self.assertIn(records.TASKS["routine"]["s1"], launch.call_args.args[0][2])
        self.assertIn(str(self.root / "plugin"), launch.call_args.args[0])
        self.assertEqual(launch.call_args.kwargs["env"]["BEADS_DIR"], str(self.root / "workspace/.beads"))
        outcome = json.loads((self.root / "results/claude-s1.run.json").read_text(encoding="utf-8"))
        self.assertEqual(outcome["workspace_revision"], "candidate")
        self.assertEqual(outcome["returncode"], 0)
        self.assertGreaterEqual(outcome["duration_seconds"], 0)
        issues = json.loads((self.root / "results/claude-s1.issues.json").read_text(encoding="utf-8"))
        self.assertEqual(issues, [ISSUE])

    def test_timed_out_session_is_recorded_as_failure(self):
        with patch.object(records.subprocess, "run", side_effect=subprocess.TimeoutExpired("agent", 10)), \
                patch.object(records, "git", return_value="candidate\n"), \
                patch.object(records, "issues_at", return_value=[]):
            self.assertEqual(records.run(self.root, "codex", "s2", "agent", 10), 124)
        outcome = json.loads((self.root / "results/codex-s2.run.json").read_text(encoding="utf-8"))
        self.assertEqual(outcome["returncode"], 124)


class PrepareTest(unittest.TestCase):
    def test_retirement_fixture_snapshots_selected_guidance(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root, guidance = base / "run", base / "guidance"
            (guidance / "plugin").mkdir(parents=True)
            (guidance / "plugin/marker.txt").write_text("baseline plugin", encoding="utf-8")
            template = guidance / "src/dotbrain/resources/templates/brain/DOTBRAIN.md"
            template.parent.mkdir(parents=True)
            template.write_text("baseline convention", encoding="utf-8")
            (template.parent / "designs").mkdir()
            (template.parent / "designs/README.md").write_text("baseline scaffold", encoding="utf-8")

            def command(argv, **kwargs):
                if argv[0] == "fixture-dotbrain" and argv[1] == "wire":
                    brain = root / f"data/brainspaces/{records.PROJECT}/.brain"
                    brain.mkdir(parents=True)
                    (brain / "project.yaml").write_text("agents: []\n", encoding="utf-8")
                return subprocess.CompletedProcess(argv, 0)

            with patch.object(records.subprocess, "run", side_effect=command) as commands, \
                    patch.object(records, "git", return_value=""), patch.object(records, "init_repo"), \
                    patch.object(records, "issues_at", return_value=[ISSUE]):
                records.prepare(root, base / "pstack", "fixture-dotbrain", "retirement", guidance)
            brain = root / f"data/brainspaces/{records.PROJECT}/.brain"
            self.assertEqual((brain / "DOTBRAIN.md").read_text(encoding="utf-8"), "baseline convention")
            self.assertEqual((brain / "designs/README.md").read_text(encoding="utf-8"), "baseline scaffold")
            self.assertIn("agents: []", (brain / "project.yaml").read_text(encoding="utf-8"))
            self.assertEqual((root / "plugin/marker.txt").read_text(encoding="utf-8"), "baseline plugin")
            self.assertTrue(all((brain / name).exists() for name in records.RETIRED_FILES))
            self.assertEqual((brain / "docs/user-notes.md").read_text(encoding="utf-8"), records.USER_NOTE)
            create = next(call for call in commands.call_args_list if call.args[0][0] == "bd")
            self.assertIn("operator", create.args[0])
            self.assertEqual(create.kwargs["env"]["BEADS_DIR"], str(root / "workspace/.beads"))


if __name__ == "__main__":
    unittest.main()

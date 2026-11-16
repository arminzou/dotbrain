"""Model-free calibration: a known-good record passes every criterion; each known-wrong one fails it."""
import json
import tempfile
import unittest
from pathlib import Path

import records

GOOD_S1 = [{"message": {"content": [{"type": "tool_use", "name": "Bash", "input": {"command": "bd create 'Due dates' -t epic"}}]}}]
GOOD_S2 = [{"item": {"type": "command_execution", "command": "bd ready --json"}}]
ISSUES = [{"id": "todo-1", "issue_type": "epic", "status": "open"}, {"id": "todo-2", "status": "closed"}]


class GradeTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        ws, data = self.root / "workspace", self.root / "data"
        for name in records.BASE_FILES:
            (ws / name).parent.mkdir(parents=True, exist_ok=True)
            (ws / name).write_text("x\n", encoding="utf-8")
        records.init_repo(ws, "Initial task list")
        (data / f"brainspaces/{records.PROJECT}/.brain").mkdir(parents=True)
        records.init_repo(data, records.READY_COMMIT)
        (self.root / "results").mkdir()
        self.issues = ISSUES
        self.write("s1", GOOD_S1)
        self.write("s2", GOOD_S2)
        self.brain("adr/0001-due-date-format.md")

    def write(self, session, evts):
        path = self.root / "results" / f"claude-{session}.jsonl"
        path.write_text("\n".join(json.dumps(e) for e in evts), encoding="utf-8")

    def brain(self, name):
        path = self.root / "data/brainspaces" / records.PROJECT / ".brain" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("decision\n", encoding="utf-8")

    def failed(self):
        result = records.grade(self.root, "claude", bd=lambda: json.dumps(self.issues))
        return [name for name, ok in result.items() if not ok]

    def test_known_good_record_passes(self):
        (self.root / "workspace/todo/due.py").write_text("x\n", encoding="utf-8")
        (self.root / "workspace/README.md").write_text("x\n", encoding="utf-8")
        self.assertEqual(self.failed(), [])

    def test_plan_file_in_repo_fails(self):
        (self.root / "workspace/DUE_DATES.md").write_text("plan\n", encoding="utf-8")
        self.assertEqual(self.failed(), ["no_repo_records"])

    def test_plan_outside_beads_fails(self):
        self.issues = []
        self.assertEqual(self.failed(), ["plan_in_beads"])

    def test_missing_brain_record_fails(self):
        (self.root / "data/brainspaces" / records.PROJECT / ".brain/adr/0001-due-date-format.md").unlink()
        self.assertEqual(self.failed(), ["reasoning_in_brain"])

    def test_resume_without_beads_fails(self):
        self.write("s2", [{"item": {"type": "command_execution", "command": "cat DUE_DATES.md"}}])
        self.assertEqual(self.failed(), ["resumed_from_beads"])

    def test_transcript_read_fails(self):
        self.write("s2", GOOD_S2 + [{"message": {"content": [{"type": "tool_use", "name": "Read",
                    "input": {"file_path": "C:/home/.claude/projects/x/session.jsonl"}}]}}])
        self.assertEqual(self.failed(), ["no_transcript_reads"])

    def test_transcript_path_in_skill_text_passes(self):
        self.write("s2", GOOD_S2 + [{"item": {"type": "command_execution",
                    "command": "echo 'never read ~/.codex/sessions' > /dev/null"}}])
        self.assertEqual(self.failed(), [])

    def test_missing_session_fails(self):
        (self.root / "results/claude-s2.jsonl").unlink()
        self.assertEqual(self.failed(), ["sessions_ran", "resumed_from_beads"])


if __name__ == "__main__":
    unittest.main()

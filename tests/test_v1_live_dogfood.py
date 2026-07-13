from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "live_dogfood_v1.py"
SPEC = importlib.util.spec_from_file_location("live_dogfood_v1", SCRIPT_PATH)
assert SPEC is not None
live_dogfood_v1 = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = live_dogfood_v1
SPEC.loader.exec_module(live_dogfood_v1)


def write_session_events(root: Path, run_id: str, rows: list[dict[str, object]]) -> None:
    session_dir = root / ".vibeagent" / "sessions" / run_id
    session_dir.mkdir(parents=True, exist_ok=True)
    (session_dir / "events.jsonl").write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )


class V1LiveDogfoodScriptTests(unittest.TestCase):
    def test_prepare_repo_creates_broken_calculator_and_command(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-live-dogfood-script-") as base:
            root = Path(base) / "repo"

            live_dogfood_v1.prepare_repo(root)
            command = live_dogfood_v1.dogfood_command(root)

            self.assertEqual(command[:3], ["python3", "-m", "vibeagent"])
            self.assertIn("--approval", command)
            self.assertIn("ask", command)
            self.assertIn("inspect this repo, fix the failing test, verify, review, and commit", command)
            self.assertIn("return left - right", (root / "calc.py").read_text(encoding="utf-8"))

    def test_audit_repo_fails_before_repair_and_passes_after_commit(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-live-dogfood-audit-") as base:
            root = Path(base) / "repo"
            live_dogfood_v1.prepare_repo(root)

            before = live_dogfood_v1.audit_repo(root, run_id=None)
            (root / "calc.py").write_text("def add(left, right):\n    return left + right\n", encoding="utf-8")
            subprocess.run(["git", "add", "calc.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "commit", "-m", "fix calculator"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            after = live_dogfood_v1.audit_repo(root, run_id=None)

            self.assertFalse(all(check.ok for check in before))
            self.assertTrue(all(check.ok for check in after))

    def test_audit_session_events_requires_live_gate_evidence(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-live-dogfood-events-") as base:
            root = Path(base)
            write_session_events(
                root,
                "run-1",
                [
                    {"type": "task", "task": "fix", "approval_policy": "allow"},
                    {"type": "tool_call", "iteration": 1, "id": "1", "name": "Edit", "input": {"file_path": "calc.py"}},
                    {"type": "tool_result", "iteration": 1, "id": "1", "name": "Edit", "result": {"kind": "edit_file", "ok": True}},
                    {"type": "result", "success": True, "status": "completed", "completion_ready": False},
                ],
            )

            checks = live_dogfood_v1.audit_session_events(root, run_id="run-1")
            failed_names = {check.name for check in checks if not check.ok}

        self.assertIn("live run used ask approval policy", failed_names)
        self.assertIn("repository inspected before side effects", failed_names)
        self.assertIn("side effects requested approval", failed_names)
        self.assertIn("agent ran failing and passing unittest verification", failed_names)
        self.assertIn("final review ready", failed_names)
        self.assertIn("session completion ready", failed_names)

    def test_audit_session_events_accepts_complete_live_gate_evidence(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-live-dogfood-events-") as base:
            root = Path(base)
            write_session_events(
                root,
                "run-1",
                [
                    {"type": "task", "task": "fix", "approval_policy": "ask"},
                    {"type": "tool_call", "iteration": 1, "id": "read", "name": "Read", "input": {"file_path": "calc.py"}},
                    {"type": "tool_result", "iteration": 1, "id": "read", "name": "Read", "result": {"kind": "read_file", "ok": True}},
                    {"type": "tool_call", "iteration": 2, "id": "fail-test", "name": "Bash", "input": {"command": "python3 -m unittest discover -s tests"}},
                    {"type": "approval_requested", "iteration": 2, "request": {"action_type": "run_command", "target": "python3 -m unittest discover -s tests"}},
                    {"type": "approval_decision", "iteration": 2, "decision": {"approved": True}},
                    {
                        "type": "tool_result",
                        "iteration": 2,
                        "id": "fail-test",
                        "name": "Bash",
                        "result": {
                            "kind": "run_command",
                            "ok": False,
                            "command": "python3 -m unittest discover -s tests",
                        },
                    },
                    {"type": "tool_call", "iteration": 2, "id": "edit", "name": "Edit", "input": {"file_path": "calc.py"}},
                    {"type": "approval_requested", "iteration": 2, "request": {"action_type": "edit_file", "target": "calc.py"}},
                    {"type": "approval_decision", "iteration": 2, "decision": {"approved": True}},
                    {"type": "tool_result", "iteration": 2, "id": "edit", "name": "Edit", "result": {"kind": "edit_file", "ok": True}},
                    {"type": "tool_call", "iteration": 3, "id": "test", "name": "Bash", "input": {"command": "python3 -m unittest discover -s tests"}},
                    {"type": "approval_requested", "iteration": 3, "request": {"action_type": "run_command", "target": "python3 -m unittest discover -s tests"}},
                    {"type": "approval_decision", "iteration": 3, "decision": {"approved": True}},
                    {
                        "type": "tool_result",
                        "iteration": 3,
                        "id": "test",
                        "name": "Bash",
                        "result": {
                            "kind": "run_command",
                            "ok": True,
                            "command": "python3 -m unittest discover -s tests",
                        },
                    },
                    {
                        "type": "tool_result",
                        "iteration": 4,
                        "id": "review",
                        "name": "final_review",
                        "result": {
                            "kind": "final_review",
                            "ok": True,
                            "ready": True,
                            "blocking_issues": [],
                            "warnings": [],
                            "files": [{"path": "calc.py", "status": "M"}],
                            "suggested_checks": [],
                            "message": "Ready.",
                        },
                    },
                    {"type": "result", "success": True, "status": "completed", "completion_ready": True},
                ],
            )

            checks = live_dogfood_v1.audit_session_events(root, run_id="run-1")

        self.assertTrue(all(check.ok for check in checks), checks)


if __name__ == "__main__":
    unittest.main()

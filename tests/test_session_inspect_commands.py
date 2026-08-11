from __future__ import annotations

import json
from contextlib import redirect_stdout
import io
from pathlib import Path
import tempfile
import unittest

from vibeagent.cli import main
from vibeagent.session_inspect_commands import (
    format_session_inspect_report_text,
    get_session_inspect_report,
)


class SessionInspectCommandTests(unittest.TestCase):
    def test_report_aggregates_bounded_session_evidence(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-inspect-") as base:
            root = Path(base)
            self._write_session(root, "run-1")

            report = get_session_inspect_report(root, "run-1")
            text = format_session_inspect_report_text(report)

        self.assertTrue(report["ok"])
        self.assertEqual(report["status"], "completed")
        self.assertEqual(report["overview"]["task"], "Repair parser")  # type: ignore[index]
        self.assertEqual(report["plan"]["items"][0]["step"], "Inspect parser")  # type: ignore[index]
        self.assertEqual(report["tasks"]["counts"]["pending"], 1)  # type: ignore[index]
        self.assertEqual(report["tasks"]["tasks"]["items"][0]["subject"], "Inspect parser")  # type: ignore[index]
        self.assertEqual(report["files"]["files"]["items"][0]["path"], "app.py")  # type: ignore[index]
        self.assertEqual(report["transcript"]["events"]["total"], 5)  # type: ignore[index]
        self.assertTrue(report["verification"]["ready"])  # type: ignore[index]
        self.assertIn("session: run-1", text)
        self.assertIn("files: 1/1", text)
        self.assertIn("tasks: 1/1", text)
        self.assertIn("timeline: 5/5", text)

    def test_report_bounds_long_plan_file_and_timeline_history(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-inspect-") as base:
            root = Path(base)
            rows: list[dict[str, object]] = [{"type": "task", "task": "Large session"}]
            rows.extend(
                {
                    "type": "tool_call",
                    "iteration": index + 1,
                    "id": f"file-{index}",
                    "name": "read_file",
                    "input": {"path": f"file-{index:03d}.py"},
                }
                for index in range(105)
            )
            rows.extend(
                {
                    "type": "tool_call",
                    "iteration": 106 + index,
                    "id": f"repeat-{index}",
                    "name": "read_file",
                    "input": {"path": "000-repeated.py"},
                }
                for index in range(25)
            )
            rows.append(
                {
                    "type": "tool_result",
                    "iteration": 131,
                    "id": "plan",
                    "name": "update_plan",
                    "result": {
                        "kind": "update_plan",
                        "plan": [
                            {"step": f"Step {index}", "status": "pending"}
                            for index in range(105)
                        ],
                    },
                }
            )
            rows.append({"type": "result", "success": True, "status": "completed", "iterations": 131})
            self._write_rows(root, "run-long", rows)
            self._write_task_store(root, "run-long", 100)

            report = get_session_inspect_report(root, "run-long")

        self.assertEqual(report["plan"]["total"], 20)  # type: ignore[index]
        self.assertEqual(report["plan"]["shown"], 20)  # type: ignore[index]
        self.assertFalse(report["plan"]["truncated"])  # type: ignore[index]
        self.assertEqual(report["tasks"]["tasks"]["total"], 100)  # type: ignore[index]
        self.assertEqual(report["tasks"]["tasks"]["shown"], 50)  # type: ignore[index]
        self.assertTrue(report["tasks"]["tasks"]["truncated"])  # type: ignore[index]
        self.assertEqual(report["files"]["files"]["total"], 106)  # type: ignore[index]
        self.assertEqual(report["files"]["files"]["shown"], 100)  # type: ignore[index]
        repeated = report["files"]["files"]["items"][0]  # type: ignore[index]
        self.assertEqual(repeated["path"], "000-repeated.py")
        self.assertEqual(len(repeated["lines"]), 20)
        self.assertTrue(repeated["linesTruncated"])
        self.assertEqual(report["transcript"]["events"]["shown"], 80)  # type: ignore[index]
        self.assertTrue(report["transcript"]["events"]["truncated"])  # type: ignore[index]
        self.assertLess(len(json.dumps(report)), 250_000)

    def test_cli_json_exposes_one_session_inspector_payload(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-inspect-") as base:
            root = Path(base)
            self._write_session(root, "run-1")
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                exit_code = main(["--json", "--cwd", base, "--session-inspect", "run-1"])
            payload = json.loads(stdout.getvalue())

        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["sessionInspect"]["session"], "run-1")
        self.assertEqual(payload["sessionInspect"]["status"], "completed")

    def test_invalid_and_missing_sessions_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-inspect-") as base:
            root = Path(base)
            invalid = get_session_inspect_report(root, "../escape")
            missing = get_session_inspect_report(root, "missing")
            self._write_session(root, "corrupt-tasks")
            (root / ".vibeagent" / "sessions" / "corrupt-tasks" / "tasks.json").write_text(
                "{bad",
                encoding="utf-8",
            )
            corrupt_tasks = get_session_inspect_report(root, "corrupt-tasks")
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                exit_code = main(["--json", "--cwd", base, "--session-inspect", "missing"])
            payload = json.loads(stdout.getvalue())

        self.assertFalse(invalid["ok"])
        self.assertIn("Invalid session id", invalid["message"])
        self.assertFalse(missing["ok"])
        self.assertFalse(corrupt_tasks["ok"])
        self.assertIn("Invalid session task store", corrupt_tasks["message"])
        self.assertEqual(exit_code, 1)
        self.assertFalse(payload["success"])

    @staticmethod
    def _write_session(root: Path, run_id: str) -> None:
        rows = [
            {"type": "task", "task": "Repair parser"},
            {
                "type": "tool_call",
                "iteration": 1,
                "id": "read-1",
                "name": "read_file",
                "input": {"path": "app.py"},
            },
            {
                "type": "tool_result",
                "iteration": 1,
                "id": "plan-1",
                "name": "update_plan",
                "result": {
                    "kind": "update_plan",
                    "plan": [{"step": "Inspect parser", "status": "completed"}],
                    "message": "Plan updated.",
                },
            },
            {
                "type": "tool_result",
                "iteration": 2,
                "id": "check-1",
                "name": "run_command",
                "result": {
                    "kind": "run_command",
                    "ok": True,
                    "command": "python -m unittest",
                    "cwd": ".",
                    "exit_code": 0,
                    "verification": True,
                },
            },
            {
                "type": "result",
                "success": True,
                "status": "completed",
                "iterations": 2,
                "message": "Parser repaired.",
            },
        ]
        SessionInspectCommandTests._write_rows(root, run_id, rows)
        SessionInspectCommandTests._write_task_store(root, run_id, 1)

    @staticmethod
    def _write_task_store(root: Path, run_id: str, count: int) -> None:
        tasks = [
            {
                "id": str(index),
                "subject": "Inspect parser" if index == 1 else f"Task {index}",
                "description": "Read parser behavior" if index == 1 else f"Task {index} description",
                "status": "pending",
                "activeForm": "Inspecting parser" if index == 1 else None,
                "owner": "main" if index == 1 else None,
                "metadata": {"ticket": index},
                "blocks": [],
                "blockedBy": [],
            }
            for index in range(1, count + 1)
        ]
        directory = root / ".vibeagent" / "sessions" / run_id
        directory.joinpath("tasks.json").write_text(
            json.dumps({"version": 1, "nextId": count + 1, "tasks": tasks}),
            encoding="utf-8",
        )

    @staticmethod
    def _write_rows(root: Path, run_id: str, rows: list[dict[str, object]]) -> None:
        directory = root / ".vibeagent" / "sessions" / run_id
        directory.mkdir(parents=True)
        directory.joinpath("events.jsonl").write_text(
            "".join(json.dumps(row) + "\n" for row in rows),
            encoding="utf-8",
        )


if __name__ == "__main__":
    unittest.main()

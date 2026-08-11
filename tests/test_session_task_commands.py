from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from vibeagent.actions import execute_action, parse_tool_action
from vibeagent.cli import main
from vibeagent.session_task_commands import (
    format_session_tasks_report_text,
    get_session_tasks_report,
)
from vibeagent.workspace import create_run_workspace


class SessionTaskCommandTests(unittest.TestCase):
    def test_report_serializes_bounded_dependency_graph_without_metadata(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-session-tasks-") as base:
            workspace = create_run_workspace(base, "run-tasks")
            execute_action(
                workspace,
                parse_tool_action(
                    "TaskCreate",
                    {
                        "subject": "Inspect API_KEY=secret-value",
                        "description": "Read parser behavior",
                        "metadata": {"token": "must-not-appear", "ticket": 7},
                    },
                ),
            )
            execute_action(
                workspace,
                parse_tool_action(
                    "TaskCreate",
                    {"subject": "Implement", "description": "Apply parser fix", "activeForm": "Implementing"},
                ),
            )
            execute_action(
                workspace,
                parse_tool_action("TaskUpdate", {"taskId": "2", "addBlockedBy": ["1"], "owner": "worker"}),
            )
            report = get_session_tasks_report(base, "run-tasks", max_tasks=1, max_text=100)
            text = format_session_tasks_report_text(report)

        self.assertTrue(report["ok"])
        self.assertEqual(report["counts"], {"pending": 2, "inProgress": 0, "completed": 0, "blocked": 1})
        self.assertEqual(report["tasks"]["total"], 2)
        self.assertEqual(report["tasks"]["shown"], 1)
        self.assertTrue(report["tasks"]["truncated"])
        self.assertEqual(report["tasks"]["items"][0]["subject"], "Inspect API_KEY=[REDACTED]")
        self.assertNotIn("metadata", report["tasks"]["items"][0])
        self.assertNotIn("must-not-appear", json.dumps(report))
        self.assertIn("tasks: 1/2", text)
        self.assertIn("omitted: 1", text)

    def test_report_rejects_missing_corrupt_symlinked_and_invalid_stores(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-session-tasks-") as base:
            root = Path(base)
            missing = get_session_tasks_report(root, "run-missing")
            workspace = create_run_workspace(root, "run-corrupt")
            task_path = workspace.session_dir / "tasks.json"
            task_path.write_text("{bad", encoding="utf-8")
            corrupt = get_session_tasks_report(root, "run-corrupt")
            task_path.unlink()
            target = root / "outside.json"
            target.write_text('{"version": 1, "nextId": 1, "tasks": []}', encoding="utf-8")
            task_path.symlink_to(target)
            symlinked = get_session_tasks_report(root, "run-corrupt")
            task_path.unlink()
            task_path.write_bytes(b"x" * 1_000_001)
            oversized = get_session_tasks_report(root, "run-corrupt")
            cyclic_payload = {
                "version": 1,
                "nextId": 3,
                "tasks": [
                    {
                        "id": "1", "subject": "First", "description": "First task", "status": "pending",
                        "activeForm": None, "owner": None, "metadata": {}, "blocks": ["2"], "blockedBy": ["2"],
                    },
                    {
                        "id": "2", "subject": "Second", "description": "Second task", "status": "pending",
                        "activeForm": None, "owner": None, "metadata": {}, "blocks": ["1"], "blockedBy": ["1"],
                    },
                ],
            }
            task_path.write_text(json.dumps(cyclic_payload), encoding="utf-8")
            cyclic = get_session_tasks_report(root, "run-corrupt")
            invalid_id = get_session_tasks_report(root, "..")
            invalid_limit = get_session_tasks_report(root, "run-corrupt", max_tasks=101)

        self.assertEqual(missing["status"], "missing")
        self.assertFalse(missing["exists"])
        self.assertIn("Session not found", missing["message"])
        self.assertEqual(corrupt["status"], "invalid")
        self.assertTrue(corrupt["exists"])
        self.assertIn("Invalid session task store", corrupt["message"])
        self.assertIn("must not be a symlink", symlinked["message"])
        self.assertIn("exceeds 1000000 bytes", oversized["message"])
        self.assertIn("dependency cycle", cyclic["message"])
        self.assertIn("Invalid session id", invalid_id["message"])
        self.assertIn("max_tasks", invalid_limit["message"])
        self.assertIn("  ok: no", format_session_tasks_report_text(corrupt))

    def test_cli_json_reads_tasks_without_creating_provider(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-session-tasks-") as base:
            workspace = create_run_workspace(base, "run-cli-tasks")
            execute_action(
                workspace,
                parse_tool_action("TaskCreate", {"subject": "Verify CLI", "description": "Read the graph"}),
            )
            stdout = io.StringIO()
            with patch("vibeagent.cli.create_chat_client") as create_chat_client, redirect_stdout(stdout):
                exit_code = main(["--json", "--cwd", base, "--session-tasks", "run-cli-tasks"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["sessionTasks"]["session"], "run-cli-tasks")
        self.assertEqual(payload["sessionTasks"]["tasks"]["items"][0]["subject"], "Verify CLI")
        create_chat_client.assert_not_called()

    def test_cli_missing_and_corrupt_task_graphs_exit_nonzero(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-session-tasks-") as base:
            missing_stdout = io.StringIO()
            with redirect_stdout(missing_stdout):
                missing_exit = main(["--json", "--cwd", base, "--session-tasks", "run-missing"])
            workspace = create_run_workspace(base, "run-corrupt")
            (workspace.session_dir / "tasks.json").write_text("[]", encoding="utf-8")
            corrupt_stdout = io.StringIO()
            with redirect_stdout(corrupt_stdout):
                corrupt_exit = main(["--json", "--cwd", base, "--session-tasks", "run-corrupt"])

        missing = json.loads(missing_stdout.getvalue())
        corrupt = json.loads(corrupt_stdout.getvalue())
        self.assertEqual(missing_exit, 1)
        self.assertFalse(missing["success"])
        self.assertEqual(corrupt_exit, 1)
        self.assertFalse(corrupt["success"])
        self.assertEqual(corrupt["sessionTasks"]["status"], "invalid")


if __name__ == "__main__":
    unittest.main()

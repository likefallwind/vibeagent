import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from vibeagent.cli import main


class CliSessionReportFlagTests(unittest.TestCase):
    def test_main_runs_sessions_json_with_structured_payload(self) -> None:
        report = {"exists": True, "ok": True, "sessions": {"total": 1}}
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_sessions_report", return_value=report) as get_sessions_report,
                patch("vibeagent.cli.format_sessions_report_text", return_value="Recent sessions:\n  run-1") as format_sessions_report_text,
                patch("vibeagent.cli.get_sessions_text") as get_sessions_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--sessions"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["sessions"], report)
        self.assertEqual(payload["text"], "Recent sessions:\n  run-1")
        get_sessions_report.assert_called_once_with(Path(base).resolve())
        format_sessions_report_text.assert_called_once_with(report)
        get_sessions_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_runs_last_json_with_structured_payload(self) -> None:
        report = {"session": "run-1", "exists": True, "ok": True, "status": "completed"}
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_last_session_report", return_value=report) as get_last_session_report,
                patch("vibeagent.cli.format_session_summary_report_text", return_value="Session: run-1\n  status: completed") as format_session_summary_report_text,
                patch("vibeagent.cli.get_last_session_text") as get_last_session_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--last"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["sessionSummary"], report)
        self.assertEqual(payload["text"], "Session: run-1\n  status: completed")
        get_last_session_report.assert_called_once_with(Path(base).resolve())
        format_session_summary_report_text.assert_called_once_with(report)
        get_last_session_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_runs_session_json_with_structured_payload(self) -> None:
        report = {"session": "run-1", "exists": True, "ok": True, "status": "completed"}
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_session_report", return_value=report) as get_session_report,
                patch("vibeagent.cli.format_session_summary_report_text", return_value="Session: run-1\n  status: completed") as format_session_summary_report_text,
                patch("vibeagent.cli.get_session_text") as get_session_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--session", "run-1"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["sessionSummary"], report)
        self.assertEqual(payload["text"], "Session: run-1\n  status: completed")
        get_session_report.assert_called_once_with("run-1", Path(base).resolve())
        format_session_summary_report_text.assert_called_once_with(report)
        get_session_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_runs_usage_json_with_structured_payload(self) -> None:
        report = {"exists": True, "ok": True, "usage": {"sessions": 1}}
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_usage_report", return_value=report) as get_usage_report,
                patch("vibeagent.cli.format_usage_report_text", return_value="Usage:\n  sessions: 1") as format_usage_report_text,
                patch("vibeagent.cli.get_usage_text") as get_usage_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--usage"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["usage"], report)
        self.assertEqual(payload["text"], "Usage:\n  sessions: 1")
        get_usage_report.assert_called_once_with(Path(base).resolve())
        format_usage_report_text.assert_called_once_with(report)
        get_usage_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_usage_json_reports_missing_sessions_as_failure(self) -> None:
        report = {"exists": False, "ok": False, "status": "missing", "message": "No sessions found."}
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_usage_report", return_value=report) as get_usage_report,
                patch("vibeagent.cli.format_usage_report_text", return_value="No sessions found.") as format_usage_report_text,
                patch("vibeagent.cli.get_usage_text") as get_usage_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--usage"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 1)
        self.assertFalse(payload["success"])
        self.assertEqual(payload["status"], "failed")
        self.assertEqual(payload["usage"], report)
        self.assertEqual(payload["text"], "No sessions found.")
        get_usage_report.assert_called_once_with(Path(base).resolve())
        format_usage_report_text.assert_called_once_with(report)
        get_usage_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_runs_cost_json_with_structured_payload(self) -> None:
        report = {"exists": True, "ok": True, "estimate": {"available": True, "estimatedCostUsd": "0.000001"}}
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_cost_report", return_value=report) as get_cost_report,
                patch("vibeagent.cli.format_cost_report_text", return_value="Cost:\n  estimatedCostUsd: $0.000001") as format_cost_report_text,
                patch("vibeagent.cli.get_cost_text") as get_cost_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--cost"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["cost"], report)
        self.assertEqual(payload["text"], "Cost:\n  estimatedCostUsd: $0.000001")
        get_cost_report.assert_called_once_with(Path(base).resolve())
        format_cost_report_text.assert_called_once_with(report)
        get_cost_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_runs_plan_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_plan_report", return_value={"session": "run-1", "ok": True}) as get_plan_report,
                patch("vibeagent.cli.get_plan_text", return_value="Plan:\n  session: run-1") as get_plan_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--plan", "run-1"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Plan:", stdout.getvalue())
        get_plan_report.assert_not_called()
        get_plan_text.assert_called_once_with(Path(base).resolve(), "run-1")
        create_chat_client.assert_not_called()

    def test_main_runs_plan_json_with_structured_payload(self) -> None:
        report = {"session": "run-1", "exists": True, "ok": True, "items": []}
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_plan_report", return_value=report) as get_plan_report,
                patch("vibeagent.cli.get_plan_text", return_value="unused") as get_plan_text,
                patch(
                    "vibeagent.cli.format_session_plan_report_text",
                    return_value="Plan:\n  session: run-1",
                ) as format_session_plan_report_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--plan", "run-1"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["sessionPlan"], report)
        get_plan_report.assert_called_once_with(Path(base).resolve(), "run-1")
        format_session_plan_report_text.assert_called_once_with(report)
        get_plan_text.assert_not_called()
        create_chat_client.assert_not_called()


if __name__ == "__main__":
    unittest.main()

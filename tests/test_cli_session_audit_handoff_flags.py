import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from vibeagent.cli import main


class CliSessionAuditHandoffFlagTests(unittest.TestCase):
    def test_main_runs_session_audit_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_session_audit_report", return_value={"session": "run-1", "ok": True}) as get_session_audit_report,
                patch("vibeagent.cli.get_session_audit_text", return_value="Session audit:\n  session: run-1") as get_session_audit_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--session-audit", "run-1"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Session audit:", stdout.getvalue())
        get_session_audit_report.assert_not_called()
        get_session_audit_text.assert_called_once_with(Path(base).resolve(), "run-1")
        create_chat_client.assert_not_called()

    def test_main_runs_session_audit_json_with_structured_payload(self) -> None:
        report = {
            "session": "run-1",
            "exists": True,
            "ok": False,
            "ready": False,
            "status": "blocked",
            "blockers": {"count": 1, "items": ["pending verification check(s)"]},
        }
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_session_audit_report", return_value=report) as get_session_audit_report,
                patch(
                    "vibeagent.cli.format_session_audit_report_text",
                    return_value="Session audit:\n  session: run-1\n  ready: no",
                ) as format_session_audit_report_text,
                patch("vibeagent.cli.get_session_audit_text", return_value="old text path") as get_session_audit_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--session-audit", "run-1", "--session-max-checks", "3"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 1)
        self.assertFalse(payload["success"])
        self.assertEqual(payload["status"], "failed")
        self.assertEqual(payload["sessionAudit"], report)
        self.assertIn("ready: no", payload["text"])
        get_session_audit_report.assert_called_once_with(Path(base).resolve(), "run-1", max_checks=3)
        format_session_audit_report_text.assert_called_once_with(report)
        get_session_audit_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_runs_session_handoff_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_session_handoff_report", return_value={"session": "run-1", "ok": True}) as get_session_handoff_report,
                patch("vibeagent.cli.get_session_handoff_text", return_value="Session handoff:\n  session: run-1") as get_session_handoff_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--session-handoff", "run-1"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Session handoff:", stdout.getvalue())
        get_session_handoff_report.assert_not_called()
        get_session_handoff_text.assert_called_once_with(Path(base).resolve(), "run-1")
        create_chat_client.assert_not_called()

    def test_main_runs_session_handoff_json_with_structured_payload(self) -> None:
        report = {
            "session": "run-1",
            "exists": True,
            "ok": False,
            "ready": False,
            "status": "blocked",
            "audit": {"blockers": {"count": 1}},
            "sections": {"readiness": "Session readiness:\n  ready: no"},
        }
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_session_handoff_report", return_value=report) as get_session_handoff_report,
                patch(
                    "vibeagent.cli.format_session_handoff_report_text",
                    return_value="Session handoff:\n  session: run-1\n  readiness:\n    ready: no",
                ) as format_session_handoff_report_text,
                patch("vibeagent.cli.get_session_handoff_text", return_value="old text path") as get_session_handoff_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--json",
                        "--cwd",
                        base,
                        "--session-handoff",
                        "run-1",
                        "--session-max-output-chars",
                        "4000",
                    ]
                )

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["sessionHandoff"], report)
        self.assertIn("ready: no", payload["text"])
        get_session_handoff_report.assert_called_once_with(Path(base).resolve(), "run-1", max_output_chars=4000)
        format_session_handoff_report_text.assert_called_once_with(report)
        get_session_handoff_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_session_detail_local_flags_pass_limit_options(self) -> None:
        cases = [
            (
                [
                    "--session-commands",
                    "run-1",
                    "--session-max-commands",
                    "3",
                    "--session-max-output-chars",
                    "4000",
                ],
                "vibeagent.cli.get_session_commands_text",
                "Command results:\n  session: run-1",
                {"max_commands": 3, "max_output_chars": 4000},
            ),
            (
                ["--session-files", "run-1", "--session-max-files", "7"],
                "vibeagent.cli.get_session_files_text",
                "Session files:\n  session: run-1",
                {"max_files": 7},
            ),
            (
                [
                    "--session-failures",
                    "run-1",
                    "--session-max-failures",
                    "4",
                    "--session-max-text",
                    "120",
                ],
                "vibeagent.cli.get_session_failures_text",
                "Session failures:\n  session: run-1",
                {"max_failures": 4, "max_text": 120},
            ),
            (
                [
                    "--session-audit",
                    "run-1",
                    "--session-max-failures",
                    "4",
                    "--session-max-files",
                    "7",
                    "--session-max-commands",
                    "3",
                    "--session-max-checks",
                    "11",
                    "--session-max-text",
                    "120",
                ],
                "vibeagent.cli.get_session_audit_text",
                "Session audit:\n  session: run-1",
                {"max_failures": 4, "max_files": 7, "max_commands": 3, "max_checks": 11, "max_text": 120},
            ),
            (
                [
                    "--session-handoff",
                    "run-1",
                    "--session-max-failures",
                    "4",
                    "--session-max-files",
                    "7",
                    "--session-max-commands",
                    "3",
                    "--session-max-checks",
                    "11",
                    "--session-max-output-chars",
                    "4000",
                    "--session-max-text",
                    "120",
                ],
                "vibeagent.cli.get_session_handoff_text",
                "Session handoff:\n  session: run-1",
                {
                    "max_failures": 4,
                    "max_files": 7,
                    "max_commands": 3,
                    "max_checks": 11,
                    "max_output_chars": 4000,
                    "max_text": 120,
                },
            ),
        ]

        for argv_tail, patch_target, text, expected_kwargs in cases:
            with self.subTest(argv=argv_tail), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()

                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch(patch_target, return_value=text) as getter,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--cwd", base, *argv_tail])

            self.assertEqual(exit_code, 0)
            self.assertEqual(stdout.getvalue(), f"{text}\n")
            getter.assert_called_once_with(Path(base).resolve(), "run-1", **expected_kwargs)
            create_chat_client.assert_not_called()

    def test_main_session_local_flags_exit_nonzero_for_missing_or_invalid_sessions(self) -> None:
        cases = [
            (
                ["--session", "missing"],
                "vibeagent.cli.get_session_text",
                "Session not found: missing",
                ("missing", Path),
            ),
            (
                ["--plan", "missing"],
                "vibeagent.cli.get_plan_text",
                "Session not found: missing",
                (Path, "missing"),
            ),
            (
                ["--session-audit", "../bad"],
                "vibeagent.cli.get_session_audit_text",
                "Invalid session id: ../bad",
                (Path, "../bad"),
            ),
        ]

        for argv_tail, patch_target, text, expected_args in cases:
            with self.subTest(argv=argv_tail), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()

                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch(patch_target, return_value=text) as getter,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--cwd", base, *argv_tail])

            self.assertEqual(exit_code, 1)
            self.assertEqual(stdout.getvalue(), f"{text}\n")
            resolved_args = tuple(Path(base).resolve() if item is Path else item for item in expected_args)
            getter.assert_called_once_with(*resolved_args)
            create_chat_client.assert_not_called()

    def test_main_session_plan_local_flag_reports_json_failure_status(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_plan_text", return_value="Session not found: missing"),
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--plan", "missing"])

        self.assertEqual(exit_code, 1)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["kind"], "local")
        self.assertFalse(payload["success"])
        self.assertEqual(payload["status"], "failed")
        self.assertEqual(payload["text"], "Session not found: missing")
        create_chat_client.assert_not_called()

    def test_main_session_summary_local_flags_exit_nonzero_for_unready_status(self) -> None:
        cases = [
            (
                ["--session", "run-1"],
                "vibeagent.cli.get_session_report",
                "Session: run-1\n  status: failed",
                {"session": "run-1", "exists": True, "ok": True, "status": "failed"},
                ("run-1", Path),
            ),
            (
                ["--last"],
                "vibeagent.cli.get_last_session_report",
                "Session: run-1\n  status: blocked",
                {"session": "run-1", "exists": True, "ok": True, "status": "blocked"},
                (Path,),
            ),
        ]

        for argv_tail, patch_target, text, report, expected_args in cases:
            with self.subTest(argv=argv_tail), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()

                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch(patch_target, return_value=report) as getter,
                    patch("vibeagent.cli.format_session_summary_report_text", return_value=text) as formatter,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--json", "--cwd", base, *argv_tail])

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 1)
            self.assertFalse(payload["success"])
            self.assertEqual(payload["status"], "failed")
            self.assertEqual(payload["text"], text)
            self.assertEqual(payload["sessionSummary"], report)
            resolved_args = tuple(Path(base).resolve() if item is Path else item for item in expected_args)
            getter.assert_called_once_with(*resolved_args)
            formatter.assert_called_once_with(report)
            create_chat_client.assert_not_called()

    def test_main_latest_session_local_flags_exit_nonzero_when_no_sessions_exist(self) -> None:
        cases = [
            (["--last"], "vibeagent.cli.get_last_session_text", (Path,)),
            (["--plan"], "vibeagent.cli.get_plan_text", (Path, None)),
            (["--session-search", "needle"], "vibeagent.cli.get_session_search_text", (Path, "needle", None)),
        ]

        for argv_tail, patch_target, expected_args in cases:
            with self.subTest(argv=argv_tail), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()

                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch(patch_target, return_value="No sessions found.") as getter,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--cwd", base, *argv_tail])

            self.assertEqual(exit_code, 1)
            self.assertEqual(stdout.getvalue(), "No sessions found.\n")
            resolved_args = tuple(Path(base).resolve() if item is Path else item for item in expected_args)
            getter.assert_called_once_with(*resolved_args)
            create_chat_client.assert_not_called()

    def test_main_sessions_list_exits_nonzero_when_no_sessions_exist(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_sessions_text", return_value="No sessions found.") as get_sessions_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--sessions"])

        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout.getvalue(), "No sessions found.\n")
        get_sessions_text.assert_called_once_with(Path(base).resolve())
        create_chat_client.assert_not_called()


if __name__ == "__main__":
    unittest.main()

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from vibeagent.cli import main


class CliSessionOutputFlagTests(unittest.TestCase):
    def test_main_runs_session_output_contexts_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_session_output_contexts_report", return_value={"session": "run-1", "ok": True}) as get_session_output_contexts_report,
                patch("vibeagent.cli.get_session_output_contexts_text", return_value="Session output contexts:\n  session: run-1") as get_session_output_contexts_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--cwd",
                        base,
                        "--session-output-contexts",
                        "run-1",
                        "--session-output-command-max",
                        "3",
                        "--session-output-max-chars",
                        "4000",
                        "--session-output-context-lines",
                        "2",
                        "--session-output-context-max",
                        "5",
                        "--session-output-context-max-bytes",
                        "1000",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertIn("Session output contexts:", stdout.getvalue())
        get_session_output_contexts_report.assert_not_called()
        get_session_output_contexts_text.assert_called_once_with(
            Path(base).resolve(),
            "run-1",
            max_commands=3,
            max_output_chars=4000,
            context_lines=2,
            max_contexts=5,
            max_bytes_per_context=1000,
        )
        create_chat_client.assert_not_called()

    def test_main_runs_session_output_contexts_json_with_structured_payload(self) -> None:
        report = {"session": "run-1", "exists": True, "ok": True, "contexts": {"total": 1}}
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_session_output_contexts_report", return_value=report) as get_session_output_contexts_report,
                patch(
                    "vibeagent.cli.format_session_output_contexts_report_text",
                    return_value="Session output contexts:\n  session: run-1",
                ) as format_session_output_contexts_report_text,
                patch("vibeagent.cli.get_session_output_contexts_text", return_value="old text path") as get_session_output_contexts_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--json",
                        "--cwd",
                        base,
                        "--session-output-contexts",
                        "run-1",
                        "--session-output-command-max",
                        "3",
                        "--session-output-max-chars",
                        "4000",
                        "--session-output-context-lines",
                        "2",
                        "--session-output-context-max",
                        "5",
                        "--session-output-context-max-bytes",
                        "1000",
                    ]
                )

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["sessionOutputContexts"], report)
        self.assertIn("Session output contexts:", payload["text"])
        expected_kwargs = {
            "max_commands": 3,
            "max_output_chars": 4000,
            "context_lines": 2,
            "max_contexts": 5,
            "max_bytes_per_context": 1000,
        }
        get_session_output_contexts_report.assert_called_once_with(Path(base).resolve(), "run-1", **expected_kwargs)
        format_session_output_contexts_report_text.assert_called_once_with(report)
        get_session_output_contexts_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_runs_session_output_diagnostics_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_session_output_diagnostics_report", return_value={"session": "run-1", "ok": True}) as get_session_output_diagnostics_report,
                patch("vibeagent.cli.get_session_output_diagnostics_text", return_value="Session output diagnostics:\n  session: run-1") as get_session_output_diagnostics_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--cwd",
                        base,
                        "--session-output-diagnostics",
                        "run-1",
                        "--session-output-command-max",
                        "3",
                        "--session-output-max-chars",
                        "4000",
                        "--session-output-context-lines",
                        "2",
                        "--session-output-context-max",
                        "5",
                        "--session-output-context-max-bytes",
                        "1000",
                        "--session-output-diagnostic-max",
                        "4",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertIn("Session output diagnostics:", stdout.getvalue())
        get_session_output_diagnostics_report.assert_not_called()
        get_session_output_diagnostics_text.assert_called_once_with(
            Path(base).resolve(),
            "run-1",
            max_commands=3,
            max_output_chars=4000,
            context_lines=2,
            max_diagnostics=4,
            max_contexts=5,
            max_bytes_per_context=1000,
        )
        create_chat_client.assert_not_called()

    def test_main_runs_session_output_diagnostics_json_with_structured_payload(self) -> None:
        report = {"session": "run-1", "exists": True, "ok": True, "diagnostics": {"total": 1}}
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_session_output_diagnostics_report", return_value=report) as get_session_output_diagnostics_report,
                patch(
                    "vibeagent.cli.format_session_output_diagnostics_report_text",
                    return_value="Session output diagnostics:\n  session: run-1",
                ) as format_session_output_diagnostics_report_text,
                patch("vibeagent.cli.get_session_output_diagnostics_text", return_value="Session output diagnostics:\n  session: run-1") as get_session_output_diagnostics_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--json",
                        "--cwd",
                        base,
                        "--session-output-diagnostics",
                        "run-1",
                        "--session-output-command-max",
                        "3",
                        "--session-output-max-chars",
                        "4000",
                        "--session-output-context-lines",
                        "2",
                        "--session-output-context-max",
                        "5",
                        "--session-output-context-max-bytes",
                        "1000",
                        "--session-output-diagnostic-max",
                        "4",
                    ]
                )

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["sessionOutputDiagnostics"], report)
        self.assertIn("Session output diagnostics:", payload["text"])
        expected_kwargs = {
            "max_commands": 3,
            "max_output_chars": 4000,
            "context_lines": 2,
            "max_diagnostics": 4,
            "max_contexts": 5,
            "max_bytes_per_context": 1000,
        }
        get_session_output_diagnostics_report.assert_called_once_with(Path(base).resolve(), "run-1", **expected_kwargs)
        format_session_output_diagnostics_report_text.assert_called_once_with(report)
        get_session_output_diagnostics_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_session_output_analysis_local_flags_exit_nonzero_for_unreadable_contexts(self) -> None:
        cases = [
            (
                [
                    "--session-output-contexts",
                    "run-1",
                    "--session-output-command-max",
                    "3",
                    "--session-output-max-chars",
                    "4000",
                    "--session-output-context-lines",
                    "2",
                    "--session-output-context-max",
                    "5",
                    "--session-output-context-max-bytes",
                    "1000",
                ],
                "vibeagent.cli.get_session_output_contexts_text",
                "Session output contexts:\n  ok: yes\n  contexts: 0/1",
                {
                    "max_commands": 3,
                    "max_output_chars": 4000,
                    "context_lines": 2,
                    "max_contexts": 5,
                    "max_bytes_per_context": 1000,
                },
            ),
            (
                [
                    "--session-output-diagnostics",
                    "run-1",
                    "--session-output-command-max",
                    "3",
                    "--session-output-max-chars",
                    "4000",
                    "--session-output-context-lines",
                    "2",
                    "--session-output-context-max",
                    "5",
                    "--session-output-context-max-bytes",
                    "1000",
                    "--session-output-diagnostic-max",
                    "4",
                ],
                "vibeagent.cli.get_session_output_diagnostics_text",
                "Session output diagnostics:\n  ok: yes\n  diagnostics: 1/1\n  contexts: 0/1",
                {
                    "max_commands": 3,
                    "max_output_chars": 4000,
                    "context_lines": 2,
                    "max_diagnostics": 4,
                    "max_contexts": 5,
                    "max_bytes_per_context": 1000,
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

            self.assertEqual(exit_code, 1)
            self.assertEqual(stdout.getvalue(), f"{text}\n")
            getter.assert_called_once_with(Path(base).resolve(), "run-1", **expected_kwargs)
            create_chat_client.assert_not_called()

    def test_main_session_output_analysis_local_flag_reports_json_failure_status(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            report = {"session": "run-1", "exists": True, "ok": True, "contexts": {"ok": 0, "total": 1}}
            text = "Session output contexts:\n  ok: yes\n  contexts: 0/1"

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_session_output_contexts_report", return_value=report) as get_session_output_contexts_report,
                patch("vibeagent.cli.format_session_output_contexts_report_text", return_value=text) as format_session_output_contexts_report_text,
                patch("vibeagent.cli.get_session_output_contexts_text") as get_session_output_contexts_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--session-output-contexts", "run-1"])

        self.assertEqual(exit_code, 1)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["kind"], "local")
        self.assertFalse(payload["success"])
        self.assertEqual(payload["status"], "failed")
        self.assertEqual(payload["text"], text)
        self.assertEqual(payload["sessionOutputContexts"], report)
        get_session_output_contexts_report.assert_called_once_with(
            Path(base).resolve(),
            "run-1",
            max_commands=20,
            max_output_chars=20000,
            context_lines=5,
            max_contexts=20,
            max_bytes_per_context=20000,
        )
        format_session_output_contexts_report_text.assert_called_once_with(report)
        get_session_output_contexts_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_session_output_diagnostics_json_reports_failure_status(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            report = {
                "session": "run-1",
                "exists": True,
                "ok": True,
                "diagnostics": {"shown": 1, "total": 1, "items": []},
                "contexts": {"ok": 0, "total": 1, "items": []},
            }
            text = "Session output diagnostics:\n  ok: yes\n  diagnostics: 1/1\n  contexts: 0/1"

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_session_output_diagnostics_report", return_value=report) as get_session_output_diagnostics_report,
                patch("vibeagent.cli.format_session_output_diagnostics_report_text", return_value=text) as format_session_output_diagnostics_report_text,
                patch("vibeagent.cli.get_session_output_diagnostics_text") as get_session_output_diagnostics_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--session-output-diagnostics", "run-1"])

        self.assertEqual(exit_code, 1)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["kind"], "local")
        self.assertFalse(payload["success"])
        self.assertEqual(payload["status"], "failed")
        self.assertEqual(payload["text"], text)
        self.assertEqual(payload["sessionOutputDiagnostics"], report)
        get_session_output_diagnostics_report.assert_called_once_with(
            Path(base).resolve(),
            "run-1",
            max_commands=20,
            max_output_chars=20000,
            context_lines=5,
            max_diagnostics=50,
            max_contexts=20,
            max_bytes_per_context=20000,
        )
        format_session_output_diagnostics_report_text.assert_called_once_with(report)
        get_session_output_diagnostics_text.assert_not_called()
        create_chat_client.assert_not_called()


if __name__ == "__main__":
    unittest.main()

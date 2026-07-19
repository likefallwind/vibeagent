import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from vibeagent.cli import main


class CliProcessOutputAnalysisFlagTests(unittest.TestCase):
    def test_main_runs_process_output_contexts_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_process_output_contexts_text", return_value="Process output contexts:\n  contexts: 1/1") as get_process_output_contexts_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--cwd",
                        base,
                        "--process-output-contexts",
                        "bg-1",
                        "--process-max-chars",
                        "2000",
                        "--process-output-context-lines",
                        "2",
                        "--process-output-context-max",
                        "5",
                        "--process-output-context-max-bytes",
                        "1000",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertIn("Process output contexts:", stdout.getvalue())
        get_process_output_contexts_text.assert_called_once_with(
            Path(base).resolve(),
            process_id="bg-1",
            max_output_chars=2000,
            context_lines=2,
            max_contexts=5,
            max_bytes_per_context=1000,
        )
        create_chat_client.assert_not_called()

    def test_main_runs_process_output_diagnostics_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_process_output_diagnostics_text", return_value="Process output diagnostics:\n  diagnostics: 1/1") as get_process_output_diagnostics_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--cwd",
                        base,
                        "--process-output-diagnostics",
                        "bg-1",
                        "--process-max-chars",
                        "2000",
                        "--process-output-context-lines",
                        "2",
                        "--process-output-diagnostic-max",
                        "7",
                        "--process-output-context-max",
                        "5",
                        "--process-output-context-max-bytes",
                        "1000",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertIn("Process output diagnostics:", stdout.getvalue())
        get_process_output_diagnostics_text.assert_called_once_with(
            Path(base).resolve(),
            process_id="bg-1",
            max_output_chars=2000,
            context_lines=2,
            max_diagnostics=7,
            max_contexts=5,
            max_bytes_per_context=1000,
        )
        create_chat_client.assert_not_called()

    def test_main_process_output_analysis_local_flags_exit_nonzero_for_failed_results(self) -> None:
        cases = [
            (
                [
                    "--process-output-contexts",
                    "missing-proc",
                    "--process-max-chars",
                    "2000",
                    "--process-output-context-lines",
                    "2",
                    "--process-output-context-max",
                    "5",
                    "--process-output-context-max-bytes",
                    "1000",
                ],
                "vibeagent.cli.get_process_output_contexts_text",
                "Process output contexts:\n  ok: no\n  message: Unknown background process id.",
            ),
            (
                [
                    "--process-output-diagnostics",
                    "bg-1",
                    "--process-max-chars",
                    "2000",
                    "--process-output-context-lines",
                    "2",
                    "--process-output-context-max",
                    "5",
                    "--process-output-context-max-bytes",
                    "1000",
                ],
                "vibeagent.cli.get_process_output_diagnostics_text",
                "Process output diagnostics:\n  diagnostics: 1/1\n  contexts: 0/1",
            ),
        ]

        for argv_tail, patch_target, text in cases:
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
            expected_kwargs = {
                "process_id": argv_tail[1],
                "max_output_chars": 2000,
                "context_lines": 2,
                "max_contexts": 5,
                "max_bytes_per_context": 1000,
            }
            if "diagnostics" in patch_target:
                expected_kwargs["max_diagnostics"] = 50
            getter.assert_called_once_with(Path(base).resolve(), **expected_kwargs)
            create_chat_client.assert_not_called()

    def test_main_process_output_analysis_local_flags_exit_nonzero_for_failed_process_state(self) -> None:
        cases = [
            (
                [
                    "--process-output-contexts",
                    "bg-1",
                    "--process-max-chars",
                    "2000",
                    "--process-output-context-lines",
                    "2",
                    "--process-output-context-max",
                    "5",
                    "--process-output-context-max-bytes",
                    "1000",
                ],
                "vibeagent.cli.get_process_output_contexts_text",
                "Process output contexts:\n  ok: yes\n  status: exited(7)\n  contexts: 1/1",
                1,
            ),
            (
                [
                    "--process-output-diagnostics",
                    "bg-1",
                    "--process-max-chars",
                    "2000",
                    "--process-output-context-lines",
                    "2",
                    "--process-output-context-max",
                    "5",
                    "--process-output-context-max-bytes",
                    "1000",
                ],
                "vibeagent.cli.get_process_output_diagnostics_text",
                "Process output diagnostics:\n  ok: yes\n  status: signaled(SIGTERM)\n  diagnostics: 1/1\n  contexts: 1/1",
                1,
            ),
            (
                [
                    "--process-output-contexts",
                    "bg-1",
                    "--process-max-chars",
                    "2000",
                    "--process-output-context-lines",
                    "2",
                    "--process-output-context-max",
                    "5",
                    "--process-output-context-max-bytes",
                    "1000",
                ],
                "vibeagent.cli.get_process_output_contexts_text",
                "Process output contexts:\n  ok: yes\n  status: exited(0)\n  contexts: 1/1",
                0,
            ),
            (
                [
                    "--process-output-diagnostics",
                    "bg-1",
                    "--process-max-chars",
                    "2000",
                    "--process-output-context-lines",
                    "2",
                    "--process-output-context-max",
                    "5",
                    "--process-output-context-max-bytes",
                    "1000",
                ],
                "vibeagent.cli.get_process_output_diagnostics_text",
                "Process output diagnostics:\n  ok: yes\n  status: running\n  diagnostics: 1/1\n  contexts: 1/1",
                0,
            ),
        ]

        for argv_tail, patch_target, text, expected_exit_code in cases:
            with self.subTest(argv=argv_tail, text=text), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()

                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch(patch_target, return_value=text) as getter,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--cwd", base, *argv_tail])

            self.assertEqual(exit_code, expected_exit_code)
            self.assertEqual(stdout.getvalue(), f"{text}\n")
            expected_kwargs = {
                "process_id": "bg-1",
                "max_output_chars": 2000,
                "context_lines": 2,
                "max_contexts": 5,
                "max_bytes_per_context": 1000,
            }
            if "diagnostics" in patch_target:
                expected_kwargs["max_diagnostics"] = 50
            getter.assert_called_once_with(Path(base).resolve(), **expected_kwargs)
            create_chat_client.assert_not_called()

    def test_main_process_output_analysis_json_outputs_structured_payloads(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            contexts_report = {
                "projectRoot": str(Path(base).resolve()),
                "ok": True,
                "processId": "bg-1",
                "pid": 1234,
                "status": "running",
                "contexts": {"ok": 1, "total": 1, "items": [{"path": "src/app.py", "line": 2, "content": "2: print('ok')"}]},
                "totalRefs": 1,
                "maxOutputChars": 2000,
                "stdoutChars": 24,
                "stderrChars": 0,
                "truncated": False,
                "message": "Extracted 1/1 output context(s) from process bg-1.",
            }
            diagnostics_report = {
                "projectRoot": str(Path(base).resolve()),
                "ok": True,
                "processId": "bg-1",
                "pid": 1234,
                "status": "running",
                "diagnostics": {"shown": 1, "total": 1, "items": [{"severity": "error", "outputLine": 1, "path": "src/app.py"}]},
                "contexts": {"ok": 1, "total": 1, "items": [{"path": "src/app.py", "line": 2, "content": "2: print('ok')"}]},
                "totalRefs": 1,
                "maxOutputChars": 2000,
                "stdoutChars": 32,
                "stderrChars": 0,
                "contextLines": 2,
                "maxDiagnostics": 7,
                "maxContexts": 5,
                "maxBytesPerContext": 1000,
                "diagnosticsTruncated": False,
                "contextsTruncated": False,
                "message": "Extracted 1/1 diagnostic(s) and 1/1 source context(s) from process bg-1.",
            }
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_process_output_contexts_report", return_value=contexts_report) as get_contexts_report,
                patch(
                    "vibeagent.cli.format_process_output_contexts_report_text",
                    return_value="Process output contexts:\n  contexts: 1/1",
                ) as format_contexts_report,
                redirect_stdout(stdout),
            ):
                contexts_exit = main(
                    [
                        "--json",
                        "--cwd",
                        base,
                        "--process-output-contexts",
                        "bg-1",
                        "--process-max-chars",
                        "2000",
                        "--process-output-context-lines",
                        "2",
                        "--process-output-context-max",
                        "5",
                        "--process-output-context-max-bytes",
                        "1000",
                    ]
                )
            contexts_payload = json.loads(stdout.getvalue())
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client_diagnostics,
                patch("vibeagent.cli.get_process_output_diagnostics_report", return_value=diagnostics_report) as get_diagnostics_report,
                patch(
                    "vibeagent.cli.format_process_output_diagnostics_report_text",
                    return_value="Process output diagnostics:\n  diagnostics: 1/1\n  contexts: 1/1",
                ) as format_diagnostics_report,
                redirect_stdout(stdout),
            ):
                diagnostics_exit = main(
                    [
                        "--json",
                        "--cwd",
                        base,
                        "--process-output-diagnostics",
                        "bg-1",
                        "--process-max-chars",
                        "2000",
                        "--process-output-context-lines",
                        "2",
                        "--process-output-diagnostic-max",
                        "7",
                        "--process-output-context-max",
                        "5",
                        "--process-output-context-max-bytes",
                        "1000",
                    ]
                )
            diagnostics_payload = json.loads(stdout.getvalue())

        self.assertEqual(contexts_exit, 0)
        self.assertEqual(contexts_payload["processOutputContexts"], contexts_report)
        get_contexts_report.assert_called_once_with(
            Path(base).resolve(),
            process_id="bg-1",
            max_output_chars=2000,
            context_lines=2,
            max_contexts=5,
            max_bytes_per_context=1000,
        )
        format_contexts_report.assert_called_once_with(contexts_report)
        create_chat_client.assert_not_called()
        self.assertEqual(diagnostics_exit, 0)
        self.assertEqual(diagnostics_payload["processOutputDiagnostics"], diagnostics_report)
        get_diagnostics_report.assert_called_once_with(
            Path(base).resolve(),
            process_id="bg-1",
            max_output_chars=2000,
            context_lines=2,
            max_diagnostics=7,
            max_contexts=5,
            max_bytes_per_context=1000,
        )
        format_diagnostics_report.assert_called_once_with(diagnostics_report)
        create_chat_client_diagnostics.assert_not_called()

    def test_main_process_output_analysis_local_flag_reports_json_failure_status(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            report = {
                "projectRoot": str(Path(base).resolve()),
                "ok": False,
                "processId": "missing-proc",
                "pid": None,
                "status": "unknown",
                "contexts": {"ok": 0, "total": 0, "items": []},
                "totalRefs": 0,
                "maxOutputChars": 4000,
                "stdoutChars": 0,
                "stderrChars": 0,
                "truncated": False,
                "message": "Unknown background process id.",
            }

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_process_output_contexts_report", return_value=report) as get_process_output_contexts_report,
                patch(
                    "vibeagent.cli.format_process_output_contexts_report_text",
                    return_value="Process output contexts:\n  ok: no",
                ) as format_process_output_contexts_report_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--process-output-contexts", "missing-proc"])

        self.assertEqual(exit_code, 1)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["kind"], "local")
        self.assertFalse(payload["success"])
        self.assertEqual(payload["status"], "failed")
        self.assertEqual(payload["text"], "Process output contexts:\n  ok: no")
        self.assertEqual(payload["processOutputContexts"], report)
        get_process_output_contexts_report.assert_called_once_with(
            Path(base).resolve(),
            process_id="missing-proc",
            max_output_chars=None,
            context_lines=5,
            max_contexts=20,
            max_bytes_per_context=20000,
        )
        format_process_output_contexts_report_text.assert_called_once_with(report)
        create_chat_client.assert_not_called()

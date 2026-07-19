import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from vibeagent.cli import main


class CliOutputDiagnosticsFlagTests(unittest.TestCase):
    def test_main_runs_output_contexts_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_output_contexts_text", return_value="Output contexts:\n  contexts: 1/1") as get_output_contexts_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--cwd",
                        base,
                        "--output-contexts",
                        "src/app.py:42:8",
                        "--output-context-lines",
                        "2",
                        "--output-context-max",
                        "5",
                        "--output-context-max-bytes",
                        "1000",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertIn("Output contexts:", stdout.getvalue())
        get_output_contexts_text.assert_called_once_with(
            Path(base).resolve(),
            "src/app.py:42:8",
            context_lines=2,
            max_contexts=5,
            max_bytes_per_context=1000,
        )
        create_chat_client.assert_not_called()

    def test_main_runs_output_diagnostics_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_output_diagnostics_text", return_value="Output diagnostics:\n  diagnostics: 1/1") as get_output_diagnostics_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--cwd",
                        base,
                        "--output-diagnostics",
                        "ERROR src/app.py:42:8 failed",
                        "--output-diagnostic-lines",
                        "2",
                        "--output-diagnostic-max",
                        "5",
                        "--output-diagnostic-context-max",
                        "6",
                        "--output-diagnostic-context-max-bytes",
                        "1000",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertIn("Output diagnostics:", stdout.getvalue())
        get_output_diagnostics_text.assert_called_once_with(
            Path(base).resolve(),
            "ERROR src/app.py:42:8 failed",
            context_lines=2,
            max_diagnostics=5,
            max_contexts=6,
            max_bytes_per_context=1000,
        )
        create_chat_client.assert_not_called()

    def test_main_runs_python_traceback_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_python_traceback_text", return_value="Python traceback:\n  diagnostics: 1/1") as get_python_traceback_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--cwd",
                        base,
                        "--python-traceback",
                        "ValueError: bad",
                        "--output-diagnostic-lines",
                        "2",
                        "--output-diagnostic-max",
                        "5",
                        "--output-diagnostic-context-max",
                        "6",
                        "--output-diagnostic-context-max-bytes",
                        "1000",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertIn("Python traceback:", stdout.getvalue())
        get_python_traceback_text.assert_called_once_with(
            Path(base).resolve(),
            "ValueError: bad",
            context_lines=2,
            max_diagnostics=5,
            max_contexts=6,
            max_bytes_per_context=1000,
        )
        create_chat_client.assert_not_called()

    def test_main_output_analysis_json_outputs_structured_payloads(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            root = Path(base)
            (root / "src").mkdir()
            (root / "src" / "app.py").write_text("one\nTwo\nraise ValueError('bad')\nfour\n", encoding="utf-8")
            (root / "tests").mkdir()
            (root / "tests" / "test_app.py").write_text("alpha\nbeta\ngamma\n", encoding="utf-8")

            def run_json(*argv: str) -> tuple[int, dict[str, object]]:
                stdout = io.StringIO()
                with redirect_stdout(stdout):
                    exit_code = main(["--json", "--cwd", base, *argv])
                return exit_code, json.loads(stdout.getvalue())

            with patch("vibeagent.cli.create_chat_client") as create_chat_client:
                contexts_exit, contexts_payload = run_json(
                    "--output-contexts",
                    "src/app.py:3: boom\ntests/test_app.py:2:5: assertion failed",
                    "--output-context-lines",
                    "1",
                    "--output-context-max-bytes",
                    "1000",
                )
                diagnostics_exit, diagnostics_payload = run_json(
                    "--output-diagnostics",
                    "warning: src/app.py:2:3 check this\nERROR src/app.py:3 failed",
                    "--output-diagnostic-lines",
                    "0",
                    "--output-diagnostic-context-max-bytes",
                    "1000",
                )
                traceback_exit, traceback_payload = run_json(
                    "--python-traceback",
                    'Traceback (most recent call last):\n  File "src/app.py", line 3, in run\nValueError: bad',
                    "--output-diagnostic-lines",
                    "0",
                    "--output-diagnostic-context-max-bytes",
                    "1000",
                )

        self.assertEqual(contexts_exit, 0)
        self.assertEqual(contexts_payload["outputContexts"]["contexts"]["ok"], 2)
        self.assertEqual(contexts_payload["outputContexts"]["contexts"]["items"][0]["path"], "src/app.py")
        self.assertIn("3: raise ValueError('bad')", contexts_payload["outputContexts"]["contexts"]["items"][0]["content"])
        self.assertEqual(diagnostics_exit, 0)
        self.assertEqual(diagnostics_payload["outputDiagnostics"]["diagnostics"]["shown"], 2)
        self.assertEqual(diagnostics_payload["outputDiagnostics"]["diagnostics"]["items"][0]["severity"], "warning")
        self.assertEqual(diagnostics_payload["outputDiagnostics"]["contexts"]["ok"], 2)
        self.assertEqual(traceback_exit, 0)
        self.assertEqual(traceback_payload["pythonTraceback"]["diagnostics"]["shown"], 3)
        self.assertEqual(traceback_payload["pythonTraceback"]["contexts"]["ok"], 1)
        self.assertIn("3: raise ValueError('bad')", traceback_payload["pythonTraceback"]["contexts"]["items"][0]["content"])
        create_chat_client.assert_not_called()

    def test_main_output_context_local_flags_exit_nonzero_for_unreadable_contexts(self) -> None:
        cases = [
            (
                [
                    "--output-contexts",
                    "ERROR missing.py:1: boom",
                    "--output-context-lines",
                    "2",
                    "--output-context-max",
                    "5",
                    "--output-context-max-bytes",
                    "1000",
                ],
                "vibeagent.cli.get_output_contexts_text",
                "Output contexts:\n  contexts: 0/1",
                ("ERROR missing.py:1: boom",),
                {"context_lines": 2, "max_contexts": 5, "max_bytes_per_context": 1000},
            ),
            (
                [
                    "--output-diagnostics",
                    "ERROR missing.py:1: boom",
                    "--output-diagnostic-lines",
                    "2",
                    "--output-diagnostic-max",
                    "5",
                    "--output-diagnostic-context-max",
                    "6",
                    "--output-diagnostic-context-max-bytes",
                    "1000",
                ],
                "vibeagent.cli.get_output_diagnostics_text",
                "Output diagnostics:\n  diagnostics: 1/1\n  contexts: 0/1",
                ("ERROR missing.py:1: boom",),
                {"context_lines": 2, "max_diagnostics": 5, "max_contexts": 6, "max_bytes_per_context": 1000},
            ),
            (
                [
                    "--python-traceback",
                    'File "missing.py", line 1\nValueError: boom',
                    "--output-diagnostic-lines",
                    "2",
                    "--output-diagnostic-max",
                    "5",
                    "--output-diagnostic-context-max",
                    "6",
                    "--output-diagnostic-context-max-bytes",
                    "1000",
                ],
                "vibeagent.cli.get_python_traceback_text",
                "Python traceback:\n  diagnostics: 2/2\n  contexts: 0/1",
                ('File "missing.py", line 1\nValueError: boom',),
                {"context_lines": 2, "max_diagnostics": 5, "max_contexts": 6, "max_bytes_per_context": 1000},
            ),
        ]

        for argv_tail, patch_target, text, expected_args, expected_kwargs in cases:
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
            getter.assert_called_once_with(Path(base).resolve(), *expected_args, **expected_kwargs)
            create_chat_client.assert_not_called()

    def test_main_output_context_local_flag_reports_json_failure_status(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            report = {
                "projectRoot": str(Path(base).resolve()),
                "ok": False,
                "contexts": {"ok": 0, "total": 1, "items": []},
                "totalRefs": 1,
                "contextLines": 5,
                "maxContexts": 20,
                "maxBytesPerContext": 20000,
                "truncated": False,
                "message": "Read 0/1 referenced context(s).",
            }

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_output_contexts_report", return_value=report) as get_output_contexts_report,
                patch(
                    "vibeagent.cli.format_output_contexts_report_text",
                    return_value="Output contexts:\n  contexts: 0/1",
                ) as format_output_contexts_report_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--output-contexts", "ERROR missing.py:1: boom"])

        self.assertEqual(exit_code, 1)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["kind"], "local")
        self.assertFalse(payload["success"])
        self.assertEqual(payload["status"], "failed")
        self.assertEqual(payload["text"], "Output contexts:\n  contexts: 0/1")
        self.assertEqual(payload["outputContexts"], report)
        get_output_contexts_report.assert_called_once_with(
            Path(base).resolve(),
            "ERROR missing.py:1: boom",
            context_lines=5,
            max_contexts=20,
            max_bytes_per_context=20000,
        )
        format_output_contexts_report_text.assert_called_once_with(report)
        create_chat_client.assert_not_called()

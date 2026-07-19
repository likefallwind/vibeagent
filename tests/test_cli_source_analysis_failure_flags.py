import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from vibeagent.cli import main


class CliSourceAnalysisFailureFlagTests(unittest.TestCase):
    def test_main_source_analysis_local_flags_exit_nonzero_for_failed_results(self) -> None:
        cases = [
            (
                ["--symbols", "src/app.py", "missing.py"],
                "vibeagent.cli.get_symbols_text",
                "Symbols:\n  files: 1/2",
                (Path, ["src/app.py", "missing.py"]),
            ),
            (
                ["--python-deps", "missing.py"],
                "vibeagent.cli.get_python_deps_text",
                "Python dependencies:\n  ok: no\n  message: Path does not exist: missing.py",
                (Path, "missing.py"),
            ),
            (
                ["--code-deps", "missing.ts"],
                "vibeagent.cli.get_code_deps_text",
                "Code dependencies:\n  ok: no\n  message: Path does not exist: missing.ts",
                (Path, "missing.ts"),
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

    def test_main_source_analysis_local_flag_reports_json_failure_status(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            report = {
                "projectRoot": str(Path(base).resolve()),
                "ok": False,
                "paths": ["missing.py"],
                "maxSymbols": 200,
                "files": {"ok": 0, "total": 1, "items": [{"path": "missing.py", "ok": False, "message": "Path does not exist: missing.py"}]},
                "counts": {"symbols": 0, "imports": 0},
                "message": "Read outlines for 0/1 source file(s).",
            }

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_symbols_report", return_value=report) as get_symbols_report,
                patch("vibeagent.cli.format_symbols_report_text", return_value="Symbols:\n  files: 0/1") as format_symbols_report_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--symbols", "missing.py"])

        self.assertEqual(exit_code, 1)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["kind"], "local")
        self.assertFalse(payload["success"])
        self.assertEqual(payload["status"], "failed")
        self.assertEqual(payload["text"], "Symbols:\n  files: 0/1")
        self.assertEqual(payload["symbols"], report)
        get_symbols_report.assert_called_once_with(Path(base).resolve(), ["missing.py"])
        format_symbols_report_text.assert_called_once_with(report)
        create_chat_client.assert_not_called()

    def test_main_scoped_symbol_local_flags_exit_nonzero_for_failed_results(self) -> None:
        cases = [
            (
                ["--python-defs", "main", "--python-path", "missing.py"],
                "vibeagent.cli.get_python_defs_text",
                "Python definitions:\n  ok: no\n  message: Path does not exist: missing.py",
                {"symbol": "main", "path": "missing.py"},
            ),
            (
                ["--python-refs", "main", "--python-path", "missing.py"],
                "vibeagent.cli.get_python_refs_text",
                "Python references:\n  ok: no\n  message: Path does not exist: missing.py",
                {"symbol": "main", "path": "missing.py"},
            ),
            (
                ["--python-ref-contexts", "main", "--python-path", "missing.py"],
                "vibeagent.cli.get_python_ref_contexts_text",
                "Python reference contexts:\n  ok: no\n  message: Path does not exist: missing.py",
                {"symbol": "main", "path": "missing.py"},
            ),
            (
                ["--python-calls", "main", "--python-path", "missing.py"],
                "vibeagent.cli.get_python_calls_text",
                "Python calls:\n  ok: no\n  message: Path does not exist: missing.py",
                {"symbol": "main", "path": "missing.py"},
            ),
            (
                ["--python-call-graph", "missing.py"],
                "vibeagent.cli.get_python_call_graph_text",
                "Python call graph:\n  ok: no\n  message: Path does not exist: missing.py",
                {},
            ),
            (
                ["--python-rename-preview", "main", "other", "--python-path", "missing.py"],
                "vibeagent.cli.get_python_rename_preview_text",
                "Python rename preview:\n  ok: no\n  message: Path does not exist: missing.py",
                {"symbol": "main", "new_name": "other", "path": "missing.py"},
            ),
            (
                ["--code-refs", "main", "--code-path", "missing.ts"],
                "vibeagent.cli.get_code_refs_text",
                "Code references:\n  ok: no\n  message: Path does not exist: missing.ts",
                {"symbol": "main", "path": "missing.ts"},
            ),
            (
                ["--code-ref-contexts", "main", "--code-path", "missing.ts"],
                "vibeagent.cli.get_code_ref_contexts_text",
                "Code reference contexts:\n  ok: no\n  message: Path does not exist: missing.ts",
                {"symbol": "main", "path": "missing.ts"},
            ),
            (
                ["--code-defs", "main", "--code-path", "missing.ts"],
                "vibeagent.cli.get_code_defs_text",
                "Code definitions:\n  ok: no\n  message: Path does not exist: missing.ts",
                {"symbol": "main", "path": "missing.ts"},
            ),
            (
                ["--code-rename-preview", "main", "other", "--code-path", "missing.ts"],
                "vibeagent.cli.get_code_rename_preview_text",
                "Code rename preview:\n  ok: no\n  message: Path does not exist: missing.ts",
                {"symbol": "main", "new_name": "other", "path": "missing.ts"},
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
            if argv_tail[0] == "--python-call-graph":
                getter.assert_called_once_with(Path(base).resolve(), "missing.py")
            else:
                getter.assert_called_once_with(Path(base).resolve(), **expected_kwargs)
            create_chat_client.assert_not_called()

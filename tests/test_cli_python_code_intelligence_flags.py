import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from vibeagent.cli import main


class CliPythonCodeIntelligenceFlagTests(unittest.TestCase):
    def test_main_runs_python_check_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_python_check_text", return_value="Python check:\n  ok: yes") as get_python_check_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--python-check", "src"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Python check:", stdout.getvalue())
        get_python_check_text.assert_called_once_with(Path(base).resolve(), "src")
        create_chat_client.assert_not_called()

    def test_main_runs_python_deps_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_python_deps_text", return_value="Python dependencies:\n  files: 1/1") as get_python_deps_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--python-deps", "src"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Python dependencies:", stdout.getvalue())
        get_python_deps_text.assert_called_once_with(Path(base).resolve(), "src")
        create_chat_client.assert_not_called()

    def test_main_runs_python_deps_local_flag_with_bounds(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_python_deps_text", return_value="Python dependencies:\n  files: 1/1") as get_python_deps_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--cwd",
                        base,
                        "--python-deps",
                        "src",
                        "--python-deps-max-files",
                        "7",
                        "--python-deps-max-imports",
                        "8",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertIn("Python dependencies:", stdout.getvalue())
        get_python_deps_text.assert_called_once_with(Path(base).resolve(), "src", max_files=7, max_imports=8)
        create_chat_client.assert_not_called()

    def test_main_runs_python_defs_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_python_defs_text", return_value="Python definitions:\n  definitions: 1/1") as get_python_defs_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--python-defs", "Runner.run", "--python-path", "src"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Python definitions:", stdout.getvalue())
        get_python_defs_text.assert_called_once_with(Path(base).resolve(), symbol="Runner.run", path="src")
        create_chat_client.assert_not_called()

    def test_main_runs_python_refs_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_python_refs_text", return_value="Python references:\n  references: 1/1") as get_python_refs_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--python-refs", "run_agent", "--python-path", "src"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Python references:", stdout.getvalue())
        get_python_refs_text.assert_called_once_with(Path(base).resolve(), symbol="run_agent", path="src")
        create_chat_client.assert_not_called()

    def test_main_runs_python_ref_contexts_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_python_ref_contexts_text", return_value="Python reference contexts:\n  contexts: 1/1") as get_python_ref_contexts_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--python-ref-contexts", "run_agent", "--python-path", "src"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Python reference contexts:", stdout.getvalue())
        get_python_ref_contexts_text.assert_called_once_with(Path(base).resolve(), symbol="run_agent", path="src")
        create_chat_client.assert_not_called()

    def test_main_runs_python_calls_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_python_calls_text", return_value="Python calls:\n  calls: 1/1") as get_python_calls_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--python-calls", "helper", "--python-path", "src"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Python calls:", stdout.getvalue())
        get_python_calls_text.assert_called_once_with(Path(base).resolve(), symbol="helper", path="src")
        create_chat_client.assert_not_called()

    def test_main_runs_python_symbol_local_flags_with_bounds(self) -> None:
        cases = [
            (
                ["--python-defs", "Runner.run", "--python-path", "src", "--python-max-matches", "3", "--python-def-max-lines", "40"],
                "vibeagent.cli.get_python_defs_text",
                "Python definitions:\n  definitions: 1/1",
                {"symbol": "Runner.run", "path": "src", "max_matches": 3, "max_lines": 40},
            ),
            (
                ["--python-refs", "run_agent", "--python-path", "src", "--python-max-matches", "4"],
                "vibeagent.cli.get_python_refs_text",
                "Python references:\n  references: 1/1",
                {"symbol": "run_agent", "path": "src", "max_matches": 4},
            ),
            (
                [
                    "--python-ref-contexts",
                    "run_agent",
                    "--python-path",
                    "src",
                    "--python-max-matches",
                    "5",
                    "--python-context-lines",
                    "1",
                    "--python-context-max-bytes",
                    "1000",
                ],
                "vibeagent.cli.get_python_ref_contexts_text",
                "Python reference contexts:\n  contexts: 1/1",
                {"symbol": "run_agent", "path": "src", "max_matches": 5, "context_lines": 1, "max_bytes_per_context": 1000},
            ),
            (
                ["--python-calls", "helper", "--python-path", "src", "--python-max-matches", "6"],
                "vibeagent.cli.get_python_calls_text",
                "Python calls:\n  calls: 1/1",
                {"symbol": "helper", "path": "src", "max_matches": 6},
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
            getter.assert_called_once_with(Path(base).resolve(), **expected_kwargs)
            create_chat_client.assert_not_called()

    def test_main_rejects_python_symbol_bounds_without_matching_local_flag(self) -> None:
        cases = [
            (
                ["--python-max-matches", "3"],
                "--python-max-matches can only be used with --python-defs, --python-refs, --python-ref-contexts, or --python-calls.",
            ),
            (
                ["--python-def-max-lines", "40"],
                "--python-def-max-lines can only be used with --python-defs.",
            ),
            (
                ["--python-refs", "run_agent", "--python-def-max-lines", "40"],
                "--python-def-max-lines can only be used with --python-defs.",
            ),
            (
                ["--python-context-lines", "1"],
                "--python-context-lines can only be used with --python-ref-contexts.",
            ),
            (
                ["--python-refs", "run_agent", "--python-context-lines", "1"],
                "--python-context-lines can only be used with --python-ref-contexts.",
            ),
            (
                ["--python-context-max-bytes", "1000"],
                "--python-context-max-bytes can only be used with --python-ref-contexts.",
            ),
            (
                ["--python-deps-max-files", "5"],
                "--python-deps-max-files can only be used with --python-deps.",
            ),
            (
                ["--python-deps-max-imports", "20"],
                "--python-deps-max-imports can only be used with --python-deps.",
            ),
            (
                ["--python-call-graph-max-files", "5"],
                "--python-call-graph-max-files can only be used with --python-call-graph.",
            ),
            (
                ["--python-call-graph-max-edges", "20"],
                "--python-call-graph-max-edges can only be used with --python-call-graph.",
            ),
        ]

        for argv, expected in cases:
            with self.subTest(argv=argv):
                stdout = io.StringIO()

                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(argv)

                self.assertEqual(exit_code, 2)
                self.assertEqual(stdout.getvalue(), f"{expected}\n")
                create_chat_client.assert_not_called()

    def test_main_runs_python_call_graph_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_python_call_graph_text", return_value="Python call graph:\n  edges: 3/3") as get_python_call_graph_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--cwd",
                        base,
                        "--python-call-graph",
                        "src",
                        "--python-call-graph-max-files",
                        "7",
                        "--python-call-graph-max-edges",
                        "9",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertIn("Python call graph:", stdout.getvalue())
        get_python_call_graph_text.assert_called_once_with(Path(base).resolve(), "src", max_files=7, max_edges=9)
        create_chat_client.assert_not_called()

    def test_main_runs_python_code_intelligence_local_flags_as_json_without_creating_client(self) -> None:
        cases = [
            (
                ["--python-check", "src"],
                "vibeagent.cli.get_python_check_report",
                "vibeagent.cli.format_python_check_report_text",
                "pythonCheck",
                (Path, "src"),
                {},
            ),
            (
                ["--python-deps", "src", "--python-deps-max-files", "7", "--python-deps-max-imports", "8"],
                "vibeagent.cli.get_python_deps_report",
                "vibeagent.cli.format_python_deps_report_text",
                "pythonDependencies",
                (Path, "src"),
                {"max_files": 7, "max_imports": 8},
            ),
            (
                ["--python-defs", "Runner.run", "--python-path", "src", "--python-max-matches", "3", "--python-def-max-lines", "40"],
                "vibeagent.cli.get_python_defs_report",
                "vibeagent.cli.format_python_defs_report_text",
                "pythonDefinitions",
                (Path,),
                {"symbol": "Runner.run", "path": "src", "max_matches": 3, "max_lines": 40},
            ),
            (
                ["--python-refs", "run_agent", "--python-path", "src", "--python-max-matches", "4"],
                "vibeagent.cli.get_python_refs_report",
                "vibeagent.cli.format_python_refs_report_text",
                "pythonReferences",
                (Path,),
                {"symbol": "run_agent", "path": "src", "max_matches": 4},
            ),
            (
                [
                    "--python-ref-contexts",
                    "run_agent",
                    "--python-path",
                    "src",
                    "--python-max-matches",
                    "5",
                    "--python-context-lines",
                    "1",
                    "--python-context-max-bytes",
                    "1000",
                ],
                "vibeagent.cli.get_python_ref_contexts_report",
                "vibeagent.cli.format_python_ref_contexts_report_text",
                "pythonReferenceContexts",
                (Path,),
                {"symbol": "run_agent", "path": "src", "max_matches": 5, "context_lines": 1, "max_bytes_per_context": 1000},
            ),
            (
                ["--python-calls", "helper", "--python-path", "src", "--python-max-matches", "6"],
                "vibeagent.cli.get_python_calls_report",
                "vibeagent.cli.format_python_calls_report_text",
                "pythonCalls",
                (Path,),
                {"symbol": "helper", "path": "src", "max_matches": 6},
            ),
            (
                ["--python-call-graph", "src", "--python-call-graph-max-files", "7", "--python-call-graph-max-edges", "8"],
                "vibeagent.cli.get_python_call_graph_report",
                "vibeagent.cli.format_python_call_graph_report_text",
                "pythonCallGraph",
                (Path, "src"),
                {"max_files": 7, "max_edges": 8},
            ),
        ]
        for argv_tail, getter_target, formatter_target, payload_key, expected_args, expected_kwargs in cases:
            with self.subTest(payload_key=payload_key), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()
                report = {"ok": True, "message": payload_key}
                rendered = f"{payload_key}: ok"

                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch(getter_target, return_value=report) as getter,
                    patch(formatter_target, return_value=rendered) as formatter,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--json", "--cwd", base, *argv_tail])

                payload = json.loads(stdout.getvalue())
                resolved_args = tuple(Path(base).resolve() if item is Path else item for item in expected_args)
                self.assertEqual(exit_code, 0)
                self.assertTrue(payload["success"])
                self.assertEqual(payload["status"], "completed")
                self.assertEqual(payload["text"], rendered)
                self.assertEqual(payload[payload_key], report)
                getter.assert_called_once_with(*resolved_args, **expected_kwargs)
                formatter.assert_called_once_with(report)
                create_chat_client.assert_not_called()

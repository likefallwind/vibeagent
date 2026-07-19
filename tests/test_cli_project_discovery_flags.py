import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from vibeagent.cli import main


class CliProjectDiscoveryFlagTests(unittest.TestCase):
    def test_main_runs_commands_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_commands_text", return_value="Project commands:\n  commands: 1/1") as get_commands_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--commands"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Project commands:", stdout.getvalue())
        get_commands_text.assert_called_once_with(Path(base).resolve())
        create_chat_client.assert_not_called()

    def test_main_runs_commands_local_flag_with_bounds(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_commands_text", return_value="Project commands:\n  commands: 1/2") as get_commands_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--commands", "--commands-max-commands", "2", "--commands-max-files", "3"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Project commands:", stdout.getvalue())
        get_commands_text.assert_called_once_with(Path(base).resolve(), max_commands=2, max_files=3)
        create_chat_client.assert_not_called()

    def test_main_rejects_commands_bounds_without_commands_local_flag(self) -> None:
        cases = [
            (["--commands-max-commands", "2"], "--commands-max-commands can only be used with --commands."),
            (["--commands-max-files", "3"], "--commands-max-files can only be used with --commands."),
        ]

        for argv, expected in cases:
            with self.subTest(argv=argv):
                stdout = io.StringIO()

                with redirect_stdout(stdout):
                    exit_code = main(argv)

                self.assertEqual(exit_code, 2)
                self.assertIn(expected, stdout.getvalue())

    def test_main_runs_related_tests_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_related_tests_text", return_value="Related tests:\n  candidates: 1/1") as get_related_tests_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--related-tests", "pkg/actions.py", "tests/test_actions.py"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Related tests:", stdout.getvalue())
        get_related_tests_text.assert_called_once_with(Path(base).resolve(), "pkg/actions.py tests/test_actions.py")
        create_chat_client.assert_not_called()

    def test_main_runs_related_tests_local_flag_with_bounds(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_related_tests_text", return_value="Related tests:\n  candidates: 1/2") as get_related_tests_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--related-tests", "pkg/actions.py", "--related-tests-max-paths", "3", "--related-tests-max-candidates", "4"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Related tests:", stdout.getvalue())
        get_related_tests_text.assert_called_once_with(Path(base).resolve(), "pkg/actions.py", max_paths=3, max_candidates=4)
        create_chat_client.assert_not_called()

    def test_main_rejects_related_tests_bounds_without_related_tests_local_flag(self) -> None:
        cases = [
            (["--related-tests-max-paths", "3"], "--related-tests-max-paths can only be used with --related-tests."),
            (["--related-tests-max-candidates", "4"], "--related-tests-max-candidates can only be used with --related-tests."),
        ]

        for argv, expected in cases:
            with self.subTest(argv=argv):
                stdout = io.StringIO()

                with redirect_stdout(stdout):
                    exit_code = main(argv)

                self.assertEqual(exit_code, 2)
                self.assertIn(expected, stdout.getvalue())

    def test_main_project_discovery_json_outputs_structured_payloads(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            root = Path(base).resolve()
            cases = [
                (
                    ["--commands", "--commands-max-commands", "2", "--commands-max-files", "3"],
                    "vibeagent.cli.get_commands_report",
                    "vibeagent.cli.format_commands_report_text",
                    "projectCommands",
                    "Project commands:\n  commands: 1/1",
                    {"max_commands": 2, "max_files": 3},
                ),
                (
                    ["--related-tests", "pkg/actions.py", "--related-tests-max-paths", "4", "--related-tests-max-candidates", "5"],
                    "vibeagent.cli.get_related_tests_report",
                    "vibeagent.cli.format_related_tests_report_text",
                    "relatedTests",
                    "Related tests:\n  candidates: 1/1",
                    {"argument": "pkg/actions.py", "max_paths": 4, "max_candidates": 5},
                ),
            ]

            for argv_tail, report_target, format_target, payload_key, text, expected_kwargs in cases:
                with self.subTest(payload_key=payload_key):
                    stdout = io.StringIO()
                    report = {"projectRoot": str(root), "ok": True, "message": "ok"}
                    with (
                        patch("vibeagent.cli.create_chat_client") as create_chat_client,
                        patch(report_target, return_value=report) as get_report,
                        patch(format_target, return_value=text) as format_report,
                        redirect_stdout(stdout),
                    ):
                        exit_code = main(["--json", "--cwd", base, *argv_tail])

                payload = json.loads(stdout.getvalue())
                self.assertEqual(exit_code, 0)
                self.assertTrue(payload["success"])
                self.assertEqual(payload[payload_key], report)
                self.assertEqual(payload["text"], text)
                get_report.assert_called_once_with(root, **expected_kwargs)
                format_report.assert_called_once_with(report)
                create_chat_client.assert_not_called()

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from vibeagent.cli import main


class CliProjectMetadataFlagTests(unittest.TestCase):
    def test_main_runs_manifests_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_manifests_text", return_value="Manifests:\n  files: 1/1") as get_manifests_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--manifests"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Manifests:", stdout.getvalue())
        get_manifests_text.assert_called_once_with(Path(base).resolve())
        create_chat_client.assert_not_called()

    def test_main_runs_manifests_local_flag_with_bounds(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_manifests_text", return_value="Manifests:\n  files: 1/2") as get_manifests_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--manifests", "--manifests-max-files", "2", "--manifests-max-items", "10"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Manifests:", stdout.getvalue())
        get_manifests_text.assert_called_once_with(Path(base).resolve(), max_files=2, max_items=10)
        create_chat_client.assert_not_called()

    def test_main_rejects_manifests_bounds_without_manifests_local_flag(self) -> None:
        cases = [
            (["--manifests-max-files", "2"], "--manifests-max-files can only be used with --manifests."),
            (["--manifests-max-items", "10"], "--manifests-max-items can only be used with --manifests."),
        ]

        for argv, expected in cases:
            with self.subTest(argv=argv):
                stdout = io.StringIO()

                with redirect_stdout(stdout):
                    exit_code = main(argv)

                self.assertEqual(exit_code, 2)
                self.assertIn(expected, stdout.getvalue())

    def test_main_runs_instructions_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_instructions_text", return_value="Project instructions:\n  files: 1/1") as get_instructions_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--instructions"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Project instructions:", stdout.getvalue())
        get_instructions_text.assert_called_once_with(Path(base).resolve())
        create_chat_client.assert_not_called()

    def test_main_runs_instructions_local_flag_with_bounds(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_instructions_text", return_value="Project instructions:\n  files: 1/2") as get_instructions_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--instructions", "--instructions-max-files", "2", "--instructions-max-bytes", "1000"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Project instructions:", stdout.getvalue())
        get_instructions_text.assert_called_once_with(Path(base).resolve(), max_files=2, max_bytes=1000)
        create_chat_client.assert_not_called()

    def test_main_rejects_instructions_bounds_without_instructions_local_flag(self) -> None:
        cases = [
            (["--instructions-max-files", "2"], "--instructions-max-files can only be used with --instructions."),
            (["--instructions-max-bytes", "1000"], "--instructions-max-bytes can only be used with --instructions."),
        ]

        for argv, expected in cases:
            with self.subTest(argv=argv):
                stdout = io.StringIO()

                with redirect_stdout(stdout):
                    exit_code = main(argv)

                self.assertEqual(exit_code, 2)
                self.assertIn(expected, stdout.getvalue())

    def test_main_runs_todos_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_todos_text", return_value="Project TODOs:\n  todos: 1/1") as get_todos_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--todos", "src"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Project TODOs:", stdout.getvalue())
        get_todos_text.assert_called_once_with(Path(base).resolve(), "src")
        create_chat_client.assert_not_called()

    def test_main_runs_todos_local_flag_with_bounds(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_todos_text", return_value="Project TODOs:\n  todos: 1/3") as get_todos_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--todos", "src", "--todos-max-items", "3", "--todos-max-files", "20"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Project TODOs:", stdout.getvalue())
        get_todos_text.assert_called_once_with(Path(base).resolve(), "src", max_items=3, max_files=20)
        create_chat_client.assert_not_called()

    def test_main_rejects_todos_bounds_without_todos_local_flag(self) -> None:
        cases = [
            (["--todos-max-items", "3"], "--todos-max-items can only be used with --todos."),
            (["--todos-max-files", "20"], "--todos-max-files can only be used with --todos."),
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

    def test_main_project_metadata_json_outputs_structured_payloads(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            root = Path(base).resolve()
            cases = [
                (
                    ["--manifests", "--manifests-max-files", "2", "--manifests-max-items", "10"],
                    "vibeagent.cli.get_manifests_report",
                    "vibeagent.cli.format_manifests_report_text",
                    "manifests",
                    "Manifests:\n  files: 1/1",
                    {"max_files": 2, "max_items": 10},
                ),
                (
                    ["--instructions", "--instructions-max-files", "2", "--instructions-max-bytes", "1000"],
                    "vibeagent.cli.get_instructions_report",
                    "vibeagent.cli.format_instructions_report_text",
                    "instructions",
                    "Project instructions:\n  files: 1/1",
                    {"max_files": 2, "max_bytes": 1000},
                ),
                (
                    ["--todos", "src", "--todos-max-items", "3", "--todos-max-files", "20"],
                    "vibeagent.cli.get_todos_report",
                    "vibeagent.cli.format_todos_report_text",
                    "todos",
                    "Project TODOs:\n  todos: 1/1",
                    {"path": "src", "max_items": 3, "max_files": 20},
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

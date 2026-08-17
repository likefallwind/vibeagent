import argparse
import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from vibeagent import MACHINE_OUTPUT_SCHEMA_VERSION, __version__, cli as cli_module
from vibeagent.cli import main


class CliEntryHelperTests(unittest.TestCase):
    def test_version_flag_is_local_and_prints_package_version(self) -> None:
        args = cli_module.parse_args(["--version"])
        stdout = io.StringIO()

        with patch("vibeagent.cli.create_chat_client") as create_chat_client, redirect_stdout(stdout):
            exit_code = main(["--version"])

        self.assertTrue(args.version)
        self.assertTrue(cli_module.has_local_flag(args))
        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout.getvalue(), f"vibeagent {__version__}\n")
        create_chat_client.assert_not_called()

    def test_version_flag_reports_json_payload(self) -> None:
        stdout = io.StringIO()

        with redirect_stdout(stdout):
            exit_code = main(["--json", "--version"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["kind"], "local")
        self.assertEqual(payload["text"], f"vibeagent {__version__}")
        self.assertEqual(payload["schemaVersion"], MACHINE_OUTPUT_SCHEMA_VERSION)
        self.assertEqual(payload["version"], __version__)

    def test_console_main_passes_process_arguments_to_main(self) -> None:
        with patch("sys.argv", ["vibeagent", "--version"]), patch("vibeagent.cli.main", return_value=0) as main_func:
            exit_code = cli_module.console_main()

        self.assertEqual(exit_code, 0)
        main_func.assert_called_once_with(["--version"])

    def test_process_and_wait_max_chars_default_to_runtime_process_limit(self) -> None:
        default_args = cli_module.parse_args(["--process-output-contexts", "bg-1"])
        process_override_args = cli_module.parse_args(
            ["--process-output-contexts", "bg-1", "--process-max-chars", "2000"]
        )
        wait_override_args = cli_module.parse_args(["--wait-process", "bg-1", "--wait-max-chars", "3000"])

        self.assertIsNone(default_args.process_max_chars)
        self.assertIsNone(default_args.wait_max_chars)
        self.assertEqual(process_override_args.process_max_chars, 2000)
        self.assertEqual(wait_override_args.wait_max_chars, 3000)

    def test_help_mentions_quoted_write_stdin_text(self) -> None:
        stdout = io.StringIO()

        with redirect_stdout(stdout), self.assertRaises(SystemExit) as raised:
            cli_module.parse_args(["--help"])

        self.assertEqual(raised.exception.code, 0)
        self.assertIn("Quote text with spaces", stdout.getvalue())

    def test_doctor_command_normalizes_to_provider_free_local_diagnostics(self) -> None:
        args = cli_module.parse_args(["doctor", "--cwd", "/tmp"])
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch(
                "vibeagent.cli.get_doctor_text",
                return_value="Doctor:\n  provider: minimax",
            ) as get_doctor_text,
            redirect_stdout(stdout),
        ):
            exit_code = main(["doctor", "--cwd", "/tmp"])

        self.assertTrue(args.doctor)
        self.assertEqual(args.task, [])
        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout.getvalue(), "Doctor:\n  provider: minimax\n")
        get_doctor_text.assert_called_once()
        create_chat_client.assert_not_called()

    def test_doctor_command_retains_json_output_and_rejects_task_arguments(self) -> None:
        json_args = cli_module.parse_args(["doctor", "--json"])
        leading_options = cli_module.parse_args(["--json", "--cwd", "/tmp", "doctor"])
        invalid_args = cli_module.parse_args(["doctor", "unexpected"])
        ordinary_task = cli_module.parse_args(["fix", "doctor"])
        stdout = io.StringIO()

        with patch("vibeagent.cli.create_chat_client") as create_chat_client, redirect_stdout(stdout):
            exit_code = main(["doctor", "unexpected"])

        self.assertTrue(json_args.doctor)
        self.assertTrue(json_args.json)
        self.assertTrue(leading_options.doctor)
        self.assertTrue(leading_options.json)
        self.assertEqual(leading_options.task, [])
        self.assertEqual(invalid_args.task, ["unexpected"])
        self.assertFalse(ordinary_task.doctor)
        self.assertEqual(ordinary_task.task, ["fix", "doctor"])
        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "Local command flags cannot be combined with a task.\n")
        create_chat_client.assert_not_called()

    def test_normalize_task_bound_diff_args_moves_task_into_diff_argument(self) -> None:
        args = argparse.Namespace(
            diff_contexts="",
            diff_hunks=None,
            diff=None,
            diff_staged=False,
            task=["src/app.py", "tests/test_app.py"],
        )

        cli_module.normalize_task_bound_diff_args(args)

        self.assertEqual(args.diff_contexts, "src/app.py tests/test_app.py")
        self.assertEqual(args.task, [])


if __name__ == "__main__":
    unittest.main()

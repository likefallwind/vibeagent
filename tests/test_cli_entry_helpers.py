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

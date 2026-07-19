import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from vibeagent.cli import main


class CliProcessLimitErrorTests(unittest.TestCase):
    def test_main_reports_process_max_chars_without_process_output_flag_as_local_flag_error(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--process-max-chars", "2000", "fix", "tests"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "--process-max-chars can only be used with --process-output, --process-output-contexts, or --process-output-diagnostics.\n")
        create_chat_client.assert_not_called()

    def test_main_reports_process_output_context_options_without_context_flag_as_local_flag_error(self) -> None:
        cases = [
            (["--process-output-context-lines", "2", "fix"], "--process-output-context-lines can only be used with --process-output-contexts or --process-output-diagnostics.\n"),
            (["--process-output-context-max", "5", "fix"], "--process-output-context-max can only be used with --process-output-contexts or --process-output-diagnostics.\n"),
            (["--process-output-context-max-bytes", "1000", "fix"], "--process-output-context-max-bytes can only be used with --process-output-contexts or --process-output-diagnostics.\n"),
            (["--process-output-diagnostic-max", "5", "fix"], "--process-output-diagnostic-max can only be used with --process-output-diagnostics.\n"),
            (["--process-output-contexts", "bg-1", "--process-output-diagnostic-max", "5"], "--process-output-diagnostic-max can only be used with --process-output-diagnostics.\n"),
        ]

        for argv, message in cases:
            with self.subTest(argv=argv):
                stdout = io.StringIO()
                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(argv)

                self.assertEqual(exit_code, 2)
                self.assertEqual(stdout.getvalue(), message)
                create_chat_client.assert_not_called()

    def test_main_reports_wait_options_without_wait_process_as_local_flag_error(self) -> None:
        cases = [
            (["--wait-timeout-ms", "2000", "fix"], "--wait-timeout-ms can only be used with --wait-process.\n"),
            (["--wait-max-chars", "2000", "fix"], "--wait-max-chars can only be used with --wait-process.\n"),
            (["--wait-stdout", "ready", "fix"], "--wait-stdout can only be used with --wait-process.\n"),
            (["--wait-stderr", "ready", "fix"], "--wait-stderr can only be used with --wait-process.\n"),
            (["--wait-regex", "fix"], "--wait-regex can only be used with --wait-process.\n"),
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
                self.assertEqual(stdout.getvalue(), expected)
                create_chat_client.assert_not_called()

    def test_main_reports_write_process_stdin_pairing_errors(self) -> None:
        cases = [
            (["--write-stdin", "hello", "fix"], "--write-stdin can only be used with --check-write-process or --write-process.\n"),
            (["--write-stdin-file", "input.txt", "fix"], "--write-stdin-file can only be used with --check-write-process or --write-process.\n"),
            (["--check-write-process", "bg-1", "--write-stdin", "hello", "--write-stdin-file", "input.txt"], "--write-stdin and --write-stdin-file cannot be used together.\n"),
            (["--check-write-process", "bg-1"], "--check-write-process requires --write-stdin or --write-stdin-file.\n"),
            (["--write-process", "bg-1"], "--write-process requires --write-stdin or --write-stdin-file.\n"),
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
                self.assertEqual(stdout.getvalue(), expected)
                create_chat_client.assert_not_called()

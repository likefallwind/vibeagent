import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from vibeagent.cli import main


class CliLocalFlagErrorTests(unittest.TestCase):
    def test_main_reports_command_cwd_without_command_check_as_local_flag_error(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--command-cwd", "src", "fix", "tests"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "--command-cwd can only be used with --command-check or --command.\n")
        create_chat_client.assert_not_called()

    def test_main_reports_start_cwd_without_start_command_as_local_flag_error(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--start-cwd", "src", "fix", "tests"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "--start-cwd can only be used with --check-start-command, --start-command, or --start.\n")
        create_chat_client.assert_not_called()

    def test_main_reports_run_options_without_run_command_as_local_flag_error(self) -> None:
        cases = [
            (["--run-cwd", "src", "fix"], "--run-cwd can only be used with --run-command, --run, --run-commands, or --check-run-commands.\n"),
            (["--run-timeout-ms", "2000", "fix"], "--run-timeout-ms can only be used with --run-command, --run, --run-commands, --run-suggested-checks, --run-focused-tests, or --run-session-verification.\n"),
            (["--run-max-chars", "2000", "fix"], "--run-max-chars can only be used with --run-command, --run, --run-commands, --run-suggested-checks, --run-focused-tests, or --run-session-verification.\n"),
            (["--run-continue-on-failure", "fix"], "--run-continue-on-failure can only be used with --run-commands, --run-suggested-checks, --run-focused-tests, or --run-session-verification.\n"),
            (["--run-output-contexts", "fix"], "--run-output-contexts can only be used with --run-command, --run, --run-commands, --run-suggested-checks, --run-focused-tests, or --run-session-verification.\n"),
            (["--run-output-diagnostics", "fix"], "--run-output-diagnostics can only be used with --run-command, --run, --run-commands, --run-suggested-checks, --run-focused-tests, or --run-session-verification.\n"),
            (["--run-output-context-lines", "2", "fix"], "--run-output-context-lines can only be used with --run-command, --run, --run-commands, --run-suggested-checks, --run-focused-tests, or --run-session-verification.\n"),
            (["--run-output-context-max", "5", "fix"], "--run-output-context-max can only be used with --run-command, --run, --run-commands, --run-suggested-checks, --run-focused-tests, or --run-session-verification.\n"),
            (["--run-output-context-max-bytes", "1000", "fix"], "--run-output-context-max-bytes can only be used with --run-command, --run, --run-commands, --run-suggested-checks, --run-focused-tests, or --run-session-verification.\n"),
            (["--run-output-diagnostic-max", "5", "fix"], "--run-output-diagnostic-max can only be used with --run-command, --run, --run-commands, --run-suggested-checks, --run-focused-tests, or --run-session-verification.\n"),
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

    def test_main_reports_port_and_http_options_without_matching_local_flag(self) -> None:
        cases = [
            (["--port-host", "0.0.0.0", "fix"], "--port-host can only be used with --port-check.\n"),
            (["--port-timeout-ms", "1500", "fix"], "--port-timeout-ms can only be used with --port-check.\n"),
            (["--http-timeout-ms", "1500", "fix"], "--http-timeout-ms can only be used with --http-check or --http-fetch.\n"),
            (["--http-max-body-chars", "1000", "fix"], "--http-max-body-chars can only be used with --http-check or --http-fetch.\n"),
            (["--http-contains", "ready", "fix"], "--http-contains can only be used with --http-check.\n"),
            (["--http-regex", "fix"], "--http-regex can only be used with --http-check.\n"),
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

    def test_main_reports_stash_count_without_stashes_as_local_flag_error(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--stash-count", "3", "fix", "tests"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "--stash-count can only be used with --stashes.\n")
        create_chat_client.assert_not_called()


if __name__ == "__main__":
    unittest.main()

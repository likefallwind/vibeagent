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

    def test_main_reports_blame_lines_without_blame_as_local_flag_error(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--blame-lines", "2:4", "fix", "tests"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "--blame-lines can only be used with --blame.\n")
        create_chat_client.assert_not_called()

    def test_main_reports_show_options_without_show_as_local_flag_error(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--show-path", "app.py", "fix", "tests"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "--show-path can only be used with --show.\n")
        create_chat_client.assert_not_called()

    def test_main_reports_log_count_without_log_as_local_flag_error(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--log-count", "2", "fix", "tests"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "--log-count can only be used with --log.\n")
        create_chat_client.assert_not_called()

    def test_main_reports_read_options_without_matching_local_flag(self) -> None:
        cases = [
            (["--read-lines", "2:4", "fix", "tests"], "--read-lines can only be used with --read.\n"),
            (["--read-max-bytes", "1000", "fix", "tests"], "--read-max-bytes can only be used with --read.\n"),
            (["--read-line-numbers", "fix", "tests"], "--read-line-numbers can only be used with --read.\n"),
            (
                ["--read-files-max-bytes", "1000", "fix", "tests"],
                "--read-files-max-bytes can only be used with --read-files.\n",
            ),
            (
                ["--read-files-line-numbers", "fix", "tests"],
                "--read-files-line-numbers can only be used with --read-files.\n",
            ),
            (
                ["--read-ranges-max-bytes", "1000", "fix", "tests"],
                "--read-ranges-max-bytes can only be used with --read-ranges.\n",
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
                self.assertEqual(stdout.getvalue(), expected)
                create_chat_client.assert_not_called()

    def test_main_reports_around_options_without_matching_local_flag(self) -> None:
        cases = [
            (["--around-lines", "5", "fix", "tests"], "--around-lines can only be used with --around.\n"),
            (["--around-max-bytes", "1000", "fix", "tests"], "--around-max-bytes can only be used with --around.\n"),
            (
                ["--around-many-max-bytes", "1000", "fix", "tests"],
                "--around-many-max-bytes can only be used with --around-many.\n",
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
                self.assertEqual(stdout.getvalue(), expected)
                create_chat_client.assert_not_called()

    def test_main_reports_output_context_options_without_output_contexts_as_local_flag_error(self) -> None:
        cases = [
            (
                ["--output-context-lines", "2", "fix", "tests"],
                "--output-context-lines can only be used with --output-contexts.\n",
            ),
            (
                ["--output-context-max", "5", "fix", "tests"],
                "--output-context-max can only be used with --output-contexts.\n",
            ),
            (
                ["--output-context-max-bytes", "1000", "fix", "tests"],
                "--output-context-max-bytes can only be used with --output-contexts.\n",
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
                self.assertEqual(stdout.getvalue(), expected)
                create_chat_client.assert_not_called()

    def test_main_reports_output_diagnostic_options_without_output_diagnostics_as_local_flag_error(self) -> None:
        cases = [
            (["--output-diagnostic-lines", "3", "fix"], "--output-diagnostic-lines can only be used with --output-diagnostics or --python-traceback.\n"),
            (["--output-diagnostic-max", "5", "fix"], "--output-diagnostic-max can only be used with --output-diagnostics or --python-traceback.\n"),
            (["--output-diagnostic-context-max", "5", "fix"], "--output-diagnostic-context-max can only be used with --output-diagnostics or --python-traceback.\n"),
            (["--output-diagnostic-context-max-bytes", "1000", "fix"], "--output-diagnostic-context-max-bytes can only be used with --output-diagnostics or --python-traceback.\n"),
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

    def test_main_reports_session_output_context_options_without_session_output_contexts_as_local_flag_error(self) -> None:
        cases = [
            (
                ["--session-output-command-max", "3", "fix", "tests"],
                "--session-output-command-max can only be used with --session-output-contexts or --session-output-diagnostics.\n",
            ),
            (
                ["--session-output-max-chars", "4000", "fix", "tests"],
                "--session-output-max-chars can only be used with --session-output-contexts or --session-output-diagnostics.\n",
            ),
            (
                ["--session-output-context-lines", "2", "fix", "tests"],
                "--session-output-context-lines can only be used with --session-output-contexts or --session-output-diagnostics.\n",
            ),
            (
                ["--session-output-context-max", "5", "fix", "tests"],
                "--session-output-context-max can only be used with --session-output-contexts or --session-output-diagnostics.\n",
            ),
            (
                ["--session-output-context-max-bytes", "1000", "fix", "tests"],
                "--session-output-context-max-bytes can only be used with --session-output-contexts or --session-output-diagnostics.\n",
            ),
            (
                ["--session-output-diagnostic-max", "4", "fix", "tests"],
                "--session-output-diagnostic-max can only be used with --session-output-diagnostics.\n",
            ),
            (
                ["--session-output-diagnostic-max", "4", "--session-output-contexts", "run-1"],
                "--session-output-diagnostic-max can only be used with --session-output-diagnostics.\n",
            ),
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

    def test_main_reports_session_limit_options_without_matching_session_view_as_local_flag_error(self) -> None:
        cases = [
            (
                ["--session-transcript-event-max", "3", "fix", "tests"],
                "--session-transcript-event-max can only be used with --transcript.\n",
            ),
            (
                ["--session-search-match-max", "3", "fix", "tests"],
                "--session-search-match-max can only be used with --session-search.\n",
            ),
            (
                ["--session-search-case-sensitive", "fix", "tests"],
                "--session-search-case-sensitive can only be used with --session-search.\n",
            ),
            (
                ["--session-max-checks", "3", "fix", "tests"],
                "--session-max-checks can only be used with --session-verification, --run-session-verification, --session-audit, or --session-handoff.\n",
            ),
            (
                ["--session-max-commands", "3", "fix", "tests"],
                "--session-max-commands can only be used with --session-commands, --session-audit, or --session-handoff.\n",
            ),
            (
                ["--session-max-output-chars", "4000", "fix", "tests"],
                "--session-max-output-chars can only be used with --session-commands or --session-handoff.\n",
            ),
            (
                ["--session-max-output-chars", "4000", "--session-audit", "run-1"],
                "--session-max-output-chars can only be used with --session-commands or --session-handoff.\n",
            ),
            (
                ["--session-max-files", "7", "--session-commands", "run-1"],
                "--session-max-files can only be used with --session-files, --session-audit, or --session-handoff.\n",
            ),
            (
                ["--session-max-failures", "4", "--session-files", "run-1"],
                "--session-max-failures can only be used with --session-failures, --session-audit, or --session-handoff.\n",
            ),
            (
                ["--session-max-text", "120", "--session-commands", "run-1"],
                "--session-max-text can only be used with --transcript, --session-search, --session-failures, --session-audit, or --session-handoff.\n",
            ),
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

    def test_main_reports_tail_options_without_tail_as_local_flag_error(self) -> None:
        cases = [
            (["--tail-lines", "5", "fix", "tests"], "--tail-lines can only be used with --tail.\n"),
            (["--tail-max-bytes", "1000", "fix", "tests"], "--tail-max-bytes can only be used with --tail.\n"),
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

    def test_main_reports_search_path_without_search_as_local_flag_error(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--search-path", "src", "fix", "tests"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "--search-path can only be used with --search or --search-contexts.\n")
        create_chat_client.assert_not_called()


if __name__ == "__main__":
    unittest.main()

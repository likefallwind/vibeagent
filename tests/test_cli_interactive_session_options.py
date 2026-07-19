import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from vibeagent.cli import main


class CliInteractiveSessionOptionsTests(unittest.TestCase):
    def test_main_parses_interactive_session_timeline_limit_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/transcript run-1 --max-events 3 --max-text 120",
                    '/session-search --run run-1 --max-matches 4 --case-sensitive --max-text 140 "Missing config"',
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_transcript_text", return_value="Transcript:\n  session: run-1") as get_transcript_text,
            patch("vibeagent.cli.get_session_search_text", return_value="Session search:\n  session: run-1") as get_session_search_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Transcript:", output)
        self.assertIn("Session search:", output)
        get_transcript_text.assert_called_once_with(run_id="run-1", max_events=3, max_text=120)
        get_session_search_text.assert_called_once_with(
            argument="Missing config",
            run_id="run-1",
            max_matches=4,
            case_sensitive=True,
            max_text=140,
        )
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_session_timeline_limit_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/transcript --max-events nope",
                    "/session-search --max-matches 0 needle",
                    "/session-search --unknown needle",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_transcript_text") as get_transcript_text,
            patch("vibeagent.cli.get_session_search_text") as get_session_search_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /transcript [run-id] [--max-events N] [--max-text N]", output)
        self.assertIn("--max-events must be a positive integer.", output)
        self.assertIn("Usage: /session-search [--run run-id] [--max-matches N] [--case-sensitive] [--max-text N] <query>", output)
        self.assertIn("--max-matches must be a positive integer.", output)
        self.assertIn("Unknown option: --unknown", output)
        get_transcript_text.assert_not_called()
        get_session_search_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_session_output_limit_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/session-output-contexts run-1 --max-commands 2 --max-output-chars 120 --context-lines 0 --max-contexts 3 --max-bytes 1000",
                    "/session-output-diagnostics run-1 --max-commands 4 --max-output-chars 140 --context-lines 1 --max-diagnostics 5 --max-contexts 6 --max-bytes 1200",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_session_output_contexts_text", return_value="Session output contexts:\n  session: run-1") as get_session_output_contexts_text,
            patch("vibeagent.cli.get_session_output_diagnostics_text", return_value="Session output diagnostics:\n  session: run-1") as get_session_output_diagnostics_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Session output contexts:", output)
        self.assertIn("Session output diagnostics:", output)
        get_session_output_contexts_text.assert_called_once_with(
            run_id="run-1",
            max_commands=2,
            max_output_chars=120,
            context_lines=0,
            max_contexts=3,
            max_bytes_per_context=1000,
        )
        get_session_output_diagnostics_text.assert_called_once_with(
            run_id="run-1",
            max_commands=4,
            max_output_chars=140,
            context_lines=1,
            max_diagnostics=5,
            max_contexts=6,
            max_bytes_per_context=1200,
        )
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_session_output_limit_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/session-output-contexts --context-lines -1",
                    "/session-output-diagnostics --max-diagnostics 0",
                    "/session-output-contexts --max-diagnostics 2",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_session_output_contexts_text") as get_session_output_contexts_text,
            patch("vibeagent.cli.get_session_output_diagnostics_text") as get_session_output_diagnostics_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /session-output-contexts [run-id]", output)
        self.assertIn("--context-lines must be a non-negative integer.", output)
        self.assertIn("Usage: /session-output-diagnostics [run-id]", output)
        self.assertIn("--max-diagnostics must be a positive integer.", output)
        self.assertIn("Unknown option: --max-diagnostics", output)
        get_session_output_contexts_text.assert_not_called()
        get_session_output_diagnostics_text.assert_not_called()
        create_chat_client.assert_not_called()


if __name__ == "__main__":
    unittest.main()

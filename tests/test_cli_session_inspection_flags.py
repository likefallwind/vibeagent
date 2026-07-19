import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from vibeagent.cli import main


class CliSessionInspectionFlagTests(unittest.TestCase):
    def test_main_runs_transcript_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_transcript_report", return_value={"session": "run-1", "ok": True}) as get_transcript_report,
                patch("vibeagent.cli.get_transcript_text", return_value="Transcript:\n  session: run-1") as get_transcript_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--cwd",
                        base,
                        "--transcript",
                        "run-1",
                        "--session-transcript-event-max",
                        "3",
                        "--session-max-text",
                        "120",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertIn("Transcript:", stdout.getvalue())
        get_transcript_report.assert_not_called()
        get_transcript_text.assert_called_once_with(Path(base).resolve(), "run-1", max_events=3, max_text=120)
        create_chat_client.assert_not_called()

    def test_main_runs_transcript_json_with_structured_payload(self) -> None:
        report = {"session": "run-1", "exists": True, "ok": True, "events": {"total": 1}}
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_transcript_report", return_value=report) as get_transcript_report,
                patch("vibeagent.cli.get_transcript_text", return_value="unused") as get_transcript_text,
                patch(
                    "vibeagent.cli.format_session_transcript_report_text",
                    return_value="Transcript:\n  session: run-1",
                ) as format_session_transcript_report_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--json",
                        "--cwd",
                        base,
                        "--transcript",
                        "run-1",
                        "--session-transcript-event-max",
                        "3",
                        "--session-max-text",
                        "120",
                    ]
                )

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["sessionTranscript"], report)
        get_transcript_report.assert_called_once_with(Path(base).resolve(), "run-1", max_events=3, max_text=120)
        format_session_transcript_report_text.assert_called_once_with(report)
        get_transcript_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_runs_session_search_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_session_search_report", return_value={"session": "run-1", "ok": True}) as get_session_search_report,
                patch("vibeagent.cli.get_session_search_text", return_value="Session search:\n  session: run-1") as get_session_search_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--cwd",
                        base,
                        "--session-search",
                        " missing config ",
                        "--session-search-run",
                        " run-1 ",
                        "--session-search-match-max",
                        "3",
                        "--session-search-case-sensitive",
                        "--session-max-text",
                        "120",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertIn("Session search:", stdout.getvalue())
        get_session_search_report.assert_not_called()
        get_session_search_text.assert_called_once_with(
            Path(base).resolve(),
            "missing config",
            "run-1",
            max_matches=3,
            max_text=120,
            case_sensitive=True,
        )
        create_chat_client.assert_not_called()

    def test_main_runs_session_search_json_with_structured_payload(self) -> None:
        report = {"session": "run-1", "exists": True, "ok": True, "matches": {"total": 1}}
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_session_search_report", return_value=report) as get_session_search_report,
                patch("vibeagent.cli.get_session_search_text", return_value="unused") as get_session_search_text,
                patch(
                    "vibeagent.cli.format_session_search_report_text",
                    return_value="Session search:\n  session: run-1",
                ) as format_session_search_report_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--json",
                        "--cwd",
                        base,
                        "--session-search",
                        "missing config",
                        "--session-search-run",
                        "run-1",
                        "--session-search-match-max",
                        "3",
                        "--session-search-case-sensitive",
                        "--session-max-text",
                        "120",
                    ]
                )

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["sessionSearch"], report)
        expected_kwargs = {"max_matches": 3, "max_text": 120, "case_sensitive": True}
        get_session_search_report.assert_called_once_with(Path(base).resolve(), "missing config", "run-1", **expected_kwargs)
        format_session_search_report_text.assert_called_once_with(report)
        get_session_search_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_runs_session_commands_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_session_commands_report", return_value={"session": "run-1", "ok": True}) as get_session_commands_report,
                patch("vibeagent.cli.get_session_commands_text", return_value="Command results:\n  session: run-1") as get_session_commands_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--session-commands", "run-1"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Command results:", stdout.getvalue())
        get_session_commands_report.assert_not_called()
        get_session_commands_text.assert_called_once_with(Path(base).resolve(), "run-1")
        create_chat_client.assert_not_called()

    def test_main_runs_session_commands_json_with_structured_payload(self) -> None:
        report = {"session": "run-1", "exists": True, "ok": True, "commands": {"total": 1}}
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_session_commands_report", return_value=report) as get_session_commands_report,
                patch("vibeagent.cli.get_session_commands_text", return_value="unused") as get_session_commands_text,
                patch(
                    "vibeagent.cli.format_session_commands_report_text",
                    return_value="Command results:\n  session: run-1",
                ) as format_session_commands_report_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--session-commands", "run-1", "--session-max-output-chars", "0"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["sessionCommands"], report)
        get_session_commands_report.assert_called_once_with(Path(base).resolve(), "run-1", max_output_chars=0)
        format_session_commands_report_text.assert_called_once_with(report)
        get_session_commands_text.assert_not_called()
        create_chat_client.assert_not_called()


if __name__ == "__main__":
    unittest.main()

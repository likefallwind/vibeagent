import unittest

from vibeagent.command_parsing import LocalCommand, parse_local_command
from vibeagent.command_session_parsing import parse_session_local_command


class CommandSessionParsingTests(unittest.TestCase):
    def test_session_parser_recognizes_session_commands(self) -> None:
        cases = {
            "/rename": LocalCommand(type="rename"),
            "/rename auth work": LocalCommand(type="rename", argument="auth work"),
            "/export": LocalCommand(type="export"),
            "/export reports/session.txt": LocalCommand(type="export", argument="reports/session.txt"),
            "/sessions": LocalCommand(type="sessions"),
            "/last": LocalCommand(type="last"),
            "/plan": LocalCommand(type="plan"),
            "/plan run-1": LocalCommand(type="plan", argument="run-1"),
            "/transcript": LocalCommand(type="transcript"),
            "/transcript run-1": LocalCommand(type="transcript", argument="run-1"),
            "/session-search missing config": LocalCommand(type="session_search", argument="missing config"),
            "/session-search --run run-1 missing config": LocalCommand(type="session_search", argument="--run run-1 missing config"),
            "/session-commands": LocalCommand(type="session_commands"),
            "/session-commands run-1": LocalCommand(type="session_commands", argument="run-1"),
            "/session-output-contexts": LocalCommand(type="session_output_contexts"),
            "/session-output-contexts run-1": LocalCommand(type="session_output_contexts", argument="run-1"),
            "/session-output-diagnostics": LocalCommand(type="session_output_diagnostics"),
            "/session-output-diagnostics run-1": LocalCommand(type="session_output_diagnostics", argument="run-1"),
            "/session-files": LocalCommand(type="session_files"),
            "/session-files run-1": LocalCommand(type="session_files", argument="run-1"),
            "/session-failures": LocalCommand(type="session_failures"),
            "/session-failures run-1": LocalCommand(type="session_failures", argument="run-1"),
            "/session-verification": LocalCommand(type="session_verification"),
            "/session-verification run-1": LocalCommand(type="session_verification", argument="run-1"),
            "/run-session-verification": LocalCommand(type="run_session_verification"),
            "/run-session-verification run-1 --no-failed": LocalCommand(
                type="run_session_verification",
                argument="run-1 --no-failed",
            ),
            "/session-audit": LocalCommand(type="session_audit"),
            "/session-audit run-1": LocalCommand(type="session_audit", argument="run-1"),
            "/session-handoff": LocalCommand(type="session_handoff"),
            "/session-handoff run-1": LocalCommand(type="session_handoff", argument="run-1"),
            "/session": LocalCommand(type="session"),
            "/session run-1": LocalCommand(type="session", argument="run-1"),
        }

        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(parse_session_local_command(raw), expected)
                self.assertEqual(parse_local_command(raw), expected)

    def test_session_parser_ignores_other_commands(self) -> None:
        self.assertIsNone(parse_session_local_command("/checkpoint ckpt-1"))
        self.assertIsNone(parse_session_local_command("session run-1"))


if __name__ == "__main__":
    unittest.main()

import unittest

from vibeagent.command_checkpoint_parsing import parse_checkpoint_local_command
from vibeagent.command_code_intel_parsing import parse_code_intel_local_command
from vibeagent.command_core_parsing import parse_core_local_command
from vibeagent.command_dispatch import LOCAL_COMMAND_PARSERS, parse_delegated_local_command
from vibeagent.command_file_edit_parsing import parse_file_edit_local_command
from vibeagent.command_git_parsing import parse_git_local_command
from vibeagent.command_inspection_parsing import parse_inspection_local_command
from vibeagent.command_json_parsing import parse_json_local_command
from vibeagent.command_parsing import LocalCommand, parse_local_command
from vibeagent.command_process_parsing import parse_process_local_command
from vibeagent.command_review_parsing import parse_review_local_command
from vibeagent.command_runtime_parsing import parse_runtime_local_command
from vibeagent.command_session_parsing import parse_session_local_command


class CommandDispatchTests(unittest.TestCase):
    def test_dispatch_parser_order_is_explicit(self) -> None:
        self.assertEqual(
            LOCAL_COMMAND_PARSERS,
            (
                parse_core_local_command,
                parse_runtime_local_command,
                parse_inspection_local_command,
                parse_code_intel_local_command,
                parse_json_local_command,
                parse_file_edit_local_command,
                parse_git_local_command,
                parse_process_local_command,
                parse_review_local_command,
                parse_session_local_command,
                parse_checkpoint_local_command,
            ),
        )

    def test_dispatch_matches_public_parser_for_representative_commands(self) -> None:
        cases = {
            "/code": LocalCommand(type="code"),
            "/code-deps src": LocalCommand(type="code_deps", argument="src"),
            "/write app.py data": LocalCommand(type="write_file", argument="app.py data"),
            "/git-status": LocalCommand(type="git_status"),
            "/session run-1": LocalCommand(type="session", argument="run-1"),
            "/checkpoint before": LocalCommand(type="checkpoint", argument="before"),
        }

        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(parse_delegated_local_command(raw), expected)
                self.assertEqual(parse_local_command(raw), expected)

    def test_dispatch_returns_none_for_non_commands(self) -> None:
        self.assertIsNone(parse_delegated_local_command("write a script"))


if __name__ == "__main__":
    unittest.main()

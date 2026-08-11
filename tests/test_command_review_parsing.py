import unittest

from vibeagent.command_parsing import LocalCommand, parse_local_command
from vibeagent.command_review_parsing import parse_review_local_command


class CommandReviewParsingTests(unittest.TestCase):
    def test_review_parser_recognizes_review_commands(self) -> None:
        cases = {
            "/status": LocalCommand(type="status"),
            "/context": LocalCommand(type="context"),
            "/init": LocalCommand(type="init"),
            "/init CLAUDE.md": LocalCommand(type="init", argument="CLAUDE.md"),
            "/doctor": LocalCommand(type="doctor"),
            "/review": LocalCommand(type="review"),
            "/review --max-files 1 --max-checks 2": LocalCommand(type="review", argument="--max-files 1 --max-checks 2"),
            "/code-review": LocalCommand(type="code_review"),
            "/code-review high --fix main...feature": LocalCommand(
                type="code_review", argument="high --fix main...feature"
            ),
            "/handoff": LocalCommand(type="handoff"),
            "/handoff --max-files 1 --max-checks 2": LocalCommand(type="handoff", argument="--max-files 1 --max-checks 2"),
            "/changes": LocalCommand(type="changes"),
            "/changes --max-files 1": LocalCommand(type="changes", argument="--max-files 1"),
            "/diff": LocalCommand(type="diff"),
            "/diff --staged app.py": LocalCommand(type="diff", argument="--staged app.py"),
            "/diff-hunks": LocalCommand(type="diff_hunks"),
            "/diff-hunks --staged app.py": LocalCommand(type="diff_hunks", argument="--staged app.py"),
            "/diff-contexts --staged app.py": LocalCommand(type="diff_contexts", argument="--staged app.py"),
        }

        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(parse_review_local_command(raw), expected)
                self.assertEqual(parse_local_command(raw), expected)

    def test_review_parser_ignores_other_commands(self) -> None:
        self.assertIsNone(parse_review_local_command("/session run-1"))
        self.assertIsNone(parse_review_local_command("review"))


if __name__ == "__main__":
    unittest.main()

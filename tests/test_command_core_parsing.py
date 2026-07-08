import unittest

from vibeagent.command_core_parsing import parse_core_local_command
from vibeagent.command_parsing import LocalCommand, parse_local_command


class CommandCoreParsingTests(unittest.TestCase):
    def test_core_parser_recognizes_core_commands(self) -> None:
        cases = {
            "/exit": LocalCommand(type="exit"),
            "/help": LocalCommand(type="help"),
            "/model": LocalCommand(type="model"),
            "/config": LocalCommand(type="config"),
            "/clear": LocalCommand(type="clear"),
            "/usage": LocalCommand(type="usage"),
            "/cost": LocalCommand(type="cost"),
            "/approval": LocalCommand(type="approval"),
            "/approval allow": LocalCommand(type="approval", argument="allow"),
            "/resume": LocalCommand(type="resume"),
            "/resume run-1": LocalCommand(type="resume", argument="run-1"),
            "/resume off": LocalCommand(type="resume", argument="off"),
            "/compact": LocalCommand(type="compact"),
            "/compact run-1": LocalCommand(type="compact", argument="run-1"),
            "/chat": LocalCommand(type="chat"),
            "/chat hello": LocalCommand(type="chat", argument="hello"),
            "/code": LocalCommand(type="code"),
            "/code write a script": LocalCommand(type="code", argument="write a script"),
        }

        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(parse_core_local_command(raw), expected)
                self.assertEqual(parse_local_command(raw), expected)

    def test_core_parser_ignores_other_commands(self) -> None:
        self.assertIsNone(parse_core_local_command("/session run-1"))
        self.assertIsNone(parse_core_local_command("/code-deps src"))
        self.assertIsNone(parse_core_local_command("chat hello"))


if __name__ == "__main__":
    unittest.main()

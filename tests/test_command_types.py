import unittest

from vibeagent import command_parsing, command_types
from vibeagent import commands


class CommandTypesTests(unittest.TestCase):
    def test_command_parsing_reexports_local_command_type(self) -> None:
        self.assertIs(command_parsing.LocalCommand, command_types.LocalCommand)
        self.assertIs(command_parsing.make_local_command, command_types.make_local_command)
        self.assertIs(commands.LocalCommand, command_types.LocalCommand)

    def test_make_local_command_builds_local_command(self) -> None:
        self.assertEqual(
            command_types.make_local_command("checkpoint", "before refactor"),
            command_types.LocalCommand(type="checkpoint", argument="before refactor"),
        )


if __name__ == "__main__":
    unittest.main()

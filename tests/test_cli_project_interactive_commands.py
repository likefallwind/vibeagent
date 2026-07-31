import unittest

from vibeagent import cli_project_interactive_commands, cli_project_local_flags


class CliProjectInteractiveCommandsTests(unittest.TestCase):
    def test_project_local_flags_reexports_interactive_helpers(self) -> None:
        self.assertIs(
            cli_project_local_flags.run_interactive_project_command,
            cli_project_interactive_commands.run_interactive_project_command,
        )
        self.assertIs(
            cli_project_local_flags.run_interactive_project_state_command,
            cli_project_interactive_commands.run_interactive_project_state_command,
        )


if __name__ == "__main__":
    unittest.main()

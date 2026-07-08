import unittest

from vibeagent import command_safety, command_safety_heredoc


class CommandSafetyHeredocTests(unittest.TestCase):
    def test_command_safety_reexports_heredoc_helpers(self) -> None:
        self.assertIs(
            command_safety.interpreter_heredoc_blocked_command_reason,
            command_safety_heredoc.interpreter_heredoc_blocked_command_reason,
        )
        self.assertIs(command_safety.shell_heredoc_script, command_safety_heredoc.shell_heredoc_script)


if __name__ == "__main__":
    unittest.main()

import unittest

from vibeagent import command_safety_shell, command_safety_wrappers


class CommandSafetyWrappersTests(unittest.TestCase):
    def test_shell_module_reexports_wrapper_helpers(self) -> None:
        self.assertIs(command_safety_shell.shell_command_segments, command_safety_wrappers.shell_command_segments)
        self.assertIs(
            command_safety_shell.unwrapped_shell_command_parts,
            command_safety_wrappers.unwrapped_shell_command_parts,
        )
        self.assertIs(command_safety_shell.shell_pipeline_segments, command_safety_wrappers.shell_pipeline_segments)


if __name__ == "__main__":
    unittest.main()

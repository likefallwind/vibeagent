import unittest

from vibeagent import cli_code_intel_interactive
from vibeagent import cli_code_intel_local_flags


class CliCodeIntelModuleTests(unittest.TestCase):
    def test_local_flags_reexports_interactive_code_intel_command_runner(self) -> None:
        self.assertIs(
            cli_code_intel_local_flags.run_interactive_code_intel_command,
            cli_code_intel_interactive.run_interactive_code_intel_command,
        )


if __name__ == "__main__":
    unittest.main()

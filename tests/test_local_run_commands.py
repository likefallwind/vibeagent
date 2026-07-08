import unittest

from vibeagent import local_run_commands, local_runtime_commands


class LocalRunCommandsTests(unittest.TestCase):
    def test_local_runtime_commands_reexports_run_helpers(self) -> None:
        self.assertIs(local_runtime_commands.get_run_text, local_run_commands.get_run_text)
        self.assertIs(local_runtime_commands.get_run_report, local_run_commands.get_run_report)
        self.assertIs(local_runtime_commands.get_run_sequence_text, local_run_commands.get_run_sequence_text)
        self.assertIs(local_runtime_commands.get_run_sequence_report, local_run_commands.get_run_sequence_report)
        self.assertIs(local_runtime_commands.parse_run_sequence_request, local_run_commands.parse_run_sequence_request)
        self.assertIs(local_runtime_commands.get_check_run_sequence_text, local_run_commands.get_check_run_sequence_text)
        self.assertIs(local_runtime_commands.get_check_run_sequence_report, local_run_commands.get_check_run_sequence_report)


if __name__ == "__main__":
    unittest.main()

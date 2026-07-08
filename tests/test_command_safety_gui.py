import unittest

from vibeagent.command_safety import get_blocked_command_reason


class CommandSafetyGuiTests(unittest.TestCase):
    def test_blocks_powershell_start_alias_for_file_explorer_targets(self) -> None:
        commands = [
            "powershell.exe -NoProfile -Command start .",
            "pwsh -NoProfile -Command start .",
            'powershell -Command "start ."',
            "powershell Start .",
            "powershell -Command start file:///tmp",
        ]
        for command in commands:
            with self.subTest(command=command):
                self.assertIn("GUI application launch", get_blocked_command_reason(command) or "")

    def test_allows_non_gui_powershell_start_prefixed_commands(self) -> None:
        self.assertIsNone(get_blocked_command_reason("powershell -Command start-sleep 1"))


if __name__ == "__main__":
    unittest.main()

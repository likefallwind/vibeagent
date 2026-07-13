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

    def test_blocks_powershell_start_process_alias_for_gui_targets(self) -> None:
        commands = [
            "powershell -Command saps .",
            "pwsh -Command saps http://127.0.0.1:5173",
        ]
        for command in commands:
            with self.subTest(command=command):
                self.assertIn("GUI application launch", get_blocked_command_reason(command) or "")

    def test_blocks_windows_start_for_gui_executables(self) -> None:
        commands = [
            'cmd.exe /c start "" notepad.exe',
            'cmd.exe /c start "Editor" notepad.exe',
            'cmd.exe /c start "Browser" /wait chrome http://127.0.0.1:5173',
            'cmd.exe /c start "" /d . msedge.exe http://127.0.0.1:5173',
            "cmd.exe /c start chrome http://127.0.0.1:5173",
            "cmd.exe /c start msedge.exe http://127.0.0.1:5173",
            "powershell -Command start notepad.exe",
            "pwsh -Command start msedge http://127.0.0.1:5173",
        ]
        for command in commands:
            with self.subTest(command=command):
                self.assertIn("GUI application launch", get_blocked_command_reason(command) or "")

    def test_allows_windows_start_for_non_gui_executables(self) -> None:
        self.assertIsNone(get_blocked_command_reason("cmd.exe /c start npm test"))
        self.assertIsNone(get_blocked_command_reason("cmd.exe /c start /wait npm test"))


if __name__ == "__main__":
    unittest.main()

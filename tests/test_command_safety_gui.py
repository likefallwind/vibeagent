import base64
import unittest

from vibeagent.command_safety import get_blocked_command_reason
from vibeagent.command_safety_powershell_gui import powershell_invocation_launches_gui


class CommandSafetyGuiTests(unittest.TestCase):
    def _powershell_encoded_command(self, payload: str) -> str:
        encoded = base64.b64encode(payload.encode("utf-16le")).decode("ascii")
        return f"powershell -EncodedCommand {encoded}"

    def _powershell_inline_encoded_command(self, option: str, payload: str) -> str:
        encoded = base64.b64encode(payload.encode("utf-16le")).decode("ascii")
        return f"powershell {option}:{encoded}"

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

    def test_blocks_powershell_expression_gui_targets(self) -> None:
        commands = [
            "powershell -Command \"iex 'explorer.exe .'\"",
            "powershell -Command \"Invoke-Expression 'xdg-open .'\"",
            "pwsh -Command \"iex 'start .'\"",
            "powershell -Command iex 'explorer.exe .'",
        ]
        for command in commands:
            with self.subTest(command=command):
                self.assertIn("GUI application launch", get_blocked_command_reason(command) or "")

    def test_allows_powershell_expression_non_gui_payload(self) -> None:
        self.assertIsNone(get_blocked_command_reason("powershell -Command \"iex 'Write-Output ok'\""))

    def test_blocks_powershell_thread_job_gui_targets(self) -> None:
        commands = [
            "powershell -Command \"Start-ThreadJob { xdg-open . }\"",
            "pwsh -Command \"Start-ThreadJob -ScriptBlock { explorer.exe . }\"",
            "powershell -Command \"ThreadJob { start . }\"",
        ]
        for command in commands:
            with self.subTest(command=command):
                self.assertIn("GUI application launch", get_blocked_command_reason(command) or "")

    def test_allows_powershell_thread_job_non_gui_payload(self) -> None:
        self.assertIsNone(get_blocked_command_reason("powershell -Command \"Start-ThreadJob { python -V }\""))

    def test_blocks_powershell_encoded_gui_targets(self) -> None:
        commands = [
            self._powershell_encoded_command("explorer.exe ."),
            self._powershell_encoded_command("xdg-open ."),
            self._powershell_encoded_command("Start-ThreadJob { xdg-open . }"),
        ]
        for command in commands:
            with self.subTest(command=command):
                self.assertIn("GUI application launch", get_blocked_command_reason(command) or "")

    def test_allows_powershell_encoded_non_gui_payload(self) -> None:
        self.assertIsNone(get_blocked_command_reason(self._powershell_encoded_command("Write-Output ok")))

    def test_blocks_powershell_inline_command_gui_targets(self) -> None:
        commands = [
            "powershell -c:xdg-open .",
            "powershell /c:start .",
            "powershell /Command:Start-ThreadJob { xdg-open . }",
        ]
        for command in commands:
            with self.subTest(command=command):
                self.assertIn("GUI application launch", get_blocked_command_reason(command) or "")

    def test_allows_powershell_inline_command_non_gui_payload(self) -> None:
        self.assertIsNone(get_blocked_command_reason("powershell -Command:Write-Output ok"))

    def test_blocks_powershell_inline_encoded_gui_targets(self) -> None:
        commands = [
            self._powershell_inline_encoded_command("-EncodedCommand", "explorer.exe ."),
            self._powershell_inline_encoded_command("-enc", "xdg-open ."),
            self._powershell_inline_encoded_command("/EncodedCommand", "Start-ThreadJob { xdg-open . }"),
        ]
        for command in commands:
            with self.subTest(command=command):
                self.assertIn("GUI application launch", get_blocked_command_reason(command) or "")

    def test_powershell_gui_detection_uses_nested_command_callback(self) -> None:
        calls: list[str] = []

        def nested_command_launches_gui(command: str) -> bool:
            calls.append(command)
            return command == "custom-gui ."

        self.assertTrue(
            powershell_invocation_launches_gui(
                ["-Command", "Start-ThreadJob { custom-gui . }"],
                nested_command_launches_gui,
            )
        )
        self.assertEqual(calls, ["Start-ThreadJob { custom-gui . }", "custom-gui ."])

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

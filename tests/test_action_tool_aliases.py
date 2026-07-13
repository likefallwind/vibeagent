from __future__ import annotations

import unittest

from vibeagent.action_parsing import parse_tool_action
from vibeagent.types import RunCommandAction, StartCommandAction


class ActionToolAliasTests(unittest.TestCase):
    def test_claude_bash_timeout_maps_to_run_command_timeout_ms(self) -> None:
        action = parse_tool_action(
            "Bash",
            {
                "command": "python -m unittest",
                "timeout": 10_000,
                "max_output_chars": 4_000,
            },
        )

        self.assertIsInstance(action, RunCommandAction)
        self.assertEqual(action.timeout_ms, 10_000)
        self.assertEqual(action.max_output_chars, 4_000)

    def test_claude_bash_background_ignores_sync_only_options(self) -> None:
        action = parse_tool_action(
            "Bash",
            {
                "command": "python -m http.server",
                "run_in_background": True,
                "timeout": 10_000,
                "timeout_ms": 20_000,
                "max_output_chars": 4_000,
            },
        )

        self.assertIsInstance(action, StartCommandAction)
        self.assertEqual(action.command, "python -m http.server")


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest

from vibeagent import (
    workflow_commands,
    workflow_diff_commands,
    workflow_diff_hunk_commands,
    workflow_diff_utils,
    workflow_plain_diff_commands,
)


class WorkflowDiffCommandsTests(unittest.TestCase):
    def test_workflow_commands_reexports_diff_utils_compatibly(self) -> None:
        self.assertIs(workflow_diff_commands.parse_diff_argument, workflow_diff_utils.parse_diff_argument)
        self.assertIs(workflow_diff_commands.clip_with_flag, workflow_diff_utils.clip_with_flag)
        self.assertIs(workflow_diff_commands.validate_diff_hunks_limits, workflow_diff_utils.validate_diff_hunks_limits)
        self.assertIs(
            workflow_diff_commands.validate_diff_contexts_limits,
            workflow_diff_utils.validate_diff_contexts_limits,
        )
        self.assertIs(workflow_commands.parse_diff_argument, workflow_diff_commands.parse_diff_argument)
        self.assertIs(workflow_commands.clip_with_flag, workflow_diff_commands.clip_with_flag)
        self.assertIs(workflow_diff_commands.get_diff_report, workflow_plain_diff_commands.get_diff_report)
        self.assertIs(workflow_diff_commands.get_diff_text, workflow_plain_diff_commands.get_diff_text)
        self.assertIs(workflow_diff_commands.format_diff_report_text, workflow_plain_diff_commands.format_diff_report_text)
        self.assertIs(workflow_diff_commands.get_diff_hunks_report, workflow_diff_hunk_commands.get_diff_hunks_report)
        self.assertIs(workflow_diff_commands.get_diff_hunks_text, workflow_diff_hunk_commands.get_diff_hunks_text)
        self.assertIs(
            workflow_diff_commands.format_diff_hunks_report_text,
            workflow_diff_hunk_commands.format_diff_hunks_report_text,
        )
        self.assertIs(workflow_diff_commands.serialize_diff_hunk, workflow_diff_hunk_commands.serialize_diff_hunk)
        self.assertIs(workflow_diff_commands.format_diff_hunk_lines, workflow_diff_hunk_commands.format_diff_hunk_lines)

    def test_diff_utils_keep_validation_behavior(self) -> None:
        self.assertEqual(workflow_diff_utils.parse_diff_argument("--staged app.py"), (True, "app.py"))
        self.assertEqual(workflow_diff_utils.parse_diff_argument("app.py"), (False, "app.py"))
        self.assertIsNone(workflow_diff_utils.parse_diff_argument("--bad"))
        self.assertEqual(workflow_diff_utils.clip_with_flag("abcdef", 3), ("abc\n[diff output truncated]", True))
        self.assertIn(
            "max_hunks must be at least 1",
            workflow_diff_utils.validate_diff_hunks_limits("Usage: x", 0, 1) or "",
        )


if __name__ == "__main__":
    unittest.main()

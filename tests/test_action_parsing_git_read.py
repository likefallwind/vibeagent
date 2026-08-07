from __future__ import annotations

import unittest

from vibeagent.action_parsing import parse_tool_action
from vibeagent.action_parsing_git import GIT_ACTION_TYPES
from vibeagent.action_parsing_git_read import GIT_READ_ACTION_TYPES, parse_git_read_action
from vibeagent.types import GitBlameAction, GitDiffContextsAction, GitShowAction


class ActionParsingGitReadTests(unittest.TestCase):
    def test_git_parser_keeps_read_action_types_registered(self) -> None:
        self.assertLessEqual(GIT_READ_ACTION_TYPES, GIT_ACTION_TYPES)
        self.assertIsNone(parse_git_read_action("git_stage", {"paths": ["app.py"]}, "raw"))

    def test_parse_git_diff_contexts_keeps_limits(self) -> None:
        action = parse_tool_action(
            "git_diff_contexts",
            {
                "path": "src/app.py",
                "staged": True,
                "context_lines": 2,
                "max_hunks": 3,
                "max_bytes_per_context": 1000,
            },
        )

        self.assertIsInstance(action, GitDiffContextsAction)
        self.assertEqual(action.path, "src/app.py")
        self.assertTrue(action.staged)
        self.assertEqual(action.context_lines, 2)
        self.assertEqual(action.max_hunks, 3)
        self.assertEqual(action.max_bytes_per_context, 1000)

    def test_parse_git_show_strips_revision(self) -> None:
        action = parse_tool_action("git_show", {"rev": " HEAD~1 ", "path": "app.py", "max_output_chars": 1000})

        self.assertIsInstance(action, GitShowAction)
        self.assertEqual(action.rev, "HEAD~1")
        self.assertEqual(action.path, "app.py")
        self.assertEqual(action.max_output_chars, 1000)

    def test_parse_git_blame_keeps_line_window(self) -> None:
        action = parse_tool_action(
            "git_blame",
            {"path": " app.py ", "start_line": 2, "line_count": 4, "max_output_chars": 1000},
        )

        self.assertIsInstance(action, GitBlameAction)
        self.assertEqual(action.path, "app.py")
        self.assertEqual(action.start_line, 2)
        self.assertEqual(action.line_count, 4)
        self.assertEqual(action.max_output_chars, 1000)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest

from vibeagent.action_parsing import parse_tool_action
from vibeagent.action_parsing_read import READ_ACTION_TYPES
from vibeagent.action_parsing_read_navigation import READ_NAVIGATION_ACTION_TYPES, parse_read_navigation_action
from vibeagent.types import ListTreeAction, RepoMapAction


class ActionParsingReadNavigationTests(unittest.TestCase):
    def test_read_parser_keeps_navigation_action_types_registered(self) -> None:
        self.assertLessEqual(READ_NAVIGATION_ACTION_TYPES, READ_ACTION_TYPES)
        self.assertIsNotNone(parse_read_navigation_action("list_files", {}, "raw"))

    def test_parse_list_tree_normalizes_ignore_patterns(self) -> None:
        action = parse_tool_action(
            "list_tree",
            {"path": "src", "max_depth": 2, "max_entries": 10, "ignore": [" __pycache__ ", "*.pyc"]},
        )

        self.assertIsInstance(action, ListTreeAction)
        self.assertEqual(action.path, "src")
        self.assertEqual(action.max_depth, 2)
        self.assertEqual(action.max_entries, 10)
        self.assertEqual(action.ignore, ("__pycache__", "*.pyc"))

    def test_parse_repo_map_keeps_limits(self) -> None:
        action = parse_tool_action("repo_map", {"path": "src", "max_depth": 4, "max_files": 20, "max_symbols": 30})

        self.assertIsInstance(action, RepoMapAction)
        self.assertEqual(action.path, "src")
        self.assertEqual(action.max_depth, 4)
        self.assertEqual(action.max_files, 20)
        self.assertEqual(action.max_symbols, 30)


if __name__ == "__main__":
    unittest.main()

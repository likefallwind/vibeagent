from __future__ import annotations

import unittest

from vibeagent.action_parsing import parse_tool_action
from vibeagent.action_parsing_project import PROJECT_ACTION_TYPES
from vibeagent.action_parsing_project_tests import PROJECT_TEST_ACTION_TYPES, parse_project_test_action
from vibeagent.types import RelatedTestsAction, RunFocusedTestCommandsAction, RunSuggestedChecksAction


class ActionParsingProjectTestsTests(unittest.TestCase):
    def test_project_parser_keeps_test_action_types_registered(self) -> None:
        self.assertLessEqual(PROJECT_TEST_ACTION_TYPES, PROJECT_ACTION_TYPES)
        self.assertIsNone(parse_project_test_action("project_overview", {}, "raw"))

    def test_parse_related_tests_strips_paths(self) -> None:
        action = parse_tool_action(
            "related_tests",
            {"paths": [" app.py ", "tests/test_app.py"], "max_paths": 3, "max_candidates": 4},
        )

        self.assertEqual(
            action,
            RelatedTestsAction(
                type="related_tests",
                paths=["app.py", "tests/test_app.py"],
                max_paths=3,
                max_candidates=4,
            ),
        )

    def test_parse_run_suggested_checks_keeps_runtime_options(self) -> None:
        action = parse_tool_action(
            "run_suggested_checks",
            {
                "max_commands": 2,
                "timeout_ms": 1000,
                "max_output_chars": 2000,
                "stop_on_failure": False,
                "extract_output_contexts": True,
                "extract_output_diagnostics": True,
                "context_lines": 3,
                "max_diagnostics": 4,
                "max_contexts": 5,
                "max_bytes_per_context": 6000,
            },
        )

        self.assertEqual(
            action,
            RunSuggestedChecksAction(
                type="run_suggested_checks",
                max_commands=2,
                timeout_ms=1000,
                max_output_chars=2000,
                stop_on_failure=False,
                extract_output_contexts=True,
                extract_output_diagnostics=True,
                context_lines=3,
                max_diagnostics=4,
                max_contexts=5,
                max_bytes_per_context=6000,
            ),
        )

    def test_parse_run_focused_test_commands_keeps_paths_and_runtime_options(self) -> None:
        action = parse_tool_action(
            "run_focused_test_commands",
            {
                "paths": ["pkg/app.py"],
                "max_paths": 7,
                "max_candidates": 8,
                "max_commands": 9,
                "timeout_ms": 1000,
                "max_output_chars": 2000,
                "stop_on_failure": False,
                "max_bytes_per_context": 3000,
            },
        )

        self.assertEqual(
            action,
            RunFocusedTestCommandsAction(
                type="run_focused_test_commands",
                paths=["pkg/app.py"],
                max_paths=7,
                max_candidates=8,
                max_commands=9,
                timeout_ms=1000,
                max_output_chars=2000,
                stop_on_failure=False,
                extract_output_contexts=False,
                extract_output_diagnostics=False,
                context_lines=5,
                max_diagnostics=50,
                max_contexts=20,
                max_bytes_per_context=3000,
            ),
        )


if __name__ == "__main__":
    unittest.main()

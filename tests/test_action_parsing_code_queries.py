from __future__ import annotations

import unittest

from vibeagent.action_parsing import parse_tool_action
from vibeagent.action_parsing_code_intel import CODE_INTEL_ACTION_TYPES, parse_code_intel_action
from vibeagent.action_parsing_code_queries import CODE_QUERY_ACTION_TYPES, parse_code_query_action
from vibeagent.types import CodeDefinitionsAction, CodeDependenciesAction, CodeReferenceContextsAction, CodeReferencesAction


class ActionParsingCodeQueriesTests(unittest.TestCase):
    def test_code_intel_parser_keeps_query_action_types_registered(self) -> None:
        self.assertLessEqual(CODE_QUERY_ACTION_TYPES, CODE_INTEL_ACTION_TYPES)
        self.assertIsNone(parse_code_query_action("python_calls", {"symbol": "run_agent"}, "raw"))

    def test_code_query_helper_matches_code_intel_entrypoint(self) -> None:
        payload = {"symbol": " runAgent ", "path": "src", "max_matches": 3}

        helper = parse_code_query_action("code_references", payload, "raw")
        entrypoint = parse_code_intel_action("code_references", payload, "raw")

        self.assertEqual(helper, entrypoint)
        self.assertEqual(entrypoint, CodeReferencesAction(type="code_references", symbol="runAgent", path="src", max_matches=3))

    def test_parse_code_dependencies_keeps_limits(self) -> None:
        action = parse_tool_action("code_dependencies", {"path": "pkg", "max_files": 4, "max_imports": 5})

        self.assertEqual(
            action,
            CodeDependenciesAction(type="code_dependencies", path="pkg", max_files=4, max_imports=5),
        )

    def test_parse_code_reference_contexts_keeps_context_limits(self) -> None:
        action = parse_tool_action(
            "code_reference_contexts",
            {
                "symbol": "runAgent",
                "path": "src",
                "max_matches": 6,
                "context_lines": 7,
                "max_bytes_per_context": 8000,
            },
        )

        self.assertEqual(
            action,
            CodeReferenceContextsAction(
                type="code_reference_contexts",
                symbol="runAgent",
                path="src",
                max_matches=6,
                context_lines=7,
                max_bytes_per_context=8000,
            ),
        )

    def test_parse_code_definitions_keeps_line_limit(self) -> None:
        action = parse_tool_action("code_definitions", {"symbol": "runAgent", "max_matches": 9, "max_lines": 10})

        self.assertEqual(
            action,
            CodeDefinitionsAction(type="code_definitions", symbol="runAgent", path=None, max_matches=9, max_lines=10),
        )


if __name__ == "__main__":
    unittest.main()

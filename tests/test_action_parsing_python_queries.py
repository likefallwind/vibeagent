from __future__ import annotations

import unittest

from vibeagent.action_parsing import parse_tool_action
from vibeagent.action_parsing_code_intel import CODE_INTEL_ACTION_TYPES, parse_code_intel_action
from vibeagent.action_parsing_python_queries import PYTHON_QUERY_ACTION_TYPES, parse_python_query_action
from vibeagent.types import (
    PythonCallGraphAction,
    PythonDefinitionsAction,
    PythonDependenciesAction,
    PythonReferenceContextsAction,
)


class ActionParsingPythonQueriesTests(unittest.TestCase):
    def test_code_intel_parser_keeps_python_query_action_types_registered(self) -> None:
        self.assertLessEqual(PYTHON_QUERY_ACTION_TYPES, CODE_INTEL_ACTION_TYPES)
        self.assertIsNone(parse_python_query_action("code_references", {"symbol": "run_agent"}, "raw"))

    def test_python_query_helper_matches_code_intel_entrypoint(self) -> None:
        payload = {"symbol": " run_agent ", "path": "pkg", "max_matches": 3, "max_lines": 4}

        helper = parse_python_query_action("python_definitions", payload, "raw")
        entrypoint = parse_code_intel_action("python_definitions", payload, "raw")

        self.assertEqual(helper, entrypoint)
        self.assertEqual(
            entrypoint,
            PythonDefinitionsAction(type="python_definitions", symbol="run_agent", path="pkg", max_matches=3, max_lines=4),
        )

    def test_parse_python_dependencies_keeps_limits(self) -> None:
        action = parse_tool_action("python_dependencies", {"path": "pkg", "max_files": 5, "max_imports": 6})

        self.assertEqual(
            action,
            PythonDependenciesAction(type="python_dependencies", path="pkg", max_files=5, max_imports=6),
        )

    def test_parse_python_call_graph_keeps_limits(self) -> None:
        action = parse_tool_action("python_call_graph", {"path": "pkg", "max_files": 7, "max_edges": 8})

        self.assertEqual(
            action,
            PythonCallGraphAction(type="python_call_graph", path="pkg", max_files=7, max_edges=8),
        )

    def test_parse_python_reference_contexts_keeps_context_limits(self) -> None:
        action = parse_tool_action(
            "python_reference_contexts",
            {
                "symbol": "run_agent",
                "path": "pkg",
                "max_matches": 9,
                "context_lines": 10,
                "max_bytes_per_context": 11_000,
            },
        )

        self.assertEqual(
            action,
            PythonReferenceContextsAction(
                type="python_reference_contexts",
                symbol="run_agent",
                path="pkg",
                max_matches=9,
                context_lines=10,
                max_bytes_per_context=11_000,
            ),
        )


if __name__ == "__main__":
    unittest.main()

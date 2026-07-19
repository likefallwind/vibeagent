from __future__ import annotations

import argparse
import unittest

from vibeagent.cli_code_intel_kwargs import (
    build_code_rename_kwargs,
    build_code_symbol_kwargs,
    build_python_call_graph_kwargs,
    build_python_deps_kwargs,
    build_python_rename_kwargs,
    build_python_symbol_kwargs,
    build_replace_python_definition_kwargs,
)


class CliCodeIntelKwargsTests(unittest.TestCase):
    def test_python_kwargs_preserve_bounds_and_path_mappings(self) -> None:
        args = argparse.Namespace(
            python_deps_max_files=7,
            python_deps_max_imports=8,
            python_max_matches=5,
            python_def_max_lines=40,
            python_context_lines=2,
            python_context_max_bytes=900,
            python_call_graph_max_files=3,
            python_call_graph_max_edges=4,
            python_path="src",
        )

        self.assertEqual(build_python_deps_kwargs(args), {"max_files": 7, "max_imports": 8})
        self.assertEqual(build_python_symbol_kwargs(args, include_max_lines=True), {"max_matches": 5, "max_lines": 40})
        self.assertEqual(
            build_python_symbol_kwargs(args, include_context=True),
            {"max_matches": 5, "context_lines": 2, "max_bytes_per_context": 900},
        )
        self.assertEqual(build_python_call_graph_kwargs(args), {"max_files": 3, "max_edges": 4})
        self.assertEqual(
            build_python_rename_kwargs(args, ["old_name", "new_name"]),
            {"symbol": "old_name", "new_name": "new_name", "path": "src"},
        )
        self.assertEqual(
            build_replace_python_definition_kwargs(args, ["Runner.run", "def run():\n    return 1\n"]),
            {"symbol": "Runner.run", "content": "def run():\n    return 1\n", "path": "src"},
        )

    def test_code_kwargs_preserve_bounds_and_rename_mappings(self) -> None:
        args = argparse.Namespace(
            code_max_matches=6,
            code_def_max_lines=50,
            code_context_lines=3,
            code_context_max_bytes=1000,
            code_path="web",
        )

        self.assertEqual(build_code_symbol_kwargs(args, include_max_lines=True), {"max_matches": 6, "max_lines": 50})
        self.assertEqual(
            build_code_symbol_kwargs(args, include_context=True),
            {"max_matches": 6, "context_lines": 3, "max_bytes_per_context": 1000},
        )
        self.assertEqual(
            build_code_rename_kwargs(args, ["runAgent", "executeAgent"]),
            {"symbol": "runAgent", "new_name": "executeAgent", "path": "web"},
        )


if __name__ == "__main__":
    unittest.main()

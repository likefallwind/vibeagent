from __future__ import annotations

import argparse
import unittest

from vibeagent.cli_read_kwargs import (
    build_find_files_kwargs,
    build_output_context_kwargs,
    build_output_diagnostic_kwargs,
    build_read_files_kwargs,
    build_read_kwargs,
    build_search_kwargs,
)


class CliReadKwargsTests(unittest.TestCase):
    def test_search_kwargs_preserve_cli_flag_mapping(self) -> None:
        args = argparse.Namespace(
            search_max_matches=5,
            search_regex=True,
            search_ignore_case=True,
            search_context_lines=2,
            search_context_max_bytes=800,
        )

        self.assertEqual(
            build_search_kwargs(args),
            {
                "max_matches": 5,
                "regex": True,
                "case_sensitive": False,
                "context_lines": 2,
            },
        )
        self.assertEqual(
            build_search_kwargs(args, include_context_bytes=True),
            {
                "max_matches": 5,
                "regex": True,
                "case_sensitive": False,
                "context_lines": 2,
                "max_bytes_per_context": 800,
            },
        )

    def test_find_files_kwargs_skip_falsey_options_and_keep_true_flags(self) -> None:
        args = argparse.Namespace(
            find_files_path="src",
            find_files_max_matches=None,
            find_files_regex=False,
            find_files_case_sensitive=True,
            find_files_include_dirs=True,
        )

        self.assertEqual(
            build_find_files_kwargs(args),
            {"path": "src", "case_sensitive": True, "include_dirs": True},
        )

    def test_read_kwargs_preserve_line_number_defaults(self) -> None:
        self.assertEqual(
            build_read_kwargs(argparse.Namespace(read_max_bytes=1000, read_line_numbers=True)),
            {"max_bytes": 1000, "show_line_numbers": True},
        )
        self.assertEqual(
            build_read_files_kwargs(argparse.Namespace(read_files_max_bytes=None, read_files_line_numbers=False)),
            {},
        )

    def test_output_analysis_kwargs_preserve_explicit_defaults(self) -> None:
        args = argparse.Namespace(
            output_context_lines=2,
            output_context_max=3,
            output_context_max_bytes=400,
            output_diagnostic_lines=4,
            output_diagnostic_max=5,
            output_diagnostic_context_max=6,
            output_diagnostic_context_max_bytes=700,
        )

        self.assertEqual(
            build_output_context_kwargs(args),
            {"context_lines": 2, "max_contexts": 3, "max_bytes_per_context": 400},
        )
        self.assertEqual(
            build_output_diagnostic_kwargs(args),
            {
                "context_lines": 4,
                "max_diagnostics": 5,
                "max_contexts": 6,
                "max_bytes_per_context": 700,
            },
        )


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest

from vibeagent.cli_parse_read import (
    parse_interactive_output_analysis_argument,
    parse_interactive_read_argument,
    parse_interactive_read_files_argument,
    parse_interactive_symbols_argument,
    parse_interactive_tail_argument,
    parse_interactive_tree_argument,
)
from vibeagent.cli_parse_read_paths import parse_interactive_read_path_options


class CliParseReadPathTests(unittest.TestCase):
    def test_parse_read_path_options_returns_unquoted_paths_and_kwargs(self) -> None:
        self.assertEqual(
            parse_interactive_read_path_options(
                "--line-numbers=false --max-bytes=200 -- a.py 'dir/b file.py'",
                "Usage",
                "max_bytes_per_file",
                "at least one path is required.",
            ),
            (
                ["a.py", "dir/b file.py"],
                {"show_line_numbers": False, "max_bytes_per_file": 200},
                None,
                True,
            ),
        )

    def test_parse_read_path_options_keeps_plain_arguments_unhandled(self) -> None:
        self.assertEqual(
            parse_interactive_read_path_options(
                "src/app.py",
                "Usage",
                "max_bytes",
                "path is required.",
            ),
            (None, {}, None, False),
        )

    def test_parse_read_path_options_reports_boolean_and_required_errors(self) -> None:
        paths, kwargs, error, handled = parse_interactive_read_path_options(
            "--line-numbers=maybe -- src/app.py",
            "Usage",
            "max_bytes",
            "path is required.",
        )
        self.assertEqual((paths, kwargs, handled), (None, {}, True))
        self.assertIn("--line-numbers must be a boolean.", error or "")

        paths, kwargs, error, handled = parse_interactive_read_path_options(
            "--line-numbers",
            "Usage",
            "max_bytes",
            "path is required.",
        )
        self.assertEqual((paths, kwargs, handled), (None, {}, True))
        self.assertIn("path is required.", error or "")

    def test_parse_read_path_options_rejects_duplicate_options(self) -> None:
        paths, kwargs, error, handled = parse_interactive_read_path_options(
            "--max-bytes 100 --max-bytes=200 -- src/app.py",
            "Usage",
            "max_bytes",
            "path is required.",
        )
        self.assertEqual((paths, kwargs, handled), (None, {}, True))
        self.assertIn("provide --max-bytes at most once.", error or "")

        paths, kwargs, error, handled = parse_interactive_read_path_options(
            "--line-numbers --line-numbers=false -- src/app.py",
            "Usage",
            "max_bytes",
            "path is required.",
        )
        self.assertEqual((paths, kwargs, handled), (None, {}, True))
        self.assertIn("provide --line-numbers at most once.", error or "")

    def test_read_entrypoints_preserve_existing_return_shapes(self) -> None:
        self.assertEqual(
            parse_interactive_read_argument(
                "--line-numbers --max-bytes 80 -- src/app.py 10:12"
            ),
            ("src/app.py 10:12", {"show_line_numbers": True, "max_bytes": 80}, None, True),
        )
        self.assertEqual(
            parse_interactive_read_files_argument(
                "--line-numbers=false --max-bytes=200 -- a.py b.py"
            ),
            (["a.py", "b.py"], {"show_line_numbers": False, "max_bytes_per_file": 200}, None, True),
        )

    def test_read_related_parsers_reject_duplicate_options(self) -> None:
        _, kwargs, error, handled = parse_interactive_output_analysis_argument(
            "--context-lines 1 --context-lines=2 -- output.py:3 failed",
            "Usage: /output-contexts [--context-lines N] -- <text>",
        )
        self.assertTrue(handled)
        self.assertEqual(kwargs, {})
        self.assertIn("provide --context-lines at most once.", error or "")

        _, kwargs, error, handled = parse_interactive_tail_argument(
            "--max-bytes 100 --max-bytes=200 -- logs/app.log"
        )
        self.assertTrue(handled)
        self.assertEqual(kwargs, {})
        self.assertIn("provide --max-bytes at most once.", error or "")

        _, kwargs, error, handled = parse_interactive_tree_argument(
            "--max-depth 1 --max-depth=2 src"
        )
        self.assertTrue(handled)
        self.assertEqual(kwargs, {})
        self.assertIn("provide --max-depth at most once.", error or "")

        _, kwargs, error, handled = parse_interactive_symbols_argument(
            "--max-symbols 10 --max-symbols=20 -- src/app.py"
        )
        self.assertTrue(handled)
        self.assertEqual(kwargs, {})
        self.assertIn("provide --max-symbols at most once.", error or "")


if __name__ == "__main__":
    unittest.main()

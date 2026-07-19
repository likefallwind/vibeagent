from __future__ import annotations

import unittest

from vibeagent.cli_parse_discovery import (
    parse_interactive_find_files_argument,
    parse_interactive_search_argument,
)
from vibeagent.cli_parse_discovery_queries import parse_interactive_query_argument


class CliParseDiscoveryQueryTests(unittest.TestCase):
    def test_parse_query_argument_accepts_value_and_boolean_options(self) -> None:
        self.assertEqual(
            parse_interactive_query_argument(
                "--path src --regex --max-matches=4 -- app",
                usage="Usage",
                value_options={
                    "--path": ("path", "string"),
                    "--max-matches": ("max_matches", "positive"),
                },
                bool_options={"--regex": ("regex", True)},
            ),
            ("app", {"path": "src", "regex": True, "max_matches": 4}, None, True),
        )

    def test_parse_query_argument_preserves_unhandled_plain_text(self) -> None:
        self.assertEqual(
            parse_interactive_query_argument(
                "plain query",
                usage="Usage",
                value_options={"--path": ("path", "string")},
                bool_options={"--regex": ("regex", True)},
            ),
            (None, {}, None, False),
        )

    def test_parse_query_argument_reports_bool_value_and_missing_query(self) -> None:
        query, kwargs, error, handled = parse_interactive_query_argument(
            "--regex=true -- app",
            usage="Usage",
            value_options={},
            bool_options={"--regex": ("regex", True)},
        )
        self.assertEqual((query, kwargs, handled), (None, {}, True))
        self.assertIn("--regex does not take a value.", error or "")

        query, kwargs, error, handled = parse_interactive_query_argument(
            "--path src",
            usage="Usage",
            value_options={"--path": ("path", "string")},
            bool_options={},
        )
        self.assertEqual((query, kwargs, handled), (None, {}, True))
        self.assertIn("query is required.", error or "")

    def test_discovery_query_entrypoints_preserve_existing_shapes(self) -> None:
        self.assertEqual(
            parse_interactive_search_argument(
                "--path vibeagent --regex --context-lines 2 --max-bytes 100 -- TODO",
                include_max_bytes=True,
            ),
            (
                "TODO",
                {
                    "path": "vibeagent",
                    "regex": True,
                    "context_lines": 2,
                    "max_bytes_per_context": 100,
                },
                None,
                True,
            ),
        )
        self.assertEqual(
            parse_interactive_find_files_argument(
                "--path src --max-matches 5 --regex --case-sensitive "
                "--include-dirs -- app.+"
            ),
            (
                "app.+",
                {
                    "path": "src",
                    "max_matches": 5,
                    "regex": True,
                    "case_sensitive": True,
                    "include_dirs": True,
                },
                None,
                True,
            ),
        )


if __name__ == "__main__":
    unittest.main()

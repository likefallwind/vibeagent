from __future__ import annotations

import unittest

from vibeagent import cli_parsing
from vibeagent.cli_parse_discovery import (
    parse_interactive_commands_argument,
    parse_interactive_option_limit_argument as discovery_parse_option_limit_argument,
)
from vibeagent.cli_parse_option_limits import parse_interactive_option_limit_argument


class CliParseOptionLimitTests(unittest.TestCase):
    def test_discovery_and_compat_modules_reexport_option_limit_parser(self) -> None:
        self.assertIs(discovery_parse_option_limit_argument, parse_interactive_option_limit_argument)
        self.assertIs(cli_parsing.parse_interactive_option_limit_argument, parse_interactive_option_limit_argument)

    def test_parse_option_limit_argument_accepts_space_and_equals_values(self) -> None:
        self.assertEqual(
            parse_interactive_option_limit_argument(
                "--max-files 3 --max-items=4",
                "Usage",
                {"--max-files": "max_files", "--max-items": "max_items"},
            ),
            ({"max_files": 3, "max_items": 4}, None, True),
        )

    def test_parse_option_limit_argument_reports_unhandled_and_invalid_values(self) -> None:
        self.assertEqual(
            parse_interactive_option_limit_argument(
                None,
                "Usage",
                {"--max-files": "max_files"},
            ),
            ({}, None, False),
        )
        self.assertEqual(
            parse_interactive_option_limit_argument(
                "plain",
                "Usage",
                {"--max-files": "max_files"},
            ),
            ({}, "Usage", True),
        )

        kwargs, error, handled = parse_interactive_option_limit_argument(
            "--max-files 0",
            "Usage",
            {"--max-files": "max_files"},
        )
        self.assertEqual((kwargs, handled), ({}, True))
        self.assertIn("--max-files must be a positive integer.", error or "")

    def test_commands_entrypoint_keeps_existing_shape(self) -> None:
        self.assertEqual(
            parse_interactive_commands_argument("--max-commands 2 --max-files=3"),
            ({"max_commands": 2, "max_files": 3}, None, True),
        )


if __name__ == "__main__":
    unittest.main()

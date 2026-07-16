from __future__ import annotations

import unittest

from vibeagent.process_request_parsing import (
    parse_positive_decimal,
    parse_single_quoted_argument,
    split_process_argument,
    validate_max_output_chars,
)


class ProcessRequestParsingTests(unittest.TestCase):
    def test_split_process_argument_handles_shell_quotes_and_shape_errors(self) -> None:
        self.assertEqual(split_process_argument("bg-1 'hello world'", max_parts=2, too_many_message="too many"), ["bg-1", "hello world"])
        self.assertEqual(split_process_argument("   ", max_parts=2, too_many_message="too many"), [])

        with self.assertRaisesRegex(ValueError, "too many"):
            split_process_argument("bg-1 2000 extra", max_parts=2, too_many_message="too many")
        with self.assertRaises(ValueError):
            split_process_argument("'unterminated", max_parts=2, too_many_message="too many")

    def test_parse_positive_decimal_rejects_non_decimal_values(self) -> None:
        self.assertEqual(parse_positive_decimal("1200", "max chars"), 1200)

        with self.assertRaisesRegex(ValueError, "invalid max chars: 1.2"):
            parse_positive_decimal("1.2", "max chars")
        with self.assertRaisesRegex(ValueError, "invalid max chars: -1"):
            parse_positive_decimal("-1", "max chars")

    def test_validate_max_output_chars_allows_inheritance_and_bounds(self) -> None:
        validate_max_output_chars(None)
        validate_max_output_chars(1_000)
        validate_max_output_chars(50_000)

        with self.assertRaisesRegex(ValueError, "at least 1000"):
            validate_max_output_chars(999)
        with self.assertRaisesRegex(ValueError, "at most 50000"):
            validate_max_output_chars(50_001)

    def test_parse_single_quoted_argument_unquotes_only_one_complete_argument(self) -> None:
        self.assertEqual(parse_single_quoted_argument("'hello world'"), "hello world")
        self.assertEqual(parse_single_quoted_argument('"hello world"'), "hello world")
        self.assertEqual(parse_single_quoted_argument("hello world"), "hello world")
        self.assertEqual(parse_single_quoted_argument("'unterminated"), "'unterminated")
        self.assertEqual(parse_single_quoted_argument("'hello' 'world'"), "'hello' 'world'")


if __name__ == "__main__":
    unittest.main()

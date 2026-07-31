import unittest

from vibeagent.check_limit_parsing import (
    parse_named_suggested_checks_limit,
    parse_suggested_checks_limit,
    parse_suggested_checks_limit_parts,
)


class CheckLimitParsingTests(unittest.TestCase):
    def test_parse_suggested_checks_limit_accepts_positional_and_named_limits(self) -> None:
        self.assertEqual(parse_suggested_checks_limit("2"), 2)
        self.assertEqual(parse_suggested_checks_limit("--max-checks 2"), 2)
        self.assertEqual(parse_suggested_checks_limit("--max-checks=3"), 3)
        self.assertEqual(parse_suggested_checks_limit("-- 4"), 4)
        self.assertEqual(parse_suggested_checks_limit("", default=5), 5)
        self.assertEqual(parse_suggested_checks_limit(None, default=6), 6)

    def test_parse_suggested_checks_limit_reports_named_option_errors(self) -> None:
        with self.assertRaisesRegex(ValueError, "--max-checks requires a value"):
            parse_suggested_checks_limit("--max-checks")
        with self.assertRaisesRegex(ValueError, "--max-checks must be an integer"):
            parse_suggested_checks_limit("--max-checks two")
        with self.assertRaisesRegex(ValueError, "Unknown option: --bad"):
            parse_suggested_checks_limit("--bad")
        with self.assertRaisesRegex(ValueError, "provide --max-checks at most once"):
            parse_suggested_checks_limit("--max-checks 1 --max-checks 2")
        with self.assertRaisesRegex(ValueError, "provide either --max-checks or trailing max"):
            parse_suggested_checks_limit("--max-checks 1 2")

    def test_parse_suggested_checks_limit_reports_positional_limit_errors(self) -> None:
        with self.assertRaisesRegex(ValueError, "expected at most one max command count"):
            parse_suggested_checks_limit("1 2")
        with self.assertRaisesRegex(ValueError, "max must be an integer"):
            parse_suggested_checks_limit("two")
        with self.assertRaisesRegex(ValueError, "max must be at least 1"):
            parse_suggested_checks_limit("0")
        with self.assertRaisesRegex(ValueError, "max must be at most 10"):
            parse_suggested_checks_limit("11")

    def test_parse_suggested_checks_limit_parts_separates_named_and_positional_values(self) -> None:
        self.assertEqual(parse_suggested_checks_limit_parts(["--max-checks", "2"]), (2, []))
        self.assertEqual(parse_suggested_checks_limit_parts(["--max-checks=3"]), (3, []))
        self.assertEqual(parse_suggested_checks_limit_parts(["4"]), (None, ["4"]))
        self.assertEqual(parse_suggested_checks_limit_parts(["--", "5"]), (None, ["5"]))

    def test_parse_named_suggested_checks_limit_reports_missing_or_non_integer_values(self) -> None:
        self.assertEqual(parse_named_suggested_checks_limit("2"), 2)
        with self.assertRaisesRegex(ValueError, "--max-checks requires a value"):
            parse_named_suggested_checks_limit(None)
        with self.assertRaisesRegex(ValueError, "--max-checks must be an integer"):
            parse_named_suggested_checks_limit("two")

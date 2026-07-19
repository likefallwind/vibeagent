import unittest

from vibeagent import action_parsing_helpers, action_parsing_scalars


class ActionParsingScalarsTests(unittest.TestCase):
    def test_action_parsing_helpers_reexports_scalar_parsing_helpers(self) -> None:
        self.assertIs(action_parsing_helpers.ActionParseError, action_parsing_scalars.ActionParseError)
        self.assertIs(action_parsing_helpers.INT_STRING_PATTERN, action_parsing_scalars.INT_STRING_PATTERN)
        self.assertIs(action_parsing_helpers.coerce_int, action_parsing_scalars.coerce_int)
        self.assertIs(action_parsing_helpers.parse_optional_positive_int, action_parsing_scalars.parse_optional_positive_int)
        self.assertIs(action_parsing_helpers.parse_optional_nonnegative_int, action_parsing_scalars.parse_optional_nonnegative_int)
        self.assertIs(action_parsing_helpers.parse_nonnegative_int, action_parsing_scalars.parse_nonnegative_int)

    def test_coerce_int_accepts_integral_numbers_and_grouped_strings(self) -> None:
        self.assertEqual(action_parsing_scalars.coerce_int(12), 12)
        self.assertEqual(action_parsing_scalars.coerce_int(12.0), 12)
        self.assertEqual(action_parsing_scalars.coerce_int("1_200"), 1200)
        self.assertEqual(action_parsing_scalars.coerce_int("1,200.0"), 1200)
        self.assertIsNone(action_parsing_scalars.coerce_int(True))
        self.assertIsNone(action_parsing_scalars.coerce_int(12.5))
        self.assertIsNone(action_parsing_scalars.coerce_int("1.5"))

    def test_parse_integer_helpers_validate_bounds_and_keep_raw_input(self) -> None:
        self.assertIsNone(action_parsing_scalars.parse_optional_positive_int(None, "limit", "{}", maximum=10))
        self.assertEqual(action_parsing_scalars.parse_optional_positive_int("10", "limit", "{}", maximum=10), 10)
        self.assertEqual(action_parsing_scalars.parse_optional_nonnegative_int("0", "offset", "{}", maximum=10), 0)
        self.assertEqual(action_parsing_scalars.parse_nonnegative_int(0, "offset", "{}", maximum=10), 0)

        with self.assertRaises(action_parsing_scalars.ActionParseError) as raised:
            action_parsing_scalars.parse_optional_positive_int("0", "limit", '{"limit": 0}', maximum=10)

        self.assertEqual(raised.exception.raw, '{"limit": 0}')
        self.assertEqual(str(raised.exception), "limit must be a positive integer.")

    def test_parse_integer_helpers_reject_values_above_maximum(self) -> None:
        with self.assertRaisesRegex(action_parsing_scalars.ActionParseError, "limit must be at most 10"):
            action_parsing_scalars.parse_nonnegative_int(11, "limit", "{}", maximum=10)


if __name__ == "__main__":
    unittest.main()

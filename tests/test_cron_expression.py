from __future__ import annotations

import os
import time
import unittest
from unittest.mock import patch

from vibeagent.cron_expression import (
    CronExpressionError,
    cron_matches,
    next_scheduled_time,
    one_shot_fire_time,
    parse_cron_expression,
    recurring_fire_time,
)


def local_timestamp(year: int, month: int, day: int, hour: int, minute: int) -> float:
    return time.mktime((year, month, day, hour, minute, 0, -1, -1, -1))


class CronExpressionTests(unittest.TestCase):
    def test_parses_standard_lists_ranges_steps_and_sunday_seven(self) -> None:
        expression = parse_cron_expression("1,15,30 9-17/2 */3 1,6,12 1-5,7")

        self.assertEqual(expression.minute.values, frozenset({1, 15, 30}))
        self.assertEqual(expression.hour.values, frozenset({9, 11, 13, 15, 17}))
        self.assertIn(1, expression.day_of_month.values)
        self.assertIn(31, expression.day_of_month.values)
        self.assertEqual(expression.month.values, frozenset({1, 6, 12}))
        self.assertEqual(expression.day_of_week.values, frozenset({0, 1, 2, 3, 4, 5}))

    def test_rejects_names_extended_syntax_bad_ranges_and_zero_steps(self) -> None:
        invalid = (
            "0 9 * JAN *",
            "0 9 L * *",
            "0 9 ? * *",
            "0 25 * * *",
            "0 9 * * 6-2",
            "*/0 * * * *",
            "0 9 * *",
        )
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(CronExpressionError):
                parse_cron_expression(value)

    def test_day_of_month_and_day_of_week_use_vixie_or_semantics(self) -> None:
        expression = parse_cron_expression("0 9 15 * 1")
        monday_not_fifteenth = local_timestamp(2026, 6, 8, 9, 0)
        fifteenth_not_monday = local_timestamp(2026, 8, 15, 9, 0)
        neither = local_timestamp(2026, 8, 16, 9, 0)

        self.assertTrue(cron_matches(expression, monday_not_fifteenth))
        self.assertTrue(cron_matches(expression, fifteenth_not_monday))
        self.assertFalse(cron_matches(expression, neither))

    def test_next_time_is_strictly_after_input_and_uses_local_time(self) -> None:
        expression = parse_cron_expression("30 14 15 3 *")
        before = local_timestamp(2026, 3, 15, 14, 29)

        result = next_scheduled_time(expression, before)

        self.assertEqual(time.localtime(result)[:5], (2026, 3, 15, 14, 30))
        self.assertGreater(result, before)

    def test_jitter_is_deterministic_and_within_documented_bounds(self) -> None:
        hourly = parse_cron_expression("0 * * * *")
        five_minutes = parse_cron_expression("*/5 * * * *")
        base = local_timestamp(2026, 8, 10, 10, 0)

        hourly_fire = recurring_fire_time("abcdef12", hourly, base)
        frequent_fire = recurring_fire_time("abcdef12", five_minutes, base)
        one_shot_fire = one_shot_fire_time("abcdef12", hourly, base)

        self.assertEqual(hourly_fire, recurring_fire_time("abcdef12", hourly, base))
        self.assertLessEqual(hourly_fire - base, 30 * 60)
        self.assertLessEqual(frequent_fire - base, 150)
        self.assertGreaterEqual(one_shot_fire, base - 90)
        self.assertLessEqual(one_shot_fire, base)
        self.assertEqual(one_shot_fire_time("abcdef12", parse_cron_expression("3 * * * *"), base + 180), base + 180)


if __name__ == "__main__":
    unittest.main()

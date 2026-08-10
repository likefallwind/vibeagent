from __future__ import annotations

from dataclasses import dataclass
import hashlib
import time


class CronExpressionError(ValueError):
    pass


@dataclass(frozen=True)
class CronField:
    values: frozenset[int]
    wildcard: bool


@dataclass(frozen=True)
class CronExpression:
    source: str
    minute: CronField
    hour: CronField
    day_of_month: CronField
    month: CronField
    day_of_week: CronField


_FIELD_SPECS = (
    ("minute", 0, 59, False),
    ("hour", 0, 23, False),
    ("day-of-month", 1, 31, False),
    ("month", 1, 12, False),
    ("day-of-week", 0, 7, True),
)
_MAX_SEARCH_MINUTES = 8 * 366 * 24 * 60


def parse_cron_expression(value: str) -> CronExpression:
    parts = value.split()
    if len(parts) != 5:
        raise CronExpressionError("expected five fields: minute hour day-of-month month day-of-week")
    fields = [
        _parse_field(part, label, minimum, maximum, sunday_seven)
        for part, (label, minimum, maximum, sunday_seven) in zip(parts, _FIELD_SPECS)
    ]
    return CronExpression(" ".join(parts), *fields)


def cron_matches(expression: CronExpression, timestamp: float) -> bool:
    local = time.localtime(timestamp)
    if local.tm_min not in expression.minute.values or local.tm_hour not in expression.hour.values:
        return False
    if local.tm_mon not in expression.month.values:
        return False
    day_of_week = (local.tm_wday + 1) % 7
    dom_match = local.tm_mday in expression.day_of_month.values
    dow_match = day_of_week in expression.day_of_week.values
    if not expression.day_of_month.wildcard and not expression.day_of_week.wildcard:
        return dom_match or dow_match
    return dom_match and dow_match


def next_scheduled_time(expression: CronExpression, after_timestamp: float) -> float:
    candidate = (int(after_timestamp) // 60 + 1) * 60
    for _ in range(_MAX_SEARCH_MINUTES):
        if cron_matches(expression, candidate):
            return float(candidate)
        candidate += 60
    raise CronExpressionError("no matching time was found within eight years")


def recurring_fire_time(
    task_id: str,
    expression: CronExpression,
    scheduled_timestamp: float,
) -> float:
    following = next_scheduled_time(expression, scheduled_timestamp)
    interval = max(60, int(following - scheduled_timestamp))
    maximum = min(30 * 60, interval // 2)
    return scheduled_timestamp + _stable_offset(task_id, maximum)


def one_shot_fire_time(task_id: str, expression: CronExpression, scheduled_timestamp: float) -> float:
    local = time.localtime(scheduled_timestamp)
    if local.tm_min not in {0, 30}:
        return scheduled_timestamp
    return scheduled_timestamp - _stable_offset(task_id, 90)


def _stable_offset(task_id: str, maximum: int) -> int:
    if maximum <= 0:
        return 0
    digest = hashlib.sha256(task_id.encode("ascii", errors="ignore")).digest()
    return int.from_bytes(digest[:8], "big") % (maximum + 1)


def _parse_field(
    text: str,
    label: str,
    minimum: int,
    maximum: int,
    sunday_seven: bool,
) -> CronField:
    if not text or any(character.isalpha() for character in text):
        raise CronExpressionError(f"{label} contains unsupported syntax")
    wildcard = text == "*"
    values: set[int] = set()
    for item in text.split(","):
        if not item:
            raise CronExpressionError(f"{label} contains an empty list item")
        base, step = _split_step(item, label)
        if base == "*":
            start, end = minimum, maximum
        elif "-" in base:
            bounds = base.split("-")
            if len(bounds) != 2:
                raise CronExpressionError(f"{label} has an invalid range")
            start = _field_int(bounds[0], label, minimum, maximum)
            end = _field_int(bounds[1], label, minimum, maximum)
            if start > end:
                raise CronExpressionError(f"{label} range start must not exceed its end")
        else:
            start = _field_int(base, label, minimum, maximum)
            end = maximum if step is not None else start
        stride = step or 1
        values.update(range(start, end + 1, stride))
    if sunday_seven and 7 in values:
        values.remove(7)
        values.add(0)
    if not values:
        raise CronExpressionError(f"{label} does not select any values")
    return CronField(frozenset(values), wildcard)


def _split_step(item: str, label: str) -> tuple[str, int | None]:
    parts = item.split("/")
    if len(parts) == 1:
        return item, None
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise CronExpressionError(f"{label} has an invalid step")
    try:
        step = int(parts[1])
    except ValueError as error:
        raise CronExpressionError(f"{label} step must be an integer") from error
    if step <= 0:
        raise CronExpressionError(f"{label} step must be positive")
    return parts[0], step


def _field_int(value: str, label: str, minimum: int, maximum: int) -> int:
    try:
        number = int(value)
    except ValueError as error:
        raise CronExpressionError(f"{label} value must be an integer") from error
    if number < minimum or number > maximum:
        raise CronExpressionError(f"{label} value must be between {minimum} and {maximum}")
    return number


__all__ = [
    "CronExpression",
    "CronExpressionError",
    "cron_matches",
    "next_scheduled_time",
    "one_shot_fire_time",
    "parse_cron_expression",
    "recurring_fire_time",
]

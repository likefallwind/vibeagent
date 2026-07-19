from __future__ import annotations

import math
import re
from typing import Any


INT_STRING_PATTERN = re.compile(r"^\d+(?:[_,]\d+)*(?:\.0+)?$")


class ActionParseError(ValueError):
    def __init__(self, message: str, raw: str):
        super().__init__(message)
        self.raw = raw


def coerce_int(value: Any) -> int | None:
    if type(value) is int:
        return value
    if type(value) is float and math.isfinite(value) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        stripped = value.strip()
        if not INT_STRING_PATTERN.fullmatch(stripped):
            return None
        normalized = stripped.replace("_", "").replace(",", "")
        if normalized.isdigit():
            return int(normalized)
        whole, _fraction = normalized.split(".", 1)
        return int(whole)
    return None


def parse_optional_positive_int(value: Any, name: str, raw: str, maximum: int | None) -> int | None:
    if value is None:
        return None
    parsed = coerce_int(value)
    if parsed is None or parsed < 1:
        raise ActionParseError(f"{name} must be a positive integer.", raw)
    if maximum is not None and parsed > maximum:
        raise ActionParseError(f"{name} must be at most {maximum}.", raw)
    return parsed


def parse_optional_nonnegative_int(value: Any, name: str, raw: str, maximum: int | None) -> int | None:
    if value is None:
        return None
    parsed = coerce_int(value)
    if parsed is None or parsed < 0:
        raise ActionParseError(f"{name} must be a non-negative integer.", raw)
    if maximum is not None and parsed > maximum:
        raise ActionParseError(f"{name} must be at most {maximum}.", raw)
    return parsed


def parse_nonnegative_int(value: Any, name: str, raw: str, maximum: int | None) -> int:
    parsed = coerce_int(value)
    if parsed is None or parsed < 0:
        raise ActionParseError(f"{name} must be a non-negative integer.", raw)
    if maximum is not None and parsed > maximum:
        raise ActionParseError(f"{name} must be at most {maximum}.", raw)
    return parsed

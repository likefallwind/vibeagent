from __future__ import annotations

import argparse
import re


MIN_AUTOCOMPACT_TOKENS = 100_000
MAX_AUTOCOMPACT_TOKENS = 1_000_000
ESTIMATED_CHARS_PER_TOKEN = 4
AUTOCOMPACT_TOKEN_RESERVE = 20_000
_TOKEN_VALUE_PATTERN = re.compile(r"^(\d+)([kKmM]?)$")


def parse_autocompact_tokens(value: str) -> int:
    normalized = value.strip()
    if normalized.lower() == "auto":
        return 0
    match = _TOKEN_VALUE_PATTERN.fullmatch(normalized)
    if match is None:
        raise argparse.ArgumentTypeError(_autocompact_usage())
    amount = int(match.group(1))
    suffix = match.group(2).lower()
    if suffix == "k":
        tokens = amount * 1_000
    elif suffix == "m":
        tokens = amount * 1_000_000
    elif 100 <= amount <= 1_000:
        tokens = amount * 1_000
    else:
        tokens = amount
    if not MIN_AUTOCOMPACT_TOKENS <= tokens <= MAX_AUTOCOMPACT_TOKENS:
        raise argparse.ArgumentTypeError(_autocompact_usage())
    return tokens


def autocompact_char_threshold(token_limit: int | None, default: int) -> int:
    if token_limit is None:
        return default
    message_tokens = max(1, token_limit - AUTOCOMPACT_TOKEN_RESERVE)
    return message_tokens * ESTIMATED_CHARS_PER_TOKEN


def resolve_autocompact_tokens(value: int | None) -> int | None:
    return value or None


def estimate_message_tokens(character_count: int) -> int:
    return max(0, (character_count + ESTIMATED_CHARS_PER_TOKEN - 1) // ESTIMATED_CHARS_PER_TOKEN)


def format_autocompact_setting(token_limit: int | None) -> str:
    if token_limit is None:
        return "auto"
    if token_limit == 1_000_000:
        return "1m"
    if token_limit % 1_000 == 0:
        return f"{token_limit // 1_000}k"
    return str(token_limit)


def _autocompact_usage() -> str:
    return "must be 'auto' or between 100k and 1M tokens (for example 500k, 200000, or 200)"


__all__ = [
    "MAX_AUTOCOMPACT_TOKENS",
    "MIN_AUTOCOMPACT_TOKENS",
    "AUTOCOMPACT_TOKEN_RESERVE",
    "autocompact_char_threshold",
    "estimate_message_tokens",
    "format_autocompact_setting",
    "parse_autocompact_tokens",
    "resolve_autocompact_tokens",
]

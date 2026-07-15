from __future__ import annotations

import argparse
from collections.abc import Sequence
import json

from .process_request_parsing import validate_max_output_chars


def parse_executable_flag_values(values: Sequence[str], flag: str) -> tuple[str, str | None]:
    if len(values) not in (1, 2):
        raise ValueError(f"{flag} expects PATH and optional true|false.")
    return values[0], values[1] if len(values) == 2 else None


def parse_multi_edit_flag_values(values: Sequence[str], flag: str) -> tuple[str, list[str]]:
    if len(values) < 3:
        raise ValueError(f"{flag} expects PATH and at least one OLD NEW pair.")
    if (len(values) - 1) % 2 != 0:
        raise ValueError(f"{flag} expects OLD NEW pairs after PATH.")
    return values[0], list(values[1:])


def parse_cli_json_value(value: str) -> object:
    try:
        return json.loads(value)
    except json.JSONDecodeError as error:
        raise ValueError(f"JSON value is invalid: {error.msg}") from error


def build_focused_tests_kwargs(args: argparse.Namespace) -> dict[str, int]:
    kwargs: dict[str, int] = {}
    if args.focused_tests_max_paths is not None:
        kwargs["max_paths"] = args.focused_tests_max_paths
    if args.focused_tests_max_candidates is not None:
        kwargs["max_candidates"] = args.focused_tests_max_candidates
    if args.focused_tests_max_commands is not None:
        kwargs["max_commands"] = args.focused_tests_max_commands
    return kwargs


def positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be a positive integer") from error
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def nonnegative_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be a non-negative integer") from error
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be a non-negative integer")
    return parsed


def timeout_ms(value: str) -> int:
    parsed = positive_int(value)
    if parsed < 100:
        raise argparse.ArgumentTypeError("must be at least 100")
    return parsed


def parse_interactive_positive_option(flag: str, value: str | None) -> tuple[int | None, str | None]:
    if value is None:
        return None, f"{flag} requires a value."
    try:
        return positive_int(value), None
    except argparse.ArgumentTypeError as error:
        return None, f"{flag} {error}."


def parse_interactive_max_chars_option(flag: str, value: str | None) -> tuple[int | None, str | None]:
    parsed, error = parse_interactive_positive_option(flag, value)
    if error or parsed is None:
        return parsed, error
    try:
        validate_max_output_chars(parsed)
    except ValueError as validation_error:
        return None, str(validation_error)
    return parsed, None


def parse_interactive_nonnegative_option(flag: str, value: str | None) -> tuple[int | None, str | None]:
    if value is None:
        return None, f"{flag} requires a value."
    try:
        return nonnegative_int(value), None
    except argparse.ArgumentTypeError as error:
        return None, f"{flag} {error}."


def parse_interactive_timeout_option(flag: str, value: str | None) -> tuple[int | None, str | None]:
    if value is None:
        return None, f"{flag} requires a value."
    try:
        return timeout_ms(value), None
    except argparse.ArgumentTypeError as error:
        return None, f"{flag} {error}."

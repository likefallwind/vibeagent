from __future__ import annotations

import argparse
from collections.abc import Sequence


def normalize_auto_mode_command_arguments(argv: Sequence[str]) -> list[str]:
    values = list(argv)
    if len(values) < 2 or values[0] != "auto-mode":
        return values
    command = values[1]
    if command not in {"defaults", "config"}:
        return values
    normalized = [f"--auto-mode-{command}"]
    index = 2
    while index < len(values):
        value = values[index]
        if value == "--label" and index + 1 < len(values):
            normalized.extend(["--auto-mode-label", values[index + 1]])
            index += 2
            continue
        normalized.append(value)
        index += 1
    return normalized


def add_auto_mode_arguments(
    parser: argparse.ArgumentParser,
    local: argparse._MutuallyExclusiveGroup,
) -> None:
    local.add_argument(
        "--auto-mode-defaults",
        action="store_true",
        help="Show built-in auto mode classifier rules without contacting a provider.",
    )
    local.add_argument(
        "--auto-mode-config",
        action="store_true",
        help="Show effective trusted auto mode configuration without contacting a provider.",
    )
    parser.add_argument(
        "--auto-mode-label",
        metavar="PREFIX",
        help="Filter auto mode rules by a case-insensitive label prefix.",
    )


__all__ = ["add_auto_mode_arguments", "normalize_auto_mode_command_arguments"]

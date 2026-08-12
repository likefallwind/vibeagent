from __future__ import annotations

import argparse
from collections.abc import Sequence


def normalize_auto_mode_command_arguments(argv: Sequence[str]) -> list[str]:
    values = list(argv)
    if not values or values[0] != "auto-mode":
        return values
    if len(values) < 2:
        return ["--auto-mode-command-error", "auto-mode requires a subcommand."]
    command = values[1]
    if command not in {"defaults", "config", "critique", "reset"}:
        return [
            "--auto-mode-command-error",
            f"Unknown auto-mode subcommand: {command}.",
        ]
    normalized = [f"--auto-mode-{command}"]
    index = 2
    while index < len(values):
        value = values[index]
        if value == "--label" and index + 1 < len(values):
            normalized.extend(["--auto-mode-label", values[index + 1]])
            index += 2
            continue
        if value == "--yes":
            normalized.append("--auto-mode-yes")
            index += 1
            continue
        normalized.append(value)
        index += 1
    return normalized


def add_auto_mode_arguments(
    parser: argparse.ArgumentParser,
    local: argparse._MutuallyExclusiveGroup,
) -> None:
    parser.add_argument(
        "--auto-mode-command-error",
        help=argparse.SUPPRESS,
    )
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
    local.add_argument(
        "--auto-mode-critique",
        action="store_true",
        help="Ask the configured model to critique custom auto mode classifier rules.",
    )
    local.add_argument(
        "--auto-mode-reset",
        action="store_true",
        help="Remove autoMode from user settings after confirmation.",
    )
    parser.add_argument(
        "--auto-mode-label",
        metavar="PREFIX",
        help="Filter auto mode rules by a case-insensitive label prefix.",
    )
    parser.add_argument(
        "--auto-mode-yes",
        action="store_true",
        help="Skip confirmation for auto-mode reset.",
    )


__all__ = ["add_auto_mode_arguments", "normalize_auto_mode_command_arguments"]

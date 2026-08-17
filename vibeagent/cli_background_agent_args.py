from __future__ import annotations

import argparse
from collections.abc import Sequence

from .cli_management_command_args import (
    extract_trailing_global_options,
    management_command_index,
)


BACKGROUND_AGENT_COMMAND_NAMES = frozenset(
    {"agents", "attach", "kill", "logs", "remote-control", "respawn", "rm", "stop"}
)


def add_background_agent_local_arguments(
    local: argparse._MutuallyExclusiveGroup,
) -> None:
    local.add_argument(
        "--background-agents",
        action="store_true",
        help="List project-local background coding agents and exit.",
    )
    local.add_argument(
        "--active-background-agents",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    local.add_argument(
        "--agent-view",
        action="store_true",
        help="Open the interactive full-screen background agent dashboard.",
    )
    local.add_argument(
        "--remote-control",
        nargs="?",
        const=True,
        default=None,
        metavar="NAME",
        help="Serve an authenticated browser control plane, optionally with a session name.",
    )
    local.add_argument(
        "--background-agent-log",
        metavar="ID",
        help="Show bounded stdout and stderr for one background coding agent and exit.",
    )
    local.add_argument(
        "--stop-background-agent",
        metavar="ID",
        help="Stop one running background coding agent and exit.",
    )
    local.add_argument(
        "--attach-background-agent",
        metavar="ID",
        help="Attach to one background coding agent in this terminal.",
    )
    local.add_argument(
        "--send-background-agent",
        nargs=2,
        metavar=("ID", "MESSAGE"),
        help="Queue a follow-up message and respawn the background coding agent if needed.",
    )
    local.add_argument(
        "--respawn-background-agent",
        metavar="ID",
        help="Restart one background coding agent from its recorded session.",
    )
    local.add_argument(
        "--respawn-all-background-agents",
        action="store_true",
        help="Restart every running project-local background coding agent.",
    )
    local.add_argument(
        "--remove-background-agent",
        metavar="ID",
        help="Remove one non-running background agent entry and logs while preserving its session.",
    )


def add_background_agent_option_arguments(parser: argparse.ArgumentParser, *, positive_int) -> None:
    parser.add_argument(
        "--remote-control-session-name-prefix",
        metavar="PREFIX",
        help="Prefix for an automatically generated Remote Control session name (default: hostname).",
    )
    parser.add_argument(
        "--remote-control-host",
        default="127.0.0.1",
        metavar="HOST",
        help="IPv4 address for Remote Control (non-loopback addresses require TLS).",
    )
    parser.add_argument(
        "--remote-control-port",
        type=int,
        default=0,
        metavar="PORT",
        help="Port for Remote Control; 0 selects an available port.",
    )
    parser.add_argument(
        "--remote-control-cert",
        metavar="PATH",
        help="TLS certificate chain for non-loopback Remote Control.",
    )
    parser.add_argument(
        "--remote-control-key",
        metavar="PATH",
        help="TLS private key for non-loopback Remote Control.",
    )
    parser.add_argument(
        "--_background-agent-followup",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--_background-agent-worker-token",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--background-agent-log-max-chars",
        type=positive_int,
        default=20_000,
        metavar="N",
        help="Maximum stdout and stderr characters shown by --background-agent-log.",
    )


def normalize_background_agent_command_arguments(argv: Sequence[str]) -> list[str]:
    values = list(argv)
    index = management_command_index(values, BACKGROUND_AGENT_COMMAND_NAMES)
    if index is None:
        return values
    command = values[index]
    command_args, trailing_globals = extract_trailing_global_options(values[index + 1 :])
    prefix = [*values[:index], *trailing_globals]
    if command == "agents":
        if _requests_json_output(prefix):
            if command_args == ["--all"]:
                return [*prefix, "--background-agents"]
            return [*prefix, "--active-background-agents", *command_args]
        return [*prefix, "--agent-view", *command_args]
    if command == "remote-control":
        return [*prefix, "--remote-control", *command_args]
    if command == "attach":
        return [*prefix, "--attach-background-agent", *command_args]
    if command == "logs":
        normalized = _normalize_logs_arguments(command_args)
        return [*prefix, "--background-agent-log", *normalized]
    if command in {"stop", "kill"}:
        return [*prefix, "--stop-background-agent", *command_args]
    if command == "respawn" and command_args == ["--all"]:
        return [*prefix, "--respawn-all-background-agents"]
    if command == "respawn":
        return [*prefix, "--respawn-background-agent", *command_args]
    if command == "rm":
        return [*prefix, "--remove-background-agent", *command_args]
    return values


def _normalize_logs_arguments(values: list[str]) -> list[str]:
    if len(values) == 3 and values[1] == "--max-chars":
        return [values[0], "--background-agent-log-max-chars", values[2]]
    return values


def _requests_json_output(values: list[str]) -> bool:
    if "--json" in values:
        return True
    return any(
        value == "--output-format" and index + 1 < len(values) and values[index + 1] == "json"
        for index, value in enumerate(values)
    )


__all__ = [
    "add_background_agent_local_arguments",
    "add_background_agent_option_arguments",
    "normalize_background_agent_command_arguments",
]

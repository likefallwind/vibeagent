from __future__ import annotations

import argparse
from collections.abc import Sequence


def add_background_agent_local_arguments(
    local: argparse._MutuallyExclusiveGroup,
) -> None:
    local.add_argument(
        "--background-agents",
        action="store_true",
        help="List project-local background coding agents and exit.",
    )
    local.add_argument(
        "--agent-view",
        action="store_true",
        help="Open the interactive full-screen background agent dashboard.",
    )
    local.add_argument(
        "--remote-control",
        action="store_true",
        help="Serve an authenticated browser control plane for project background agents.",
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
        "--remove-background-agent",
        metavar="ID",
        help="Remove one non-running background agent entry and logs while preserving its session.",
    )


def add_background_agent_option_arguments(parser: argparse.ArgumentParser, *, positive_int) -> None:
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
    if values and values[0] == "agents":
        return ["--agent-view", *values[1:]]
    if values and values[0] == "remote-control":
        return ["--remote-control", *values[1:]]
    if len(values) >= 2 and values[0] == "attach":
        return ["--attach-background-agent", values[1], *values[2:]]
    return values


__all__ = [
    "add_background_agent_local_arguments",
    "add_background_agent_option_arguments",
    "normalize_background_agent_command_arguments",
]

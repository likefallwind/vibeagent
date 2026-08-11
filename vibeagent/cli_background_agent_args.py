from __future__ import annotations

import argparse


def add_background_agent_local_arguments(
    local: argparse._MutuallyExclusiveGroup,
) -> None:
    local.add_argument(
        "--background-agents",
        action="store_true",
        help="List project-local background coding agents and exit.",
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


__all__ = [
    "add_background_agent_local_arguments",
    "add_background_agent_option_arguments",
]

from __future__ import annotations

import argparse


def add_local_report_arguments(local: argparse._MutuallyExclusiveGroup) -> None:
    local.add_argument("--usage", action="store_true", help="Show local session usage and exit.")
    local.add_argument("--cost", action="store_true", help="Show configured cost estimate and exit.")
    local.add_argument("--save-config", action="store_true", help="Save non-secret provider defaults to .vibeagent/config.json and exit.")

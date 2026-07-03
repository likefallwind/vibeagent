from __future__ import annotations

import argparse

from .cli_exit_codes import LOCAL_RESULT_ARG_NAMES, local_result_arg_selected


LOCAL_FLAG_ARG_NAMES = frozenset({*LOCAL_RESULT_ARG_NAMES, "usage"})


def has_local_flag(args: argparse.Namespace) -> bool:
    return any(local_result_arg_selected(getattr(args, name, None)) for name in LOCAL_FLAG_ARG_NAMES)


__all__ = ["LOCAL_FLAG_ARG_NAMES", "has_local_flag"]

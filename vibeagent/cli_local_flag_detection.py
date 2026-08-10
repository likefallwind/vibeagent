from __future__ import annotations

import argparse

from .cli_exit_codes import LOCAL_RESULT_ARG_NAMES, local_result_arg_selected


LOCAL_FLAG_ARG_NAMES = frozenset({*LOCAL_RESULT_ARG_NAMES, "usage"})


def has_local_flag(args: argparse.Namespace) -> bool:
    return any(_local_arg_selected(name, getattr(args, name, None)) for name in LOCAL_FLAG_ARG_NAMES)


def has_non_model_local_flag(args: argparse.Namespace) -> bool:
    return any(
        _local_arg_selected(name, getattr(args, name, None))
        for name in LOCAL_FLAG_ARG_NAMES
        if name != "model"
    )


def _local_arg_selected(name: str, value: object) -> bool:
    if name in {"model", "tools"}:
        return value is True
    return local_result_arg_selected(value)


__all__ = ["LOCAL_FLAG_ARG_NAMES", "has_local_flag", "has_non_model_local_flag"]

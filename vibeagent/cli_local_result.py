from __future__ import annotations

import argparse
from collections.abc import Callable
from collections.abc import Mapping
from typing import TypeVar

from . import MACHINE_OUTPUT_SCHEMA_VERSION, __version__
from .cli_exit_codes import local_result_exit_code
from .cli_output import print_output


T = TypeVar("T")


def local_text_or_report(
    args: argparse.Namespace,
    payload_key: str,
    report_factory: Callable[[], T],
    report_formatter: Callable[[T], str],
    text_factory: Callable[[], str],
) -> tuple[str, dict[str, object]]:
    if args.json:
        report = report_factory()
        return report_formatter(report), {payload_key: report}
    return text_factory(), {}


def emit_local_result(args: argparse.Namespace, text: str, payload_extra: Mapping[str, object] | None = None) -> int:
    exit_code = local_result_exit_code(args, text)
    payload: dict[str, object] = {
        "kind": "local",
        "schemaVersion": MACHINE_OUTPUT_SCHEMA_VERSION,
        "version": __version__,
        "success": exit_code == 0,
        "text": text,
    }
    if payload_extra:
        payload.update(payload_extra)
    if exit_code != 0:
        payload["status"] = "failed"
    print_output(payload, args.json)
    return exit_code


__all__ = ["emit_local_result", "local_text_or_report"]

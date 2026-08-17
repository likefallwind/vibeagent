from __future__ import annotations

import argparse
from collections.abc import Callable
from collections.abc import Mapping
import json
from typing import TypeVar

from .cli_exit_codes import local_result_exit_code
from .cli_machine_output import machine_result_status_fields, machine_runtime_fields
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


def emit_local_result(
    args: argparse.Namespace,
    text: str,
    payload_extra: Mapping[str, object] | None = None,
    *,
    raw_json: object | None = None,
) -> int:
    exit_code = local_result_exit_code(args, text)
    if args.json and raw_json is not None:
        print(json.dumps(raw_json, ensure_ascii=False, sort_keys=True))
        return exit_code
    stop_reason = "completed" if exit_code == 0 else "failed"
    payload: dict[str, object] = {
        "kind": "local",
        **machine_runtime_fields(),
        "success": exit_code == 0,
        **machine_result_status_fields(
            status=stop_reason,
            stop_reason=stop_reason,
            exit_code=exit_code,
        ),
        "text": text,
    }
    if payload_extra:
        payload.update(payload_extra)
    print_output(payload, args.json)
    return exit_code


__all__ = ["emit_local_result", "local_text_or_report"]

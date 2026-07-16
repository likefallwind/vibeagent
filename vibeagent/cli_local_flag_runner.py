from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from . import __version__
from .cli_config import (
    build_provider_env,
    format_save_config_report_text,
    resolve_project_root,
    save_project_config_from_args,
    save_project_config_report_from_args,
)
from .cli_exit_codes import (
    LOCAL_RESULT_ARG_NAMES,
    has_bad_session_summary_status,
    has_incomplete_top_level_count,
    has_local_diagnostic_error,
    has_positive_top_level_count,
    has_process_status_failure,
    has_session_verification_issue,
    has_top_level_error,
    has_top_level_field,
    has_top_level_ok,
    local_result_arg_selected,
    process_status_value_failed,
)
from .cli_local_dispatch import dispatch_local_flag
from .cli_local_result import emit_local_result
from .cli_output import format_error, print_error_result, print_interrupted_result


def run_local_flag(args: argparse.Namespace, command_namespace: dict[str, Any]) -> int:
    try:
        if args.version:
            payload = {"version": __version__} if args.json else None
            return emit_local_result(args, f"vibeagent {__version__}", payload)
        project_root = resolve_project_root(args.cwd)
        config_root = project_root or Path.cwd()
        payload_extra: dict[str, object] = {}
        if args.save_config:
            if args.json:
                save_config_report = save_project_config_report_from_args(args, config_root)
                payload_extra["saveConfig"] = save_config_report
                text = format_save_config_report_text(save_config_report)
            else:
                text = save_project_config_from_args(args, config_root)
        else:
            provider_env = build_provider_env(args, config_root)
            if (flag_result := dispatch_local_flag(args, project_root, config_root, provider_env, command_namespace)) is not None:
                text, payload = flag_result
                payload_extra.update(payload)
            else:
                text = ""
        return emit_local_result(args, text, payload_extra)
    except KeyboardInterrupt:
        return print_interrupted_result(args.json, args.output_format)
    except Exception as error:
        return print_error_result(format_error(error), args.json, prefix=True, output_format=args.output_format)


__all__ = [
    "LOCAL_RESULT_ARG_NAMES",
    "has_bad_session_summary_status",
    "has_incomplete_top_level_count",
    "has_local_diagnostic_error",
    "has_positive_top_level_count",
    "has_process_status_failure",
    "has_session_verification_issue",
    "has_top_level_error",
    "has_top_level_field",
    "has_top_level_ok",
    "local_result_arg_selected",
    "process_status_value_failed",
    "run_local_flag",
]

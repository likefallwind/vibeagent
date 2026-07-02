from __future__ import annotations

import argparse
from typing import Any

from .cli_local_result import local_text_or_report
from .cli_parse_core import parse_cli_json_value


def _report_text(commands: dict[str, Any], formatter_name: str, title: str, report: Any) -> str:
    return commands[formatter_name](title, report)


def run_json_local_flag(
    args: argparse.Namespace,
    project_root: Any,
    commands: dict[str, Any],
) -> tuple[str, dict[str, object]] | None:
    root = project_root or "."
    if args.config_check is not None:
        return local_text_or_report(
            args,
            "configCheck",
            lambda: commands["get_config_check_report"](root, args.config_check or None),
            commands["format_config_check_report_text"],
            lambda: commands["get_config_check_text"](root, args.config_check or None),
        )
    if args.check_json_set is not None:
        json_kwargs = {
            "path": args.check_json_set[0],
            "pointer": args.check_json_set[1],
            "value": parse_cli_json_value(args.check_json_set[2]),
            "create_missing": args.json_create_missing,
        }
        return local_text_or_report(
            args,
            "checkJsonSet",
            lambda: commands["get_check_json_set_report"](root, **json_kwargs),
            lambda report: _report_text(commands, "format_json_pointer_report_text", "Check JSON set:", report),
            lambda: commands["get_check_json_set_text"](root, **json_kwargs),
        )
    if args.json_set is not None:
        json_kwargs = {
            "path": args.json_set[0],
            "pointer": args.json_set[1],
            "value": parse_cli_json_value(args.json_set[2]),
            "create_missing": args.json_create_missing,
        }
        return local_text_or_report(
            args,
            "jsonSet",
            lambda: commands["get_json_set_report"](root, **json_kwargs),
            lambda report: _report_text(commands, "format_json_pointer_report_text", "JSON set:", report),
            lambda: commands["get_json_set_text"](root, **json_kwargs),
        )
    if args.check_json_remove is not None:
        json_kwargs = {"path": args.check_json_remove[0], "pointer": args.check_json_remove[1]}
        return local_text_or_report(
            args,
            "checkJsonRemove",
            lambda: commands["get_check_json_remove_report"](root, **json_kwargs),
            lambda report: _report_text(commands, "format_json_pointer_report_text", "Check JSON remove:", report),
            lambda: commands["get_check_json_remove_text"](root, **json_kwargs),
        )
    if args.json_remove is not None:
        json_kwargs = {"path": args.json_remove[0], "pointer": args.json_remove[1]}
        return local_text_or_report(
            args,
            "jsonRemove",
            lambda: commands["get_json_remove_report"](root, **json_kwargs),
            lambda report: _report_text(commands, "format_json_pointer_report_text", "JSON remove:", report),
            lambda: commands["get_json_remove_text"](root, **json_kwargs),
        )
    if args.check_json_patch is not None:
        json_kwargs = {"path": args.check_json_patch[0], "operations": parse_cli_json_value(args.check_json_patch[1])}
        return local_text_or_report(
            args,
            "checkJsonPatch",
            lambda: commands["get_check_json_patch_report"](root, **json_kwargs),
            lambda report: _report_text(commands, "format_json_patch_report_text", "Check JSON patch:", report),
            lambda: commands["get_check_json_patch_text"](root, **json_kwargs),
        )
    if args.json_patch is not None:
        json_kwargs = {"path": args.json_patch[0], "operations": parse_cli_json_value(args.json_patch[1])}
        return local_text_or_report(
            args,
            "jsonPatch",
            lambda: commands["get_json_patch_report"](root, **json_kwargs),
            lambda report: _report_text(commands, "format_json_patch_report_text", "JSON patch:", report),
            lambda: commands["get_json_patch_text"](root, **json_kwargs),
        )
    return None


INTERACTIVE_JSON_COMMANDS: dict[str, str] = {
    "config_check": "get_config_check_text",
    "check_json_set": "get_check_json_set_text",
    "json_set": "get_json_set_text",
    "check_json_remove": "get_check_json_remove_text",
    "json_remove": "get_json_remove_text",
    "check_json_patch": "get_check_json_patch_text",
    "json_patch": "get_json_patch_text",
}


def run_interactive_json_command(command: Any, commands: dict[str, Any]) -> str | None:
    getter_name = INTERACTIVE_JSON_COMMANDS.get(command.type)
    if getter_name is None:
        return None
    return commands[getter_name](argument=command.argument)

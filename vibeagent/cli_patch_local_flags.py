from __future__ import annotations

import argparse
from typing import Any

from .cli_local_result import local_text_or_report


def _report_text(commands: dict[str, Any], formatter_name: str, title: str, report: Any) -> str:
    return commands[formatter_name](title, report)


def run_patch_local_flag(
    args: argparse.Namespace,
    project_root: Any,
    commands: dict[str, Any],
) -> tuple[str, dict[str, object]] | None:
    root = project_root or "."
    if args.check_patch is not None:
        patch_kwargs = {"path": args.check_patch[0], "patch": args.check_patch[1]}
        return local_text_or_report(
            args,
            "checkPatch",
            lambda: commands["get_check_patch_report"](root, **patch_kwargs),
            lambda report: _report_text(commands, "format_patch_report_text", "Check patch:", report),
            lambda: commands["get_check_patch_text"](root, **patch_kwargs),
        )
    if args.patch is not None:
        patch_kwargs = {"path": args.patch[0], "patch": args.patch[1]}
        return local_text_or_report(
            args,
            "patch",
            lambda: commands["get_patch_report"](root, **patch_kwargs),
            lambda report: _report_text(commands, "format_patch_report_text", "Patch:", report),
            lambda: commands["get_patch_text"](root, **patch_kwargs),
        )
    if args.check_patches is not None:
        return local_text_or_report(
            args,
            "checkPatches",
            lambda: commands["get_check_patches_report"](root, patch=args.check_patches),
            lambda report: _report_text(commands, "format_patches_report_text", "Check patches:", report),
            lambda: commands["get_check_patches_text"](root, patch=args.check_patches),
        )
    if args.patches is not None:
        return local_text_or_report(
            args,
            "patches",
            lambda: commands["get_patches_report"](root, patch=args.patches),
            lambda report: _report_text(commands, "format_patches_report_text", "Patches:", report),
            lambda: commands["get_patches_text"](root, patch=args.patches),
        )
    if args.check_regex_replace is not None:
        regex_kwargs = {
            "path": args.check_regex_replace[0],
            "pattern": args.check_regex_replace[1],
            "replacement": args.check_regex_replace[2],
            "count": args.regex_count,
            "case_sensitive": not args.regex_ignore_case,
            "multiline": args.regex_multiline,
            "max_replacements": args.regex_max_replacements,
        }
        return local_text_or_report(
            args,
            "checkRegexReplace",
            lambda: commands["get_check_regex_replace_report"](root, **regex_kwargs),
            lambda report: _report_text(commands, "format_regex_replace_report_text", "Check regex replace:", report),
            lambda: commands["get_check_regex_replace_text"](root, **regex_kwargs),
        )
    if args.regex_replace is not None:
        regex_kwargs = {
            "path": args.regex_replace[0],
            "pattern": args.regex_replace[1],
            "replacement": args.regex_replace[2],
            "count": args.regex_count,
            "case_sensitive": not args.regex_ignore_case,
            "multiline": args.regex_multiline,
            "max_replacements": args.regex_max_replacements,
        }
        return local_text_or_report(
            args,
            "regexReplace",
            lambda: commands["get_regex_replace_report"](root, **regex_kwargs),
            lambda report: _report_text(commands, "format_regex_replace_report_text", "Regex replace:", report),
            lambda: commands["get_regex_replace_text"](root, **regex_kwargs),
        )
    return None


INTERACTIVE_PATCH_COMMANDS: dict[str, str] = {
    "check_patch": "get_check_patch_text",
    "patch_file": "get_patch_text",
    "check_patches": "get_check_patches_text",
    "patch_files": "get_patches_text",
    "check_regex_replace": "get_check_regex_replace_text",
    "regex_replace": "get_regex_replace_text",
}


def run_interactive_patch_command(command: Any, commands: dict[str, Any]) -> str | None:
    getter_name = INTERACTIVE_PATCH_COMMANDS.get(command.type)
    if getter_name is None:
        return None
    return commands[getter_name](argument=command.argument)

from __future__ import annotations

import argparse
from typing import Any

from .cli_local_result import local_text_or_report
from .cli_parse_core import parse_multi_edit_flag_values


def _report_text(commands: dict[str, Any], formatter_name: str, title: str, report: Any) -> str:
    return commands[formatter_name](title, report)


def run_text_edit_local_flag(
    args: argparse.Namespace,
    project_root: Any,
    commands: dict[str, Any],
) -> tuple[str, dict[str, object]] | None:
    root = project_root or "."
    if args.check_replace_lines is not None:
        line_kwargs = {
            "path": args.check_replace_lines[0],
            "start_line": args.check_replace_lines[1],
            "end_line": args.check_replace_lines[2],
            "content": args.check_replace_lines[3],
        }
        return local_text_or_report(
            args,
            "checkReplaceLines",
            lambda: commands["get_check_replace_lines_report"](root, **line_kwargs),
            lambda report: _report_text(commands, "format_line_edit_report_text", "Check replace lines:", report),
            lambda: commands["get_check_replace_lines_text"](root, **line_kwargs),
        )
    if args.replace_lines is not None:
        line_kwargs = {
            "path": args.replace_lines[0],
            "start_line": args.replace_lines[1],
            "end_line": args.replace_lines[2],
            "content": args.replace_lines[3],
        }
        return local_text_or_report(
            args,
            "replaceLines",
            lambda: commands["get_replace_lines_report"](root, **line_kwargs),
            lambda report: _report_text(commands, "format_line_edit_report_text", "Replace lines:", report),
            lambda: commands["get_replace_lines_text"](root, **line_kwargs),
        )
    if args.check_insert_lines is not None:
        line_kwargs = {
            "path": args.check_insert_lines[0],
            "line": args.check_insert_lines[1],
            "content": args.check_insert_lines[2],
        }
        return local_text_or_report(
            args,
            "checkInsertLines",
            lambda: commands["get_check_insert_lines_report"](root, **line_kwargs),
            lambda report: _report_text(commands, "format_line_edit_report_text", "Check insert lines:", report),
            lambda: commands["get_check_insert_lines_text"](root, **line_kwargs),
        )
    if args.insert_lines is not None:
        line_kwargs = {
            "path": args.insert_lines[0],
            "line": args.insert_lines[1],
            "content": args.insert_lines[2],
        }
        return local_text_or_report(
            args,
            "insertLines",
            lambda: commands["get_insert_lines_report"](root, **line_kwargs),
            lambda report: _report_text(commands, "format_line_edit_report_text", "Insert lines:", report),
            lambda: commands["get_insert_lines_text"](root, **line_kwargs),
        )
    if args.check_append is not None:
        append_kwargs = {"path": args.check_append[0], "content": args.check_append[1]}
        return local_text_or_report(
            args,
            "checkAppend",
            lambda: commands["get_check_append_file_report"](root, **append_kwargs),
            lambda report: _report_text(commands, "format_line_edit_report_text", "Check append:", report),
            lambda: commands["get_check_append_file_text"](root, **append_kwargs),
        )
    if args.append is not None:
        append_kwargs = {"path": args.append[0], "content": args.append[1]}
        return local_text_or_report(
            args,
            "append",
            lambda: commands["get_append_file_report"](root, **append_kwargs),
            lambda report: _report_text(commands, "format_line_edit_report_text", "Append:", report),
            lambda: commands["get_append_file_text"](root, **append_kwargs),
        )
    if args.check_write is not None:
        write_kwargs = {"path": args.check_write[0], "content": args.check_write[1]}
        return local_text_or_report(
            args,
            "checkWrite",
            lambda: commands["get_check_write_file_report"](root, **write_kwargs),
            lambda report: _report_text(commands, "format_line_edit_report_text", "Check write:", report),
            lambda: commands["get_check_write_file_text"](root, **write_kwargs),
        )
    if args.write is not None:
        write_kwargs = {"path": args.write[0], "content": args.write[1]}
        return local_text_or_report(
            args,
            "write",
            lambda: commands["get_write_file_report"](root, **write_kwargs),
            lambda report: _report_text(commands, "format_line_edit_report_text", "Write:", report),
            lambda: commands["get_write_file_text"](root, **write_kwargs),
        )
    if args.check_write_files is not None:
        return local_text_or_report(
            args,
            "checkWriteFiles",
            lambda: commands["get_check_write_files_report"](root, files=args.check_write_files),
            lambda report: _report_text(commands, "format_write_files_report_text", "Check write files:", report),
            lambda: commands["get_check_write_files_text"](root, files=args.check_write_files),
        )
    if args.write_files is not None:
        return local_text_or_report(
            args,
            "writeFiles",
            lambda: commands["get_write_files_report"](root, files=args.write_files),
            lambda report: _report_text(commands, "format_write_files_report_text", "Write files:", report),
            lambda: commands["get_write_files_text"](root, files=args.write_files),
        )
    if args.check_edit is not None:
        edit_kwargs = {"path": args.check_edit[0], "old": args.check_edit[1], "new": args.check_edit[2]}
        return local_text_or_report(
            args,
            "checkEdit",
            lambda: commands["get_check_edit_file_report"](root, **edit_kwargs),
            lambda report: _report_text(commands, "format_line_edit_report_text", "Check edit:", report),
            lambda: commands["get_check_edit_file_text"](root, **edit_kwargs),
        )
    if args.edit is not None:
        edit_kwargs = {"path": args.edit[0], "old": args.edit[1], "new": args.edit[2]}
        return local_text_or_report(
            args,
            "edit",
            lambda: commands["get_edit_file_report"](root, **edit_kwargs),
            lambda report: _report_text(commands, "format_line_edit_report_text", "Edit:", report),
            lambda: commands["get_edit_file_text"](root, **edit_kwargs),
        )
    if args.check_multi_edit is not None:
        path, edits = parse_multi_edit_flag_values(args.check_multi_edit, "--check-multi-edit")
        return local_text_or_report(
            args,
            "checkMultiEdit",
            lambda: commands["get_check_multi_edit_file_report"](root, path=path, edits=edits),
            lambda report: _report_text(commands, "format_line_edit_report_text", "Check multi edit:", report),
            lambda: commands["get_check_multi_edit_file_text"](root, path=path, edits=edits),
        )
    if args.multi_edit is not None:
        path, edits = parse_multi_edit_flag_values(args.multi_edit, "--multi-edit")
        return local_text_or_report(
            args,
            "multiEdit",
            lambda: commands["get_multi_edit_file_report"](root, path=path, edits=edits),
            lambda report: _report_text(commands, "format_line_edit_report_text", "Multi edit:", report),
            lambda: commands["get_multi_edit_file_text"](root, path=path, edits=edits),
        )
    return None


INTERACTIVE_TEXT_EDIT_COMMANDS: dict[str, str] = {
    "check_replace_lines": "get_check_replace_lines_text",
    "replace_lines": "get_replace_lines_text",
    "check_insert_lines": "get_check_insert_lines_text",
    "insert_lines": "get_insert_lines_text",
    "check_append_file": "get_check_append_file_text",
    "append_file": "get_append_file_text",
    "check_write_file": "get_check_write_file_text",
    "write_file": "get_write_file_text",
    "check_write_files": "get_check_write_files_text",
    "write_files": "get_write_files_text",
    "check_edit_file": "get_check_edit_file_text",
    "edit_file": "get_edit_file_text",
    "check_multi_edit_file": "get_check_multi_edit_file_text",
    "multi_edit_file": "get_multi_edit_file_text",
}


def run_interactive_text_edit_command(command: Any, commands: dict[str, Any]) -> str | None:
    getter_name = INTERACTIVE_TEXT_EDIT_COMMANDS.get(command.type)
    if getter_name is None:
        return None
    return commands[getter_name](argument=command.argument)

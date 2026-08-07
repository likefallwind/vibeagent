from __future__ import annotations

import argparse
from typing import Any

from .cli_edit_directory_local_flags import run_edit_directory_local_flag
from .cli_edit_file_local_flags import run_edit_file_local_flag
from .cli_local_result import local_text_or_report
from .cli_parse_core import parse_executable_flag_values


def _report_text(commands: dict[str, Any], formatter_name: str, title: str, report: Any) -> str:
    return commands[formatter_name](title, report)


def run_edit_local_flag(
    args: argparse.Namespace,
    project_root: Any,
    commands: dict[str, Any],
) -> tuple[str, dict[str, object]] | None:
    root = project_root or "."
    file_result = run_edit_file_local_flag(args, root, commands)
    if file_result is not None:
        return file_result
    directory_result = run_edit_directory_local_flag(args, root, commands)
    if directory_result is not None:
        return directory_result
    if args.check_executable is not None:
        path, executable = parse_executable_flag_values(args.check_executable, "--check-executable")
        return local_text_or_report(
            args,
            "checkSetExecutable",
            lambda: commands["get_check_set_executable_report"](root, path=path, executable=executable),
            lambda report: _report_text(commands, "format_executable_report_text", "Check executable:", report),
            lambda: commands["get_check_set_executable_text"](root, path=path, executable=executable),
        )
    if args.set_executable is not None:
        path, executable = parse_executable_flag_values(args.set_executable, "--set-executable")
        return local_text_or_report(
            args,
            "setExecutable",
            lambda: commands["get_set_executable_report"](root, path=path, executable=executable),
            lambda report: _report_text(commands, "format_executable_report_text", "Set executable:", report),
            lambda: commands["get_set_executable_text"](root, path=path, executable=executable),
        )
    return None


INTERACTIVE_EDIT_COMMANDS: dict[str, str] = {
    "check_delete_file": "get_check_delete_file_text",
    "delete_file": "get_delete_file_text",
    "check_delete_files": "get_check_delete_files_text",
    "delete_files": "get_delete_files_text",
    "check_move_file": "get_check_move_file_text",
    "move_file": "get_move_file_text",
    "check_move_files": "get_check_move_files_text",
    "move_files": "get_move_files_text",
    "check_copy_file": "get_check_copy_file_text",
    "copy_file": "get_copy_file_text",
    "check_copy_files": "get_check_copy_files_text",
    "copy_files": "get_copy_files_text",
    "check_move_dir": "get_check_move_dir_text",
    "move_dir": "get_move_dir_text",
    "check_move_dirs": "get_check_move_dirs_text",
    "move_dirs": "get_move_dirs_text",
    "check_copy_dir": "get_check_copy_dir_text",
    "copy_dir": "get_copy_dir_text",
    "check_copy_dirs": "get_check_copy_dirs_text",
    "copy_dirs": "get_copy_dirs_text",
    "check_create_dir": "get_check_create_dir_text",
    "create_dir": "get_create_dir_text",
    "check_create_dirs": "get_check_create_dirs_text",
    "create_dirs": "get_create_dirs_text",
    "check_delete_empty_dir": "get_check_delete_empty_dir_text",
    "delete_empty_dir": "get_delete_empty_dir_text",
    "check_delete_empty_dirs": "get_check_delete_empty_dirs_text",
    "delete_empty_dirs": "get_delete_empty_dirs_text",
    "check_set_executable": "get_check_set_executable_text",
    "set_executable": "get_set_executable_text",
}


def run_interactive_edit_command(command: Any, commands: dict[str, Any]) -> str | None:
    getter_name = INTERACTIVE_EDIT_COMMANDS.get(command.type)
    if getter_name is None:
        return None
    return commands[getter_name](argument=command.argument)

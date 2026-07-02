from __future__ import annotations

import argparse
from typing import Any

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
    if args.check_delete is not None:
        delete_kwargs = {"path": args.check_delete}
        return local_text_or_report(
            args,
            "checkDelete",
            lambda: commands["get_check_delete_file_report"](root, **delete_kwargs),
            lambda report: _report_text(commands, "format_line_edit_report_text", "Check delete:", report),
            lambda: commands["get_check_delete_file_text"](root, **delete_kwargs),
        )
    if args.delete is not None:
        delete_kwargs = {"path": args.delete}
        return local_text_or_report(
            args,
            "delete",
            lambda: commands["get_delete_file_report"](root, **delete_kwargs),
            lambda report: _report_text(commands, "format_line_edit_report_text", "Delete:", report),
            lambda: commands["get_delete_file_text"](root, **delete_kwargs),
        )
    if args.check_delete_files is not None:
        return local_text_or_report(
            args,
            "checkDeleteFiles",
            lambda: commands["get_check_delete_files_report"](root, paths=args.check_delete_files),
            lambda report: commands["format_path_list_report_text"]("Check delete files:", report, include_diff=True),
            lambda: commands["get_check_delete_files_text"](root, paths=args.check_delete_files),
        )
    if args.delete_files is not None:
        return local_text_or_report(
            args,
            "deleteFiles",
            lambda: commands["get_delete_files_report"](root, paths=args.delete_files),
            lambda report: commands["format_path_list_report_text"]("Delete files:", report, include_diff=True),
            lambda: commands["get_delete_files_text"](root, paths=args.delete_files),
        )
    if args.check_move is not None:
        transfer_kwargs = {"source": args.check_move[0], "destination": args.check_move[1]}
        return local_text_or_report(
            args,
            "checkMove",
            lambda: commands["get_check_move_file_report"](root, **transfer_kwargs),
            lambda report: _report_text(commands, "format_file_transfer_report_text", "Check move:", report),
            lambda: commands["get_check_move_file_text"](root, **transfer_kwargs),
        )
    if args.move is not None:
        transfer_kwargs = {"source": args.move[0], "destination": args.move[1]}
        return local_text_or_report(
            args,
            "move",
            lambda: commands["get_move_file_report"](root, **transfer_kwargs),
            lambda report: _report_text(commands, "format_file_transfer_report_text", "Move:", report),
            lambda: commands["get_move_file_text"](root, **transfer_kwargs),
        )
    if args.check_move_files is not None:
        return local_text_or_report(
            args,
            "checkMoveFiles",
            lambda: commands["get_check_move_files_report"](root, transfers=args.check_move_files),
            lambda report: _report_text(commands, "format_file_transfer_list_report_text", "Check move files:", report),
            lambda: commands["get_check_move_files_text"](root, transfers=args.check_move_files),
        )
    if args.move_files is not None:
        return local_text_or_report(
            args,
            "moveFiles",
            lambda: commands["get_move_files_report"](root, transfers=args.move_files),
            lambda report: _report_text(commands, "format_file_transfer_list_report_text", "Move files:", report),
            lambda: commands["get_move_files_text"](root, transfers=args.move_files),
        )
    if args.check_copy is not None:
        transfer_kwargs = {"source": args.check_copy[0], "destination": args.check_copy[1]}
        return local_text_or_report(
            args,
            "checkCopy",
            lambda: commands["get_check_copy_file_report"](root, **transfer_kwargs),
            lambda report: _report_text(commands, "format_file_transfer_report_text", "Check copy:", report),
            lambda: commands["get_check_copy_file_text"](root, **transfer_kwargs),
        )
    if args.copy is not None:
        transfer_kwargs = {"source": args.copy[0], "destination": args.copy[1]}
        return local_text_or_report(
            args,
            "copy",
            lambda: commands["get_copy_file_report"](root, **transfer_kwargs),
            lambda report: _report_text(commands, "format_file_transfer_report_text", "Copy:", report),
            lambda: commands["get_copy_file_text"](root, **transfer_kwargs),
        )
    if args.check_copy_files is not None:
        return local_text_or_report(
            args,
            "checkCopyFiles",
            lambda: commands["get_check_copy_files_report"](root, transfers=args.check_copy_files),
            lambda report: _report_text(commands, "format_file_transfer_list_report_text", "Check copy files:", report),
            lambda: commands["get_check_copy_files_text"](root, transfers=args.check_copy_files),
        )
    if args.copy_files is not None:
        return local_text_or_report(
            args,
            "copyFiles",
            lambda: commands["get_copy_files_report"](root, transfers=args.copy_files),
            lambda report: _report_text(commands, "format_file_transfer_list_report_text", "Copy files:", report),
            lambda: commands["get_copy_files_text"](root, transfers=args.copy_files),
        )
    if args.check_move_dir is not None:
        transfer_kwargs = {"source": args.check_move_dir[0], "destination": args.check_move_dir[1]}
        return local_text_or_report(
            args,
            "checkMoveDir",
            lambda: commands["get_check_move_dir_report"](root, **transfer_kwargs),
            lambda report: _report_text(commands, "format_file_transfer_report_text", "Check move dir:", report),
            lambda: commands["get_check_move_dir_text"](root, **transfer_kwargs),
        )
    if args.move_dir is not None:
        transfer_kwargs = {"source": args.move_dir[0], "destination": args.move_dir[1]}
        return local_text_or_report(
            args,
            "moveDir",
            lambda: commands["get_move_dir_report"](root, **transfer_kwargs),
            lambda report: _report_text(commands, "format_file_transfer_report_text", "Move dir:", report),
            lambda: commands["get_move_dir_text"](root, **transfer_kwargs),
        )
    if args.check_move_dirs is not None:
        return local_text_or_report(
            args,
            "checkMoveDirs",
            lambda: commands["get_check_move_dirs_report"](root, transfers=args.check_move_dirs),
            lambda report: _report_text(commands, "format_file_transfer_list_report_text", "Check move dirs:", report),
            lambda: commands["get_check_move_dirs_text"](root, transfers=args.check_move_dirs),
        )
    if args.move_dirs is not None:
        return local_text_or_report(
            args,
            "moveDirs",
            lambda: commands["get_move_dirs_report"](root, transfers=args.move_dirs),
            lambda report: _report_text(commands, "format_file_transfer_list_report_text", "Move dirs:", report),
            lambda: commands["get_move_dirs_text"](root, transfers=args.move_dirs),
        )
    if args.check_copy_dir is not None:
        transfer_kwargs = {"source": args.check_copy_dir[0], "destination": args.check_copy_dir[1]}
        return local_text_or_report(
            args,
            "checkCopyDir",
            lambda: commands["get_check_copy_dir_report"](root, **transfer_kwargs),
            lambda report: _report_text(commands, "format_file_transfer_report_text", "Check copy dir:", report),
            lambda: commands["get_check_copy_dir_text"](root, **transfer_kwargs),
        )
    if args.copy_dir is not None:
        transfer_kwargs = {"source": args.copy_dir[0], "destination": args.copy_dir[1]}
        return local_text_or_report(
            args,
            "copyDir",
            lambda: commands["get_copy_dir_report"](root, **transfer_kwargs),
            lambda report: _report_text(commands, "format_file_transfer_report_text", "Copy dir:", report),
            lambda: commands["get_copy_dir_text"](root, **transfer_kwargs),
        )
    if args.check_copy_dirs is not None:
        return local_text_or_report(
            args,
            "checkCopyDirs",
            lambda: commands["get_check_copy_dirs_report"](root, transfers=args.check_copy_dirs),
            lambda report: _report_text(commands, "format_file_transfer_list_report_text", "Check copy dirs:", report),
            lambda: commands["get_check_copy_dirs_text"](root, transfers=args.check_copy_dirs),
        )
    if args.copy_dirs is not None:
        return local_text_or_report(
            args,
            "copyDirs",
            lambda: commands["get_copy_dirs_report"](root, transfers=args.copy_dirs),
            lambda report: _report_text(commands, "format_file_transfer_list_report_text", "Copy dirs:", report),
            lambda: commands["get_copy_dirs_text"](root, transfers=args.copy_dirs),
        )
    if args.check_mkdir is not None:
        return local_text_or_report(
            args,
            "checkCreateDir",
            lambda: commands["get_check_create_dir_report"](root, path=args.check_mkdir),
            lambda report: _report_text(commands, "format_path_action_report_text", "Check mkdir:", report),
            lambda: commands["get_check_create_dir_text"](root, path=args.check_mkdir),
        )
    if args.mkdir is not None:
        return local_text_or_report(
            args,
            "createDir",
            lambda: commands["get_create_dir_report"](root, path=args.mkdir),
            lambda report: _report_text(commands, "format_path_action_report_text", "Mkdir:", report),
            lambda: commands["get_create_dir_text"](root, path=args.mkdir),
        )
    if args.check_mkdirs is not None:
        return local_text_or_report(
            args,
            "checkCreateDirs",
            lambda: commands["get_check_create_dirs_report"](root, paths=args.check_mkdirs),
            lambda report: _report_text(commands, "format_path_list_report_text", "Check mkdirs:", report),
            lambda: commands["get_check_create_dirs_text"](root, paths=args.check_mkdirs),
        )
    if args.mkdirs is not None:
        return local_text_or_report(
            args,
            "createDirs",
            lambda: commands["get_create_dirs_report"](root, paths=args.mkdirs),
            lambda report: _report_text(commands, "format_path_list_report_text", "Mkdirs:", report),
            lambda: commands["get_create_dirs_text"](root, paths=args.mkdirs),
        )
    if args.check_rmdir is not None:
        return local_text_or_report(
            args,
            "checkDeleteEmptyDir",
            lambda: commands["get_check_delete_empty_dir_report"](root, path=args.check_rmdir),
            lambda report: _report_text(commands, "format_path_action_report_text", "Check rmdir:", report),
            lambda: commands["get_check_delete_empty_dir_text"](root, path=args.check_rmdir),
        )
    if args.rmdir is not None:
        return local_text_or_report(
            args,
            "deleteEmptyDir",
            lambda: commands["get_delete_empty_dir_report"](root, path=args.rmdir),
            lambda report: _report_text(commands, "format_path_action_report_text", "Rmdir:", report),
            lambda: commands["get_delete_empty_dir_text"](root, path=args.rmdir),
        )
    if args.check_rmdirs is not None:
        return local_text_or_report(
            args,
            "checkDeleteEmptyDirs",
            lambda: commands["get_check_delete_empty_dirs_report"](root, paths=args.check_rmdirs),
            lambda report: _report_text(commands, "format_path_list_report_text", "Check rmdirs:", report),
            lambda: commands["get_check_delete_empty_dirs_text"](root, paths=args.check_rmdirs),
        )
    if args.rmdirs is not None:
        return local_text_or_report(
            args,
            "deleteEmptyDirs",
            lambda: commands["get_delete_empty_dirs_report"](root, paths=args.rmdirs),
            lambda report: _report_text(commands, "format_path_list_report_text", "Rmdirs:", report),
            lambda: commands["get_delete_empty_dirs_text"](root, paths=args.rmdirs),
        )
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

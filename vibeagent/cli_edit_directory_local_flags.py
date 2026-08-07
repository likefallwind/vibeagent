from __future__ import annotations

import argparse
from typing import Any

from .cli_local_result import local_text_or_report


def _report_text(commands: dict[str, Any], formatter_name: str, title: str, report: Any) -> str:
    return commands[formatter_name](title, report)


def run_edit_directory_local_flag(
    args: argparse.Namespace,
    root: Any,
    commands: dict[str, Any],
) -> tuple[str, dict[str, object]] | None:
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
    return None

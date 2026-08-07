from __future__ import annotations

import argparse
from typing import Any

from .cli_local_result import local_text_or_report


def _report_text(commands: dict[str, Any], formatter_name: str, title: str, report: Any) -> str:
    return commands[formatter_name](title, report)


def run_edit_file_local_flag(
    args: argparse.Namespace,
    root: Any,
    commands: dict[str, Any],
) -> tuple[str, dict[str, object]] | None:
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
    return None

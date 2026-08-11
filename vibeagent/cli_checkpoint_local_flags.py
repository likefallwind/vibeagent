from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from .cli_local_result import local_text_or_report


def run_checkpoint_local_flag(
    args: argparse.Namespace,
    project_root: Path | None,
    commands: dict[str, Any],
) -> tuple[str, dict[str, object]] | None:
    root = project_root or "."
    if args.checkpoint is not None:
        return local_text_or_report(
            args,
            "checkpoint",
            lambda: commands["get_checkpoint_report"](root, args.checkpoint or None),
            commands["format_checkpoint_create_report_text"],
            lambda: commands["get_checkpoint_text"](root, args.checkpoint or None),
        )
    if args.checkpoints:
        return local_text_or_report(
            args,
            "checkpoints",
            lambda: commands["get_checkpoints_report"](root),
            commands["format_checkpoints_report_text"],
            lambda: commands["get_checkpoints_text"](root),
        )
    if args.checkpoint_show is not None:
        return local_text_or_report(
            args,
            "checkpointShow",
            lambda: commands["get_checkpoint_show_report"](args.checkpoint_show, root),
            commands["format_checkpoint_show_report_text"],
            lambda: commands["get_checkpoint_show_text"](args.checkpoint_show, root),
        )
    if args.checkpoint_diff is not None:
        return local_text_or_report(
            args,
            "checkpointDiff",
            lambda: commands["get_checkpoint_diff_report"](args.checkpoint_diff, root),
            commands["format_checkpoint_diff_report_text"],
            lambda: commands["get_checkpoint_diff_text"](args.checkpoint_diff, root),
        )
    if args.checkpoint_status is not None:
        return local_text_or_report(
            args,
            "checkpointStatus",
            lambda: commands["get_checkpoint_status_report"](args.checkpoint_status, root),
            commands["format_checkpoint_status_report_text"],
            lambda: commands["get_checkpoint_status_text"](args.checkpoint_status, root),
        )
    if args.check_checkpoint_restore is not None:
        return local_text_or_report(
            args,
            "checkCheckpointRestore",
            lambda: commands["get_check_checkpoint_restore_report"](args.check_checkpoint_restore, root),
            commands["format_check_checkpoint_restore_report_text"],
            lambda: commands["get_check_checkpoint_restore_text"](args.check_checkpoint_restore, root),
        )
    if args.checkpoint_restore is not None:
        return local_text_or_report(
            args,
            "checkpointRestore",
            lambda: commands["get_checkpoint_restore_report"](args.checkpoint_restore, root),
            commands["format_checkpoint_restore_report_text"],
            lambda: commands["get_checkpoint_restore_text"](args.checkpoint_restore, root),
        )
    if args.check_checkpoint_delete is not None:
        return local_text_or_report(
            args,
            "checkCheckpointDelete",
            lambda: commands["get_check_checkpoint_delete_report"](args.check_checkpoint_delete, root),
            commands["format_check_checkpoint_delete_report_text"],
            lambda: commands["get_check_checkpoint_delete_text"](args.check_checkpoint_delete, root),
        )
    if args.checkpoint_delete is not None:
        return local_text_or_report(
            args,
            "checkpointDelete",
            lambda: commands["get_checkpoint_delete_report"](args.checkpoint_delete, root),
            commands["format_checkpoint_delete_report_text"],
            lambda: commands["get_checkpoint_delete_text"](args.checkpoint_delete, root),
        )
    if args.check_checkpoint_prune is not None:
        return local_text_or_report(
            args,
            "checkCheckpointPrune",
            lambda: commands["get_check_checkpoint_prune_report"](args.check_checkpoint_prune, root),
            commands["format_check_checkpoint_prune_report_text"],
            lambda: commands["get_check_checkpoint_prune_text"](args.check_checkpoint_prune, root),
        )
    if args.checkpoint_prune is not None:
        return local_text_or_report(
            args,
            "checkpointPrune",
            lambda: commands["get_checkpoint_prune_report"](args.checkpoint_prune, root),
            commands["format_checkpoint_prune_report_text"],
            lambda: commands["get_checkpoint_prune_text"](args.checkpoint_prune, root),
        )
    if args.session_rewind_points is not None:
        run_id = args.session_rewind_points
        return local_text_or_report(
            args,
            "sessionRewindPoints",
            lambda: commands["get_session_rewind_points_report"](root, run_id),
            commands["format_session_rewind_points_report_text"],
            lambda: commands["format_session_rewind_points_report_text"](
                commands["get_session_rewind_points_report"](root, run_id)
            ),
        )
    if args.check_session_rewind is not None:
        run_id, checkpoint_id, mode = args.check_session_rewind
        return local_text_or_report(
            args,
            "checkSessionRewind",
            lambda: commands["get_check_session_rewind_report"](root, run_id, checkpoint_id, mode),
            commands["format_check_session_rewind_report_text"],
            lambda: commands["format_check_session_rewind_report_text"](
                commands["get_check_session_rewind_report"](root, run_id, checkpoint_id, mode)
            ),
        )
    if args.session_rewind is not None:
        run_id, checkpoint_id, mode = args.session_rewind
        return local_text_or_report(
            args,
            "sessionRewind",
            lambda: commands["get_session_rewind_report"](root, run_id, checkpoint_id, mode),
            commands["format_session_rewind_report_text"],
            lambda: commands["format_session_rewind_report_text"](
                commands["get_session_rewind_report"](root, run_id, checkpoint_id, mode)
            ),
        )
    return None


def run_interactive_checkpoint_command(
    command: Any,
    commands: dict[str, Any],
    run_id: str | None = None,
) -> str | None:
    if command.type == "checkpoint":
        if run_id is None:
            return commands["get_checkpoint_text"](label=command.argument)
        return commands["get_checkpoint_text"](label=command.argument, session_run_id=run_id)
    if command.type == "checkpoints":
        return commands["get_checkpoints_text"]()
    if command.type == "checkpoint_show":
        return commands["get_checkpoint_show_text"](command.argument)
    if command.type == "checkpoint_diff":
        return commands["get_checkpoint_diff_text"](command.argument)
    if command.type == "checkpoint_status":
        return commands["get_checkpoint_status_text"](command.argument)
    if command.type == "check_checkpoint_restore":
        return commands["get_check_checkpoint_restore_text"](command.argument)
    if command.type == "checkpoint_restore":
        return commands["get_checkpoint_restore_text"](command.argument)
    if command.type == "check_checkpoint_delete":
        return commands["get_check_checkpoint_delete_text"](command.argument)
    if command.type == "checkpoint_delete":
        return commands["get_checkpoint_delete_text"](command.argument)
    if command.type == "check_checkpoint_prune":
        return commands["get_check_checkpoint_prune_text"](command.argument)
    if command.type == "checkpoint_prune":
        return commands["get_checkpoint_prune_text"](command.argument)
    return None

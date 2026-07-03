from __future__ import annotations

from pathlib import Path

from .workflow_checkpoint_commands import (
    build_checkpoint_create_report,
    checkpoint_status_error_report,
    create_local_checkpoint_metadata,
    get_check_checkpoint_delete_report,
    get_check_checkpoint_prune_report,
    get_check_checkpoint_restore_report,
    get_checkpoint_delete_report,
    get_checkpoint_delete_text,
    get_checkpoint_diff_report,
    get_checkpoint_diff_text,
    get_checkpoint_prune_report,
    get_checkpoint_report,
    get_checkpoint_restore_report,
    get_checkpoint_show_report,
    get_checkpoint_show_text,
    get_checkpoint_status_report,
    get_checkpoint_status_text,
    get_checkpoint_text,
    get_checkpoints_report,
    get_checkpoints_text,
    read_local_checkpoint_metadata,
    serialize_checkpoint_info,
    serialize_checkpoint_metadata,
)
from .workflow_diff_commands import (
    clip_with_flag,
    format_diff_contexts_report_text,
    format_diff_hunk_lines,
    format_diff_hunks_report_text,
    format_diff_report_text,
    get_diff_contexts_report,
    get_diff_contexts_text,
    get_diff_hunks_report,
    get_diff_hunks_text,
    get_diff_report,
    get_diff_text,
    parse_diff_argument,
    serialize_diff_hunk,
    serialize_file_context_result,
    validate_diff_contexts_limits,
    validate_diff_hunks_limits,
)
from .workflow_runtime_commands import (
    blocked_command_examples,
    build_project_instructions_template,
    format_context_report_text,
    format_doctor_report_text,
    format_init_report_text,
    format_status_report_text,
    get_command_hard_block_report,
    get_context_report,
    get_context_text,
    get_doctor_report,
    get_doctor_text,
    get_init_report,
    get_status_report,
    get_status_text,
    init_project_instructions,
    normalize_project_instructions_file_name,
)
from .workflow_checkpoint_utils import (
    CHECKPOINT_UNTRACKED_SHOW_LIMIT,
    checkpoint_root,
    clip_local_checkpoint_untracked_paths,
    count_status_kinds,
    display_checkpoint_file,
    format_checkpoint_created,
    is_runtime_checkpoint_path,
    is_safe_checkpoint_relative_path,
    local_checkpoint_untracked_files_match,
    local_checkpoint_untracked_paths,
    normalize_checkpoint_label,
    parse_checkpoint_keep_last,
    read_checkpoint_patch,
    read_checkpoints,
    read_git_head,
    read_local_checkpoint_untracked_manifest,
    resolve_checkpoint_dir,
    restore_local_checkpoint_untracked_files,
    run_git_checkpoint_command,
    save_local_checkpoint_untracked_files,
    short_head,
)
from .workflow_checkpoint_formatting import (
    format_check_checkpoint_delete_report_text,
    format_check_checkpoint_prune_report_text,
    format_check_checkpoint_restore_report_text,
    format_checkpoint_create_report_text,
    format_checkpoint_delete_report_text,
    format_checkpoint_diff_report_text,
    format_checkpoint_prune_report_text,
    format_checkpoint_restore_report_text,
    format_checkpoint_restore_report_text_with_title,
    format_checkpoint_show_report_text,
    format_checkpoint_status_report_text,
    format_checkpoints_report_text,
)
from .workflow_change_commands import (
    format_changes_report_text,
    get_changes_report,
    get_changes_text,
)
from .workflow_review_commands import (
    format_handoff_report_text,
    format_review_report_text,
    get_handoff_plan_text,
    get_handoff_report,
    get_handoff_text,
    get_review_report,
    get_review_text,
)
from .workflow_review_formatting import (
    filter_handoff_status,
    format_check_location,
    format_review_check,
    format_review_file,
    format_review_process,
    format_review_syntax_check,
    is_runtime_status_path,
)
from .workflow_review_reports import (
    final_review_common_report,
    final_review_status_checks,
    local_final_review_workspace,
    serialize_focused_review_command,
)


def get_check_checkpoint_restore_text(checkpoint_id: str | None, project_root: str | Path = ".") -> str:
    return format_check_checkpoint_restore_report_text(get_check_checkpoint_restore_report(checkpoint_id, project_root))


def get_checkpoint_restore_text(checkpoint_id: str | None, project_root: str | Path = ".") -> str:
    return format_checkpoint_restore_report_text(get_checkpoint_restore_report(checkpoint_id, project_root))


def get_check_checkpoint_delete_text(checkpoint_id: str | None, project_root: str | Path = ".") -> str:
    report = get_check_checkpoint_delete_report(checkpoint_id, project_root)
    if str(report.get("message") or "").startswith("Usage:"):
        return str(report["message"])
    return format_check_checkpoint_delete_report_text(report)


def get_check_checkpoint_prune_text(keep_last: str | int | None, project_root: str | Path = ".") -> str:
    return format_check_checkpoint_prune_report_text(get_check_checkpoint_prune_report(keep_last, project_root))


def get_checkpoint_prune_text(keep_last: str | int | None, project_root: str | Path = ".") -> str:
    return format_checkpoint_prune_report_text(get_checkpoint_prune_report(keep_last, project_root))

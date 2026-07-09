from __future__ import annotations

from types import ModuleType
from typing import Any


COMMAND_EXPORT_PREFIXES = ("format_", "get_")
COMMAND_EXPORT_NAMES = {"init_project_instructions", "parse_local_command"}

INTERNAL_COMMAND_EXPORT_NAMES = {
    "format_check_location",
    "format_checkpoint_created",
    "format_checkpoint_restore_report_text_with_title",
    "format_code_rename_observation",
    "format_command_output_context_lines",
    "format_command_output_diagnostic_lines",
    "format_diff_hunk_lines",
    "format_executable_observation",
    "format_file_transfer_list_observation",
    "format_file_transfer_observation",
    "format_json_patch_observation",
    "format_json_pointer_observation",
    "format_line_edit_observation",
    "format_manifest_summary",
    "format_patch_observation",
    "format_patches_observation",
    "format_path_action_observation",
    "format_path_list_observation",
    "format_project_command",
    "format_python_rename_observation",
    "format_regex_replace_observation",
    "format_replace_python_definition_observation",
    "format_repo_map_symbols",
    "format_review_check",
    "format_review_file",
    "format_review_process",
    "format_review_syntax_check",
    "format_serialized_symbol_file",
    "format_structured_command_checks",
    "format_structured_command_output_analysis_lines",
    "format_symbol_file",
    "format_tool_property",
    "format_write_files_observation",
    "get_blocked_command_reason",
    "get_command_hard_block_report",
    "get_handoff_plan_text",
    "get_last_session_id",
    "get_session_output_contexts_observation",
    "get_session_output_diagnostics_observation",
}


def is_command_export_name(name: str) -> bool:
    return (
        name.startswith(COMMAND_EXPORT_PREFIXES) or name in COMMAND_EXPORT_NAMES
    ) and name not in INTERNAL_COMMAND_EXPORT_NAMES


def command_export_names(command_module: ModuleType) -> list[str]:
    return sorted(name for name in vars(command_module) if is_command_export_name(name))


def install_command_exports(target_globals: dict[str, Any], command_module: ModuleType) -> list[str]:
    names = command_export_names(command_module)
    target_globals.update({name: getattr(command_module, name) for name in names})
    return names

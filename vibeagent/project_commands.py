from __future__ import annotations

from pathlib import Path

from .output_serialization import serialize_output_context_result, serialize_output_diagnostic
from .project_command_utils import (
    commands_attr as _commands_attr,
    execute_action as _execute_action,
    plain_data as _plain_data,
)
from .project_discovery_commands import (
    format_find_files_report_text,
    format_glob_report_text,
    format_search_contexts_report_text,
    format_search_report_text,
    format_tree_report_text,
    get_find_files_report,
    get_find_files_text,
    get_glob_report,
    get_glob_text,
    get_search_contexts_report,
    get_search_contexts_text,
    get_search_report,
    get_search_text,
    get_tree_report,
    get_tree_text,
)
from .project_file_info_commands import (
    file_type_text,
    format_file_info_report_text,
    format_image_info_report_text,
    get_file_info_report,
    get_file_info_text,
    get_image_info_report,
    get_image_info_text,
    serialize_file_info_result,
    serialize_image_info_result,
    yes_no_unknown,
)
from .project_output_commands import (
    format_output_contexts_report_text,
    format_output_diagnostics_report_text,
    format_python_traceback_report_text,
    get_output_contexts_report,
    get_output_contexts_text,
    get_output_diagnostics_report,
    get_output_diagnostics_text,
    get_python_traceback_report,
    get_python_traceback_text,
)
from .project_overview_reports import (
    format_overview_report_text,
    format_project_command_report_item as _format_project_command_report_item,
)
from .project_repo_map_commands import (
    format_repo_map_report_text,
    format_repo_map_symbols,
    format_symbol_file,
    get_repo_map_report,
    get_repo_map_text,
)
from .project_symbol_commands import (
    format_serialized_symbol_file,
    format_symbols_report_text,
    get_symbols_report,
    get_symbols_text,
    parse_symbols_paths,
    serialize_symbol,
    serialize_symbol_file,
)
from .local_command_workspace import local_command_workspace
from .types import (
    ProjectOverviewAction,
)


def get_overview_report(project_root: str | Path = ".", max_files: int = 80, max_commands: int = 20, max_checks: int = 10) -> dict[str, object]:
    root = Path(project_root).resolve()
    workspace = local_command_workspace(root, "local-overview")
    observation = _execute_action(
        workspace,
        ProjectOverviewAction(
            type="project_overview",
            max_files=max_files,
            max_commands=max_commands,
            max_checks=max_checks,
        ),
    )
    if observation.kind != "project_overview":
        return {
            "projectRoot": str(root),
            "ok": False,
            "git": {"isRepo": False, "branch": "", "head": "", "upstream": "", "ahead": 0, "behind": 0, "status": ""},
            "files": {"shown": 0, "total": 0, "paths": []},
            "tree": {"shown": 0, "total": 0, "truncated": False, "entries": []},
            "commands": {"shown": 0, "total": 0, "truncated": False, "items": []},
            "manifests": {"shown": 0, "total": 0, "truncated": False, "items": []},
            "instructions": {"shown": 0, "total": 0, "truncated": False, "sources": []},
            "todos": {"shown": 0, "total": 0, "truncated": False, "items": []},
            "suggestedChecks": {"shown": 0, "total": 0, "truncated": False, "items": []},
            "tools": {"available": 0, "total": 0, "items": []},
            "message": f"Unexpected observation: {observation.kind}",
        }

    tools = [_plain_data(tool) for tool in observation.tools]
    return {
        "projectRoot": observation.project_root,
        "ok": observation.ok,
        "git": {
            "isRepo": observation.is_git_repo,
            "branch": observation.git_branch,
            "head": observation.git_head,
            "upstream": observation.git_upstream,
            "ahead": observation.git_ahead,
            "behind": observation.git_behind,
            "status": observation.git_status,
        },
        "files": {"shown": len(observation.files), "total": observation.total_files, "paths": list(observation.files)},
        "tree": {
            "shown": len(observation.tree),
            "total": observation.total_tree_entries,
            "truncated": observation.repo_truncated,
            "entries": list(observation.tree),
        },
        "commands": {
            "shown": len(observation.commands),
            "total": observation.commands_total,
            "truncated": observation.commands_truncated,
            "items": [_plain_data(item) for item in observation.commands],
        },
        "manifests": {
            "shown": len(observation.manifests),
            "total": observation.manifest_files_total,
            "truncated": observation.manifests_truncated,
            "items": [_plain_data(item) for item in observation.manifests],
        },
        "instructions": {
            "shown": len(observation.instruction_sources),
            "total": observation.instruction_files_total,
            "truncated": observation.instructions_truncated,
            "sources": [_plain_data(item) for item in observation.instruction_sources],
        },
        "todos": {
            "shown": len(observation.todos),
            "total": observation.todos_total,
            "truncated": observation.todos_truncated,
            "items": [_plain_data(item) for item in observation.todos],
        },
        "suggestedChecks": {
            "shown": len(observation.suggested_checks),
            "total": observation.suggested_checks_total,
            "truncated": observation.suggested_checks_truncated,
            "items": [_plain_data(item) for item in observation.suggested_checks],
        },
        "tools": {
            "available": sum(1 for item in tools if isinstance(item, dict) and bool(item.get("available"))),
            "total": len(tools),
            "items": tools,
        },
        "message": observation.message,
    }


def get_overview_text(project_root: str | Path = ".", max_files: int = 80, max_commands: int = 20, max_checks: int = 10) -> str:
    get_report = _commands_attr("get_overview_report", get_overview_report)
    formatter = _commands_attr("format_overview_report_text", format_overview_report_text)
    return formatter(get_report(project_root, max_files=max_files, max_commands=max_commands, max_checks=max_checks))

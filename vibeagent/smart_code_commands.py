from __future__ import annotations

from pathlib import Path

from .smart_code_common import (
    execute_action_for_commands as _execute_action,
    format_rename_report_text as _format_rename_report_text,
    rename_observation_report as _rename_observation_report,
    rename_unexpected_report as _rename_unexpected_report,
    rename_usage_report as _rename_usage_report,
)
from .smart_code_formatting import (
    format_code_defs_report_text,
    format_code_deps_report_text,
    format_code_ref_contexts_report_text,
    format_code_refs_report_text,
)
from .smart_code_symbol_commands import (
    get_code_defs_report,
    get_code_defs_text,
    get_code_deps_report,
    get_code_deps_text,
    get_code_ref_contexts_report,
    get_code_ref_contexts_text,
    get_code_refs_report,
    get_code_refs_text,
)
from .smart_code_parsing import parse_rename_argument, parse_replace_python_definition_argument, parse_symbol_path_argument
from .smart_python_commands import (
    format_python_call_graph_report_text,
    format_python_calls_report_text,
    format_python_check_report_text,
    format_python_defs_report_text,
    format_python_deps_report_text,
    format_python_ref_contexts_report_text,
    format_python_refs_report_text,
    format_python_rename_observation,
    format_python_rename_report_text,
    format_replace_python_definition_observation,
    format_replace_python_definition_report_text,
    get_check_replace_python_definition_report,
    get_check_replace_python_definition_text,
    get_python_call_graph_report,
    get_python_call_graph_text,
    get_python_calls_report,
    get_python_calls_text,
    get_python_check_report,
    get_python_check_text,
    get_python_defs_report,
    get_python_defs_text,
    get_python_deps_report,
    get_python_deps_text,
    get_python_ref_contexts_report,
    get_python_ref_contexts_text,
    get_python_refs_report,
    get_python_refs_text,
    get_python_rename_preview_report,
    get_python_rename_preview_text,
    get_python_rename_report,
    get_python_rename_text,
    get_replace_python_definition_report,
    get_replace_python_definition_text,
)
from .types import (
    CodeRenameAction,
    CodeRenamePreviewAction,
)
from .workspace_core import RunWorkspace


def get_code_rename_preview_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    symbol: str | None = None,
    new_name: str | None = None,
    path: str | None = None,
    max_files: int = 100,
    max_replacements: int = 500,
) -> str:
    report = get_code_rename_preview_report(
        project_root,
        argument=argument,
        symbol=symbol,
        new_name=new_name,
        path=path,
        max_files=max_files,
        max_replacements=max_replacements,
    )
    return format_code_rename_report_text("Code rename preview:", report)


def get_code_rename_preview_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    symbol: str | None = None,
    new_name: str | None = None,
    path: str | None = None,
    max_files: int = 100,
    max_replacements: int = 500,
) -> dict[str, object]:
    usage = "/code-rename-preview <symbol> <new_name> [path]"
    root = Path(project_root).resolve()
    try:
        parsed_symbol, parsed_new_name, parsed_path = parse_rename_argument(
            argument,
            symbol=symbol,
            new_name=new_name,
            path=path,
            usage=usage,
        )
    except ValueError as error:
        return _rename_usage_report(root, usage, symbol, new_name, path, max_files, max_replacements, str(error))
    workspace = RunWorkspace(root=root, run_id="local-code-rename-preview", session_dir=root / ".vibeagent" / "sessions" / "local-code-rename-preview")
    observation = _execute_action(
        workspace,
        CodeRenamePreviewAction(
            type="code_rename_preview",
            symbol=parsed_symbol,
            new_name=parsed_new_name,
            path=parsed_path,
            max_files=max_files,
            max_replacements=max_replacements,
        ),
    )
    if observation.kind != "code_rename_preview":
        return _rename_unexpected_report(root, parsed_symbol, parsed_new_name, parsed_path, max_files, max_replacements, f"Unexpected observation: {observation.kind}")
    return _rename_observation_report(root, observation, max_files=max_files, max_replacements=max_replacements)


def get_code_rename_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    symbol: str | None = None,
    new_name: str | None = None,
    path: str | None = None,
    max_files: int = 100,
    max_replacements: int = 2000,
) -> str:
    report = get_code_rename_report(
        project_root,
        argument=argument,
        symbol=symbol,
        new_name=new_name,
        path=path,
        max_files=max_files,
        max_replacements=max_replacements,
    )
    return format_code_rename_report_text("Code rename:", report)


def get_code_rename_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    symbol: str | None = None,
    new_name: str | None = None,
    path: str | None = None,
    max_files: int = 100,
    max_replacements: int = 2000,
) -> dict[str, object]:
    usage = "/code-rename <symbol> <new_name> [path]"
    root = Path(project_root).resolve()
    try:
        parsed_symbol, parsed_new_name, parsed_path = parse_rename_argument(
            argument,
            symbol=symbol,
            new_name=new_name,
            path=path,
            usage=usage,
        )
    except ValueError as error:
        return _rename_usage_report(root, usage, symbol, new_name, path, max_files, max_replacements, str(error))
    workspace = RunWorkspace(root=root, run_id="local-code-rename", session_dir=root / ".vibeagent" / "sessions" / "local-code-rename")
    observation = _execute_action(
        workspace,
        CodeRenameAction(
            type="code_rename",
            symbol=parsed_symbol,
            new_name=parsed_new_name,
            path=parsed_path,
            max_files=max_files,
            max_replacements=max_replacements,
        ),
    )
    if observation.kind != "code_rename":
        return _rename_unexpected_report(root, parsed_symbol, parsed_new_name, parsed_path, max_files, max_replacements, f"Unexpected observation: {observation.kind}")
    return _rename_observation_report(root, observation, max_files=max_files, max_replacements=max_replacements)


def format_code_rename_report_text(title: str, report: dict[str, object]) -> str:
    return _format_rename_report_text(title, report, include_language=True)


def format_code_rename_observation(title: str, root: Path, observation: object) -> str:
    return format_code_rename_report_text(title, _rename_observation_report(root, observation, max_files=100, max_replacements=2000))

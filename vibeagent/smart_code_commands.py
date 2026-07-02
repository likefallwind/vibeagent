from __future__ import annotations

from pathlib import Path

from .command_parsing import parse_optional_single_path_argument
from .smart_code_common import (
    commands_attr as _commands_attr,
    execute_action_for_commands as _execute_action,
    format_rename_report_text as _format_rename_report_text,
    plain_data as _plain_data,
    rename_observation_report as _rename_observation_report,
    rename_unexpected_report as _rename_unexpected_report,
    rename_usage_report as _rename_usage_report,
    symbol_report_base as _symbol_report_base,
)
from .smart_code_formatting import (
    format_code_defs_report_text,
    format_code_deps_report_text,
    format_code_ref_contexts_report_text,
    format_code_refs_report_text,
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
    CodeDefinitionsAction,
    CodeDependenciesAction,
    CodeReferenceContextsAction,
    CodeReferencesAction,
    CodeRenameAction,
    CodeRenamePreviewAction,
)
from .workspace_core import RunWorkspace

def get_code_deps_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    max_files: int = 100,
    max_imports: int = 500,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        path = parse_optional_single_path_argument(argument)
    except ValueError as error:
        return {
            "projectRoot": str(root),
            "ok": False,
            "path": ".",
            "files": {"shown": 0, "total": 0, "truncated": False, "items": []},
            "maxFiles": max_files,
            "maxImports": max_imports,
            "message": f"Usage: /code-deps [path]\nError: {error}",
        }
    workspace = RunWorkspace(root=root, run_id="local-code-deps", session_dir=root / ".vibeagent" / "sessions" / "local-code-deps")
    observation = _execute_action(
        workspace,
        CodeDependenciesAction(type="code_dependencies", path=path, max_files=max_files, max_imports=max_imports),
    )
    if observation.kind != "code_dependencies":
        return {
            "projectRoot": str(root),
            "ok": False,
            "path": path or ".",
            "files": {"shown": 0, "total": 0, "truncated": False, "items": []},
            "maxFiles": max_files,
            "maxImports": max_imports,
            "message": f"Unexpected observation: {observation.kind}",
        }
    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "path": observation.path or ".",
        "files": {
            "shown": len(observation.files),
            "total": observation.total,
            "truncated": observation.truncated,
            "items": [_plain_data(item) for item in observation.files],
        },
        "maxFiles": max_files,
        "maxImports": max_imports,
        "message": observation.message,
    }


def _code_symbol_usage_report(
    report: dict[str, object],
    key: str,
    *,
    max_matches: int,
    max_lines: int | None = None,
    context_lines: int | None = None,
    max_bytes_per_context: int | None = None,
) -> dict[str, object]:
    report[key] = report.pop("items")
    report["maxMatches"] = max_matches
    if max_lines is not None:
        report["maxLines"] = max_lines
    if context_lines is not None:
        report["contextLines"] = context_lines
    if max_bytes_per_context is not None:
        report["maxBytesPerContext"] = max_bytes_per_context
    return report


def _code_symbol_unexpected_report(root: Path, symbol: str, path: str | None, key: str, message: str, **limits: object) -> dict[str, object]:
    report: dict[str, object] = {
        "projectRoot": str(root),
        "ok": False,
        "symbol": symbol,
        "path": path or ".",
        key: {"shown": 0, "total": 0, "truncated": False, "items": []},
        "message": message,
    }
    report.update(limits)
    return report


def get_code_refs_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    symbol: str | None = None,
    path: str | None = None,
    max_matches: int = 200,
) -> dict[str, object]:
    root, parsed_symbol, parsed_path, usage_report = _symbol_report_base(project_root, "/code-refs <symbol> [path]", parse_symbol_path_argument, argument, symbol, path)
    if usage_report is not None:
        return _code_symbol_usage_report(usage_report, "references", max_matches=max_matches)
    workspace = RunWorkspace(root=root, run_id="local-code-refs", session_dir=root / ".vibeagent" / "sessions" / "local-code-refs")
    observation = _execute_action(workspace, CodeReferencesAction(type="code_references", symbol=parsed_symbol or "", path=parsed_path, max_matches=max_matches))
    if observation.kind != "code_references":
        return _code_symbol_unexpected_report(root, parsed_symbol or "", parsed_path, "references", f"Unexpected observation: {observation.kind}", maxMatches=max_matches)
    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "symbol": observation.symbol,
        "path": observation.path or ".",
        "references": {"shown": len(observation.references), "total": observation.total, "truncated": observation.truncated, "items": [_plain_data(item) for item in observation.references]},
        "maxMatches": max_matches,
        "message": observation.message,
    }


def get_code_ref_contexts_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    symbol: str | None = None,
    path: str | None = None,
    max_matches: int = 50,
    context_lines: int = 3,
    max_bytes_per_context: int = 20_000,
) -> dict[str, object]:
    root, parsed_symbol, parsed_path, usage_report = _symbol_report_base(project_root, "/code-ref-contexts <symbol> [path]", parse_symbol_path_argument, argument, symbol, path)
    if usage_report is not None:
        return _code_symbol_usage_report(
            usage_report,
            "contexts",
            max_matches=max_matches,
            context_lines=context_lines,
            max_bytes_per_context=max_bytes_per_context,
        )
    workspace = RunWorkspace(root=root, run_id="local-code-ref-contexts", session_dir=root / ".vibeagent" / "sessions" / "local-code-ref-contexts")
    observation = _execute_action(
        workspace,
        CodeReferenceContextsAction(
            type="code_reference_contexts",
            symbol=parsed_symbol or "",
            path=parsed_path,
            max_matches=max_matches,
            context_lines=context_lines,
            max_bytes_per_context=max_bytes_per_context,
        ),
    )
    if observation.kind != "code_reference_contexts":
        return _code_symbol_unexpected_report(
            root,
            parsed_symbol or "",
            parsed_path,
            "contexts",
            f"Unexpected observation: {observation.kind}",
            maxMatches=max_matches,
            contextLines=context_lines,
            maxBytesPerContext=max_bytes_per_context,
        )
    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "symbol": observation.symbol,
        "path": observation.path or ".",
        "contexts": {"shown": len(observation.contexts), "total": observation.total, "truncated": observation.truncated, "items": [_plain_data(item) for item in observation.contexts]},
        "maxMatches": max_matches,
        "contextLines": observation.context_lines,
        "maxBytesPerContext": observation.max_bytes_per_context,
        "message": observation.message,
    }


def get_code_defs_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    symbol: str | None = None,
    path: str | None = None,
    max_matches: int = 50,
    max_lines: int = 80,
) -> dict[str, object]:
    root, parsed_symbol, parsed_path, usage_report = _symbol_report_base(project_root, "/code-defs <symbol> [path]", parse_symbol_path_argument, argument, symbol, path)
    if usage_report is not None:
        return _code_symbol_usage_report(usage_report, "definitions", max_matches=max_matches, max_lines=max_lines)
    workspace = RunWorkspace(root=root, run_id="local-code-defs", session_dir=root / ".vibeagent" / "sessions" / "local-code-defs")
    observation = _execute_action(
        workspace,
        CodeDefinitionsAction(type="code_definitions", symbol=parsed_symbol or "", path=parsed_path, max_matches=max_matches, max_lines=max_lines),
    )
    if observation.kind != "code_definitions":
        return _code_symbol_unexpected_report(
            root,
            parsed_symbol or "",
            parsed_path,
            "definitions",
            f"Unexpected observation: {observation.kind}",
            maxMatches=max_matches,
            maxLines=max_lines,
        )
    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "symbol": observation.symbol,
        "path": observation.path or ".",
        "definitions": {"shown": len(observation.definitions), "total": observation.total, "truncated": observation.truncated, "items": [_plain_data(item) for item in observation.definitions]},
        "errors": list(observation.errors),
        "maxMatches": max_matches,
        "maxLines": max_lines,
        "message": observation.message,
    }


def get_code_deps_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    max_files: int = 100,
    max_imports: int = 500,
) -> str:
    get_report = _commands_attr("get_code_deps_report", get_code_deps_report)
    formatter = _commands_attr("format_code_deps_report_text", format_code_deps_report_text)
    return formatter(get_report(project_root, argument, max_files=max_files, max_imports=max_imports))

def get_code_refs_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    symbol: str | None = None,
    path: str | None = None,
    max_matches: int = 200,
) -> str:
    get_report = _commands_attr("get_code_refs_report", get_code_refs_report)
    formatter = _commands_attr("format_code_refs_report_text", format_code_refs_report_text)
    return formatter(get_report(project_root, argument=argument, symbol=symbol, path=path, max_matches=max_matches))

def get_code_ref_contexts_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    symbol: str | None = None,
    path: str | None = None,
    max_matches: int = 50,
    context_lines: int = 3,
    max_bytes_per_context: int = 20_000,
) -> str:
    get_report = _commands_attr("get_code_ref_contexts_report", get_code_ref_contexts_report)
    formatter = _commands_attr("format_code_ref_contexts_report_text", format_code_ref_contexts_report_text)
    return formatter(
        get_report(
            project_root,
            argument=argument,
            symbol=symbol,
            path=path,
            max_matches=max_matches,
            context_lines=context_lines,
            max_bytes_per_context=max_bytes_per_context,
        )
    )

def get_code_defs_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    symbol: str | None = None,
    path: str | None = None,
    max_matches: int = 50,
    max_lines: int = 80,
) -> str:
    get_report = _commands_attr("get_code_defs_report", get_code_defs_report)
    formatter = _commands_attr("format_code_defs_report_text", format_code_defs_report_text)
    return formatter(
        get_report(
            project_root,
            argument=argument,
            symbol=symbol,
            path=path,
            max_matches=max_matches,
            max_lines=max_lines,
        )
    )

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

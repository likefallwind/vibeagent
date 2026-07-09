from __future__ import annotations

from pathlib import Path

from .smart_code_common import (
    execute_action_for_commands as _execute_action,
    format_rename_report_text as _format_rename_report_text,
    rename_observation_report as _rename_observation_report,
    rename_unexpected_report as _rename_unexpected_report,
    rename_usage_report as _rename_usage_report,
)
from .smart_python_check_commands import (
    format_python_check_report_text,
    format_python_deps_report_text,
    get_python_check_report,
    get_python_check_text,
    get_python_deps_report,
    get_python_deps_text,
)
from .smart_code_parsing import parse_rename_argument, parse_replace_python_definition_argument
from .smart_python_symbols import (
    format_python_call_graph_report_text,
    format_python_calls_report_text,
    format_python_defs_report_text,
    format_python_ref_contexts_report_text,
    format_python_refs_report_text,
    get_python_call_graph_report,
    get_python_call_graph_text,
    get_python_calls_report,
    get_python_calls_text,
    get_python_defs_report,
    get_python_defs_text,
    get_python_ref_contexts_report,
    get_python_ref_contexts_text,
    get_python_refs_report,
    get_python_refs_text,
)
from .types import (
    CheckReplacePythonDefinitionAction,
    PythonRenameAction,
    PythonRenamePreviewAction,
    ReplacePythonDefinitionAction,
)
from .workspace_core import RunWorkspace


def get_python_rename_preview_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    symbol: str | None = None,
    new_name: str | None = None,
    path: str | None = None,
    max_files: int = 100,
    max_replacements: int = 500,
) -> str:
    report = get_python_rename_preview_report(
        project_root,
        argument=argument,
        symbol=symbol,
        new_name=new_name,
        path=path,
        max_files=max_files,
        max_replacements=max_replacements,
    )
    return format_python_rename_report_text("Python rename preview:", report)


def get_python_rename_preview_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    symbol: str | None = None,
    new_name: str | None = None,
    path: str | None = None,
    max_files: int = 100,
    max_replacements: int = 500,
) -> dict[str, object]:
    usage = "/python-rename-preview <symbol> <new_name> [path]"
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
    workspace = RunWorkspace(root=root, run_id="local-python-rename-preview", session_dir=root / ".vibeagent" / "sessions" / "local-python-rename-preview")
    observation = _execute_action(
        workspace,
        PythonRenamePreviewAction(
            type="python_rename_preview",
            symbol=parsed_symbol,
            new_name=parsed_new_name,
            path=parsed_path,
            max_files=max_files,
            max_replacements=max_replacements,
        ),
    )
    if observation.kind != "python_rename_preview":
        return _rename_unexpected_report(root, parsed_symbol, parsed_new_name, parsed_path, max_files, max_replacements, f"Unexpected observation: {observation.kind}")
    return _rename_observation_report(root, observation, max_files=max_files, max_replacements=max_replacements)


def get_python_rename_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    symbol: str | None = None,
    new_name: str | None = None,
    path: str | None = None,
    max_files: int = 100,
    max_replacements: int = 2000,
) -> str:
    report = get_python_rename_report(
        project_root,
        argument=argument,
        symbol=symbol,
        new_name=new_name,
        path=path,
        max_files=max_files,
        max_replacements=max_replacements,
    )
    return format_python_rename_report_text("Python rename:", report)


def get_python_rename_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    symbol: str | None = None,
    new_name: str | None = None,
    path: str | None = None,
    max_files: int = 100,
    max_replacements: int = 2000,
) -> dict[str, object]:
    usage = "/python-rename <symbol> <new_name> [path]"
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
    workspace = RunWorkspace(root=root, run_id="local-python-rename", session_dir=root / ".vibeagent" / "sessions" / "local-python-rename")
    observation = _execute_action(
        workspace,
        PythonRenameAction(
            type="python_rename",
            symbol=parsed_symbol,
            new_name=parsed_new_name,
            path=parsed_path,
            max_files=max_files,
            max_replacements=max_replacements,
        ),
    )
    if observation.kind != "python_rename":
        return _rename_unexpected_report(root, parsed_symbol, parsed_new_name, parsed_path, max_files, max_replacements, f"Unexpected observation: {observation.kind}")
    return _rename_observation_report(root, observation, max_files=max_files, max_replacements=max_replacements)


def get_check_replace_python_definition_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    symbol: str | None = None,
    content: str | None = None,
    path: str | None = None,
) -> str:
    report = get_check_replace_python_definition_report(project_root, argument=argument, symbol=symbol, content=content, path=path)
    return format_replace_python_definition_report_text("Check replace Python definition:", report)


def get_check_replace_python_definition_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    symbol: str | None = None,
    content: str | None = None,
    path: str | None = None,
) -> dict[str, object]:
    usage = "/check-replace-python-def <symbol> <content> [path]"
    root = Path(project_root).resolve()
    try:
        parsed_symbol, parsed_content, parsed_path = parse_replace_python_definition_argument(
            argument,
            symbol=symbol,
            content=content,
            path=path,
            usage=usage,
        )
    except ValueError as error:
        return _replace_python_definition_usage_report(root, usage, symbol, path, str(error))
    workspace = RunWorkspace(root=root, run_id="local-check-replace-python-def", session_dir=root / ".vibeagent" / "sessions" / "local-check-replace-python-def")
    observation = _execute_action(
        workspace,
        CheckReplacePythonDefinitionAction(
            type="check_replace_python_definition",
            symbol=parsed_symbol,
            content=parsed_content,
            path=parsed_path,
        ),
    )
    if observation.kind != "check_replace_python_definition":
        return _replace_python_definition_unexpected_report(root, parsed_symbol, parsed_path, f"Unexpected observation: {observation.kind}")
    return _replace_python_definition_observation_report(root, observation)


def get_replace_python_definition_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    symbol: str | None = None,
    content: str | None = None,
    path: str | None = None,
) -> str:
    report = get_replace_python_definition_report(project_root, argument=argument, symbol=symbol, content=content, path=path)
    return format_replace_python_definition_report_text("Replace Python definition:", report)


def get_replace_python_definition_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    symbol: str | None = None,
    content: str | None = None,
    path: str | None = None,
) -> dict[str, object]:
    usage = "/replace-python-def <symbol> <content> [path]"
    root = Path(project_root).resolve()
    try:
        parsed_symbol, parsed_content, parsed_path = parse_replace_python_definition_argument(
            argument,
            symbol=symbol,
            content=content,
            path=path,
            usage=usage,
        )
    except ValueError as error:
        return _replace_python_definition_usage_report(root, usage, symbol, path, str(error))
    workspace = RunWorkspace(root=root, run_id="local-replace-python-def", session_dir=root / ".vibeagent" / "sessions" / "local-replace-python-def")
    observation = _execute_action(
        workspace,
        ReplacePythonDefinitionAction(
            type="replace_python_definition",
            symbol=parsed_symbol,
            content=parsed_content,
            path=parsed_path,
        ),
    )
    if observation.kind != "replace_python_definition":
        return _replace_python_definition_unexpected_report(root, parsed_symbol, parsed_path, f"Unexpected observation: {observation.kind}")
    return _replace_python_definition_observation_report(root, observation)


def _replace_python_definition_usage_report(root: Path, usage: str, symbol: str | None, path: str | None, error: str) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": False,
        "symbol": symbol or "",
        "path": path or ".",
        "definition": {"qualifiedName": None, "path": None, "startLine": None, "endLine": None},
        "diff": "",
        "message": f"Usage: {usage}\nError: {error}",
    }


def _replace_python_definition_unexpected_report(root: Path, symbol: str, path: str | None, message: str) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": False,
        "symbol": symbol,
        "path": path or ".",
        "definition": {"qualifiedName": None, "path": None, "startLine": None, "endLine": None},
        "diff": "",
        "message": message,
    }


def _replace_python_definition_observation_report(root: Path, observation: object) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": bool(getattr(observation, "ok")),
        "symbol": getattr(observation, "symbol"),
        "path": getattr(observation, "path") or ".",
        "definition": {
            "qualifiedName": getattr(observation, "qualified_name"),
            "path": getattr(observation, "definition_path"),
            "startLine": getattr(observation, "start_line"),
            "endLine": getattr(observation, "end_line"),
        },
        "diff": str(getattr(observation, "diff", "")),
        "message": str(getattr(observation, "message")),
    }


def format_replace_python_definition_report_text(title: str, report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    definition = report.get("definition") if isinstance(report.get("definition"), dict) else {}
    diff = str(report.get("diff") or "")
    lines = [
        title,
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  symbol: {report.get('symbol') or ''}",
        f"  path: {report.get('path') or '.'}",
        f"  definition: {definition.get('qualifiedName') or '-'}",
        f"  definitionPath: {definition.get('path') or '-'}",
        f"  lines: {definition.get('startLine') or '-'}:{definition.get('endLine') or '-'}",
        f"  message: {message}",
    ]
    if diff:
        lines.append("  diff:")
        lines.extend(f"    {diff_line}" for diff_line in diff.splitlines())
    return "\n".join(lines)


def format_replace_python_definition_observation(title: str, root: Path, observation: object) -> str:
    return format_replace_python_definition_report_text(title, _replace_python_definition_observation_report(root, observation))


def format_python_rename_report_text(title: str, report: dict[str, object]) -> str:
    return _format_rename_report_text(title, report, include_language=False)


def format_python_rename_observation(title: str, root: Path, observation: object) -> str:
    return format_python_rename_report_text(title, _rename_observation_report(root, observation, max_files=100, max_replacements=2000))

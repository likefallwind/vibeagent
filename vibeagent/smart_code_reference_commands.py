from __future__ import annotations

from pathlib import Path

from .smart_code_common import (
    commands_attr as _commands_attr,
    execute_action_for_commands as _execute_action,
    plain_data as _plain_data,
    symbol_report_base as _symbol_report_base,
)
from .smart_code_formatting import (
    format_code_defs_report_text,
    format_code_ref_contexts_report_text,
    format_code_refs_report_text,
)
from .local_command_workspace import local_command_workspace
from .smart_code_parsing import parse_symbol_path_argument
from .types import CodeDefinitionsAction, CodeReferenceContextsAction, CodeReferencesAction


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
    workspace = local_command_workspace(root, "local-code-refs")
    observation = _execute_action(workspace, CodeReferencesAction(type="code_references", symbol=parsed_symbol or "", path=parsed_path, max_matches=max_matches))
    if observation.kind != "code_references":
        return _code_symbol_unexpected_report(root, parsed_symbol or "", parsed_path, "references", f"Unexpected observation: {observation.kind}", maxMatches=max_matches)
    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "symbol": observation.symbol,
        "path": observation.path or ".",
        "references": {
            "shown": len(observation.references),
            "total": observation.total,
            "truncated": observation.truncated,
            "items": [_plain_data(item) for item in observation.references],
        },
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
    workspace = local_command_workspace(root, "local-code-ref-contexts")
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
        "contexts": {
            "shown": len(observation.contexts),
            "total": observation.total,
            "truncated": observation.truncated,
            "items": [_plain_data(item) for item in observation.contexts],
        },
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
    workspace = local_command_workspace(root, "local-code-defs")
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
        "definitions": {
            "shown": len(observation.definitions),
            "total": observation.total,
            "truncated": observation.truncated,
            "items": [_plain_data(item) for item in observation.definitions],
        },
        "errors": list(observation.errors),
        "maxMatches": max_matches,
        "maxLines": max_lines,
        "message": observation.message,
    }


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

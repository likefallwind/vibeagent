from __future__ import annotations

import argparse
from typing import Any

from .cli_local_result import local_text_or_report


def run_python_local_flag(
    args: argparse.Namespace,
    project_root: Any,
    commands: dict[str, Any],
) -> tuple[str, dict[str, object]] | None:
    root = project_root or "."
    if args.python_check is not None:
        return local_text_or_report(
            args,
            "pythonCheck",
            lambda: commands["get_python_check_report"](root, args.python_check or None),
            commands["format_python_check_report_text"],
            lambda: commands["get_python_check_text"](root, args.python_check or None),
        )
    if args.python_deps is not None:
        python_deps_kwargs = {}
        if args.python_deps_max_files is not None:
            python_deps_kwargs["max_files"] = args.python_deps_max_files
        if args.python_deps_max_imports is not None:
            python_deps_kwargs["max_imports"] = args.python_deps_max_imports
        return local_text_or_report(
            args,
            "pythonDependencies",
            lambda: commands["get_python_deps_report"](root, args.python_deps or None, **python_deps_kwargs),
            commands["format_python_deps_report_text"],
            lambda: commands["get_python_deps_text"](root, args.python_deps or None, **python_deps_kwargs),
        )
    if args.python_defs is not None:
        python_kwargs = {}
        if args.python_max_matches is not None:
            python_kwargs["max_matches"] = args.python_max_matches
        if args.python_def_max_lines is not None:
            python_kwargs["max_lines"] = args.python_def_max_lines
        return local_text_or_report(
            args,
            "pythonDefinitions",
            lambda: commands["get_python_defs_report"](
                root,
                symbol=args.python_defs,
                path=args.python_path,
                **python_kwargs,
            ),
            commands["format_python_defs_report_text"],
            lambda: commands["get_python_defs_text"](
                root,
                symbol=args.python_defs,
                path=args.python_path,
                **python_kwargs,
            ),
        )
    if args.python_refs is not None:
        python_kwargs = {}
        if args.python_max_matches is not None:
            python_kwargs["max_matches"] = args.python_max_matches
        return local_text_or_report(
            args,
            "pythonReferences",
            lambda: commands["get_python_refs_report"](
                root,
                symbol=args.python_refs,
                path=args.python_path,
                **python_kwargs,
            ),
            commands["format_python_refs_report_text"],
            lambda: commands["get_python_refs_text"](
                root,
                symbol=args.python_refs,
                path=args.python_path,
                **python_kwargs,
            ),
        )
    if args.python_ref_contexts is not None:
        python_kwargs = {}
        if args.python_max_matches is not None:
            python_kwargs["max_matches"] = args.python_max_matches
        if args.python_context_lines is not None:
            python_kwargs["context_lines"] = args.python_context_lines
        if args.python_context_max_bytes is not None:
            python_kwargs["max_bytes_per_context"] = args.python_context_max_bytes
        return local_text_or_report(
            args,
            "pythonReferenceContexts",
            lambda: commands["get_python_ref_contexts_report"](
                root,
                symbol=args.python_ref_contexts,
                path=args.python_path,
                **python_kwargs,
            ),
            commands["format_python_ref_contexts_report_text"],
            lambda: commands["get_python_ref_contexts_text"](
                root,
                symbol=args.python_ref_contexts,
                path=args.python_path,
                **python_kwargs,
            ),
        )
    if args.python_calls is not None:
        python_kwargs = {}
        if args.python_max_matches is not None:
            python_kwargs["max_matches"] = args.python_max_matches
        return local_text_or_report(
            args,
            "pythonCalls",
            lambda: commands["get_python_calls_report"](
                root,
                symbol=args.python_calls,
                path=args.python_path,
                **python_kwargs,
            ),
            commands["format_python_calls_report_text"],
            lambda: commands["get_python_calls_text"](
                root,
                symbol=args.python_calls,
                path=args.python_path,
                **python_kwargs,
            ),
        )
    if args.python_call_graph is not None:
        python_call_graph_kwargs = {}
        if args.python_call_graph_max_files is not None:
            python_call_graph_kwargs["max_files"] = args.python_call_graph_max_files
        if args.python_call_graph_max_edges is not None:
            python_call_graph_kwargs["max_edges"] = args.python_call_graph_max_edges
        return local_text_or_report(
            args,
            "pythonCallGraph",
            lambda: commands["get_python_call_graph_report"](root, args.python_call_graph or None, **python_call_graph_kwargs),
            commands["format_python_call_graph_report_text"],
            lambda: commands["get_python_call_graph_text"](root, args.python_call_graph or None, **python_call_graph_kwargs),
        )
    if args.python_rename_preview is not None:
        python_rename_kwargs = {
            "symbol": args.python_rename_preview[0],
            "new_name": args.python_rename_preview[1],
            "path": args.python_path,
        }
        return local_text_or_report(
            args,
            "pythonRenamePreview",
            lambda: commands["get_python_rename_preview_report"](root, **python_rename_kwargs),
            lambda report: commands["format_python_rename_report_text"]("Python rename preview:", report),
            lambda: commands["get_python_rename_preview_text"](root, **python_rename_kwargs),
        )
    if args.python_rename is not None:
        python_rename_kwargs = {
            "symbol": args.python_rename[0],
            "new_name": args.python_rename[1],
            "path": args.python_path,
        }
        return local_text_or_report(
            args,
            "pythonRename",
            lambda: commands["get_python_rename_report"](root, **python_rename_kwargs),
            lambda report: commands["format_python_rename_report_text"]("Python rename:", report),
            lambda: commands["get_python_rename_text"](root, **python_rename_kwargs),
        )
    if args.check_replace_python_def is not None:
        replace_definition_kwargs = {
            "symbol": args.check_replace_python_def[0],
            "content": args.check_replace_python_def[1],
            "path": args.python_path,
        }
        return local_text_or_report(
            args,
            "checkReplacePythonDefinition",
            lambda: commands["get_check_replace_python_definition_report"](root, **replace_definition_kwargs),
            lambda report: commands["format_replace_python_definition_report_text"](
                "Check replace Python definition:",
                report,
            ),
            lambda: commands["get_check_replace_python_definition_text"](root, **replace_definition_kwargs),
        )
    if args.replace_python_def is not None:
        replace_definition_kwargs = {
            "symbol": args.replace_python_def[0],
            "content": args.replace_python_def[1],
            "path": args.python_path,
        }
        return local_text_or_report(
            args,
            "replacePythonDefinition",
            lambda: commands["get_replace_python_definition_report"](root, **replace_definition_kwargs),
            lambda report: commands["format_replace_python_definition_report_text"](
                "Replace Python definition:",
                report,
            ),
            lambda: commands["get_replace_python_definition_text"](root, **replace_definition_kwargs),
        )
    return None


def run_code_intel_local_flag(
    args: argparse.Namespace,
    project_root: Any,
    commands: dict[str, Any],
) -> tuple[str, dict[str, object]] | None:
    root = project_root or "."
    if args.code_deps is not None:
        return local_text_or_report(
            args,
            "codeDependencies",
            lambda: commands["get_code_deps_report"](root, args.code_deps or None),
            commands["format_code_deps_report_text"],
            lambda: commands["get_code_deps_text"](root, args.code_deps or None),
        )
    if args.code_refs is not None:
        code_kwargs = {}
        if args.code_max_matches is not None:
            code_kwargs["max_matches"] = args.code_max_matches
        return local_text_or_report(
            args,
            "codeReferences",
            lambda: commands["get_code_refs_report"](
                root,
                symbol=args.code_refs,
                path=args.code_path,
                **code_kwargs,
            ),
            commands["format_code_refs_report_text"],
            lambda: commands["get_code_refs_text"](
                root,
                symbol=args.code_refs,
                path=args.code_path,
                **code_kwargs,
            ),
        )
    if args.code_ref_contexts is not None:
        code_kwargs = {}
        if args.code_max_matches is not None:
            code_kwargs["max_matches"] = args.code_max_matches
        if args.code_context_lines is not None:
            code_kwargs["context_lines"] = args.code_context_lines
        if args.code_context_max_bytes is not None:
            code_kwargs["max_bytes_per_context"] = args.code_context_max_bytes
        return local_text_or_report(
            args,
            "codeReferenceContexts",
            lambda: commands["get_code_ref_contexts_report"](
                root,
                symbol=args.code_ref_contexts,
                path=args.code_path,
                **code_kwargs,
            ),
            commands["format_code_ref_contexts_report_text"],
            lambda: commands["get_code_ref_contexts_text"](
                root,
                symbol=args.code_ref_contexts,
                path=args.code_path,
                **code_kwargs,
            ),
        )
    if args.code_defs is not None:
        code_kwargs = {}
        if args.code_max_matches is not None:
            code_kwargs["max_matches"] = args.code_max_matches
        if args.code_def_max_lines is not None:
            code_kwargs["max_lines"] = args.code_def_max_lines
        return local_text_or_report(
            args,
            "codeDefinitions",
            lambda: commands["get_code_defs_report"](
                root,
                symbol=args.code_defs,
                path=args.code_path,
                **code_kwargs,
            ),
            commands["format_code_defs_report_text"],
            lambda: commands["get_code_defs_text"](
                root,
                symbol=args.code_defs,
                path=args.code_path,
                **code_kwargs,
            ),
        )
    if args.code_rename_preview is not None:
        code_rename_kwargs = {
            "symbol": args.code_rename_preview[0],
            "new_name": args.code_rename_preview[1],
            "path": args.code_path,
        }
        return local_text_or_report(
            args,
            "codeRenamePreview",
            lambda: commands["get_code_rename_preview_report"](root, **code_rename_kwargs),
            lambda report: commands["format_code_rename_report_text"]("Code rename preview:", report),
            lambda: commands["get_code_rename_preview_text"](root, **code_rename_kwargs),
        )
    if args.code_rename is not None:
        code_rename_kwargs = {
            "symbol": args.code_rename[0],
            "new_name": args.code_rename[1],
            "path": args.code_path,
        }
        return local_text_or_report(
            args,
            "codeRename",
            lambda: commands["get_code_rename_report"](root, **code_rename_kwargs),
            lambda report: commands["format_code_rename_report_text"]("Code rename:", report),
            lambda: commands["get_code_rename_text"](root, **code_rename_kwargs),
        )
    return None


def _symbol_text(
    command: Any,
    commands: dict[str, Any],
    command_name: str,
    getter_name: str,
    *,
    include_context: bool = False,
    include_max_lines: bool = False,
) -> str:
    symbol, path, kwargs, error, uses_named_options = commands["parse_interactive_python_symbol_argument"](
        command.argument,
        command_name=command_name,
        include_context=include_context,
        include_max_lines=include_max_lines,
    )
    if error:
        return error
    if uses_named_options:
        return commands[getter_name](symbol=symbol, path=path, **kwargs)
    return commands[getter_name](argument=command.argument)


SIMPLE_CODE_INTEL_COMMANDS: dict[str, str] = {
    "python_check": "get_python_check_text",
    "python_rename_preview": "get_python_rename_preview_text",
    "python_rename": "get_python_rename_text",
    "check_replace_python_definition": "get_check_replace_python_definition_text",
    "replace_python_definition": "get_replace_python_definition_text",
    "code_deps": "get_code_deps_text",
    "code_rename_preview": "get_code_rename_preview_text",
    "code_rename": "get_code_rename_text",
}


def run_interactive_code_intel_command(command: Any, commands: dict[str, Any]) -> str | None:
    simple_getter = SIMPLE_CODE_INTEL_COMMANDS.get(command.type)
    if simple_getter is not None:
        return commands[simple_getter](argument=command.argument)
    if command.type == "python_deps":
        path, kwargs, error, uses_named_options = commands["parse_interactive_python_deps_argument"](command.argument)
        if error:
            return error
        if uses_named_options:
            return commands["get_python_deps_text"](argument=path, **kwargs)
        return commands["get_python_deps_text"](argument=command.argument)
    if command.type == "python_call_graph":
        path, kwargs, error, uses_named_options = commands["parse_interactive_python_call_graph_argument"](command.argument)
        if error:
            return error
        if uses_named_options:
            return commands["get_python_call_graph_text"](argument=path, **kwargs)
        return commands["get_python_call_graph_text"](argument=command.argument)
    if command.type == "python_defs":
        return _symbol_text(
            command,
            commands,
            "python-defs",
            "get_python_defs_text",
            include_max_lines=True,
        )
    if command.type == "python_refs":
        return _symbol_text(command, commands, "python-refs", "get_python_refs_text")
    if command.type == "python_ref_contexts":
        return _symbol_text(
            command,
            commands,
            "python-ref-contexts",
            "get_python_ref_contexts_text",
            include_context=True,
        )
    if command.type == "python_calls":
        return _symbol_text(command, commands, "python-calls", "get_python_calls_text")
    if command.type == "code_refs":
        return _symbol_text(command, commands, "code-refs", "get_code_refs_text")
    if command.type == "code_ref_contexts":
        return _symbol_text(
            command,
            commands,
            "code-ref-contexts",
            "get_code_ref_contexts_text",
            include_context=True,
        )
    if command.type == "code_defs":
        return _symbol_text(
            command,
            commands,
            "code-defs",
            "get_code_defs_text",
            include_max_lines=True,
        )
    return None

from __future__ import annotations

import argparse
from typing import Any

from .cli_code_intel_interactive import run_interactive_code_intel_command
from .cli_code_intel_kwargs import (
    build_code_rename_kwargs,
    build_code_symbol_kwargs,
    build_python_call_graph_kwargs,
    build_python_deps_kwargs,
    build_python_rename_kwargs,
    build_python_symbol_kwargs,
    build_replace_python_definition_kwargs,
)
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
        python_deps_kwargs = build_python_deps_kwargs(args)
        return local_text_or_report(
            args,
            "pythonDependencies",
            lambda: commands["get_python_deps_report"](root, args.python_deps or None, **python_deps_kwargs),
            commands["format_python_deps_report_text"],
            lambda: commands["get_python_deps_text"](root, args.python_deps or None, **python_deps_kwargs),
        )
    if args.python_defs is not None:
        python_kwargs = build_python_symbol_kwargs(args, include_max_lines=True)
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
        python_kwargs = build_python_symbol_kwargs(args)
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
        python_kwargs = build_python_symbol_kwargs(args, include_context=True)
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
        python_kwargs = build_python_symbol_kwargs(args)
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
        python_call_graph_kwargs = build_python_call_graph_kwargs(args)
        return local_text_or_report(
            args,
            "pythonCallGraph",
            lambda: commands["get_python_call_graph_report"](root, args.python_call_graph or None, **python_call_graph_kwargs),
            commands["format_python_call_graph_report_text"],
            lambda: commands["get_python_call_graph_text"](root, args.python_call_graph or None, **python_call_graph_kwargs),
        )
    if args.python_rename_preview is not None:
        python_rename_kwargs = build_python_rename_kwargs(args, args.python_rename_preview)
        return local_text_or_report(
            args,
            "pythonRenamePreview",
            lambda: commands["get_python_rename_preview_report"](root, **python_rename_kwargs),
            lambda report: commands["format_python_rename_report_text"]("Python rename preview:", report),
            lambda: commands["get_python_rename_preview_text"](root, **python_rename_kwargs),
        )
    if args.python_rename is not None:
        python_rename_kwargs = build_python_rename_kwargs(args, args.python_rename)
        return local_text_or_report(
            args,
            "pythonRename",
            lambda: commands["get_python_rename_report"](root, **python_rename_kwargs),
            lambda report: commands["format_python_rename_report_text"]("Python rename:", report),
            lambda: commands["get_python_rename_text"](root, **python_rename_kwargs),
        )
    if args.check_replace_python_def is not None:
        replace_definition_kwargs = build_replace_python_definition_kwargs(args, args.check_replace_python_def)
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
        replace_definition_kwargs = build_replace_python_definition_kwargs(args, args.replace_python_def)
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
        code_kwargs = build_code_symbol_kwargs(args)
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
        code_kwargs = build_code_symbol_kwargs(args, include_context=True)
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
        code_kwargs = build_code_symbol_kwargs(args, include_max_lines=True)
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
        code_rename_kwargs = build_code_rename_kwargs(args, args.code_rename_preview)
        return local_text_or_report(
            args,
            "codeRenamePreview",
            lambda: commands["get_code_rename_preview_report"](root, **code_rename_kwargs),
            lambda report: commands["format_code_rename_report_text"]("Code rename preview:", report),
            lambda: commands["get_code_rename_preview_text"](root, **code_rename_kwargs),
        )
    if args.code_rename is not None:
        code_rename_kwargs = build_code_rename_kwargs(args, args.code_rename)
        return local_text_or_report(
            args,
            "codeRename",
            lambda: commands["get_code_rename_report"](root, **code_rename_kwargs),
            lambda report: commands["format_code_rename_report_text"]("Code rename:", report),
            lambda: commands["get_code_rename_text"](root, **code_rename_kwargs),
        )
    return None

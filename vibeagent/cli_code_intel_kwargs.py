from __future__ import annotations

from typing import Any


def build_python_deps_kwargs(args: Any) -> dict[str, object]:
    return _include_not_none(
        args,
        {
            "python_deps_max_files": "max_files",
            "python_deps_max_imports": "max_imports",
        },
    )


def build_python_symbol_kwargs(args: Any, *, include_context: bool = False, include_max_lines: bool = False) -> dict[str, object]:
    kwargs = _include_not_none(args, {"python_max_matches": "max_matches"})
    if include_context:
        kwargs.update(
            _include_not_none(
                args,
                {
                    "python_context_lines": "context_lines",
                    "python_context_max_bytes": "max_bytes_per_context",
                },
            )
        )
    if include_max_lines:
        kwargs.update(_include_not_none(args, {"python_def_max_lines": "max_lines"}))
    return kwargs


def build_python_call_graph_kwargs(args: Any) -> dict[str, object]:
    return _include_not_none(
        args,
        {
            "python_call_graph_max_files": "max_files",
            "python_call_graph_max_edges": "max_edges",
        },
    )


def build_python_rename_kwargs(args: Any, values: list[str]) -> dict[str, object]:
    return {"symbol": values[0], "new_name": values[1], "path": args.python_path}


def build_replace_python_definition_kwargs(args: Any, values: list[str]) -> dict[str, object]:
    return {"symbol": values[0], "content": values[1], "path": args.python_path}


def build_code_symbol_kwargs(args: Any, *, include_context: bool = False, include_max_lines: bool = False) -> dict[str, object]:
    kwargs = _include_not_none(args, {"code_max_matches": "max_matches"})
    if include_context:
        kwargs.update(
            _include_not_none(
                args,
                {
                    "code_context_lines": "context_lines",
                    "code_context_max_bytes": "max_bytes_per_context",
                },
            )
        )
    if include_max_lines:
        kwargs.update(_include_not_none(args, {"code_def_max_lines": "max_lines"}))
    return kwargs


def build_code_rename_kwargs(args: Any, values: list[str]) -> dict[str, object]:
    return {"symbol": values[0], "new_name": values[1], "path": args.code_path}


def _include_not_none(args: Any, mapping: dict[str, str]) -> dict[str, object]:
    return {target: value for source, target in mapping.items() if (value := getattr(args, source)) is not None}

from __future__ import annotations

from typing import Any

from .action_parsing_helpers import (
    ActionParseError,
    parse_nonnegative_int,
    parse_optional_positive_int,
    parse_path_list,
    parse_read_file_contexts,
    parse_read_file_paths,
    parse_read_file_ranges,
)
from .action_tool_alias_utils import truthy_alias_bool
from .types import (
    CodeOutlineAction,
    ConfigCheckAction,
    FileInfoAction,
    ImageInfoAction,
    ViewImageAction,
    ListFilesAction,
    ListTreeAction,
    NotebookReadAction,
    OutputContextsAction,
    OutputDiagnosticsAction,
    PythonCheckAction,
    PythonSymbolsAction,
    ReadFileAction,
    ReadFileContextAction,
    ReadFileContextsAction,
    ReadFileRangesAction,
    ReadFilesAction,
    RepoMapAction,
    TailFileAction,
)


READ_ACTION_TYPES = {
    "list_files",
    "list_tree",
    "repo_map",
    "read_file",
    "notebook_read",
    "read_file_context",
    "read_file_contexts",
    "output_contexts",
    "output_diagnostics",
    "python_traceback",
    "tail_file",
    "read_files",
    "read_file_ranges",
    "file_info",
    "image_info",
    "view_image",
    "python_symbols",
    "code_outline",
    "python_check",
    "config_check",
}


def parse_read_action(action_type: object, value: dict[str, Any], raw: str) -> object | None:
    if action_type not in READ_ACTION_TYPES:
        return None

    if action_type == "list_files":
        path = value.get("path")
        if path is not None and not isinstance(path, str):
            raise ActionParseError("list_files action path must be a string when provided.", raw)
        return ListFilesAction(type="list_files", path=path)

    if action_type == "list_tree":
        path = value.get("path")
        max_depth = value.get("max_depth", 3)
        max_entries = value.get("max_entries", 200)
        ignore = value.get("ignore", ())
        if path is not None and not isinstance(path, str):
            raise ActionParseError("list_tree action path must be a string when provided.", raw)
        if not isinstance(ignore, (list, tuple)):
            raise ActionParseError("list_tree action ignore must be a list of strings when provided.", raw)
        ignore_patterns = tuple(item.strip() for item in ignore if isinstance(item, str) and item.strip())
        if len(ignore_patterns) != len(ignore):
            raise ActionParseError("list_tree action ignore must be a list of non-empty strings.", raw)
        max_depth = parse_optional_positive_int(max_depth, "max_depth", raw, maximum=10) or 3
        max_entries = parse_optional_positive_int(max_entries, "max_entries", raw, maximum=1000) or 200
        return ListTreeAction(
            type="list_tree",
            path=path,
            max_depth=max_depth,
            max_entries=max_entries,
            ignore=ignore_patterns,
        )

    if action_type == "repo_map":
        path = value.get("path")
        max_depth = value.get("max_depth", 3)
        max_files = value.get("max_files", 80)
        max_symbols = value.get("max_symbols", 120)
        if path is not None and not isinstance(path, str):
            raise ActionParseError("repo_map action path must be a string when provided.", raw)
        max_depth = parse_optional_positive_int(max_depth, "max_depth", raw, maximum=10) or 3
        max_files = parse_optional_positive_int(max_files, "max_files", raw, maximum=500) or 80
        max_symbols = parse_optional_positive_int(max_symbols, "max_symbols", raw, maximum=500) or 120
        return RepoMapAction(
            type="repo_map",
            path=path,
            max_depth=max_depth,
            max_files=max_files,
            max_symbols=max_symbols,
        )

    if action_type == "read_file":
        path = value.get("path")
        if not isinstance(path, str):
            raise ActionParseError("read_file action requires a string path.", raw)
        start_line = parse_optional_positive_int(value.get("start_line"), "start_line", raw, maximum=None)
        line_count = parse_optional_positive_int(value.get("line_count"), "line_count", raw, maximum=1000)
        max_bytes = parse_optional_positive_int(value.get("max_bytes", 20_000), "max_bytes", raw, maximum=200_000) or 20_000
        show_line_numbers = value.get("show_line_numbers", False)
        if not isinstance(show_line_numbers, bool):
            raise ActionParseError("read_file action show_line_numbers must be a boolean when provided.", raw)
        if max_bytes < 1000:
            raise ActionParseError("max_bytes must be at least 1000.", raw)
        if line_count is not None and start_line is None:
            raise ActionParseError("read_file action line_count requires start_line.", raw)
        return ReadFileAction(
            type="read_file",
            path=path,
            start_line=start_line,
            line_count=line_count,
            max_bytes=max_bytes,
            show_line_numbers=show_line_numbers,
        )

    if action_type == "notebook_read":
        path = value.get("path")
        if not isinstance(path, str):
            raise ActionParseError("notebook_read action requires a string path.", raw)
        return NotebookReadAction(
            type="notebook_read",
            path=path,
            start_cell=parse_optional_positive_int(value.get("start_cell"), "start_cell", raw, maximum=10_000) or 1,
            cell_count=parse_optional_positive_int(value.get("cell_count"), "cell_count", raw, maximum=200) or 50,
            include_outputs=truthy_alias_bool(value.get("include_outputs")),
            max_source_chars=parse_optional_positive_int(value.get("max_source_chars"), "max_source_chars", raw, maximum=20_000) or 2_000,
        )

    if action_type == "read_file_context":
        path = value.get("path")
        if not isinstance(path, str):
            raise ActionParseError("read_file_context action requires a string path.", raw)
        line = parse_optional_positive_int(value.get("line"), "line", raw, maximum=None)
        if line is None:
            raise ActionParseError("read_file_context action requires line.", raw)
        context_lines = parse_nonnegative_int(value.get("context_lines", 20), "context_lines", raw, maximum=500)
        max_bytes = parse_optional_positive_int(value.get("max_bytes", 20_000), "max_bytes", raw, maximum=200_000) or 20_000
        if max_bytes < 1000:
            raise ActionParseError("max_bytes must be at least 1000.", raw)
        return ReadFileContextAction(
            type="read_file_context",
            path=path,
            line=line,
            context_lines=context_lines,
            max_bytes=max_bytes,
        )

    if action_type == "read_file_contexts":
        max_bytes_per_context = parse_optional_positive_int(
            value.get("max_bytes_per_context", 20_000),
            "max_bytes_per_context",
            raw,
            maximum=200_000,
        ) or 20_000
        if max_bytes_per_context < 1000:
            raise ActionParseError("max_bytes_per_context must be at least 1000.", raw)
        return ReadFileContextsAction(
            type="read_file_contexts",
            contexts=parse_read_file_contexts(value.get("contexts"), raw),
            max_bytes_per_context=max_bytes_per_context,
        )

    if action_type == "output_contexts":
        text = value.get("text")
        if not isinstance(text, str) or not text.strip():
            raise ActionParseError("output_contexts action requires non-empty text.", raw)
        if len(text) > 200_000:
            raise ActionParseError("output_contexts text must be at most 200000 characters.", raw)
        context_lines = parse_nonnegative_int(value.get("context_lines", 5), "context_lines", raw, maximum=500)
        parse_optional_positive_int(value.get("max_diagnostics", 50), "max_diagnostics", raw, maximum=200)
        max_contexts = parse_optional_positive_int(value.get("max_contexts", 20), "max_contexts", raw, maximum=100) or 20
        max_bytes_per_context = parse_optional_positive_int(
            value.get("max_bytes_per_context", 20_000),
            "max_bytes_per_context",
            raw,
            maximum=200_000,
        ) or 20_000
        if max_bytes_per_context < 1000:
            raise ActionParseError("max_bytes_per_context must be at least 1000.", raw)
        return OutputContextsAction(
            type="output_contexts",
            text=text,
            context_lines=context_lines,
            max_contexts=max_contexts,
            max_bytes_per_context=max_bytes_per_context,
        )

    if action_type in {"output_diagnostics", "python_traceback"}:
        label = "python_traceback" if action_type == "python_traceback" else "output_diagnostics"
        text = value.get("text")
        if not isinstance(text, str) or not text.strip():
            raise ActionParseError(f"{label} action requires non-empty text.", raw)
        if len(text) > 200_000:
            raise ActionParseError(f"{label} text must be at most 200000 characters.", raw)
        context_lines = parse_nonnegative_int(value.get("context_lines", 2), "context_lines", raw, maximum=500)
        max_diagnostics = parse_optional_positive_int(value.get("max_diagnostics", 50), "max_diagnostics", raw, maximum=200) or 50
        max_contexts = parse_optional_positive_int(value.get("max_contexts", 20), "max_contexts", raw, maximum=100) or 20
        max_bytes_per_context = parse_optional_positive_int(
            value.get("max_bytes_per_context", 20_000),
            "max_bytes_per_context",
            raw,
            maximum=200_000,
        ) or 20_000
        if max_bytes_per_context < 1000:
            raise ActionParseError("max_bytes_per_context must be at least 1000.", raw)
        return OutputDiagnosticsAction(
            type="output_diagnostics",
            text=text,
            context_lines=context_lines,
            max_diagnostics=max_diagnostics,
            max_contexts=max_contexts,
            max_bytes_per_context=max_bytes_per_context,
        )

    if action_type == "tail_file":
        path = value.get("path")
        if not isinstance(path, str):
            raise ActionParseError("tail_file action requires a string path.", raw)
        line_count = parse_optional_positive_int(value.get("line_count", 80), "line_count", raw, maximum=1000) or 80
        max_bytes = parse_optional_positive_int(value.get("max_bytes", 20_000), "max_bytes", raw, maximum=200_000) or 20_000
        if max_bytes < 1000:
            raise ActionParseError("max_bytes must be at least 1000.", raw)
        return TailFileAction(type="tail_file", path=path, line_count=line_count, max_bytes=max_bytes)

    if action_type == "read_files":
        max_bytes_per_file = parse_optional_positive_int(
            value.get("max_bytes_per_file", 20_000),
            "max_bytes_per_file",
            raw,
            maximum=200_000,
        ) or 20_000
        if max_bytes_per_file < 1000:
            raise ActionParseError("max_bytes_per_file must be at least 1000.", raw)
        show_line_numbers = value.get("show_line_numbers", False)
        if not isinstance(show_line_numbers, bool):
            raise ActionParseError("read_files action show_line_numbers must be a boolean when provided.", raw)
        return ReadFilesAction(
            type="read_files",
            paths=parse_read_file_paths(value.get("paths"), raw),
            max_bytes_per_file=max_bytes_per_file,
            show_line_numbers=show_line_numbers,
        )

    if action_type == "read_file_ranges":
        max_bytes_per_range = parse_optional_positive_int(
            value.get("max_bytes_per_range", 20_000),
            "max_bytes_per_range",
            raw,
            maximum=200_000,
        ) or 20_000
        if max_bytes_per_range < 1000:
            raise ActionParseError("max_bytes_per_range must be at least 1000.", raw)
        return ReadFileRangesAction(
            type="read_file_ranges",
            ranges=parse_read_file_ranges(value.get("ranges"), raw),
            max_bytes_per_range=max_bytes_per_range,
        )

    if action_type == "file_info":
        return FileInfoAction(type="file_info", paths=parse_path_list(value.get("paths"), raw, "file_info", maximum=50))

    if action_type == "image_info":
        return ImageInfoAction(type="image_info", paths=parse_path_list(value.get("paths"), raw, "image_info", maximum=20))

    if action_type == "view_image":
        path = value.get("path")
        if not isinstance(path, str) or not path.strip():
            raise ActionParseError("view_image action requires a non-empty path.", raw)
        max_bytes = parse_optional_positive_int(
            value.get("max_bytes", 5_000_000), "max_bytes", raw, maximum=5_000_000
        ) or 5_000_000
        return ViewImageAction(type="view_image", path=path.strip(), max_bytes=max_bytes)

    if action_type == "python_symbols":
        return PythonSymbolsAction(
            type="python_symbols",
            paths=parse_path_list(value.get("paths"), raw, "python_symbols", maximum=20),
        )

    if action_type == "code_outline":
        max_symbols = parse_optional_positive_int(value.get("max_symbols", 200), "max_symbols", raw, maximum=1000) or 200
        return CodeOutlineAction(
            type="code_outline",
            paths=parse_path_list(value.get("paths"), raw, "code_outline", maximum=20),
            max_symbols=max_symbols,
        )

    if action_type == "python_check":
        path = value.get("path")
        max_files = value.get("max_files", 200)
        if path is not None and not isinstance(path, str):
            raise ActionParseError("python_check action path must be a string when provided.", raw)
        max_files = parse_optional_positive_int(max_files, "max_files", raw, maximum=500) or 200
        return PythonCheckAction(type="python_check", path=path, max_files=max_files)

    if action_type == "config_check":
        path = value.get("path")
        max_files = value.get("max_files", 200)
        if path is not None and not isinstance(path, str):
            raise ActionParseError("config_check action path must be a string when provided.", raw)
        max_files = parse_optional_positive_int(max_files, "max_files", raw, maximum=500) or 200
        return ConfigCheckAction(type="config_check", path=path, max_files=max_files)

    raise AssertionError(f"Unhandled read action type: {action_type!r}")

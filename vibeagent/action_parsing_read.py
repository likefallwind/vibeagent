from __future__ import annotations

from typing import Any

from .action_parsing_helpers import (
    ActionParseError,
    parse_optional_positive_int,
    parse_path_list,
)
from .action_parsing_read_files import READ_FILE_ACTION_TYPES, parse_read_file_action
from .action_parsing_read_navigation import READ_NAVIGATION_ACTION_TYPES, parse_read_navigation_action
from .action_parsing_read_output import READ_OUTPUT_ACTION_TYPES, parse_read_output_action
from .types import (
    CodeOutlineAction,
    ConfigCheckAction,
    FileInfoAction,
    ImageInfoAction,
    ViewImageAction,
    PythonCheckAction,
    PythonSymbolsAction,
)


READ_ACTION_TYPES = READ_NAVIGATION_ACTION_TYPES | READ_OUTPUT_ACTION_TYPES | READ_FILE_ACTION_TYPES | {
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

    navigation_action = parse_read_navigation_action(action_type, value, raw)
    if navigation_action is not None:
        return navigation_action
    output_action = parse_read_output_action(action_type, value, raw)
    if output_action is not None:
        return output_action
    file_action = parse_read_file_action(action_type, value, raw)
    if file_action is not None:
        return file_action

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

from __future__ import annotations

from .workspace_core import RunWorkspace
from .workspace_file_context import read_project_file_context_result, read_project_file_tail_result
from .workspace_file_helpers import (
    count_file_lines,
    detect_binary_file,
    format_line_excerpt,
    format_numbered_lines,
    parse_image_header,
    parse_jpeg_dimensions,
    parse_webp_dimensions,
    read_utf8_text_file,
    truncate_utf8_text_bytes,
)
from .workspace_output_contexts import (
    GENERIC_FILE_LINE_RE,
    PYTHON_EXCEPTION_SUMMARY_RE,
    PYTHON_TRACEBACK_LOCATION_RE,
    add_output_line_reference,
    classify_output_diagnostic_line,
    extract_output_line_references,
    is_url_reference_match,
    looks_like_project_source_reference,
    normalize_output_reference_path,
    read_output_contexts_result,
    read_output_diagnostics_result,
)
from .workspace_resolve import resolve_inside_run


def read_project_file(
    workspace: RunWorkspace,
    relative_path: str,
    max_bytes: int = 20_000,
    start_line: int | None = None,
    line_count: int | None = None,
) -> str:
    return str(
        read_project_file_result(
            workspace,
            relative_path,
            max_bytes=max_bytes,
            start_line=start_line,
            line_count=line_count,
        )["content"]
    )


def read_project_file_result(
    workspace: RunWorkspace,
    relative_path: str,
    max_bytes: int = 20_000,
    start_line: int | None = None,
    line_count: int | None = None,
    show_line_numbers: bool = False,
) -> dict[str, object]:
    if max_bytes < 1:
        raise ValueError("max_bytes must be at least 1.")
    if max_bytes > 200_000:
        raise ValueError("max_bytes must be at most 200000.")
    target = resolve_inside_run(workspace.root, relative_path)
    if not target.is_file():
        raise ValueError(f"File does not exist: {relative_path}")
    content = read_utf8_text_file(target, relative_path)
    total_bytes = len(content.encode("utf-8"))
    if start_line is not None:
        excerpt = format_line_excerpt(content, start_line, line_count or 200)
        excerpt_bytes = len(excerpt.encode("utf-8"))
        if excerpt_bytes > max_bytes:
            excerpt = f"{truncate_utf8_text_bytes(excerpt, max_bytes)}\n[file truncated]"
            return {
                "content": excerpt,
                "truncated": True,
                "total_bytes": total_bytes,
                "max_bytes": max_bytes,
            }
        return {
            "content": excerpt,
            "truncated": False,
            "total_bytes": total_bytes,
            "max_bytes": max_bytes,
        }
    if show_line_numbers:
        numbered = format_numbered_lines(content, start_line=1)
        numbered_bytes = len(numbered.encode("utf-8"))
        if numbered_bytes <= max_bytes:
            return {
                "content": numbered,
                "truncated": False,
                "total_bytes": total_bytes,
                "max_bytes": max_bytes,
            }
        return {
            "content": f"{truncate_utf8_text_bytes(numbered, max_bytes)}\n[file truncated]",
            "truncated": True,
            "total_bytes": total_bytes,
            "max_bytes": max_bytes,
        }
    if total_bytes <= max_bytes:
        return {
            "content": content,
            "truncated": False,
            "total_bytes": total_bytes,
            "max_bytes": max_bytes,
        }
    return {
        "content": f"{truncate_utf8_text_bytes(content, max_bytes)}\n[file truncated]",
        "truncated": True,
        "total_bytes": total_bytes,
        "max_bytes": max_bytes,
    }


def read_project_file_info(workspace: RunWorkspace, relative_path: str) -> dict[str, object]:
    target = resolve_inside_run(workspace.root, relative_path)
    if not target.exists():
        return {
            "path": relative_path,
            "ok": False,
            "exists": False,
            "is_file": False,
            "is_dir": False,
            "size_bytes": None,
            "line_count": None,
            "is_binary": None,
            "message": f"Path does not exist: {relative_path}",
        }

    is_file = target.is_file()
    is_dir = target.is_dir()
    size_bytes = target.stat().st_size if is_file else None
    is_binary = detect_binary_file(target) if is_file else None
    line_count = count_file_lines(target) if is_file and is_binary is False else None
    kind = "file" if is_file else "directory" if is_dir else "path"
    return {
        "path": relative_path,
        "ok": True,
        "exists": True,
        "is_file": is_file,
        "is_dir": is_dir,
        "size_bytes": size_bytes,
        "line_count": line_count,
        "is_binary": is_binary,
        "message": f"Inspected {kind}: {relative_path}",
    }


def read_project_image_info(workspace: RunWorkspace, relative_path: str) -> dict[str, object]:
    target = resolve_inside_run(workspace.root, relative_path)
    if not target.exists():
        return {
            "path": relative_path,
            "ok": False,
            "exists": False,
            "is_file": False,
            "size_bytes": None,
            "format": None,
            "mime_type": None,
            "width": None,
            "height": None,
            "message": f"Path does not exist: {relative_path}",
        }
    if not target.is_file():
        return {
            "path": relative_path,
            "ok": False,
            "exists": True,
            "is_file": False,
            "size_bytes": None,
            "format": None,
            "mime_type": None,
            "width": None,
            "height": None,
            "message": f"Path is not a file: {relative_path}",
        }

    size_bytes = target.stat().st_size
    with target.open("rb") as handle:
        data = handle.read(1_048_576)

    image_format, mime_type, width, height = parse_image_header(data)
    ok = image_format is not None and width is not None and height is not None
    if ok:
        message = f"Inspected {image_format} image: {relative_path}"
    elif image_format is not None:
        message = f"Could not determine {image_format} dimensions: {relative_path}"
    else:
        message = f"Unsupported or unrecognized image format: {relative_path}"

    return {
        "path": relative_path,
        "ok": ok,
        "exists": True,
        "is_file": True,
        "size_bytes": size_bytes,
        "format": image_format,
        "mime_type": mime_type,
        "width": width,
        "height": height,
        "message": message,
    }


def read_project_image_payload(workspace: RunWorkspace, relative_path: str, max_bytes: int = 5_000_000) -> dict[str, object]:
    if max_bytes < 1 or max_bytes > 5_000_000:
        raise ValueError("max_bytes must be between 1 and 5000000.")
    info = read_project_image_info(workspace, relative_path)
    if not info["ok"]:
        raise ValueError(str(info["message"]))
    size_bytes = int(info["size_bytes"])
    if size_bytes > max_bytes:
        raise ValueError(f"Image exceeds max_bytes ({size_bytes} > {max_bytes}): {relative_path}")
    target = resolve_inside_run(workspace.root, relative_path)
    with target.open("rb") as handle:
        data = handle.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise ValueError(f"Image exceeds max_bytes: {relative_path}")
    return {**info, "data": data, "max_bytes": max_bytes}

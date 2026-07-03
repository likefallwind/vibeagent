from __future__ import annotations

import re
from pathlib import Path

from .workspace_core import RunWorkspace
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


def read_project_file_tail_result(
    workspace: RunWorkspace,
    relative_path: str,
    line_count: int = 80,
    max_bytes: int = 20_000,
) -> dict[str, object]:
    if line_count < 1:
        raise ValueError("line_count must be at least 1.")
    if line_count > 1000:
        raise ValueError("line_count must be at most 1000.")
    if max_bytes < 1000:
        raise ValueError("max_bytes must be at least 1000.")
    if max_bytes > 200_000:
        raise ValueError("max_bytes must be at most 200000.")
    target = resolve_inside_run(workspace.root, relative_path)
    if not target.is_file():
        raise ValueError(f"File does not exist: {relative_path}")

    content = read_utf8_text_file(target, relative_path)
    lines = content.splitlines()
    total_lines = len(lines)
    start_line = max(1, total_lines - line_count + 1) if total_lines else 1
    excerpt = format_line_excerpt(content, start_line, line_count) if total_lines else ""
    truncated_by_lines = total_lines > line_count
    excerpt_bytes = len(excerpt.encode("utf-8"))
    truncated_by_bytes = excerpt_bytes > max_bytes
    if truncated_by_bytes:
        excerpt = f"{truncate_utf8_text_bytes(excerpt, max_bytes)}\n[file tail truncated]"

    returned_lines = 0 if not excerpt else len(excerpt.splitlines())
    return {
        "content": excerpt,
        "start_line": start_line,
        "line_count": returned_lines,
        "requested_line_count": line_count,
        "total_lines": total_lines,
        "truncated": truncated_by_lines or truncated_by_bytes,
        "max_bytes": max_bytes,
    }


def read_project_file_context_result(
    workspace: RunWorkspace,
    relative_path: str,
    line: int,
    context_lines: int = 20,
    max_bytes: int = 20_000,
) -> dict[str, object]:
    if line < 1:
        raise ValueError("line must be at least 1.")
    if context_lines < 0:
        raise ValueError("context_lines must be at least 0.")
    if context_lines > 500:
        raise ValueError("context_lines must be at most 500.")
    if max_bytes < 1000:
        raise ValueError("max_bytes must be at least 1000.")
    if max_bytes > 200_000:
        raise ValueError("max_bytes must be at most 200000.")
    target = resolve_inside_run(workspace.root, relative_path)
    if not target.is_file():
        raise ValueError(f"File does not exist: {relative_path}")

    content = read_utf8_text_file(target, relative_path)
    lines = content.splitlines()
    total_lines = len(lines)
    if total_lines == 0:
        excerpt = ""
        start_line = 1
        returned_lines = 0
        end_line = 0
    else:
        start_line = max(1, line - context_lines)
        end_line = min(total_lines, line + context_lines)
        requested_count = min(1000, max(0, end_line - start_line + 1))
        end_line = start_line + requested_count - 1 if requested_count else start_line - 1
        excerpt = format_line_excerpt(content, start_line, requested_count) if requested_count else ""
        returned_lines = 0 if not excerpt else len(excerpt.splitlines())

    truncated_by_context = total_lines > returned_lines
    truncated_by_bytes = len(excerpt.encode("utf-8")) > max_bytes
    if truncated_by_bytes:
        excerpt = f"{truncate_utf8_text_bytes(excerpt, max_bytes)}\n[file context truncated]"
        returned_lines = len(excerpt.splitlines())

    return {
        "content": excerpt,
        "line": line,
        "context_lines": context_lines,
        "start_line": start_line,
        "end_line": end_line,
        "line_count": returned_lines,
        "total_lines": total_lines,
        "target_line_exists": 1 <= line <= total_lines,
        "truncated": truncated_by_context or truncated_by_bytes,
        "max_bytes": max_bytes,
    }


PYTHON_TRACEBACK_LOCATION_RE = re.compile(r'File "([^"\n]+)", line ([1-9][0-9]*)')
PYTHON_EXCEPTION_SUMMARY_RE = re.compile(
    r"^(?:E\s+)?((?:[A-Za-z_]\w*\.)*(?:[A-Za-z_]\w*(?:Error|Exception|Warning|Failure|Fatal|Interrupt|Exit)"
    r"|AssertionError|KeyboardInterrupt|SystemExit|BaseException))(?::|\b)"
)
GENERIC_FILE_LINE_RE = re.compile(
    r"(?P<path>(?:[A-Za-z]:)?(?:\.{1,2}/|/)?[A-Za-z0-9_@%+=.,~/-]+)"
    r":(?P<line>[1-9][0-9]*)(?::(?P<column>[1-9][0-9]*))?"
)


def read_output_contexts_result(
    workspace: RunWorkspace,
    text: str,
    context_lines: int = 5,
    max_contexts: int = 20,
    max_bytes_per_context: int = 20_000,
) -> dict[str, object]:
    if not text or not text.strip():
        raise ValueError("text must not be empty.")
    if len(text) > 200_000:
        raise ValueError("text must be at most 200000 characters.")
    if context_lines < 0:
        raise ValueError("context_lines must be at least 0.")
    if context_lines > 500:
        raise ValueError("context_lines must be at most 500.")
    if max_contexts < 1:
        raise ValueError("max_contexts must be at least 1.")
    if max_contexts > 100:
        raise ValueError("max_contexts must be at most 100.")
    if max_bytes_per_context < 1000:
        raise ValueError("max_bytes_per_context must be at least 1000.")
    if max_bytes_per_context > 200_000:
        raise ValueError("max_bytes_per_context must be at most 200000.")

    references = extract_output_line_references(workspace, text)
    shown_references = references[:max_contexts]
    contexts: list[dict[str, object]] = []
    for reference in shown_references:
        normalized_path = str(reference["path"])
        line = int(reference["line"])
        try:
            context = read_project_file_context_result(
                workspace,
                normalized_path,
                line=line,
                context_lines=context_lines,
                max_bytes=max_bytes_per_context,
            )
            contexts.append(
                {
                    "path": normalized_path,
                    "line": line,
                    "column": reference["column"],
                    "raw": reference["raw"],
                    "ok": True,
                    "content": context["content"],
                    "message": f"Read {normalized_path} around line {line}.",
                    "context_lines": context["context_lines"],
                    "start_line": context["start_line"],
                    "end_line": context["end_line"],
                    "line_count": context["line_count"],
                    "total_lines": context["total_lines"],
                    "target_line_exists": context["target_line_exists"],
                    "truncated": context["truncated"],
                    "max_bytes": context["max_bytes"],
                }
            )
        except ValueError as error:
            contexts.append(
                {
                    "path": normalized_path,
                    "line": line,
                    "column": reference["column"],
                    "raw": reference["raw"],
                    "ok": False,
                    "content": "",
                    "message": str(error),
                    "context_lines": context_lines,
                    "start_line": 1,
                    "end_line": 0,
                    "line_count": 0,
                    "total_lines": None,
                    "target_line_exists": False,
                    "truncated": False,
                    "max_bytes": max_bytes_per_context,
                }
            )

    return {
        "contexts": contexts,
        "total_refs": len(references),
        "truncated": len(references) > len(shown_references),
        "message": f"Read {sum(1 for item in contexts if item['ok'])}/{len(contexts)} output context(s) from {len(references)} reference(s).",
    }


def read_output_diagnostics_result(
    workspace: RunWorkspace,
    text: str,
    context_lines: int = 2,
    max_diagnostics: int = 50,
    max_contexts: int = 20,
    max_bytes_per_context: int = 20_000,
) -> dict[str, object]:
    if not text or not text.strip():
        raise ValueError("text must not be empty.")
    if len(text) > 200_000:
        raise ValueError("text must be at most 200000 characters.")
    if context_lines < 0:
        raise ValueError("context_lines must be at least 0.")
    if context_lines > 500:
        raise ValueError("context_lines must be at most 500.")
    if max_diagnostics < 1:
        raise ValueError("max_diagnostics must be at least 1.")
    if max_diagnostics > 200:
        raise ValueError("max_diagnostics must be at most 200.")

    contexts_result = read_output_contexts_result(
        workspace,
        text,
        context_lines=context_lines,
        max_contexts=max_contexts,
        max_bytes_per_context=max_bytes_per_context,
    )

    diagnostics: list[dict[str, object]] = []
    for output_line, raw_line in enumerate(text.splitlines(), start=1):
        stripped = raw_line.strip()
        if not stripped:
            continue
        references = extract_output_line_references(workspace, raw_line)
        severity = classify_output_diagnostic_line(stripped)
        if severity is None and not references:
            continue
        reference = references[0] if references else None
        diagnostics.append(
            {
                "severity": severity or "info",
                "output_line": output_line,
                "text": truncate_utf8_text_bytes(stripped, 1_000),
                "path": str(reference["path"]) if reference else None,
                "line": int(reference["line"]) if reference else None,
                "column": int(reference["column"]) if reference and reference["column"] is not None else None,
                "raw": str(reference["raw"]) if reference else None,
            }
        )

    shown_diagnostics = diagnostics[:max_diagnostics]
    ok_contexts = sum(1 for item in contexts_result["contexts"] if isinstance(item, dict) and item.get("ok"))
    return {
        "diagnostics": shown_diagnostics,
        "contexts": contexts_result["contexts"],
        "total_diagnostics": len(diagnostics),
        "total_refs": contexts_result["total_refs"],
        "diagnostics_truncated": len(diagnostics) > len(shown_diagnostics),
        "contexts_truncated": contexts_result["truncated"],
        "message": (
            f"Found {len(diagnostics)} diagnostic line(s) and {contexts_result['total_refs']} file reference(s); "
            f"read {ok_contexts}/{len(contexts_result['contexts'])} referenced context(s)."
        ),
    }


def classify_output_diagnostic_line(line: str) -> str | None:
    lowered = line.lower()
    if "warning" in lowered or re.search(r"(^|[^a-z])warn(?:ing)?[:\s]", lowered):
        return "warning"
    python_exception = PYTHON_EXCEPTION_SUMMARY_RE.match(line)
    if python_exception:
        return "warning" if python_exception.group(1).endswith("Warning") else "error"
    if "traceback" in lowered or "exception" in lowered or "fatal" in lowered or re.search(r"(^|[^a-z])error[:\s]", lowered):
        return "error"
    if re.search(r"(^|[^a-z])(failed|failure|failures|failing)[:\s]", lowered):
        return "failure"
    return None


def extract_output_line_references(workspace: RunWorkspace, text: str) -> list[dict[str, object]]:
    references: list[dict[str, object]] = []
    seen: set[tuple[str, int, int | None]] = set()

    for match in PYTHON_TRACEBACK_LOCATION_RE.finditer(text):
        add_output_line_reference(
            workspace,
            references,
            seen,
            raw_path=match.group(1),
            line_text=match.group(2),
            column_text=None,
            raw=match.group(0),
        )

    for match in GENERIC_FILE_LINE_RE.finditer(text):
        if is_url_reference_match(text, match.start()):
            continue
        raw_path = match.group("path")
        if not looks_like_project_source_reference(raw_path):
            continue
        add_output_line_reference(
            workspace,
            references,
            seen,
            raw_path=raw_path,
            line_text=match.group("line"),
            column_text=match.group("column"),
            raw=match.group(0),
        )
    return references


def is_url_reference_match(text: str, start: int) -> bool:
    return "://" in text[max(0, start - 12) : start]


def add_output_line_reference(
    workspace: RunWorkspace,
    references: list[dict[str, object]],
    seen: set[tuple[str, int, int | None]],
    raw_path: str,
    line_text: str,
    column_text: str | None,
    raw: str,
) -> None:
    try:
        line = int(line_text)
        column = int(column_text) if column_text else None
    except ValueError:
        return
    normalized_path = normalize_output_reference_path(workspace, raw_path)
    if normalized_path is None:
        return
    key = (normalized_path, line, column)
    if key in seen:
        return
    seen.add(key)
    references.append({"path": normalized_path, "line": line, "column": column, "raw": raw})


def normalize_output_reference_path(workspace: RunWorkspace, raw_path: str) -> str | None:
    cleaned = raw_path.strip().strip("'\"`()[]{}<>,")
    if not cleaned or "://" in cleaned or cleaned.startswith(("http://", "https://")):
        return None
    path = Path(cleaned)
    if path.is_absolute():
        try:
            return path.resolve().relative_to(workspace.root.resolve()).as_posix()
        except ValueError:
            return None
    normalized = path.as_posix()
    if normalized.startswith("./"):
        normalized = normalized[2:]
    if not normalized or normalized.startswith("../") or normalized == "..":
        return None
    return normalized


def looks_like_project_source_reference(raw_path: str) -> bool:
    if "://" in raw_path or raw_path.startswith(("http://", "https://")):
        return False
    path = raw_path.replace("\\", "/")
    if path in {".", ".."}:
        return False
    if "/" in path or path.startswith("."):
        return True
    suffix = Path(path).suffix.lower()
    return suffix in {
        ".py",
        ".js",
        ".jsx",
        ".ts",
        ".tsx",
        ".go",
        ".rs",
        ".java",
        ".kt",
        ".c",
        ".cc",
        ".cpp",
        ".h",
        ".hpp",
        ".json",
        ".toml",
        ".yaml",
        ".yml",
        ".md",
        ".css",
        ".html",
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

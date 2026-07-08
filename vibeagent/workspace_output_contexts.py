from __future__ import annotations

from pathlib import Path
import re

from .workspace_core import RunWorkspace
from .workspace_file_context import read_project_file_context_result
from .workspace_file_helpers import truncate_utf8_text_bytes


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


__all__ = [
    "GENERIC_FILE_LINE_RE",
    "PYTHON_EXCEPTION_SUMMARY_RE",
    "PYTHON_TRACEBACK_LOCATION_RE",
    "add_output_line_reference",
    "classify_output_diagnostic_line",
    "extract_output_line_references",
    "is_url_reference_match",
    "looks_like_project_source_reference",
    "normalize_output_reference_path",
    "read_output_contexts_result",
    "read_output_diagnostics_result",
]

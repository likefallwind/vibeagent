from __future__ import annotations

from pathlib import Path

from .workspace_core import PROJECT_INSTRUCTION_CONTENT_LIMIT, RunWorkspace
from .workspace_instruction_rules import (
    InstructionDocument,
    discover_path_instruction_documents,
    discover_instruction_documents,
    instruction_document_sort_key,
    matching_instruction_documents,
    startup_instruction_documents,
)
from .workspace_instruction_state import claim_unloaded_instruction_documents
from .workspace_instruction_state import DEFAULT_INSTRUCTION_CONSUMER


def read_project_instructions(workspace: RunWorkspace, max_bytes: int = 12_000, max_files: int = 20) -> str | None:
    metadata = read_project_instruction_sources(workspace, max_bytes=max_bytes, max_files=max_files)
    text = str(metadata["text"])
    return text if text.strip() else None


def read_project_instruction_sources(
    workspace: RunWorkspace,
    max_bytes: int = 12_000,
    max_files: int = 20,
) -> dict[str, object]:
    _validate_instruction_limits(max_bytes, max_files)
    documents = discover_instruction_documents(workspace)
    scanned = documents[:max_files]
    included_paths = {document.path for document in startup_instruction_documents(scanned)}
    text, text_truncated = _format_instruction_documents(
        [document for document in scanned if document.path in included_paths],
        max_bytes,
    )
    omitted_files = max(0, len(documents) - len(scanned))
    if omitted_files:
        text, omitted_truncated = _append_bounded(
            text,
            f"[{omitted_files} additional project instruction file(s) omitted]",
            max_bytes,
        )
        text_truncated = text_truncated or omitted_truncated
    return {
        "ok": not any(document.error for document in scanned),
        "files": [_source_metadata(document, document.path in included_paths) for document in scanned],
        "total_files": len(documents),
        "scanned_files": len(scanned),
        "omitted_files": omitted_files,
        "truncated": text_truncated or bool(omitted_files),
        "text": text,
        "message": (
            f"Loaded {len(included_paths)} startup instruction file(s); discovered {len(documents)} total source(s)."
            if documents
            else "No project instruction files found."
        ),
    }


def read_path_instruction_context(
    workspace: RunWorkspace,
    relative_paths: list[str],
    *,
    max_bytes: int = 12_000,
    max_files: int = 20,
    claim: bool = True,
    consumer_id: str = DEFAULT_INSTRUCTION_CONSUMER,
) -> dict[str, object]:
    _validate_instruction_limits(max_bytes, max_files)
    documents = discover_path_instruction_documents(workspace, relative_paths)
    matching = matching_instruction_documents(documents, relative_paths)
    selected = matching[:max_files]
    if claim:
        selected = claim_unloaded_instruction_documents(workspace, selected, consumer_id)
    text, text_truncated = _format_instruction_documents(selected, max_bytes)
    omitted_files = max(0, len(matching) - min(len(matching), max_files))
    return {
        "ok": True,
        "paths": list(dict.fromkeys(relative_paths)),
        "consumer": consumer_id,
        "files": [_source_metadata(document, True) for document in selected],
        "total_files": len(matching),
        "scanned_files": min(len(matching), max_files),
        "omitted_files": omitted_files,
        "truncated": text_truncated or bool(omitted_files),
        "text": text,
        "message": (
            f"Loaded {len(selected)} new path-scoped instruction file(s)."
            if selected
            else "No new path-scoped instructions loaded."
        ),
    }


def project_instruction_scope(relative_path: str) -> str:
    path = Path(relative_path)
    if path.parts[:2] == (".claude", "rules") or path == Path(".claude") / "CLAUDE.md":
        return "."
    scope = path.parent.as_posix()
    return "." if scope == "." else scope


def project_instruction_sort_key(relative_path: str) -> tuple[int, int, str]:
    document = InstructionDocument(
        path=relative_path,
        scope=project_instruction_scope(relative_path),
        content="",
        bytes=0,
        chars=0,
    )
    return instruction_document_sort_key(document)


def _source_metadata(document: InstructionDocument, included: bool) -> dict[str, object]:
    if document.error is not None:
        message = document.error
    elif document.empty:
        message = "Instruction file is empty."
    elif included:
        message = "Included."
    elif document.patterns:
        message = "Deferred until a matching project file is read."
    else:
        message = "Deferred until a file in this scope is read."
    return {
        "path": document.path,
        "scope": document.scope,
        "bytes": document.bytes,
        "chars": document.chars,
        "empty": document.empty,
        "included": included,
        "message": message,
        "reason": document.reason,
        "patterns": list(document.patterns),
    }


def _format_instruction_documents(documents: list[InstructionDocument], max_bytes: int) -> tuple[str, bool]:
    chunks = [
        "\n".join(
            [
                f"File: {document.path}",
                f"Scope: {document.scope}",
                "Instructions:",
                document.content,
            ]
        )
        for document in documents
        if document.error is None and not document.empty
    ]
    combined = "\n\n".join(chunks)
    encoded = combined.encode("utf-8")
    if len(encoded) <= max_bytes:
        return combined, False
    return _truncate_utf8(encoded, max_bytes) + "\n[project instructions truncated]", True


def _append_bounded(current: str, suffix: str, max_bytes: int) -> tuple[str, bool]:
    combined = f"{current}\n\n{suffix}" if current else suffix
    encoded = combined.encode("utf-8")
    if len(encoded) <= max_bytes:
        return combined, False
    return _truncate_utf8(encoded, max_bytes), True


def _truncate_utf8(encoded: bytes, max_bytes: int) -> str:
    bounded = encoded[:max_bytes]
    while bounded:
        try:
            return bounded.decode("utf-8")
        except UnicodeDecodeError:
            bounded = bounded[:-1]
    return ""


def _validate_instruction_limits(max_bytes: int, max_files: int) -> None:
    if max_bytes < 1:
        raise ValueError("max_bytes must be at least 1.")
    if max_bytes > PROJECT_INSTRUCTION_CONTENT_LIMIT:
        raise ValueError(f"max_bytes must be at most {PROJECT_INSTRUCTION_CONTENT_LIMIT}.")
    if max_files < 1:
        raise ValueError("max_files must be at least 1.")
    if max_files > 200:
        raise ValueError("max_files must be at most 200.")


__all__ = [
    "project_instruction_scope",
    "project_instruction_sort_key",
    "read_path_instruction_context",
    "read_project_instruction_sources",
    "read_project_instructions",
]

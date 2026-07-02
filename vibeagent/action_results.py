from __future__ import annotations

from .session import command_output_tail, read_session_events, session_command_entries, session_dir
from .types import (
    CodeRenamePreviewFile,
    CodeRenameReplacement,
    PythonRenamePreviewFile,
    PythonRenameReplacement,
    ReferenceContextResult,
)
from .workspace import read_project_file_context_result
from .workspace_core import RunWorkspace


def parse_session_search_counts(text: str) -> tuple[int, int]:
    total_matches = 0
    shown_matches = 0
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("matches:"):
            raw_total = stripped.split(":", 1)[1].strip()
            if raw_total.isdigit():
                total_matches = int(raw_total)
        elif stripped.startswith("shown:"):
            raw_shown = stripped.split(":", 1)[1].strip().split("/", 1)[0]
            if raw_shown.isdigit():
                shown_matches = int(raw_shown)
    return total_matches, shown_matches


def parse_session_commands_counts(text: str) -> tuple[int, int]:
    command_count = 0
    shown_commands = 0
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("commands:"):
            raw_total = stripped.split(":", 1)[1].strip()
            if raw_total.isdigit():
                command_count = int(raw_total)
        elif stripped.startswith("shown:"):
            raw_shown = stripped.split(":", 1)[1].strip().split("/", 1)[0]
            if raw_shown.isdigit():
                shown_commands = int(raw_shown)
    return command_count, shown_commands


def build_session_command_output_scan_text(
    workspace: RunWorkspace,
    run_id: str,
    max_commands: int,
    max_output_chars: int,
) -> tuple[bool, int, int, str, str]:
    current_session_dir = session_dir(workspace.root, run_id)
    if not current_session_dir.is_dir():
        return False, 0, 0, "", f"Session not found: {run_id}"

    entries = session_command_entries(read_session_events(workspace.root, run_id))
    shown_entries = entries[-max_commands:]
    chunks: list[str] = []
    for entry in shown_entries:
        result = entry["result"]
        command = result.get("command")
        header = f"# {entry['kind']}[{entry['index']}] command: {command if isinstance(command, str) else 'unknown'}"
        stdout = command_output_tail(result.get("stdout") if isinstance(result.get("stdout"), str) else "", max_output_chars)
        stderr = command_output_tail(result.get("stderr") if isinstance(result.get("stderr"), str) else "", max_output_chars)
        chunks.append("\n".join([header, "stdout:", stdout, "stderr:", stderr]))
    return True, len(entries), len(shown_entries), "\n\n".join(chunks), (
        f"Scanned {len(shown_entries)}/{len(entries)} command result(s) from session {run_id}."
    )


def parse_session_files_counts(text: str) -> tuple[int, int]:
    file_count = 0
    shown_files = 0
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("files:"):
            raw_total = stripped.split(":", 1)[1].strip()
            if raw_total.isdigit():
                file_count = int(raw_total)
        elif stripped.startswith("shown:"):
            raw_shown = stripped.split(":", 1)[1].strip().split("/", 1)[0]
            if raw_shown.isdigit():
                shown_files = int(raw_shown)
    return file_count, shown_files


def parse_session_failures_counts(text: str) -> tuple[int, int]:
    failure_count = 0
    shown_failures = 0
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("failures:"):
            raw_total = stripped.split(":", 1)[1].strip()
            if raw_total.isdigit():
                failure_count = int(raw_total)
        elif stripped.startswith("shown:"):
            raw_shown = stripped.split(":", 1)[1].strip().split("/", 1)[0]
            if raw_shown.isdigit():
                shown_failures = int(raw_shown)
    return failure_count, shown_failures


def build_reference_context_results(
    workspace: RunWorkspace,
    references: list[dict[str, object]],
    symbol: str,
    context_lines: int,
    max_bytes_per_context: int,
) -> list[ReferenceContextResult]:
    contexts: list[ReferenceContextResult] = []
    for reference in references:
        path = str(reference["path"])
        line = int(reference["line"])
        context = read_project_file_context_result(
            workspace,
            path,
            line=line,
            context_lines=context_lines,
            max_bytes=max_bytes_per_context,
        )
        contexts.append(
            ReferenceContextResult(
                path=path,
                line=line,
                column=int(reference.get("column", 0)),
                symbol=str(reference.get("symbol", symbol)),
                kind=str(reference.get("kind", "reference")),
                language=str(reference["language"]) if reference.get("language") is not None else None,
                matched_line=str(reference.get("context", "")),
                content=str(context["content"]),
                context_lines=int(context["context_lines"]),
                start_line=int(context["start_line"]),
                end_line=int(context["end_line"]),
                line_count=int(context["line_count"]),
                total_lines=int(context["total_lines"]) if context["total_lines"] is not None else None,
                truncated=bool(context["truncated"]),
                max_bytes=int(context["max_bytes"]),
            )
        )
    return contexts


def build_python_rename_preview_files(preview: dict[str, object]) -> list[PythonRenamePreviewFile]:
    return [
        PythonRenamePreviewFile(
            path=str(file["path"]),
            replacements=[
                PythonRenameReplacement(**replacement)
                for replacement in list(file["replacements"])
            ],
            diff=str(file["diff"]),
            truncated=bool(file["truncated"]),
        )
        for file in list(preview["files"])
    ]


def build_code_rename_preview_files(preview: dict[str, object]) -> list[CodeRenamePreviewFile]:
    return [
        CodeRenamePreviewFile(
            path=str(file["path"]),
            language=str(file["language"]),
            replacements=[
                CodeRenameReplacement(**replacement)
                for replacement in list(file["replacements"])
            ],
            diff=str(file["diff"]),
            truncated=bool(file["truncated"]),
        )
        for file in list(preview["files"])
    ]

from __future__ import annotations

from pathlib import Path

from .workspace_core import (
    PROJECT_INSTRUCTION_CONTENT_LIMIT,
    PROJECT_INSTRUCTION_FILE_NAMES,
    RunWorkspace,
)
from .workspace_search_files import list_files


def read_project_instructions(workspace: RunWorkspace, max_bytes: int = 12_000, max_files: int = 20) -> str | None:
    metadata = read_project_instruction_sources(workspace, max_bytes=max_bytes, max_files=max_files)
    text = str(metadata["text"])
    return text if text.strip() else None


def read_project_instruction_sources(
    workspace: RunWorkspace,
    max_bytes: int = 12_000,
    max_files: int = 20,
) -> dict[str, object]:
    if max_bytes < 1:
        raise ValueError("max_bytes must be at least 1.")
    if max_bytes > PROJECT_INSTRUCTION_CONTENT_LIMIT:
        raise ValueError(f"max_bytes must be at most {PROJECT_INSTRUCTION_CONTENT_LIMIT}.")
    if max_files < 1:
        raise ValueError("max_files must be at least 1.")
    if max_files > 200:
        raise ValueError("max_files must be at most 200.")

    instruction_files = sorted(
        (file for file in list_files(workspace.root) if Path(file).name in PROJECT_INSTRUCTION_FILE_NAMES),
        key=project_instruction_sort_key,
    )
    scanned_files = instruction_files[:max_files]
    sources: list[dict[str, object]] = []
    chunks: list[str] = []
    for relative_path in scanned_files:
        instructions_path = workspace.root / relative_path
        try:
            content = instructions_path.read_text(encoding="utf-8")
        except UnicodeDecodeError as error:
            sources.append(
                {
                    "path": relative_path,
                    "scope": project_instruction_scope(relative_path),
                    "bytes": instructions_path.stat().st_size,
                    "chars": 0,
                    "empty": False,
                    "included": False,
                    "message": f"Instruction file is not valid UTF-8: {error}",
                }
            )
            continue
        included = bool(content.strip())
        sources.append(
            {
                "path": relative_path,
                "scope": project_instruction_scope(relative_path),
                "bytes": len(content.encode("utf-8")),
                "chars": len(content),
                "empty": not included,
                "included": included,
                "message": "Included." if included else "Instruction file is empty.",
            }
        )
        if included:
            chunks.append(
                "\n".join(
                    [
                        f"File: {relative_path}",
                        f"Scope: {project_instruction_scope(relative_path)}",
                        "Instructions:",
                        content,
                    ]
                )
            )

    omitted_files = max(0, len(instruction_files) - len(scanned_files))
    if omitted_files:
        chunks.append(f"[{omitted_files} additional project instruction file(s) omitted]")

    combined = "\n\n".join(chunks)
    text_truncated = len(combined) > max_bytes
    text = f"{combined[:max_bytes]}\n[project instructions truncated]" if text_truncated else combined
    return {
        "ok": True,
        "files": sources,
        "total_files": len(instruction_files),
        "scanned_files": len(scanned_files),
        "omitted_files": omitted_files,
        "truncated": text_truncated or bool(omitted_files),
        "text": text,
        "message": (
            f"Read {len(scanned_files)}/{len(instruction_files)} project instruction file(s)."
            if instruction_files
            else "No project instruction files found."
        ),
    }


def project_instruction_scope(relative_path: str) -> str:
    scope = Path(relative_path).parent.as_posix()
    return "." if scope == "." else scope


def project_instruction_sort_key(relative_path: str) -> tuple[int, str, int, str]:
    path = Path(relative_path)
    scope = project_instruction_scope(relative_path)
    file_order = {"AGENTS.md": 0, "CLAUDE.md": 1}.get(path.name, 2)
    return len(path.parts), scope, file_order, relative_path

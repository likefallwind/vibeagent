from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shlex

from .workspace_resolve import resolve_inside_run


@dataclass(frozen=True)
class ProcessStdinArgument:
    process_id: str | None
    content: str | None
    stdin_file: str | None = None


def read_project_stdin_file(project_root: str | Path, relative_path: str, option_name: str) -> str:
    path = resolve_inside_run(project_root, relative_path)
    if not path.exists():
        raise ValueError(f"{option_name} does not exist: {relative_path}")
    if not path.is_file():
        raise ValueError(f"{option_name} is not a file: {relative_path}")
    return path.read_text(encoding="utf-8")


def parse_process_stdin_file_argument(
    argument: str,
    *,
    project_root: str | Path,
    option_name: str = "--stdin-file",
) -> ProcessStdinArgument:
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        raise ValueError(str(error)) from error

    process_id: str | None = None
    content_parts: list[str] = []
    stdin_file: str | None = None
    index = 0
    while index < len(parts):
        part = parts[index]
        if part == "--":
            content_parts.extend(parts[index + 1 :])
            break
        if part == option_name or part.startswith(f"{option_name}="):
            if stdin_file is not None:
                raise ValueError(f"provide {option_name} at most once.")
            if part.startswith(f"{option_name}="):
                stdin_file = part.split("=", 1)[1]
                index += 1
            else:
                if index + 1 >= len(parts):
                    raise ValueError(f"{option_name} requires a value.")
                stdin_file = parts[index + 1]
                index += 2
            if stdin_file == "":
                raise ValueError(f"{option_name} must be a non-empty path.")
            continue
        if part.startswith("--"):
            raise ValueError(f"Unknown option: {part}")
        if process_id is None:
            process_id = part
        else:
            content_parts.append(part)
        index += 1

    content = " ".join(content_parts) if content_parts else None
    if stdin_file is not None and content is not None:
        raise ValueError(f"text and {option_name} cannot be used together.")
    if stdin_file is not None:
        content = read_project_stdin_file(project_root, stdin_file, option_name)
    return ProcessStdinArgument(process_id=process_id, content=content, stdin_file=stdin_file)
